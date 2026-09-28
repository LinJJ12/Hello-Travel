"""TTL 缓存与重试工具的单元测试。"""

from __future__ import annotations

import time

import pytest

from app.core.cache import TTLCache
from app.core.retry import retry_async, retry_sync


def test_cache_hit_and_miss():
    cache = TTLCache(ttl=60)
    assert cache.get("missing") is None
    cache.set("k", {"v": 1})
    assert cache.get("k") == {"v": 1}
    assert len(cache) == 1


def test_cache_expiry():
    cache = TTLCache(ttl=0.05)
    cache.set("k", 1)
    assert cache.get("k") == 1
    time.sleep(0.08)
    assert cache.get("k") is None


def test_cache_evicts_when_full():
    cache = TTLCache(ttl=60, maxsize=2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)  # 触发淘汰
    assert len(cache) == 2


def test_cache_clear():
    cache = TTLCache(ttl=60)
    cache.set("a", 1)
    cache.clear()
    assert len(cache) == 0


def test_retry_sync_eventually_succeeds():
    attempts = {"n": 0}

    def flaky():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise ValueError("boom")
        return "ok"

    assert retry_sync(flaky, attempts=5, base_delay=0.01) == "ok"
    assert attempts["n"] == 3


def test_retry_sync_exhausts_and_raises():
    def always_fail():
        raise ValueError("always")

    with pytest.raises(ValueError):
        retry_sync(always_fail, attempts=3, base_delay=0.01)


def test_retry_sync_does_not_catch_unlisted_exception():
    def raises_type_error():
        raise TypeError("not retryable")

    with pytest.raises(TypeError):
        retry_sync(raises_type_error, attempts=3, base_delay=0.01, exceptions=(ValueError,))


async def test_retry_async_eventually_succeeds():
    attempts = {"n": 0}

    async def flaky():
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise ValueError("boom")
        return 42

    assert await retry_async(flaky, attempts=4, base_delay=0.01) == 42
    assert attempts["n"] == 2
