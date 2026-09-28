"""POI 相关 API 路由。

合并说明：用统一日志替代原实现散落的 ``print``；``/poi/detail`` 与 ``/poi/search``
改为对接真实的 ``AmapService`` REST 实现（原实现依赖 MCP 桩，恒返回空）。
"""


import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...core.logging import get_logger
from ...services.amap_service import get_amap_service

logger = get_logger(__name__)

router = APIRouter(prefix="/poi", tags=["POI"])


class POIDetailResponse(BaseModel):
    """POI详情响应"""
    success: bool
    message: str
    data: dict | None = None


@router.get(
    "/detail/{poi_id}",
    response_model=POIDetailResponse,
    summary="获取POI详情",
    description="根据POI ID获取详细信息,包括图片"
)
async def get_poi_detail(poi_id: str):
    """获取 POI 详情。

    ``AmapService`` 是同步阻塞实现（httpx 同步请求 + ``time.sleep`` 退避），这里用
    ``asyncio.to_thread`` 下放到线程池，避免阻塞事件循环——否则同进程内的 WebSocket
    进度推送与其他请求都会被一并卡住。
    """
    try:
        amap_service = get_amap_service()
        result = await asyncio.to_thread(amap_service.get_poi_detail, poi_id)

        return POIDetailResponse(
            success=bool(result),
            message="获取POI详情成功" if result else "未获取到 POI 详情",
            data=result,
        )

    except Exception as e:  # noqa: BLE001
        logger.error("获取POI详情失败: %s", e)
        raise HTTPException(status_code=500, detail=f"获取POI详情失败: {e}") from e


@router.get(
    "/search",
    summary="搜索POI",
    description="根据关键词搜索POI"
)
async def search_poi(keywords: str, city: str = "北京"):
    """搜索 POI。同步阻塞调用同样下放到线程池执行。"""
    try:
        amap_service = get_amap_service()
        result = await asyncio.to_thread(amap_service.search_poi, keywords, city)

        return {
            "success": bool(result),
            "message": "搜索成功" if result else "未获取到 POI 数据",
            "data": result,
        }

    except Exception as e:  # noqa: BLE001
        logger.error("搜索POI失败: %s", e)
        raise HTTPException(status_code=500, detail=f"搜索POI失败: {e}") from e


@router.get(
    "/image",
    summary="代理获取小红书图片",
    description="按景点名从缓存取图（miss 自动重搜新直链并立即下载），或代理白名单内的小红书稳定直链，规避 CDN 防盗链与时效签名（issue #28）"
)
async def proxy_attraction_image(name: str | None = None, url: str | None = None):
    """
    代理小红书图片，二选一传参：

    - name: 景点名。优先读关键词磁盘缓存；miss 时自动重搜新直链并立即下载
      （搜索返回的直链约 1 分钟即失效，浏览器直接引用必然 403）。
    - url: 小红书稳定格式图片直链（仅限 *.xiaohongshu.com / *.xhscdn.com），
      用于代理行程数据中内嵌的直链。
    """
    from fastapi.responses import Response

    from ...services.xhs_service import (
        XHSImageProxyError,
        fetch_xhs_image_bytes,
        get_photo_bytes_from_xhs,
    )

    if name:
        result = await get_photo_bytes_from_xhs(f"{name} 风景")
        if result is None:
            raise HTTPException(status_code=404, detail=f"未能获取 {name} 的景点图片")
        data, content_type = result
        return Response(
            content=data,
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=86400"},
        )

    if url:
        try:
            data, content_type = fetch_xhs_image_bytes(url)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except XHSImageProxyError as e:
            logger.error("图片代理失败: %s", e)
            raise HTTPException(status_code=502, detail=str(e)) from e
        except Exception as e:  # noqa: BLE001
            logger.error("图片代理异常: %s", e)
            raise HTTPException(status_code=502, detail=f"图片代理请求失败: {e}") from e
        return Response(
            content=data,
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=86400"},
        )

    raise HTTPException(status_code=400, detail="必须提供 name 或 url 查询参数")


@router.get(
    "/photo",
    summary="获取景点图片",
    description="根据景点名称从小红书获取图片"
)
async def get_attraction_photo(name: str, city: str | None = None):
    """获取景点图片。"""
    try:
        from ...services.xhs_service import get_photo_from_xhs

        # 为了避免同名的流行歌曲（如许嵩的《断桥残雪》）、小说或人名干扰
        # 强制带上前缀“景点”，能够绝对限定搜索范围在旅游打卡贴内
        query_kw = f"{name} 风景"
        photo_url = await get_photo_from_xhs(query_kw)

        if not photo_url:
            # 兜底：交由前端展示默认占位图
            logger.warning("无法为 %s 找到对应的小红书景点图片，返回空", name)
            photo_url = ""

        return {
            "success": True,
            "message": "获取图片成功",
            "data": {
                "name": name,
                "photo_url": photo_url,
            },
        }

    except Exception as e:  # noqa: BLE001
        logger.error("获取景点图片失败: %s", e)
        raise HTTPException(status_code=500, detail=f"获取景点图片失败: {e}") from e
