"""AI 行程问答路由。

合并说明：用统一结构化日志替代原实现散落的 ``print``。
"""

from fastapi import APIRouter, HTTPException

from ...core.logging import get_logger
from ...models.schemas import TripChatRequest, TripChatResponse
from ...services.chat_service import chat_with_trip_context

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["AI问答"])


@router.post(
    "/ask",
    response_model=TripChatResponse,
    summary="行程智能问答",
    description="根据当前旅行计划上下文,回答用户关于行程的问题"
)
async def ask_about_trip(request: TripChatRequest):
    """AI 行程问答。"""
    try:
        logger.info("💬 收到行程问答: %s...", request.message[:50])

        # 将 history 转换为 dict 列表
        history = [{"role": m.role, "content": m.content} for m in (request.history or [])]

        reply = await chat_with_trip_context(
            message=request.message,
            trip_plan_dict=request.trip_plan,
            history=history,
        )

        logger.info("✅ AI 回复: %s...", reply[:80])

        return TripChatResponse(
            success=True,
            reply=reply,
        )

    except Exception as e:  # noqa: BLE001
        logger.exception("❌ 行程问答失败: %s", e)
        raise HTTPException(status_code=500, detail=f"AI问答服务异常: {e!s}") from e
