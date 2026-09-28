"""旅行规划 API 路由 - WebSocket 同步 + 轮询兼容模式。

合并说明（相对 TripStar 原实现）：

- 内存任务表由「裸 dict」改为带 TTL 回收与容量上限的 ``JobStore``，避免进程
  长时间运行时任务状态无限堆积；磁盘持久化（历史计划）保持不变，内存被回收后
  仍可从磁盘回读；
- 全部 ``print`` 调试输出替换为统一结构化日志。
"""

import asyncio
import contextlib
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from ...agents.trip_planner_agent import get_trip_planner_agent
from ...core.constants import JOB_TTL_SECONDS
from ...core.job_store import JobStore
from ...core.logging import get_logger
from ...models.schemas import TripPlanResponse, TripRequest
from ...services.knowledge_graph_service import build_knowledge_graph

logger = get_logger(__name__)

router = APIRouter(prefix="/trip", tags=["旅行规划"])

# 内存任务存储：带 TTL 回收 + 容量上限（单实例部署足够）
_tasks: JobStore = JobStore(ttl=JOB_TTL_SECONDS, maxsize=256)
_FINAL_TASK_STATUS = {"completed", "failed"}
_TASKS_DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "trip_tasks"


def _create_task_state(task_id: str) -> dict[str, Any]:
    """初始化任务状态。"""
    return {
        "task_id": task_id,
        "plan_id": task_id,
        "status": "processing",
        "stage": "submitted",
        "progress": 0,
        "message": "任务已提交，等待执行...",
        "result": None,
        "error": None,
        "request_payload": None,
        "subscribers": [],  # list[asyncio.Queue]
    }


def _serialize_result(result: Any) -> Any:
    if result is None:
        return None
    if hasattr(result, "model_dump"):
        return result.model_dump(mode="json")
    return result


def _task_file_path(task_id: str) -> Path:
    """获取任务持久化文件路径。"""
    return _TASKS_DATA_DIR / f"{task_id}.json"


def _normalize_loaded_task(task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """将磁盘中的任务结构恢复为内存可用格式。"""
    task = _create_task_state(task_id)
    task.update(
        {
            "plan_id": payload.get("plan_id", task_id),
            "status": payload.get("status", "failed"),
            "stage": payload.get("stage", "failed"),
            "progress": payload.get("progress", 100),
            "message": payload.get("message", ""),
            "result": payload.get("result"),
            "error": payload.get("error"),
            "request_payload": payload.get("request_payload"),
        }
    )
    task["subscribers"] = []

    # 服务重启后，处理中任务无法恢复执行，直接标记为失败，避免前端无限等待。
    if task["status"] not in _FINAL_TASK_STATUS:
        task["status"] = "failed"
        task["stage"] = "failed"
        task["progress"] = 100
        task["error"] = "服务已重启，未完成的旅行规划任务无法恢复，请重新生成。"
        task["message"] = task["error"]

    return task


def _persist_task_state(task_id: str, task: dict[str, Any]) -> None:
    """将任务状态持久化到本地 JSON 文件。"""
    try:
        _TASKS_DATA_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "task_id": task_id,
            "plan_id": task.get("plan_id", task_id),
            "status": task.get("status", "processing"),
            "stage": task.get("stage", ""),
            "progress": task.get("progress", 0),
            "message": task.get("message", ""),
            "result": _serialize_result(task.get("result")),
            "error": task.get("error"),
            "request_payload": task.get("request_payload"),
        }
        target = _task_file_path(task_id)
        tmp = target.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        tmp.replace(target)
    except Exception as e:  # noqa: BLE001
        logger.warning("持久化任务 %s 失败: %s", task_id, e)


def _load_task_from_disk(task_id: str) -> dict[str, Any] | None:
    """从磁盘加载单个任务。"""
    path = _task_file_path(task_id)
    if not path.exists():
        return None

    try:
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
        if not isinstance(payload, dict):
            return None
        task = _normalize_loaded_task(task_id, payload)
        _tasks.set(task_id, task)
        return task
    except Exception as e:  # noqa: BLE001
        logger.warning("读取任务 %s 失败: %s", task_id, e)
        return None


def _load_persisted_tasks() -> None:
    """服务启动时预加载历史任务。"""
    if not _TASKS_DATA_DIR.exists():
        return

    loaded = 0
    for path in sorted(_TASKS_DATA_DIR.glob("*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                payload = json.load(f)
            if not isinstance(payload, dict):
                continue
            task_id = str(payload.get("task_id") or path.stem)
            _tasks.set(task_id, _normalize_loaded_task(task_id, payload))
            loaded += 1
        except Exception as e:  # noqa: BLE001
            logger.warning("加载历史任务 %s 失败: %s", path.name, e)

    if loaded:
        logger.info("📦 已加载 %s 个持久化旅行任务", loaded)


def _get_task(task_id: str) -> dict[str, Any] | None:
    """优先从内存读取任务，不存在时回退到磁盘。"""
    return _tasks.get(task_id) or _load_task_from_disk(task_id)


def _build_history_item(task_id: str, payload: dict[str, Any], updated_at: str) -> dict[str, Any] | None:
    """从持久化任务中提取首页历史列表所需的摘要。"""
    if payload.get("status") != "completed":
        return None

    result = payload.get("result") or {}
    plan = result.get("data") or {}
    request_payload = payload.get("request_payload") or {}

    city = plan.get("city") or request_payload.get("city") or ""
    cities = plan.get("cities") or []
    start_date = plan.get("start_date") or request_payload.get("start_date") or ""
    end_date = plan.get("end_date") or request_payload.get("end_date") or ""
    days = plan.get("days") or []
    travel_days = request_payload.get("travel_days") or (len(days) if isinstance(days, list) else 0)
    overall_suggestions = plan.get("overall_suggestions") or result.get("message") or ""

    if not city and not cities:
        return None

    # 多城市时 city 显示为 "北京 → 西安" 形式
    display_city = " → ".join(cities) if len(cities) > 1 else city

    return {
        "plan_id": payload.get("plan_id", task_id),
        "task_id": task_id,
        "city": display_city,
        "cities": cities,
        "start_date": start_date,
        "end_date": end_date,
        "travel_days": travel_days,
        "updated_at": updated_at,
        "overall_suggestions": overall_suggestions,
    }


def _load_history_items(limit: int = 10) -> list[dict[str, Any]]:
    """按最近更新时间返回已完成的历史计划摘要。"""
    if not _TASKS_DATA_DIR.exists():
        return []

    items: list[dict[str, Any]] = []
    for path in sorted(_TASKS_DATA_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            with open(path, encoding="utf-8") as f:
                payload = json.load(f)
            if not isinstance(payload, dict):
                continue
            updated_at = datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
            item = _build_history_item(str(payload.get("task_id") or path.stem), payload, updated_at)
            if item:
                items.append(item)
            if len(items) >= limit:
                break
        except Exception as e:  # noqa: BLE001
            logger.warning("读取历史任务 %s 失败: %s", path.name, e)

    return items


def _build_task_event(task_id: str, task: dict[str, Any], include_result: bool = True) -> dict[str, Any]:
    """从任务状态构建对前端可消费的事件对象。"""
    event = {
        "task_id": task_id,
        "plan_id": task.get("plan_id", task_id),
        "status": task.get("status", "processing"),
        "stage": task.get("stage", ""),
        "progress": task.get("progress", 0),
        "message": task.get("message", ""),
    }
    if task.get("error"):
        event["error"] = task["error"]
    if task.get("status") == "failed" and task.get("request_payload") is not None:
        event["request_payload"] = task["request_payload"]
    if include_result and task.get("result") is not None:
        event["result"] = _serialize_result(task["result"])
    return event


def _broadcast_task_event(task_id: str, event: dict[str, Any]) -> None:
    """将任务事件广播给当前所有 WebSocket 订阅者。"""
    task = _tasks.get(task_id)
    if not task:
        return

    dead_queues = []
    for queue in task.get("subscribers", []):
        try:
            queue.put_nowait(event)
        except Exception:  # noqa: BLE001
            dead_queues.append(queue)

    if dead_queues:
        task["subscribers"] = [q for q in task.get("subscribers", []) if q not in dead_queues]


async def _update_task_state(
    task_id: str,
    *,
    status: str | None = None,
    stage: str | None = None,
    progress: int | None = None,
    message: str | None = None,
    result: Any = None,
    error: str | None = None,
) -> None:
    """更新任务状态并广播事件。"""
    task = _tasks.get(task_id)
    if not task:
        return

    if status is not None:
        task["status"] = status
    if stage is not None:
        task["stage"] = stage
    if progress is not None:
        task["progress"] = progress
    if message is not None:
        task["message"] = message
    if result is not None:
        task["result"] = result
    if error is not None:
        task["error"] = error

    _persist_task_state(task_id, task)
    event = _build_task_event(task_id, task, include_result=True)
    _broadcast_task_event(task_id, event)


@router.post(
    "/plan",
    summary="提交旅行规划任务",
    description="异步提交旅行规划请求，立即返回 task_id；可通过 WebSocket 或 /trip/status/{task_id} 获取执行状态",
)
async def plan_trip(request: TripRequest):
    """提交旅行规划任务（立即返回 task_id）。"""
    task_id = str(uuid.uuid4())[:8]
    state = _create_task_state(task_id)
    state["request_payload"] = request.model_dump(mode="json")
    _tasks.set(task_id, state)
    _persist_task_state(task_id, state)

    _city_display = " → ".join(cs.city for cs in request.cities) if request.cities else request.city
    logger.info(
        "📥 收到旅行规划请求 (task_id=%s): 城市=%s 日期=%s~%s 天数=%s",
        task_id,
        _city_display,
        request.start_date,
        request.end_date,
        request.travel_days,
    )

    await _update_task_state(
        task_id,
        status="processing",
        stage="submitted",
        progress=5,
        message="任务已提交，正在初始化流程...",
    )

    # 启动后台任务
    asyncio.create_task(_run_trip_planning(task_id, request))

    return {
        "task_id": task_id,
        "plan_id": task_id,
        "status": "processing",
        "ws_url": f"/api/trip/ws/{task_id}",
        "message": f"任务已提交，可通过 WebSocket /api/trip/ws/{task_id} 实时订阅状态",
    }


async def _save_preferences_after_trip(user_id: str, request: TripRequest, trip_plan) -> None:
    """行程生成成功后，异步提取用户偏好并写入记忆库（失败不影响主流程）"""
    try:
        from ...memory import MemoryManager, PreferenceExtractor

        user_query = (
            f"城市: {request.city}; "
            f"偏好: {', '.join(request.preferences) if request.preferences else '无'}; "
            f"额外要求: {request.free_text_input or '无'}"
        )
        if hasattr(trip_plan, "model_dump"):
            trip_content = json.dumps(trip_plan.model_dump(mode="json"), ensure_ascii=False)
        else:
            trip_content = str(trip_plan)

        extractor = PreferenceExtractor()
        prefs = await extractor.extract_preferences(user_query, trip_content)
        mm = MemoryManager.get_instance()
        for content, score in prefs:
            await mm.add_memory(user_id, content, source="implicit", init_weight=score)
        logger.info("🧠 用户 %s 偏好记忆已更新，新增/合并 %s 条", user_id[:8], len(prefs))
    except Exception as e:  # noqa: BLE001
        logger.warning("偏好记忆提取失败: %s", e)


async def _run_trip_planning(task_id: str, request: TripRequest):
    """后台执行旅行规划并推送进度。"""
    try:
        await _update_task_state(
            task_id,
            status="processing",
            stage="initializing",
            progress=10,
            message="正在获取多智能体系统实例...",
        )
        agent = get_trip_planner_agent()

        async def progress_callback(stage: str, message: str, progress: int) -> None:
            await _update_task_state(
                task_id,
                status="processing",
                stage=stage,
                progress=progress,
                message=message,
            )

        trip_plan = await agent.plan_trip(request, progress_callback=progress_callback)

        # 异步提取用户偏好到记忆库（不阻塞主流程）
        _user_id = (getattr(request, "user_id", "") or "").strip()
        if _user_id and os.getenv("ENABLE_USER_MEMORY", "false").lower() == "true":
            asyncio.create_task(_save_preferences_after_trip(_user_id, request, trip_plan))

        await _update_task_state(
            task_id,
            status="processing",
            stage="graph_building",
            progress=95,
            message="正在构建知识图谱...",
        )
        graph_data = build_knowledge_graph(trip_plan, language=getattr(request, "language", "zh") or "zh")

        trip_result = TripPlanResponse(
            success=True,
            message="旅行计划生成成功",
            plan_id=task_id,
            data=trip_plan,
            graph_data=graph_data,
        )

        logger.info("✅ 任务 %s 完成", task_id)
        await _update_task_state(
            task_id,
            status="completed",
            stage="completed",
            progress=100,
            message="旅行计划生成成功",
            result=trip_result,
        )

    except Exception as e:  # noqa: BLE001
        logger.exception("❌ 任务 %s 失败: %s", task_id, e)

        # 针对小红书 Cookie 过期异常做出特殊处理返回给前端
        try:
            from ...services.xhs_service import XHSCookieExpiredError

            error_msg = f"【认证失败】{e!s}" if isinstance(e, XHSCookieExpiredError) else str(e)
        except ImportError:
            error_msg = str(e)

        await _update_task_state(
            task_id,
            status="failed",
            stage="failed",
            progress=100,
            message=error_msg,
            error=error_msg,
        )


@router.websocket("/ws/{task_id}")
async def trip_task_ws(websocket: WebSocket, task_id: str):
    """WebSocket 订阅任务状态。"""
    await websocket.accept()
    task = _get_task(task_id)
    if not task:
        await websocket.send_json(
            {
                "task_id": task_id,
                "plan_id": task_id,
                "status": "failed",
                "stage": "failed",
                "progress": 100,
                "message": "任务不存在",
                "error": "任务不存在",
            }
        )
        await websocket.close(code=1008)
        return

    queue: asyncio.Queue = asyncio.Queue()
    task["subscribers"].append(queue)

    # 先发送快照，保证前端后连也能同步当前状态
    snapshot = _build_task_event(task_id, task, include_result=True)
    await websocket.send_json(snapshot)
    if snapshot["status"] in _FINAL_TASK_STATUS:
        with contextlib.suppress(Exception):
            await websocket.close()
        task["subscribers"] = [q for q in task.get("subscribers", []) if q is not queue]
        return

    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event)
            if event.get("status") in _FINAL_TASK_STATUS:
                break
    except WebSocketDisconnect:
        pass
    finally:
        task = _tasks.get(task_id)
        if task:
            task["subscribers"] = [q for q in task.get("subscribers", []) if q is not queue]
        with contextlib.suppress(Exception):
            await websocket.close()


@router.get(
    "/history",
    summary="最近历史计划",
    description="返回最近成功生成的旅行计划摘要，供首页快速找回历史计划",
)
async def get_trip_history(limit: int = 10):
    """查询最近的历史计划摘要。"""
    safe_limit = max(1, min(int(limit or 10), 50))
    return {
        "items": _load_history_items(safe_limit),
    }


@router.get(
    "/status/{task_id}",
    summary="查询任务状态",
    description="轮询旅行规划任务的执行状态和结果（兼容旧客户端）",
)
async def get_task_status(task_id: str):
    """查询任务执行状态。"""
    task = _get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task["status"] == "completed":
        return {
            "task_id": task_id,
            "plan_id": task.get("plan_id", task_id),
            "status": "completed",
            "result": _serialize_result(task.get("result")),
        }
    if task["status"] == "failed":
        return {
            "task_id": task_id,
            "plan_id": task.get("plan_id", task_id),
            "status": "failed",
            "error": task.get("error", ""),
            "request_payload": task.get("request_payload"),
        }
    return {
        "task_id": task_id,
        "plan_id": task.get("plan_id", task_id),
        "status": "processing",
        "stage": task.get("stage", ""),
        "progress": task.get("progress", 0),
        "progress_text": task.get("message", "处理中..."),
    }


@router.get(
    "/health",
    summary="健康检查",
    description="检查旅行规划服务是否正常",
)
async def health_check():
    """健康检查。"""
    try:
        agent = get_trip_planner_agent()
        return {
            "status": "healthy",
            "service": "trip-planner",
            "agent_name": agent.planner_agent.name,
            "tools_count": len(agent.weather_agent.list_tools()) + len(agent.hotel_agent.list_tools()),
        }
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"服务不可用: {e!s}") from e


_load_persisted_tasks()
