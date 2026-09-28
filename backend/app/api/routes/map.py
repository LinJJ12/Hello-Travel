"""地图服务API路由。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from ...core.constants import ErrorCode
from ...core.logging import get_logger
from ...models.schemas import (
    POISearchResponse,
    RouteInfo,
    RouteRequest,
    RouteResponse,
    WeatherResponse,
)
from ...services.amap_service import get_amap_service

logger = get_logger(__name__)

router = APIRouter(prefix="/map", tags=["地图服务"])


@router.get(
    "/poi",
    response_model=POISearchResponse,
    summary="搜索POI",
    description="根据关键词搜索POI(兴趣点)",
)
def search_poi(
    keywords: str = Query(..., description="搜索关键词", examples=["故宫"]),
    city: str = Query(..., description="城市", examples=["北京"]),
    citylimit: bool = Query(True, description="是否限制在城市范围内"),
) -> POISearchResponse:
    """搜索 POI（阻塞式外部调用，使用同步路由交由线程池执行）。"""
    try:
        service = get_amap_service()
        pois = service.search_poi(keywords, city, citylimit)
        return POISearchResponse(success=True, message="POI搜索成功", data=pois)
    except Exception as exc:  # noqa: BLE001
        logger.exception("POI搜索失败: %s", exc)
        raise HTTPException(
            status_code=500,
            detail={"code": ErrorCode.AMAP_ERROR, "message": f"POI搜索失败: {exc}"},
        ) from exc


@router.get(
    "/weather",
    response_model=WeatherResponse,
    summary="查询天气",
    description="查询指定城市的天气信息",
)
def get_weather(city: str = Query(..., description="城市名称", examples=["北京"])) -> WeatherResponse:
    """查询天气。"""
    try:
        service = get_amap_service()
        weather_info = service.get_weather(city)
        return WeatherResponse(success=True, message="天气查询成功", data=weather_info)
    except Exception as exc:  # noqa: BLE001
        logger.exception("天气查询失败: %s", exc)
        raise HTTPException(
            status_code=500,
            detail={"code": ErrorCode.AMAP_ERROR, "message": f"天气查询失败: {exc}"},
        ) from exc


@router.post(
    "/route",
    response_model=RouteResponse,
    summary="规划路线",
    description="规划两点之间的路线",
)
def plan_route(request: RouteRequest) -> RouteResponse:
    """规划路线。

    原实现在无法解析路线时返回空 dict，会触发 ``RouteResponse`` 校验错误；
    这里改为返回 ``data=None`` 并给出说明。
    """
    try:
        service = get_amap_service()
        route_info = service.plan_route(
            origin_address=request.origin_address,
            destination_address=request.destination_address,
            origin_city=request.origin_city,
            destination_city=request.destination_city,
            route_type=request.route_type,
        )

        if not route_info:
            return RouteResponse(success=False, message="未能解析出有效路线，请检查起终点地址", data=None)

        return RouteResponse(success=True, message="路线规划成功", data=RouteInfo(**route_info))
    except Exception as exc:  # noqa: BLE001
        logger.exception("路线规划失败: %s", exc)
        raise HTTPException(
            status_code=500,
            detail={"code": ErrorCode.AMAP_ERROR, "message": f"路线规划失败: {exc}"},
        ) from exc


@router.get("/health", summary="健康检查", description="检查地图服务是否正常")
async def health_check() -> dict[str, Any]:
    """健康检查：报告地图服务配置与缓存状态。"""
    try:
        service = get_amap_service()
        return {
            "status": "healthy",
            "service": "map-service",
            "amap_configured": bool(service.api_key),
            "cache_entries": len(service._cache),
        }
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=503,
            detail={"code": ErrorCode.CONFIG_ERROR, "message": f"服务不可用: {exc}"},
        ) from exc
