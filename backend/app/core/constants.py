"""全局常量与错误码。"""

from __future__ import annotations

from enum import Enum


class ErrorCode(str, Enum):
    """API 层对外暴露的语义化错误码，便于前端与监控区分错误类型。"""

    CONFIG_ERROR = "CONFIG_ERROR"
    AMAP_ERROR = "AMAP_ERROR"
    LLM_ERROR = "LLM_ERROR"
    PARSE_ERROR = "PARSE_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UPSTREAM_ERROR = "UPSTREAM_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"


# 中国大陆常见经纬度范围，用于校验 POI 坐标是否离谱
CHINA_LNG_RANGE = (73.0, 136.0)
CHINA_LAT_RANGE = (18.0, 54.0)

# 外部服务超时（秒）
AMAP_TIMEOUT = 20.0

# 外部调用重试策略
RETRY_ATTEMPTS = 3
RETRY_BASE_DELAY = 0.6
RETRY_MAX_DELAY = 6.0

# 高德 POI / 天气结果缓存时长（秒）
AMAP_CACHE_TTL = 600.0

# 异步任务在内存中保留的时长（秒），超时后由清理任务回收
JOB_TTL_SECONDS = 3600
