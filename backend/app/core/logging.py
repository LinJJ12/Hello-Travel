"""统一日志配置。

替代项目里散落的 ``print`` 调试输出，提供带时间戳、级别和模块名的结构化日志。
"""

from __future__ import annotations

import logging
import sys

_CONFIGURED = False

_DEFAULT_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 这些第三方库在 DEBUG 级别会非常吵，统一压到 WARNING
_NOISY_LOGGERS = ("httpx", "httpcore", "openai", "urllib3", "asyncio", "multipart")


def setup_logging(level: str = "INFO") -> None:
    """初始化根日志器（幂等，可重复调用）。"""
    global _CONFIGURED
    if _CONFIGURED:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_DEFAULT_FORMAT, datefmt=_DATE_FORMAT))

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(getattr(logging, str(level).upper(), logging.INFO))

    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """获取带统一配置的日志器。"""
    return logging.getLogger(name)
