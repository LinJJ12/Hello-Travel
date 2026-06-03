"""旅行规划API路由"""

from fastapi import APIRouter, HTTPException
from ...models.schemas import (
    TripRequest,
    TripPlanResponse,
    ErrorResponse
)
from ...agents.trip_planner_agent import get_trip_planner_agent
import asyncio
import uuid
from typing import Dict, Any

router = APIRouter(prefix="/trip", tags=["旅行规划"])

# 简单的内存任务队列 (非持久化)
_job_store: Dict[str, Dict[str, Any]] = {}


def _start_background_plan(job_id: str, request: TripRequest):
    """同步执行行程生成并将结果存入任务存储（用于在线程中运行）。"""
    try:
        _job_store[job_id] = {
            "status": "pending",
            "stage": "生成行程",
            "progress": 70,
            "message": "正在调用旅行规划 Agent 生成每日行程"
        }
        agent = get_trip_planner_agent()
        trip_plan = agent.plan_trip(request)

        resp = TripPlanResponse(success=True, message="旅行计划生成成功", data=trip_plan)
        _job_store[job_id] = {
            "status": "done",
            "stage": "完成",
            "progress": 100,
            "message": "旅行计划生成成功",
            "response": resp.dict()
        }
    except Exception as e:
        # 记录异常信息，方便前端查看
        _job_store[job_id] = {"status": "failed", "error": str(e)}


async def _start_background_plan_async(job_id: str, request: TripRequest):
    """异步包装器：在后台线程执行同步任务并捕获异常。"""
    try:
        await asyncio.to_thread(_start_background_plan, job_id, request)
    except Exception as e:
        _job_store[job_id] = {"status": "failed", "error": str(e)}


@router.post(
    "/plan",
    response_model=TripPlanResponse,
    summary="生成旅行计划",
    description="根据用户输入的旅行需求,生成详细的旅行计划"
)
async def plan_trip(request: TripRequest):
    """
    生成旅行计划

    Args:
        request: 旅行请求参数

    Returns:
        旅行计划响应
    """
    try:
        print(f"\n{'='*60}")
        print(f"📥 收到旅行规划请求:")
        print(f"   城市: {request.city}")
        print(f"   日期: {request.start_date} - {request.end_date}")
        print(f"   天数: {request.travel_days}")
        print(f"{'='*60}\n")

        # 获取Agent实例
        print("🔄 获取多智能体系统实例...")
        agent = get_trip_planner_agent()

        # 生成旅行计划
        print("🚀 开始生成旅行计划...")
        trip_plan = agent.plan_trip(request)

        print("✅ 旅行计划生成成功,准备返回响应\n")

        return TripPlanResponse(
            success=True,
            message="旅行计划生成成功",
            data=trip_plan
        )

    except Exception as e:
        print(f"❌ 生成旅行计划失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"生成旅行计划失败: {str(e)}"
        )



@router.post("/plan_async", summary="异步生成旅行计划", description="异步生成旅行计划，立即返回 job_id")
async def plan_trip_async(request: TripRequest):
    """异步接口：返回 job_id，实际任务在后台执行。"""
    job_id = str(uuid.uuid4())
    _job_store[job_id] = {
        "status": "pending",
        "stage": "排队",
        "progress": 10,
        "message": "任务已创建，正在准备规划资源"
    }

    # 使用 asyncio 在后台调度执行（在独立线程运行同步任务）
    asyncio.create_task(_start_background_plan_async(job_id, request))

    return {"job_id": job_id, "status": "pending"}


@router.get("/plan_result/{job_id}", summary="查询异步行程结果")
async def get_plan_result(job_id: str):
    """查询异步任务结果"""
    if job_id not in _job_store:
        raise HTTPException(status_code=404, detail="job_id 未找到")

    entry = _job_store[job_id]
    if entry.get("status") == "pending":
        return {
            "status": "pending",
            "stage": entry.get("stage", "处理中"),
            "progress": entry.get("progress", 50),
            "message": entry.get("message", "正在生成旅行计划")
        }
    if entry.get("status") == "done":
        return entry.get("response")
    # failed
    raise HTTPException(status_code=500, detail=entry.get("error", "任务执行失败"))


@router.get(
    "/health",
    summary="健康检查",
    description="检查旅行规划服务是否正常"
)
async def health_check():
    """健康检查"""
    try:
        # 检查Agent是否可用
        agent = get_trip_planner_agent()
        
        return {
            "status": "healthy",
            "service": "trip-planner",
            "agent_name": agent.agent.name,
            "tools_count": len(agent.agent.list_tools())
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"服务不可用: {str(e)}"
        )
