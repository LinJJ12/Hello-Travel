"""高德地图服务封装 - 直接 HTTP API 实现"""

import json
from typing import List, Dict, Any, Optional, Tuple

import httpx

from ..config import get_settings
from ..models.schemas import Location, POIInfo, WeatherInfo


AMAP_API_BASE = "https://restapi.amap.com"


class AmapService:
    """高德地图服务封装类"""
    
    def __init__(self):
        """初始化服务"""
        settings = get_settings()
        if not settings.amap_api_key:
            raise ValueError("高德地图API Key未配置,请在.env文件中设置AMAP_API_KEY")
        self.api_key = settings.amap_api_key

    def _request(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """发送 HTTP 请求到高德 API"""
        request_params = {**params, "key": self.api_key, "output": "JSON"}
        response = httpx.get(f"{AMAP_API_BASE}{path}", params=request_params, timeout=20.0)
        response.raise_for_status()
        data = response.json()
        if data.get("status") not in {"1", 1, True}:
            raise ValueError(data.get("info", "高德地图接口返回失败"))
        return data

    @staticmethod
    def _parse_location(location_str: str) -> Optional[Location]:
        """从经纬度字符串解析成 Location 对象"""
        if not location_str:
            return None
        try:
            longitude, latitude = location_str.split(",")
            return Location(longitude=float(longitude), latitude=float(latitude))
        except Exception:
            return None
    
    def search_poi(self, keywords: str, city: str, citylimit: bool = True) -> List[POIInfo]:
        """
        搜索POI
        
        Args:
            keywords: 搜索关键词
            city: 城市
            citylimit: 是否限制在城市范围内
            
        Returns:
            POI信息列表
        """
        try:
            data = self._request(
                "/v3/place/text",
                {
                    "keywords": keywords,
                    "city": city,
                    "citylimit": str(citylimit).lower(),
                },
            )

            pois: List[POIInfo] = []
            for item in data.get("pois", [])[:10]:
                location = self._parse_location(item.get("location", ""))
                if not location:
                    continue
                
                # 处理 tel 字段 - 高德 API 返回的可能是列表或字符串
                tel = item.get("tel")
                if isinstance(tel, list):
                    tel = tel[0] if tel else None
                elif not isinstance(tel, str):
                    tel = None
                
                pois.append(
                    POIInfo(
                        id=item.get("id", ""),
                        name=item.get("name", ""),
                        type=item.get("type", ""),
                        address=item.get("address", ""),
                        location=location,
                        tel=tel,
                    )
                )

            # 详细日志
            print(f"✅ POI搜索结果: 成功解析 {len(pois)} 个POI")
            for i, poi in enumerate(pois[:3], 1):
                print(f"   {i}. {poi.name}")
                print(f"      地址: {poi.address}")
                print(f"      坐标: ({poi.location.longitude}, {poi.location.latitude})")
            if len(pois) > 3:
                print(f"   ... 还有 {len(pois)-3} 个POI")
            return pois

        except Exception as e:
            print(f"❌ POI搜索失败: {str(e)}")
            return []
    
    def get_weather(self, city: str) -> List[WeatherInfo]:
        """
        查询天气
        
        Args:
            city: 城市名称
            
        Returns:
            天气信息列表
        """
        try:
            # 先地理编码获取城市代码
            _, adcode = self._geocode_meta(city)
            weather_query = adcode or city
            
            data = self._request(
                "/v3/weather/weatherInfo",
                {
                    "city": weather_query,
                    "extensions": "all",
                },
            )

            weather_list: List[WeatherInfo] = []
            forecasts = data.get("forecasts") or []
            if forecasts:
                casts = forecasts[0].get("casts", [])
                for cast in casts:
                    weather_list.append(
                        WeatherInfo(
                            date=cast.get("date", ""),
                            day_weather=cast.get("dayweather", ""),
                            night_weather=cast.get("nightweather", ""),
                            day_temp=cast.get("daytemp", 0),
                            night_temp=cast.get("nighttemp", 0),
                            wind_direction=cast.get("daywind", ""),
                            wind_power=cast.get("daypower", ""),
                        )
                    )

            print(f"✅ 天气查询结果: 成功解析 {len(weather_list)} 天天气数据")
            return weather_list

        except Exception as e:
            print(f"❌ 天气查询失败: {str(e)}")
            return []
    
    def _geocode_meta(self, city: str) -> Tuple[Optional[Location], Optional[str]]:
        """地理编码，获取坐标和行政区代码"""
        try:
            data = self._request(
                "/v3/geocode/geo",
                {"address": city},
            )
            geocodes = data.get("geocodes") or []
            if not geocodes:
                return None, None
            first = geocodes[0]
            return self._parse_location(first.get("location", "")), first.get("adcode")
        except Exception as e:
            print(f"⚠️ 地理编码失败: {str(e)}")
            return None, None

    def plan_route(
        self,
        origin_address: str,
        destination_address: str,
        origin_city: Optional[str] = None,
        destination_city: Optional[str] = None,
        route_type: str = "walking"
    ) -> Dict[str, Any]:
        """
        规划路线
        
        Args:
            origin_address: 起点地址
            destination_address: 终点地址
            origin_city: 起点城市
            destination_city: 终点城市
            route_type: 路线类型 (walking/driving/transit)
            
        Returns:
            路线信息
        """
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
            params: Dict[str, Any] = {"origin": origin, "destination": destination}
            if origin_city:
                params["city"] = origin_city
            if destination_city:
                params["cityd"] = destination_city

            data = self._request(path, params)
            route = data.get("route") or {}

            distance = 0.0
            duration = 0
            if route_type == "walking" and route.get("paths"):
                first = route["paths"][0]
                distance = float(first.get("distance", 0) or 0)
                duration = int(float(first.get("duration", 0) or 0))
            elif route_type == "driving" and route.get("paths"):
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

        except Exception as e:
            print(f"❌ 路线规划失败: {str(e)}")
            return {}
    
    def geocode(self, address: str, city: Optional[str] = None) -> Optional[Location]:
        """
        地理编码(地址转坐标)

        Args:
            address: 地址
            city: 城市

        Returns:
            经纬度坐标
        """
        try:
            params: Dict[str, Any] = {"address": address}
            if city:
                params["city"] = city
            data = self._request("/v3/geocode/geo", params)
            geocodes = data.get("geocodes") or []
            if not geocodes:
                return None
            return self._parse_location(geocodes[0].get("location", ""))

        except Exception as e:
            print(f"❌ 地理编码失败: {str(e)}")
            return None

    def get_poi_detail(self, poi_id: str) -> Dict[str, Any]:
        """
        获取POI详情

        Args:
            poi_id: POI ID

        Returns:
            POI详情信息
        """
        try:
            data = self._request(
                "/v5/place/detail",
                {"id": poi_id},
            )
            return data

        except Exception as e:
            print(f"❌ 获取POI详情失败: {str(e)}")
            return {"id": poi_id, "error": str(e)}


# 创建全局服务实例
_amap_service = None


def get_amap_service() -> AmapService:
    """获取高德地图服务实例(单例模式)"""
    global _amap_service
    
    if _amap_service is None:
        _amap_service = AmapService()
    
    return _amap_service

