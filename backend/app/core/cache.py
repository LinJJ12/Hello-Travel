"""进程内 TTL 缓存。

高德地图的 POI / 天气 / 地理编码结果在短时间内是稳定的，重复调用既慢又浪费配额。
这里提供一个线程安全的轻量 TTL 缓存，供 :class:`AmapService` 使用。
"""

from __future__ import annotations

import threading
import time
from typing import Any


class TTLCache:
    """线程安全的键值缓存，条目在 ``ttl`` 秒后过期。"""

    def __init__(self, ttl: float = 300.0, maxsize: int = 512) -> None:
        self._ttl = float(ttl)
        self._maxsize = int(maxsize)
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        """命中则返回值，未命中或已过期返回 ``None``。"""
        with self._lock:
            item = self._store.get(key)
            if item is None:
                return None
            expires_at, value = item
            if expires_at < time.monotonic():
                self._store.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any) -> None:
        """写入缓存；超出容量时淘汰最先过期的一项。"""
        with self._lock:
            if len(self._store) >= self._maxsize and key not in self._store:
                oldest_key = min(self._store.items(), key=lambda kv: kv[1][0])[0]
                self._store.pop(oldest_key, None)
            self._store[key] = (time.monotonic() + self._ttl, value)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)
