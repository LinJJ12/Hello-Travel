"""轻量重试工具（同步 + 异步），带指数退避。

用于包裹高德地图、LLM 等外部调用，缓解偶发的网络抖动与限流。
刻意不引入 ``tenacity`` 依赖，保持依赖精简。
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from typing import Any

RetryableExceptions = tuple[type[BaseException], ...]


def _delay_for(attempt: int, base_delay: float, factor: float, max_delay: float) -> float:
    return min(max_delay, base_delay * (factor ** (attempt - 1)))


def retry_sync(
    fn: Callable[[], Any],
    *,
    attempts: int = 3,
    base_delay: float = 0.5,
    factor: float = 2.0,
    max_delay: float = 8.0,
    exceptions: RetryableExceptions = (Exception,),
    on_retry: Callable[[int, BaseException, float], None] | None = None,
) -> Any:
    """同步重试：失败后按指数退避重试，最后一次仍失败则抛出原异常。"""
    last_exc: BaseException | None = None
    for attempt in range(1, max(1, attempts) + 1):
        try:
            return fn()
        except exceptions as exc:  # type: ignore[misc]
            last_exc = exc
            if attempt >= attempts:
                break
            delay = _delay_for(attempt, base_delay, factor, max_delay)
            if on_retry is not None:
                on_retry(attempt, exc, delay)
            time.sleep(delay)
    assert last_exc is not None
    raise last_exc


async def retry_async(
    fn: Callable[[], Any],
    *,
    attempts: int = 3,
    base_delay: float = 0.5,
    factor: float = 2.0,
    max_delay: float = 8.0,
    exceptions: RetryableExceptions = (Exception,),
    on_retry: Callable[[int, BaseException, float], None] | None = None,
) -> Any:
    """异步重试：语义同 :func:`retry_sync`，使用 ``asyncio.sleep`` 退避。"""
    last_exc: BaseException | None = None
    for attempt in range(1, max(1, attempts) + 1):
        try:
            return await fn()
        except exceptions as exc:  # type: ignore[misc]
            last_exc = exc
            if attempt >= attempts:
                break
            delay = _delay_for(attempt, base_delay, factor, max_delay)
            if on_retry is not None:
                on_retry(attempt, exc, delay)
            await asyncio.sleep(delay)
    assert last_exc is not None
    raise last_exc
