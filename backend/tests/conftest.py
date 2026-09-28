"""pytest 全局配置。

在导入应用之前注入测试用环境变量，避免 ``validate_config`` 因缺少密钥而告警，
并确保测试不读取真实 ``.env``。

同时把任务持久化目录与**运行时配置文件**都重定向到临时目录：
后者若不隔离，开发者本地 ``backend/runtime_settings.json``（例如在前端设置页
保存过配置）会覆盖 ``settings``，导致用例结果依赖本机状态、时好时坏。
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

# 让 tests 能 import app
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# 必须在导入 app.config 之前设置
os.environ.setdefault("VITE_AMAP_WEB_KEY", "test-amap-web-key")
os.environ.setdefault("VITE_AMAP_WEB_JS_KEY", "test-amap-js-key")
os.environ.setdefault("LLM_API_KEY", "test-llm-key")
os.environ.setdefault("LLM_BASE_URL", "https://example.invalid/v1")
os.environ.setdefault("LLM_MODEL_ID", "test-model")
os.environ.setdefault("XHS_COOKIE", "a1=test; web_session=test")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("ENVIRONMENT", "local")
# 记忆模块默认关闭，保证 /api/memory/* 走「未开启」分支
os.environ.setdefault("ENABLE_USER_MEMORY", "false")
# 运行时配置隔离：指向一次性临时目录，避免读到开发者本地配置
os.environ.setdefault(
    "RUNTIME_SETTINGS_FILE",
    str(Path(tempfile.mkdtemp(prefix="tripstar-test-")) / "runtime_settings.json"),
)

from app import config as app_config  # noqa: E402

# 记录导入期的干净状态，供每个用例前恢复（防止某个用例改了配置后污染后续用例）
_CLEAN_RUNTIME_KEYS = {
    key: getattr(app_config.settings, key) for key in app_config._RUNTIME_SETTING_KEYS
}
# _sync_env_from_settings 会回写这些环境变量，同样需要还原
_SYNCED_ENV_KEYS = (
    "OPENAI_API_KEY",
    "LLM_API_KEY",
    "OPENAI_BASE_URL",
    "LLM_BASE_URL",
    "OPENAI_MODEL",
    "LLM_MODEL_ID",
)
_CLEAN_ENV = {key: os.environ.get(key) for key in _SYNCED_ENV_KEYS}


@pytest.fixture(autouse=True)
def _isolate_runtime_state(tmp_path, monkeypatch):
    """每个用例前把运行时配置恢复为导入期状态，并重定向持久化文件。"""
    monkeypatch.setattr(app_config, "_RUNTIME_SETTINGS_FILE", tmp_path / "runtime_settings.json")
    monkeypatch.setattr(app_config, "_runtime_overrides", {})
    for key, value in _CLEAN_RUNTIME_KEYS.items():
        setattr(app_config.settings, key, value)
    for key, value in _CLEAN_ENV.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    yield


@pytest.fixture(autouse=True)
def _isolate_task_storage(tmp_path, monkeypatch):
    """把所有任务落盘路径重定向到临时目录。"""
    from app.api.routes import trip as trip_routes

    monkeypatch.setattr(trip_routes, "_TASKS_DATA_DIR", tmp_path / "trip_tasks")
    yield
