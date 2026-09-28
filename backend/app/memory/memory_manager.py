"""记忆管理器：权重衰减（惰性遗忘）、合并、TOP-K 召回、Prompt 组装"""
import os
import time
from typing import Optional

from ..core.logging import get_logger
from .base import BaseMemoryStore
from .data_model import MemoryItem
from .in_memory_store import InMemoryStore
from .sqlite_store import SqliteMemoryStore

logger = get_logger(__name__)

# ========== 环境变量配置 ==========
DECAY_FACTOR = float(os.getenv("MEMORY_DECAY_FACTOR", "0.97"))
MEMORY_WEIGHT_THRESHOLD = float(os.getenv("MEMORY_THRESHOLD", "2.0"))
MAX_RECALL_COUNT = int(os.getenv("MEMORY_MAX_RECALL", "10"))
MIN_INIT_WEIGHT = float(os.getenv("MIN_INIT_WEIGHT", "4.0"))
MAX_SINGLE_CONTENT_LENGTH = int(os.getenv("MEMORY_MAX_SINGLE_CONTENT", "120"))
DAY_SECONDS = 86400
USE_SQLITE_PERSIST = os.getenv("MEMORY_USE_SQLITE", "false").lower() == "true"


class MemoryManager:
    """单例记忆管理器"""

    _instance: Optional["MemoryManager"] = None

    def __init__(self) -> None:
        if USE_SQLITE_PERSIST:
            self.store: BaseMemoryStore = SqliteMemoryStore()
            logger.info("Memory module enabled: using SQLite persistent storage")
        else:
            self.store: BaseMemoryStore = InMemoryStore()
            logger.info("Memory module enabled: using in-memory storage")

    @classmethod
    def get_instance(cls) -> "MemoryManager":
        if cls._instance is None:
            cls._instance = MemoryManager()
        return cls._instance

    async def _apply_forget_and_filter(
        self, items: list[MemoryItem]
    ) -> tuple[list[MemoryItem], list[str]]:
        """惰性遗忘：读取时按时间差衰减权重，低于阈值的标记删除"""
        now = time.time()
        valid_items: list[MemoryItem] = []
        to_remove_ids: list[str] = []

        for item in items:
            delta_days = (now - item.last_access_time) / DAY_SECONDS
            item.weight *= DECAY_FACTOR ** delta_days
            item.update_access()

            if item.weight >= MEMORY_WEIGHT_THRESHOLD:
                valid_items.append(item)
            else:
                to_remove_ids.append(item.memory_id)
                logger.info(
                    f"[Forget] memory eliminated. id={item.memory_id}, "
                    f"weight={item.weight:.2f}, content={item.content}"
                )
        return valid_items, to_remove_ids

    async def recall_user_memory(self, user_id: str) -> list[MemoryItem]:
        """召回记忆：衰减过滤 + 权重降序 + TOP-K 截断"""
        all_items = await self.store.list_all(user_id)
        valid_items, remove_ids = await self._apply_forget_and_filter(all_items)

        for mid in remove_ids:
            await self.store.delete(user_id, mid)

        # 写回衰减后的权重与刷新后的访问时间。
        # 修复：原实现只删除被淘汰项，存活项的衰减权重与 last_access_time 从不落库，
        # 导致「惰性遗忘」按“上次保存时间”而非“上次访问时间”计算——被频繁召回的记忆
        # 依然会因时间久远被遗忘，且访问时间永远不更新。
        for item in valid_items:
            await self.store.save(user_id, item)

        valid_items.sort(key=lambda x: x.weight, reverse=True)
        top_k_items = valid_items[:MAX_RECALL_COUNT]
        logger.debug(
            f"[Recall] user={user_id}, valid_total={len(valid_items)}, "
            f"max_recall_limit={MAX_RECALL_COUNT}, final_selected={len(top_k_items)}"
        )
        return top_k_items

    async def add_memory(
        self, user_id: str, content: str, source: str, init_weight: float
    ) -> None:
        """新增记忆；相同文本合并权重；低于准入门槛直接拒绝"""
        if init_weight < MIN_INIT_WEIGHT:
            logger.debug(
                f"[RejectAdd] weight below limit. user={user_id}, "
                f"score={init_weight:.2f}, content={content}"
            )
            return

        all_items = await self.store.list_all(user_id)
        for item in all_items:
            if item.content.strip() == content.strip():
                old_weight = item.weight
                item.weight = min(10.0, item.weight + init_weight * 0.4)
                item.update_access()
                await self.store.save(user_id, item)
                logger.info(
                    f"[MergeMemory] user={user_id}, source={source}, "
                    f"old_w={old_weight:.2f} -> new_w={item.weight:.2f}, content={content}"
                )
                return

        new_item = MemoryItem.create(content, source, init_weight)
        await self.store.save(user_id, new_item)
        logger.info(
            f"[NewMemory] user={user_id}, source={source}, "
            f"w={init_weight:.2f}, mid={new_item.memory_id}, content={content}"
        )

    async def build_prompt_snippet(self, user_id: str) -> str:
        """组装注入 Agent 的偏好文本（TOP-K + 单条长度截断，双层防护）"""
        memories = await self.recall_user_memory(user_id)
        if not memories:
            return ""

        safe_memories = memories[:MAX_RECALL_COUNT]
        lines = []
        for m in safe_memories:
            short_content = m.content[:MAX_SINGLE_CONTENT_LENGTH].strip()
            lines.append(f"- {short_content}")

        snippet = "【用户历史旅行偏好】\n" + "\n".join(lines)
        logger.debug(
            f"[BuildPromptSnippet] user={user_id}, inject_memory_count={len(safe_memories)}"
        )
        return snippet
