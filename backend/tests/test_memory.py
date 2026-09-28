"""记忆模块回归测试：存储层读写 + 惰性遗忘写回。

覆盖两个已修复的真实缺陷：

1. ``SqliteMemoryStore.list_all`` 原先直接 ``MemoryItem(**dict(row))``，而 ``SELECT *``
   的结果里带着 ``user_id``（并非 ``MemoryItem`` 字段），必然抛 ``TypeError``，
   导致开启 ``MEMORY_USE_SQLITE=true`` 后记忆读取完全不可用；
2. ``MemoryManager.recall_user_memory`` 原先只删除被淘汰项，存活项衰减后的权重与
   刷新后的 ``last_access_time`` 从不写回，导致「惰性遗忘」按上次保存时间而非
   上次访问时间计算，被频繁召回的记忆依然会被遗忘。
"""

from __future__ import annotations

import time

import pytest

from app.memory.data_model import MemoryItem
from app.memory.in_memory_store import InMemoryStore
from app.memory.memory_manager import MemoryManager
from app.memory.sqlite_store import SqliteMemoryStore

DAY_SECONDS = 86400


# --------------------------------------------------------------------------- #
# SqliteMemoryStore
# --------------------------------------------------------------------------- #
async def test_sqlite_store_round_trip(tmp_path):
    """回归：写入后应能完整读回，不能因多余列而 TypeError。"""
    store = SqliteMemoryStore(db_path=str(tmp_path / "memory.db"))
    item = MemoryItem.create("偏爱小众自然景点", "explicit", 8.0)

    await store.save("user-1", item)
    items = await store.list_all("user-1")

    assert len(items) == 1
    got = items[0]
    assert got.memory_id == item.memory_id
    assert got.content == "偏爱小众自然景点"
    assert got.source == "explicit"
    assert got.weight == pytest.approx(8.0)
    assert got.create_time == pytest.approx(item.create_time)
    assert got.last_access_time == pytest.approx(item.last_access_time)


async def test_sqlite_store_isolates_users(tmp_path):
    store = SqliteMemoryStore(db_path=str(tmp_path / "memory.db"))
    await store.save("u1", MemoryItem.create("A", "explicit", 5.0))
    await store.save("u2", MemoryItem.create("B", "explicit", 5.0))

    assert [i.content for i in await store.list_all("u1")] == ["A"]
    assert [i.content for i in await store.list_all("u2")] == ["B"]


async def test_sqlite_store_delete_and_clear(tmp_path):
    store = SqliteMemoryStore(db_path=str(tmp_path / "memory.db"))
    a = MemoryItem.create("A", "explicit", 5.0)
    b = MemoryItem.create("B", "explicit", 5.0)
    await store.save("u1", a)
    await store.save("u1", b)

    assert await store.delete("u1", a.memory_id) is True
    assert await store.delete("u1", "not-exist") is False
    assert [i.content for i in await store.list_all("u1")] == ["B"]

    await store.clear("u1")
    assert await store.list_all("u1") == []


async def test_sqlite_store_overwrites_same_memory_id(tmp_path):
    store = SqliteMemoryStore(db_path=str(tmp_path / "memory.db"))
    item = MemoryItem.create("初始", "explicit", 5.0)
    await store.save("u1", item)

    item.weight = 7.5
    await store.save("u1", item)

    items = await store.list_all("u1")
    assert len(items) == 1
    assert items[0].weight == pytest.approx(7.5)


# --------------------------------------------------------------------------- #
# InMemoryStore（对照组，保证两个实现语义一致）
# --------------------------------------------------------------------------- #
async def test_in_memory_store_round_trip():
    store = InMemoryStore()
    item = MemoryItem.create("喜欢美食", "implicit", 6.0)
    await store.save("u1", item)

    items = await store.list_all("u1")
    assert len(items) == 1
    assert items[0].content == "喜欢美食"

    assert await store.delete("u1", item.memory_id) is True
    assert await store.list_all("u1") == []


# --------------------------------------------------------------------------- #
# MemoryManager：惰性遗忘写回
# --------------------------------------------------------------------------- #
def _manager_with(store) -> MemoryManager:
    """绕过 __init__（其存储后端由环境变量在导入期决定），注入指定 store。"""
    manager = object.__new__(MemoryManager)
    manager.store = store
    return manager


async def test_recall_persists_decayed_weight(tmp_path):
    """回归：衰减后的权重与刷新后的访问时间必须落库。"""
    store = SqliteMemoryStore(db_path=str(tmp_path / "memory.db"))
    manager = _manager_with(store)

    item = MemoryItem.create("偏爱自然风光", "explicit", 9.0)
    item.last_access_time = time.time() - 30 * DAY_SECONDS  # 伪造 30 天未访问
    await store.save("u1", item)

    recalled = await manager.recall_user_memory("u1")
    assert len(recalled) == 1
    decayed_weight = recalled[0].weight
    assert decayed_weight < 9.0

    stored = await store.list_all("u1")
    assert len(stored) == 1
    # 关键断言：衰减结果已写回，而不是每次从 9.0 重新计算
    assert stored[0].weight == pytest.approx(decayed_weight)
    # 访问时间被刷新，后续衰减从"现在"重新起算
    assert stored[0].last_access_time > item.last_access_time


async def test_recall_removes_item_below_threshold(tmp_path):
    """权重衰减到阈值以下时应被淘汰并删除。"""
    store = SqliteMemoryStore(db_path=str(tmp_path / "memory.db"))
    manager = _manager_with(store)

    weak = MemoryItem.create("权重很低的记忆", "implicit", 2.0)
    weak.last_access_time = time.time() - 400 * DAY_SECONDS
    await store.save("u1", weak)

    recalled = await manager.recall_user_memory("u1")
    assert recalled == []
    assert await store.list_all("u1") == []


async def test_build_prompt_snippet_formats_lines(tmp_path):
    store = SqliteMemoryStore(db_path=str(tmp_path / "memory.db"))
    manager = _manager_with(store)

    await manager.add_memory("u1", "偏爱小众自然景点", source="explicit", init_weight=8.0)
    snippet = await manager.build_prompt_snippet("u1")

    assert snippet.startswith("【用户历史旅行偏好】")
    assert "- 偏爱小众自然景点" in snippet


async def test_build_prompt_snippet_empty_when_no_memory():
    manager = _manager_with(InMemoryStore())
    assert await manager.build_prompt_snippet("nobody") == ""
