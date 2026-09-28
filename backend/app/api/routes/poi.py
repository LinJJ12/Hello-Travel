"""POI相关API路由。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...core.constants import ErrorCode
from ...core.logging import get_logger
from ...services.amap_service import get_amap_service
from ...services.unsplash_service import get_unsplash_service

logger = get_logger(__name__)

router = APIRouter(prefix="/poi", tags=["POI"])


class POIDetailResponse(BaseModel):
    """POI详情响应。"""

    success: bool
    message: str
    data: dict | None = None


@router.get(
    "/detail/{poi_id}",
    response_model=POIDetailResponse,
    summary="获取POI详情",
    description="根据POI ID获取详细信息,包括图片",
)
def get_poi_detail(poi_id: str) -> POIDetailResponse:
    """获取 POI 详情。"""
    try:
        amap_service = get_amap_service()
        result = amap_service.get_poi_detail(poi_id)
        return POIDetailResponse(success=True, message="获取POI详情成功", data=result)
    except Exception as exc:  # noqa: BLE001
        logger.exception("获取POI详情失败: %s", exc)
        raise HTTPException(
            status_code=500,
            detail={"code": ErrorCode.AMAP_ERROR, "message": f"获取POI详情失败: {exc}"},
        ) from exc


@router.get("/search", summary="搜索POI", description="根据关键词搜索POI")
def search_poi(keywords: str, city: str = "北京") -> dict[str, Any]:
    """搜索 POI。"""
    try:
        amap_service = get_amap_service()
        result = amap_service.search_poi(keywords, city)
        return {"success": True, "message": "搜索成功", "data": result}
    except Exception as exc:  # noqa: BLE001
        logger.exception("搜索POI失败: %s", exc)
        raise HTTPException(
            status_code=500,
            detail={"code": ErrorCode.AMAP_ERROR, "message": f"搜索POI失败: {exc}"},
        ) from exc


@router.get("/photo", summary="获取景点图片", description="根据景点名称从Unsplash获取图片")
def get_attraction_photo(name: str) -> dict[str, Any]:
    """获取景点图片。"""
    try:
        unsplash_service = get_unsplash_service()
        photo_url = unsplash_service.get_photo_url(f"{name} China landmark") or unsplash_service.get_photo_url(name)
        return {
            "success": True,
            "message": "获取图片成功",
            "data": {"name": name, "photo_url": photo_url},
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("获取景点图片失败: %s", exc)
        raise HTTPException(
            status_code=500,
            detail={"code": ErrorCode.UPSTREAM_ERROR, "message": f"获取景点图片失败: {exc}"},
        ) from exc
