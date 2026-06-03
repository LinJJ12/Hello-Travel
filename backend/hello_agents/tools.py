"""本地 MCPTool 兼容层。"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

import httpx

AMAP_API_BASE = "https://restapi.amap.com"


class MCPTool:
    """将项目里用到的 MCP 工具调用，映射到高德开放 API。"""

    def __init__(self, name: str, description: str = "", server_command=None, env=None, auto_expand: bool = False):
        self.name = name
        self.description = description
        self.server_command = server_command or []
        self.env = env or {}
        self.auto_expand = auto_expand
        self._available_tools = [
            {"name": "maps_text_search"},
            {"name": "maps_weather"},
            {"name": "maps_direction_walking_by_address"},
            {"name": "maps_direction_driving_by_address"},
            {"name": "maps_direction_transit_integrated_by_address"},
            {"name": "maps_geo"},
            {"name": "maps_search_detail"},
        ]

    def _api_key(self) -> str:
        # 先从 env 参数获取
        key = self.env.get("AMAP_MAPS_API_KEY") or self.env.get("AMAP_API_KEY")
        if key:
            return key
        # 再从环境变量获取
        key = os.getenv("AMAP_API_KEY") or os.getenv("AMAP_MAPS_API_KEY")
        if key:
            return key
        raise ValueError("高德地图API Key未配置")

    def _request(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        request_params = {**params, "key": self._api_key(), "output": "JSON"}
        response = httpx.get(f"{AMAP_API_BASE}{path}", params=request_params, timeout=20.0)
        response.raise_for_status()
        data = response.json()
        if data.get("status") not in {"1", 1, True}:
            raise ValueError(data.get("info", "高德地图接口返回失败"))
        return data

    @staticmethod
    def _parse_location(location: str) -> Optional[Dict[str, float]]:
        if not location:
            return None
        try:
            longitude, latitude = location.split(",")
            return {"longitude": float(longitude), "latitude": float(latitude)}
        except Exception:
            return None

    def run(self, payload: Dict[str, Any]) -> str:
        try:
            tool_name = payload.get("tool_name", "")
            arguments = payload.get("arguments", {}) or {}

            if tool_name == "maps_text_search":
                data = self._request(
                    "/v3/place/text",
                    {
                        "keywords": arguments.get("keywords", ""),
                        "city": arguments.get("city", ""),
                        "citylimit": arguments.get("citylimit", "true"),
                    },
                )
                pois = []
                for item in data.get("pois", [])[:10]:
                    pois.append({
                        "id": item.get("id", ""),
                        "name": item.get("name", ""),
                        "type": item.get("type", ""),
                        "address": item.get("address", ""),
                        "location": self._parse_location(item.get("location", "")),
                        "tel": item.get("tel"),
                    })
                return json.dumps({"status": "ok", "data": pois}, ensure_ascii=False)

            if tool_name == "maps_geo":
                data = self._request(
                    "/v3/geocode/geo",
                    {
                        "address": arguments.get("address", ""),
                        **({"city": arguments.get("city")} if arguments.get("city") else {}),
                    },
                )
                geocodes = data.get("geocodes", [])
                if geocodes:
                    first = geocodes[0]
                    return json.dumps(
                        {
                            "status": "ok",
                            "data": {
                                "location": self._parse_location(first.get("location", "")),
                                "adcode": first.get("adcode"),
                            },
                        },
                        ensure_ascii=False,
                    )
                return json.dumps({"status": "ok", "data": None}, ensure_ascii=False)

            if tool_name == "maps_weather":
                geo_data = self._request(
                    "/v3/geocode/geo",
                    {"address": arguments.get("city", "")},
                )
                geocodes = geo_data.get("geocodes", [])
                city_code = geocodes[0].get("adcode") if geocodes else arguments.get("city", "")
                data = self._request(
                    "/v3/weather/weatherInfo",
                    {"city": city_code, "extensions": "all"},
                )
                forecasts = []
                for forecast in data.get("forecasts", []):
                    for cast in forecast.get("casts", []):
                        forecasts.append({
                            "date": cast.get("date", ""),
                            "day_weather": cast.get("dayweather", ""),
                            "night_weather": cast.get("nightweather", ""),
                            "day_temp": cast.get("daytemp", 0),
                            "night_temp": cast.get("nighttemp", 0),
                            "wind_direction": cast.get("daywind", ""),
                            "wind_power": cast.get("daypower", ""),
                        })
                return json.dumps({"status": "ok", "data": forecasts}, ensure_ascii=False)

            if tool_name in {"maps_direction_walking_by_address", "maps_direction_driving_by_address", "maps_direction_transit_integrated_by_address"}:
                origin_address = arguments.get("origin_address", "")
                destination_address = arguments.get("destination_address", "")
                origin_city = arguments.get("origin_city")
                destination_city = arguments.get("destination_city")

                origin_geo = self._request(
                    "/v3/geocode/geo",
                    {"address": origin_address, **({"city": origin_city} if origin_city else {})},
                )
                destination_geo = self._request(
                    "/v3/geocode/geo",
                    {"address": destination_address, **({"city": destination_city} if destination_city else {})},
                )

                origin_codes = origin_geo.get("geocodes", [])
                destination_codes = destination_geo.get("geocodes", [])
                if not origin_codes or not destination_codes:
                    return json.dumps({"status": "ok", "data": None}, ensure_ascii=False)

                origin_location = origin_codes[0].get("location", "")
                destination_location = destination_codes[0].get("location", "")
                route_path = {
                    "maps_direction_walking_by_address": "/v3/direction/walking",
                    "maps_direction_driving_by_address": "/v3/direction/driving",
                    "maps_direction_transit_integrated_by_address": "/v3/direction/transit/integrated",
                }[tool_name]

                params = {"origin": origin_location, "destination": destination_location}
                if tool_name == "maps_direction_transit_integrated_by_address":
                    if origin_city:
                        params["city"] = origin_city
                    if destination_city:
                        params["cityd"] = destination_city
                data = self._request(route_path, params)
                return json.dumps({"status": "ok", "data": data}, ensure_ascii=False)

            if tool_name == "maps_search_detail":
                data = self._request("/v5/place/detail", {"id": arguments.get("id", "")})
                return json.dumps({"status": "ok", "data": data}, ensure_ascii=False)

            return json.dumps({"status": "error", "message": f"未支持的工具: {tool_name}"}, ensure_ascii=False)

        except Exception as exc:
            return json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False)
