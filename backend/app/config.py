"""配置管理模块。"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

from .core.logging import get_logger, setup_logging

logger = get_logger(__name__)

# 加载环境变量（.env 位于 backend/ 目录）
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_FILE)

# 兼容旧布局：如果存在同级 HelloAgents/.env，也加载（不覆盖已有变量）
_helloagents_env = Path(__file__).resolve().parent.parent.parent.parent / "HelloAgents" / ".env"
if _helloagents_env.exists():
    load_dotenv(_helloagents_env, override=False)


class Settings(BaseSettings):
    """应用配置。"""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        case_sensitive=False,
        extra="ignore",
    )

    # 应用基本配置
    app_name: str = "HelloAgents智能旅行助手"
    app_version: str = "1.1.0"
    debug: bool = False
    environment: str = "local"

    # 服务器配置
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS 配置（逗号分隔）
    cors_origins: str = (
        "http://localhost:5173,http://localhost:3000,"
        "http://127.0.0.1:5173,http://127.0.0.1:3000"
    )

    # 高德地图 API 配置
    amap_api_key: str = ""

    # Unsplash API 配置
    unsplash_access_key: str = ""
    unsplash_secret_key: str = ""

    # LLM 配置（兼容 LLM_* 与 OPENAI_* 两套命名）
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model_id: str = "gpt-4"
    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = ""

    # 日志配置
    log_level: str = "INFO"

    # 高德结果缓存时长（秒），设为 0 可关闭缓存
    amap_cache_ttl: float = 600.0

    # 是否在非 local 环境隐藏 API 文档
    show_docs_environments: str = "local,dev,staging"

    def get_cors_origins_list(self) -> list[str]:
        """获取 CORS origins 列表。"""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def resolved_llm_api_key(self) -> str:
        """按优先级解析 LLM API Key。"""
        return self.llm_api_key or self.openai_api_key or os.getenv("OPENAI_API_KEY", "")

    @property
    def resolved_llm_base_url(self) -> str:
        return (
            self.llm_base_url
            or self.openai_base_url
            or os.getenv("OPENAI_BASE_URL", "")
            or "https://api.openai.com/v1"
        )

    @property
    def resolved_llm_model(self) -> str:
        return self.llm_model_id or self.openai_model or os.getenv("OPENAI_MODEL", "") or "gpt-4"

    @property
    def docs_enabled(self) -> bool:
        allowed = {item.strip().lower() for item in self.show_docs_environments.split(",")}
        return self.environment.strip().lower() in allowed


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """获取配置单例（进程内只解析一次）。"""
    return Settings()


def validate_config(settings: Settings | None = None) -> bool:
    """校验必要配置，缺失必需项时抛出 ``ValueError``。"""
    settings = settings or get_settings()
    errors: list[str] = []
    warnings: list[str] = []

    if not settings.amap_api_key:
        errors.append("AMAP_API_KEY 未配置（高德地图服务不可用）")

    if not settings.resolved_llm_api_key:
        warnings.append("LLM_API_KEY / OPENAI_API_KEY 未配置，LLM 相关功能不可用")

    if errors:
        raise ValueError("配置错误:\n" + "\n".join(f"  - {e}" for e in errors))

    for warning in warnings:
        logger.warning("配置警告: %s", warning)

    return True


def log_config_summary(settings: Settings | None = None) -> None:
    """以日志形式打印当前配置（不泄露密钥明文）。"""
    settings = settings or get_settings()
    logger.info("应用: %s v%s (env=%s)", settings.app_name, settings.app_version, settings.environment)
    logger.info("服务器: %s:%s", settings.host, settings.port)
    logger.info("高德地图 Key: %s", "已配置" if settings.amap_api_key else "未配置")
    logger.info("LLM Key: %s", "已配置" if settings.resolved_llm_api_key else "未配置")
    logger.info("LLM Base URL: %s", settings.resolved_llm_base_url)
    logger.info("LLM Model: %s", settings.resolved_llm_model)
    logger.info("Unsplash Key: %s", "已配置" if settings.unsplash_access_key else "未配置")
    logger.info("日志级别: %s", settings.log_level)


def init_config() -> Settings:
    """初始化日志并返回配置（供应用启动时调用）。"""
    settings = get_settings()
    setup_logging(settings.log_level)
    return settings


# 向后兼容旧接口
def print_config() -> None:
    log_config_summary()


# 创建全局配置实例（兼容既有 `from ..config import settings` 的用法）
settings = get_settings()
