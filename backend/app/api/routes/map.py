"""地图服务 API 路由。

合并说明：原实现依赖 ``AmapService.mcp_tool``（MCP 桩），``/map/health`` 会因
该属性不存在而必然 500；``/map/poi``、``/map/weather`` 也始终返回空数据。
现改为对接真实的 ``AmapService`` REST 实现，并用 ``amap_configured`` 暴露配置状态。
"""

from fastapi import APIRouter, HTTPException, Query

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
    description="根据关键词搜索POI(兴趣点)"
)
def search_poi(
    keywords: str = Query(..., description="搜索关键词", example="故宫"),
    city: str = Query(..., description="城市", example="北京"),
    citylimit: bool = Query(True, description="是否限制在城市范围内")
):
    """搜索 POI。

    注意：这里刻意使用同步 ``def``。``AmapService`` 是同步阻塞实现（httpx 同步请求 +
    ``time.sleep`` 退避重试），若写成 ``async def`` 会直接阻塞事件循环，导致同一进程内
    的 WebSocket 进度推送与其他请求全部卡住。用 ``def`` 交给 FastAPI 线程池执行。
    """
    try:
        service = get_amap_service()
        pois = service.search_poi(keywords, city, citylimit)

        return POISearchResponse(
            success=bool(pois),
            message="POI搜索成功" if pois else "未获取到 POI 数据",
            data=pois,
        )

    except Exception as e:  # noqa: BLE001
        logger.error("POI搜索失败: %s", e)
        raise HTTPException(status_code=500, detail=f"POI搜索失败: {e}") from e


@router.get(
    "/weather",
    response_model=WeatherResponse,
    summary="查询天气",
    description="查询指定城市的天气信息"
)
def get_weather(
    city: str = Query(..., description="城市名称", example="北京")
):
    """查询天气。同步 ``def``，原因同 :func:`search_poi`（底层为阻塞式 httpx）。"""
    try:
        service = get_amap_service()
        weather_info = service.get_weather(city)

        return WeatherResponse(
            success=bool(weather_info),
            message="天气查询成功" if weather_info else "未获取到天气数据",
            data=weather_info,
        )

    except Exception as e:  # noqa: BLE001
        logger.error("天气查询失败: %s", e)
        raise HTTPException(status_code=500, detail=f"天气查询失败: {e}") from e


@router.post(
    "/route",
    response_model=RouteResponse,
    summary="规划路线",
    description="规划两点之间的路线"
)
def plan_route(request: RouteRequest):
    """规划路线。同步 ``def``，原因同 :func:`search_poi`（底层为阻塞式 httpx）。"""
    try:
        service = get_amap_service()
        route_info = service.plan_route(
            origin_address=request.origin_address,
            destination_address=request.destination_address,
            origin_city=request.origin_city,
            destination_city=request.destination_city,
            route_type=request.route_type,
        )

        # 注意：解析失败时 service 返回空 dict，这里必须显式返回 success=False，
        # 不能把 {} 塞进 data（响应模型 data 为 Optional[RouteInfo]，空 dict 会触发校验错误）。
        if not route_info:
            return RouteResponse(
                success=False,
                message="未能获取路线数据",
                data=None,
            )

        return RouteResponse(
            success=True,
            message="路线规划成功",
            data=RouteInfo(
                distance=float(route_info.get("distance", 0) or 0),
                duration=int(route_info.get("duration", 0) or 0),
                route_type=request.route_type,
                description=str(route_info.get("distance_text") or route_info.get("description") or ""),
            ),
        )

    except Exception as e:  # noqa: BLE001
        logger.error("路线规划失败: %s", e)
        raise HTTPException(status_code=500, detail=f"路线规划失败: {e}") from e


@router.get(
    "/health",
    summary="健康检查",
    description="检查地图服务是否正常"
)
async def health_check():
    """健康检查。

    回归修复：原实现访问 ``service.mcp_tool._available_tools``，而 ``AmapService``
    并没有 ``mcp_tool`` 属性，该端点必然抛 AttributeError → 503。
    """
    try:
        service = get_amap_service()
        return {
            "status": "healthy",
            "service": "map-service",
            "amap_configured": service.configured,
            "cache_entries": len(service._cache),
        }
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"服务不可用: {e}") from e
