"""用户偏好记忆模块

带权重的用户专属旅行偏好记忆，支持：
- LLM 自动提取偏好并打分，低于准入门槛不入库
- 权重随时间惰性衰减，低于遗忘阈值自动删除
- 相同偏好权重合并，上限 10.0
- TOP-K 召回 + 单条长度截断，防止 Prompt 膨胀
- 内存 / SQLite 两种存储，可通过环境变量切换

合并说明：日志统一走 ``app.core.logging``，替代原先独立的
``logging.getLogger("tripstar.memory")``，以便与全站日志格式、级别保持一致。
"""

from ..core.logging import get_logger
from .data_model import MemoryItem
from .memory_manager import MemoryManager
from .preference_extractor import PreferenceExtractor

logger = get_logger("tripstar.memory")

__all__ = ["MemoryManager", "PreferenceExtractor", "MemoryItem", "logger"]
