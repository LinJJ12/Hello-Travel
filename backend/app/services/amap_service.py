"""高德地图服务封装 - 直接 HTTP REST API 实现。

合并说明：TripStar 原实现的 ``AmapService`` 是 MCP 桩代码——``search_poi`` /
``get_weather`` / ``plan_route`` / ``geocode`` 全部返回空列表或空字典，导致
``/api/map/*`` 系列端点实际不可用；``/api/map/health`` 还访问了并不存在的
``service.mcp_tool`` 属性。这里移植 Hello-Travel 的真实 REST 实现并做了适配：

- 直接调用 ``restapi.amap.com``，不再依赖 ``uvx amap-mcp-server`` 子进程；
- POI / 天气 / 地理编码 / POI 详情统一走进程内 TTL 缓存；
- 外部请求带指数退避重试；
- 未配置 Key 时优雅降级（返回空结果）而非抛错，配合前端设置页的「先启动后配置」。
"""

from __future__ import annotations

from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import httpx

from ..config import get_settings
from ..core.cache import TTLCache
from ..core.constants import AMAP_TIMEOUT, RETRY_ATTEMPTS, RETRY_BASE_DELAY, RETRY_MAX_DELAY
from ..core.logging import get_logger
from ..core.retry import retry_sync
from ..models.schemas import Location, POIInfo, WeatherInfo

logger = get_logger(__name__)

AMAP_API_BASE = "https://restapi.amap.com"

# 需要重试的底层异常（网络类）
_RETRYABLE = (httpx.HTTPError, OSError)


class AmapService:
    """高德地图服务封装类。"""

    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = (settings.vite_amap_web_key or "").strip()
        ttl = max(0.0, float(settings.amap_cache_ttl))
        self._cache = TTLCache(ttl=ttl or 0.01, maxsize=1024)
        if not self.api_key:
            logger.warning("高德地图 Web 服务 Key 未配置，/api/map 与 /api/poi 将返回空结果")

    @property
    def configured(self) -> bool:
        """是否已配置高德 Web 服务 Key。"""
        return bool(self.api_key)

    # ------------------------------------------------------------------ #
    # 底层请求
    # ------------------------------------------------------------------ #
    def _request(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        """发送 HTTP 请求到高德 API（带重试）。"""

        def _call() -> dict[str, Any]:
            request_params = {**params, "key": self.api_key, "output": "JSON"}
            response = httpx.get(
                f"{AMAP_API_BASE}{path}",
                params=request_params,
                timeout=AMAP_TIMEOUT,
                trust_env=False,
            )
            response.raise_for_status()
            return response.json()

        def _on_retry(attempt: int, exc: BaseException, delay: float) -> None:
            logger.warning("高德接口 %s 第 %s 次失败(%s)，%.1fs 后重试", path, attempt, exc, delay)

        data = retry_sync(
            _call,
            attempts=RETRY_ATTEMPTS,
            base_delay=RETRY_BASE_DELAY,
            max_delay=RETRY_MAX_DELAY,
            exceptions=_RETRYABLE,
            on_retry=_on_retry,
        )
        if data.get("status") not in {"1", 1}:
            raise ValueError(data.get("info", "高德地图接口返回失败"))
        return data

    @staticmethod
    def _parse_location(location_str: str) -> Location | None:
        """从经纬度字符串解析成 Location 对象。"""
        if not location_str:
            return None
        try:
            longitude, latitude = location_str.split(",")
            return Location(longitude=float(longitude), latitude=float(latitude))
        except (ValueError, AttributeError):
            return None

    @staticmethod
    def _normalize_tel(tel: Any) -> str | None:
        if isinstance(tel, list):
            return tel[0] if tel else None
        if isinstance(tel, str):
            return tel or None
        return None

    def _poi_from_item(self, item: dict[str, Any]) -> POIInfo | None:
        location = self._parse_location(item.get("location", ""))
        if not location:
            return None
        return POIInfo(
            id=item.get("id", ""),
            name=item.get("name", ""),
            type=item.get("type", ""),
            address=item.get("address", ""),
            location=location,
            tel=self._normalize_tel(item.get("tel")),
        )

    # ------------------------------------------------------------------ #
    # POI 搜索
    # ------------------------------------------------------------------ #
    def search_poi(
        self, keywords: str, city: str, citylimit: bool = True, limit: int = 10
    ) -> list[POIInfo]:
        """搜索 POI（带缓存）。"""
        if not self.configured:
            return []

        cache_key = f"poi::{keywords}::{city}::{citylimit}::{limit}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.debug("POI 命中缓存: %s @ %s", keywords, city)
            return cached

        try:
            data = self._request(
                "/v3/place/text",
                {
                    "keywords": keywords,
                    "city": city,
                    "citylimit": str(citylimit).lower(),
                },
            )
            pois: list[POIInfo] = []
            for item in data.get("pois", [])[:limit]:
                poi = self._poi_from_item(item)
                if poi:
                    pois.append(poi)

            logger.info("POI 搜索 '%s' @ %s → %s 条", keywords, city, len(pois))
            self._cache.set(cache_key, pois)
            return pois

        except Exception as exc:  # noqa: BLE001 - 对外统一降级为空列表
            logger.error("POI 搜索失败 '%s' @ %s: %s", keywords, city, exc)
            return []

    def search_pois_multi(
        self,
        keywords: Sequence[str],
        city: str,
        per_keyword: int = 8,
        max_workers: int = 4,
    ) -> list[POIInfo]:
        """多关键词并行搜索并按 POI id / 名称去重。"""
        terms = [term.strip() for term in keywords if term and term.strip()]
        if not terms:
            return []

        merged: list[POIInfo] = []
        with ThreadPoolExecutor(max_workers=min(max_workers, len(terms))) as pool:
            futures = [pool.submit(self.search_poi, term, city, True, per_keyword) for term in terms]
            for future in futures:
                try:
                    merged.extend(future.result())
                except Exception as exc:  # noqa: BLE001
                    logger.warning("并行 POI 搜索子任务失败: %s", exc)

        seen: set[str] = set()
        deduped: list[POIInfo] = []
        for poi in merged:
            key = poi.id or f"{poi.name}::{poi.address}"
            if key in seen:
                continue
            seen.add(key)
            deduped.append(poi)

        logger.info("多关键词 POI 搜索 %s @ %s → 合并去重后 %s 条", list(terms), city, len(deduped))
        return deduped

    # ------------------------------------------------------------------ #
    # 天气
    # ------------------------------------------------------------------ #
    def get_weather(self, city: str) -> list[WeatherInfo]:
        """查询天气（带缓存）。"""
        if not self.configured:
            return []

        cache_key = f"weather::{city}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.debug("天气命中缓存: %s", city)
            return cached

        try:
            _, adcode = self._geocode_meta(city)
            weather_query = adcode or city

            data = self._request(
                "/v3/weather/weatherInfo",
                {"city": weather_query, "extensions": "all"},
            )

            weather_list: list[WeatherInfo] = []
            forecasts = data.get("forecasts") or []
            if forecasts:
                for cast in forecasts[0].get("casts", []):
                    weather_list.append(
                        WeatherInfo(
                            date=cast.get("date", ""),
                            city=city,
                            day_weather=cast.get("dayweather", ""),
                            night_weather=cast.get("nightweather", ""),
                            day_temp=cast.get("daytemp", 0),
                            night_temp=cast.get("nighttemp", 0),
                            wind_direction=cast.get("daywind", ""),
                            wind_power=cast.get("daypower", ""),
                        )
                    )

            logger.info("天气查询 %s → %s 天", city, len(weather_list))
            self._cache.set(cache_key, weather_list)
            return weather_list

        except Exception as exc:  # noqa: BLE001
            logger.error("天气查询失败 %s: %s", city, exc)
            return []

    def _geocode_meta(self, city: str) -> tuple[Location | None, str | None]:
        """地理编码，获取坐标和行政区代码（带缓存）。"""
        cache_key = f"geocode_meta::{city}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            data = self._request("/v3/geocode/geo", {"address": city})
            geocodes = data.get("geocodes") or []
            if not geocodes:
                return None, None
            first = geocodes[0]
            result = (self._parse_location(first.get("location", "")), first.get("adcode"))
            self._cache.set(cache_key, result)
            return result
        except Exception as exc:  # noqa: BLE001
            logger.warning("地理编码失败 %s: %s", city, exc)
            return None, None

    # ------------------------------------------------------------------ #
    # 路线规划
    # ------------------------------------------------------------------ #
    def plan_route(
        self,
        origin_address: str,
        destination_address: str,
        origin_city: str | None = None,
        destination_city: str | None = None,
        route_type: str = "walking",
    ) -> dict[str, Any]:
        """规划路线。失败或无法解析时返回 ``{}``。"""
        if not self.configured:
            return {}

        try:
            origin_location = self.geocode(origin_address, origin_city)
            destination_location = self.geocode(destination_address, destination_city)
            if not origin_location or not destination_location:
                return {}

            origin = f"{origin_location.longitude},{origin_location.latitude}"
            destination = f"{destination_location.longitude},{destination_location.latitude}"

            route_map = {
                "walking": "/v3/direction/walking",
                "driving": "/v3/direction/driving",
                "transit": "/v3/direction/transit/integrated",
            }
            path = route_map.get(route_type, "/v3/direction/walking")
            params: dict[str, Any] = {"origin": origin, "destination": destination}
            if origin_city:
                params["city"] = origin_city
            if destination_city:
                params["cityd"] = destination_city

            data = self._request(path, params)
            route = data.get("route") or {}

            distance = 0.0
            duration = 0
            if route_type in {"walking", "driving"} and route.get("paths"):
                first = route["paths"][0]
                distance = float(first.get("distance", 0) or 0)
                duration = int(float(first.get("duration", 0) or 0))
            elif route_type == "transit" and route.get("transits"):
                first = route["transits"][0]
                distance = float(first.get("distance", 0) or 0)
                duration = int(float(first.get("duration", 0) or 0))

            return {
                "distance": distance,
                "duration": duration,
                "route_type": route_type,
                "description": f"{route_type}路线规划结果",
            }

        except Exception as exc:  # noqa: BLE001
            logger.error("路线规划失败: %s", exc)
            return {}

    def geocode(self, address: str, city: str | None = None) -> Location | None:
        """地理编码（地址转坐标，带缓存）。"""
        if not self.configured:
            return None

        cache_key = f"geocode::{address}::{city}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            params: dict[str, Any] = {"address": address}
            if city:
                params["city"] = city
            data = self._request("/v3/geocode/geo", params)
            geocodes = data.get("geocodes") or []
            if not geocodes:
                return None
            location = self._parse_location(geocodes[0].get("location", ""))
            if location:
                self._cache.set(cache_key, location)
            return location

        except Exception as exc:  # noqa: BLE001
            logger.error("地理编码失败: %s", exc)
            return None

    def get_poi_detail(self, poi_id: str) -> dict[str, Any]:
        """获取 POI 详情。"""
        if not self.configured:
            return {}

        cache_key = f"poi_detail::{poi_id}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            data = self._request("/v5/place/detail", {"id": poi_id})
            self._cache.set(cache_key, data)
            return data
        except Exception as exc:  # noqa: BLE001
            logger.error("获取POI详情失败: %s", exc)
            return {"id": poi_id, "error": str(exc)}


# 创建全局服务实例
_amap_service: AmapService | None = None


def get_amap_service() -> AmapService:
    """获取高德地图服务实例(单例模式)"""
    global _amap_service
    if _amap_service is None:
        _amap_service = AmapService()
    return _amap_service


def reset_amap_service() -> None:
    """重置高德地图服务实例（用于运行时配置更新后热生效）。"""
    global _amap_service
    _amap_service = None
