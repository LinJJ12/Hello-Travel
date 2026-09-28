"""内存任务存储（带 TTL 回收）。

原实现用一个裸 dict 保存异步规划任务，永不清理，长时间运行会持续占用内存。
这里封装一个带过期回收与容量上限的线程安全存储。
"""

from __future__ import annotations

import threading
import time
from typing import Any

from .constants import JOB_TTL_SECONDS


class JobStore:
    """线程安全的任务存储，条目在 ``ttl`` 秒后自动过期。"""

    def __init__(self, ttl: float = JOB_TTL_SECONDS, maxsize: int = 256) -> None:
        self._ttl = float(ttl)
        self._maxsize = int(maxsize)
        self._store: dict[str, dict[str, Any]] = {}
        self._created: dict[str, float] = {}
        self._lock = threading.Lock()

    def _purge_locked(self) -> None:
        now = time.monotonic()
        expired = [key for key, created in self._created.items() if now - created > self._ttl]
        for key in expired:
            self._store.pop(key, None)
            self._created.pop(key, None)

    def set(self, job_id: str, payload: dict[str, Any]) -> None:
        with self._lock:
            self._purge_locked()
            if len(self._store) >= self._maxsize and job_id not in self._store:
                oldest = min(self._created.items(), key=lambda kv: kv[1])[0]
                self._store.pop(oldest, None)
                self._created.pop(oldest, None)
            self._store[job_id] = payload
            self._created.setdefault(job_id, time.monotonic())

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            self._purge_locked()
            return self._store.get(job_id)

    def __contains__(self, job_id: str) -> bool:
        with self._lock:
            self._purge_locked()
            return job_id in self._store

    def __len__(self) -> int:
        with self._lock:
            self._purge_locked()
            return len(self._store)
