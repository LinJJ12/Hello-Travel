"""配置管理模块。

在 TripStar 原有「环境变量 + 运行时覆盖（前端设置页热更新）」双层配置之上，
合并了 Hello-Travel 的工程化改进：

- 统一结构化日志（``setup_logging`` / ``get_logger``），替代散落的 ``print``；
- 引入 ``environment`` 与 ``docs_enabled``，非公开环境自动隐藏交互文档；
- 新增 ``amap_cache_ttl``，供高德 REST 服务复用 TTL 缓存。

注意：``validate_config`` 刻意保持「只告警不抛错」。本项目的密钥支持在
前端设置页运行时填写，若启动即因缺少密钥而抛错，会破坏「先启动、后配置」
的体验。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .core.logging import get_logger, setup_logging

logger = get_logger(__name__)

# 加载环境变量：优先 backend/.env，其次当前工作目录 .env（不覆盖已有值）
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_FILE)
load_dotenv(override=False)

# 兼容旧布局：如果存在同级 HelloAgents/.env，也加载（不覆盖已有变量）
helloagents_env = Path(__file__).resolve().parent.parent.parent.parent / "HelloAgents" / ".env"
if helloagents_env.exists():
    load_dotenv(helloagents_env, override=False)


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        case_sensitive=False,
        extra="ignore",
    )

    # 应用基本配置
    app_name: str = "旅途星辰 TripStar"
    app_version: str = "2.2.0"
    debug: bool = False
    environment: str = "local"

    # 服务器配置
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS配置 - 使用字符串,在代码中分割
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"

    # 高德地图API配置
    vite_amap_web_key: str = ""
    vite_amap_web_js_key: str = ""

    # Google Maps API配置
    google_maps_api_key: str = ""
    google_maps_proxy: str = ""

    # 小红书配置
    xhs_cookie: str = ""

    # LLM配置 (从环境变量读取,由HelloAgents管理)
    openai_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("OPENAI_API_KEY", "LLM_API_KEY"),
    )
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        validation_alias=AliasChoices("OPENAI_BASE_URL", "LLM_BASE_URL"),
    )
    openai_model: str = Field(
        default="gpt-4",
        validation_alias=AliasChoices("OPENAI_MODEL", "LLM_MODEL_ID"),
    )

    # 日志配置
    log_level: str = "INFO"

    # 高德结果缓存时长（秒），设为 0 可关闭缓存
    amap_cache_ttl: float = 600.0

    # 允许展示 API 文档的环境（逗号分隔）
    show_docs_environments: str = "local,dev,staging"

    def get_cors_origins_list(self) -> list[str]:
        """获取CORS origins列表"""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def docs_enabled(self) -> bool:
        """当前环境是否允许暴露 /docs、/redoc 与 openapi.json。"""
        allowed = {item.strip().lower() for item in self.show_docs_environments.split(",")}
        return self.environment.strip().lower() in allowed


# 创建全局配置实例
settings = Settings()
# 运行时配置的持久化位置。允许用环境变量覆盖：
# - 测试时指向临时目录，避免读取开发者本地配置导致用例结果不确定；
# - 多实例部署时可指向共享/独立卷。
_RUNTIME_SETTINGS_FILE = Path(
    os.getenv("RUNTIME_SETTINGS_FILE")
    or Path(__file__).resolve().parent.parent / "runtime_settings.json"
)
_RUNTIME_SETTING_KEYS = {
    "vite_amap_web_key",
    "vite_amap_web_js_key",
    "google_maps_api_key",
    "google_maps_proxy",
    "xhs_cookie",
    "openai_api_key",
    "openai_base_url",
    "openai_model",
}


def _load_runtime_overrides() -> dict[str, Any]:
    """加载本地持久化的运行时配置覆盖项。"""
    if not _RUNTIME_SETTINGS_FILE.exists():
        return {}
    try:
        with open(_RUNTIME_SETTINGS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return {k: data[k] for k in _RUNTIME_SETTING_KEYS if k in data}
    except Exception as exc:  # noqa: BLE001
        logger.warning("读取运行时配置失败，已回退到环境变量: %s", exc)
    return {}


def _persist_runtime_overrides(overrides: dict[str, Any]) -> None:
    """持久化运行时配置覆盖项。"""
    _RUNTIME_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_RUNTIME_SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(overrides, f, ensure_ascii=False, indent=2)


def _sync_env_from_settings() -> None:
    """将运行时配置同步到环境变量，兼容读取 env 的第三方组件。"""
    if settings.openai_api_key:
        os.environ["OPENAI_API_KEY"] = settings.openai_api_key
        os.environ["LLM_API_KEY"] = settings.openai_api_key
    if settings.openai_base_url:
        os.environ["OPENAI_BASE_URL"] = settings.openai_base_url
        os.environ["LLM_BASE_URL"] = settings.openai_base_url
    if settings.openai_model:
        os.environ["OPENAI_MODEL"] = settings.openai_model
        os.environ["LLM_MODEL_ID"] = settings.openai_model


def _apply_runtime_overrides(overrides: dict[str, Any]) -> None:
    """将覆盖项应用到全局 settings 实例。"""
    for key, value in overrides.items():
        if key in _RUNTIME_SETTING_KEYS and hasattr(settings, key):
            setattr(settings, key, value if value is not None else "")
    _sync_env_from_settings()


_runtime_overrides = _load_runtime_overrides()
_apply_runtime_overrides(_runtime_overrides)

_SECRET_SETTING_KEYS = {
    "openai_api_key",
    "xhs_cookie",
    "vite_amap_web_key",
}
_MASK_CHAR = "\u2022"


def _mask_secret(value: str) -> str:
    """返回不可还原掩码，仅保留少量首尾字符供用户辨认。"""
    if not value:
        return ""
    if len(value) <= 8:
        return _MASK_CHAR * 8
    return f"{value[:4]}{_MASK_CHAR * 8}{value[-4:]}"


def get_settings() -> Settings:
    """获取配置实例"""
    return settings


def get_runtime_settings() -> dict[str, str]:
    """获取当前运行时配置（供前端设置页读取）。

    机密字段以掩码返回；进程内部需要真实值时直接读取 settings。
    """
    raw = {
        "vite_amap_web_key": settings.vite_amap_web_key or "",
        "vite_amap_web_js_key": settings.vite_amap_web_js_key or "",
        "google_maps_api_key": settings.google_maps_api_key or "",
        "google_maps_proxy": settings.google_maps_proxy or "",
        "xhs_cookie": settings.xhs_cookie or "",
        "openai_api_key": settings.openai_api_key or "",
        "openai_base_url": settings.openai_base_url or "",
        "openai_model": settings.openai_model or "",
    }
    return {
        key: _mask_secret(value) if key in _SECRET_SETTING_KEYS else value
        for key, value in raw.items()
    }


def update_runtime_settings(updates: dict[str, Any]) -> dict[str, str]:
    """更新并持久化运行时配置。"""
    global _runtime_overrides

    normalized: dict[str, str] = {}
    for key, value in updates.items():
        if key not in _RUNTIME_SETTING_KEYS:
            continue
        text = str(value).strip() if value is not None else ""
        # 前端保存未修改的密码框时可能原样回传掩码；这时保持后端真实值不变。
        if _MASK_CHAR in text:
            continue
        normalized[key] = text

    _runtime_overrides.update(normalized)
    _persist_runtime_overrides(_runtime_overrides)
    _apply_runtime_overrides(_runtime_overrides)
    return get_runtime_settings()


def validate_config(settings_obj: Settings | None = None) -> bool:
    """校验配置完整性。

    仅记录告警，不抛异常——密钥支持在前端设置页运行时补充。
    """
    settings_obj = settings_obj or settings
    warnings: list[str] = []

    if not settings_obj.vite_amap_web_key:
        warnings.append("VITE_AMAP_WEB_KEY 未配置，地理编码 / POI / 天气 / 路线等功能不可用")

    llm_api_key = (
        settings_obj.openai_api_key
        or os.getenv("LLM_API_KEY")
        or os.getenv("OPENAI_API_KEY")
    )
    if not llm_api_key:
        warnings.append("LLM API Key 未配置，AI 生成功能不可用")

    if not settings_obj.xhs_cookie:
        warnings.append("XHS_COOKIE 未配置，小红书景点与图片功能不可用")

    for warning in warnings:
        logger.warning("配置警告: %s", warning)

    return True


def log_config_summary(settings_obj: Settings | None = None) -> None:
    """以日志形式输出当前配置（不泄露密钥明文）。"""
    settings_obj = settings_obj or settings
    logger.info("应用: %s v%s (env=%s)", settings_obj.app_name, settings_obj.app_version, settings_obj.environment)
    logger.info("服务器: %s:%s", settings_obj.host, settings_obj.port)
    logger.info("高德地图 Web Key: %s", "已配置" if settings_obj.vite_amap_web_key else "未配置")
    logger.info("高德地图 JS Key: %s", "已配置" if settings_obj.vite_amap_web_js_key else "未配置")
    logger.info("Google Maps Key: %s", "已配置" if settings_obj.google_maps_api_key else "未配置")
    logger.info("Google Maps 代理: %s", settings_obj.google_maps_proxy or "未配置")
    logger.info("小红书 Cookie: %s", "已配置" if settings_obj.xhs_cookie else "未配置")

    llm_api_key = (
        settings_obj.openai_api_key
        or os.getenv("LLM_API_KEY")
        or os.getenv("OPENAI_API_KEY")
    )
    logger.info("LLM API Key: %s", "已配置" if llm_api_key else "未配置")
    logger.info("LLM Base URL: %s", settings_obj.openai_base_url)
    logger.info("LLM Model: %s", settings_obj.openai_model)
    logger.info("日志级别: %s", settings_obj.log_level)


def init_config() -> Settings:
    """初始化日志并返回配置（供应用启动时调用）。"""
    setup_logging(settings.log_level)
    return settings


# 向后兼容旧接口
def print_config() -> None:
    log_config_summary()
