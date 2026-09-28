"""旅行规划API路由。"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException

from ...agents.trip_planner_agent import get_trip_planner_agent
from ...core.constants import ErrorCode
from ...core.job_store import JobStore
from ...core.logging import get_logger
from ...models.schemas import TripPlanResponse, TripRequest

logger = get_logger(__name__)

router = APIRouter(prefix="/trip", tags=["旅行规划"])

# 异步任务存储（带 TTL 回收，避免内存无限增长）
_job_store = JobStore()

# 各阶段进度提示，供前端轮询展示
_PROGRESS_STAGES = [
    (20, "采集景点与坐标", "正在检索目的地景点与真实坐标"),
    (45, "查询天气", "正在获取目的地天气与温度"),
    (65, "搜索酒店", "正在匹配住宿偏好与酒店位置"),
    (85, "生成每日行程", "正在编排每日节奏、餐饮与预算"),
]


def _run_plan_job(job_id: str, request: TripRequest) -> None:
    """同步执行行程生成并将结果写入任务存储（在线程池中运行）。"""
    try:
        _job_store.set(
            job_id,
            {
                "status": "pending",
                "stage": "生成行程",
                "progress": 70,
                "message": "正在调用旅行规划 Agent 生成每日行程",
            },
        )
        agent = get_trip_planner_agent()
        trip_plan = agent.plan_trip(request)
        response = TripPlanResponse(success=True, message="旅行计划生成成功", data=trip_plan)
        _job_store.set(
            job_id,
            {
                "status": "done",
                "stage": "完成",
                "progress": 100,
                "message": "旅行计划生成成功",
                "response": response.model_dump(),
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("异步行程任务 %s 失败: %s", job_id, exc)
        _job_store.set(job_id, {"status": "failed", "error": str(exc)})


async def _run_plan_job_async(job_id: str, request: TripRequest) -> None:
    """异步包装器：把同步任务放到线程池，避免阻塞事件循环。"""
    try:
        await asyncio.to_thread(_run_plan_job, job_id, request)
    except Exception as exc:  # noqa: BLE001
        logger.exception("异步行程任务 %s 异常: %s", job_id, exc)
        _job_store.set(job_id, {"status": "failed", "error": str(exc)})


@router.post(
    "/plan",
    response_model=TripPlanResponse,
    summary="生成旅行计划（同步）",
    description="根据用户输入的旅行需求,生成详细的旅行计划。耗时较长,建议前端使用 /plan_async。",
)
def plan_trip(request: TripRequest) -> TripPlanResponse:
    """生成旅行计划。

    注意：这里刻意使用同步 ``def`` —— 内部是高德 / LLM 的阻塞式 I/O，
    FastAPI 会自动把它放进线程池执行，从而不会阻塞事件循环。
    """
    logger.info("收到同步规划请求: %s (%s天)", request.city, request.travel_days)
    try:
        agent = get_trip_planner_agent()
        trip_plan = agent.plan_trip(request)
        return TripPlanResponse(success=True, message="旅行计划生成成功", data=trip_plan)
    except Exception as exc:  # noqa: BLE001
        logger.exception("生成旅行计划失败: %s", exc)
        raise HTTPException(
            status_code=500,
            detail={"code": ErrorCode.UPSTREAM_ERROR, "message": f"生成旅行计划失败: {exc}"},
        ) from exc


@router.post("/plan_async", summary="异步生成旅行计划", description="异步生成旅行计划，立即返回 job_id")
async def plan_trip_async(request: TripRequest) -> dict[str, Any]:
    """异步接口：返回 job_id，实际任务在后台执行。"""
    job_id = str(uuid.uuid4())
    _job_store.set(
        job_id,
        {"status": "pending", "stage": "排队", "progress": 10, "message": "任务已创建，正在准备规划资源"},
    )
    asyncio.create_task(_run_plan_job_async(job_id, request))
    return {"job_id": job_id, "status": "pending", "stages": [s[1] for s in _PROGRESS_STAGES]}


@router.get("/plan_result/{job_id}", summary="查询异步行程结果")
async def get_plan_result(job_id: str) -> dict[str, Any]:
    """查询异步任务结果。"""
    entry = _job_store.get(job_id)
    if entry is None:
        raise HTTPException(
            status_code=404,
            detail={"code": ErrorCode.NOT_FOUND, "message": "job_id 未找到或已过期"},
        )

    status = entry.get("status")
    if status == "pending":
        return {
            "status": "pending",
            "stage": entry.get("stage", "处理中"),
            "progress": entry.get("progress", 50),
            "message": entry.get("message", "正在生成旅行计划"),
        }
    if status == "done":
        return entry.get("response", {})
    raise HTTPException(
        status_code=500,
        detail={"code": ErrorCode.UPSTREAM_ERROR, "message": entry.get("error", "任务执行失败")},
    )


@router.get("/health", summary="健康检查", description="检查旅行规划服务是否正常")
async def health_check() -> dict[str, Any]:
    """健康检查：报告 LLM 与地图服务可用性。"""
    try:
        agent = get_trip_planner_agent()
        return {
            "status": "healthy",
            "service": "trip-planner",
            "llm_model": agent.llm.model,
            "amap_configured": bool(agent.amap_service.api_key),
            "pending_jobs": len(_job_store),
        }
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=503,
            detail={"code": ErrorCode.CONFIG_ERROR, "message": f"服务不可用: {exc}"},
        ) from exc
