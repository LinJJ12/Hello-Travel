"""pytest 全局配置。

在导入应用之前注入测试用环境变量，避免 ``validate_config`` 因缺少密钥而失败。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# 让 tests 能 import app / hello_agents
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# 必须在导入 app.config 之前设置
os.environ.setdefault("AMAP_API_KEY", "test-amap-key")
os.environ.setdefault("LLM_API_KEY", "test-llm-key")
os.environ.setdefault("LLM_BASE_URL", "https://example.invalid/v1")
os.environ.setdefault("LLM_MODEL_ID", "test-model")
os.environ.setdefault("LOG_LEVEL", "WARNING")
