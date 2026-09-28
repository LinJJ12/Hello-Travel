"""pytest 全局配置。

在导入应用之前注入测试用环境变量，避免 ``validate_config`` 因缺少密钥而告警，
并确保测试不读取真实 ``.env``。

同时把任务持久化目录重定向到临时目录，避免测试在仓库里留下
``backend/data/trip_tasks`` 垃圾文件。
"""

from __future__ import annotations

import os
import sys
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


@pytest.fixture(autouse=True)
def _isolate_task_storage(tmp_path, monkeypatch):
    """把所有任务落盘路径重定向到临时目录。"""
    from app.api.routes import trip as trip_routes

    monkeypatch.setattr(trip_routes, "_TASKS_DATA_DIR", tmp_path / "trip_tasks")
    yield
