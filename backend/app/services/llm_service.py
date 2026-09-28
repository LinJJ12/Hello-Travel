"""LLM服务模块。"""

from __future__ import annotations

from hello_agents import HelloAgentsLLM

from ..config import get_settings
from ..core.logging import get_logger

logger = get_logger(__name__)

# 全局 LLM 实例
_llm_instance: HelloAgentsLLM | None = None


def get_llm() -> HelloAgentsLLM:
    """获取 LLM 实例（单例模式）。"""
    global _llm_instance

    if _llm_instance is None:
        settings = get_settings()
        _llm_instance = HelloAgentsLLM(
            api_key=settings.resolved_llm_api_key or None,
            base_url=settings.resolved_llm_base_url,
            model=settings.resolved_llm_model,
        )
        logger.info("LLM 服务初始化完成 (provider=%s, model=%s)", _llm_instance.provider, _llm_instance.model)

    return _llm_instance


def reset_llm() -> None:
    """重置 LLM 实例（用于测试或重新配置）。"""
    global _llm_instance
    _llm_instance = None
