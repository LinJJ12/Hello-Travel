"""Unsplash图片服务。

改用项目已有的 ``httpx``（原实现依赖 ``requests``，但 requirements.txt 并未声明，
属于隐性缺失依赖），并补充统一日志与未配置密钥时的优雅降级。
"""

from __future__ import annotations

from typing import Any

import httpx

from ..config import get_settings
from ..core.logging import get_logger
from ..core.retry import retry_sync

logger = get_logger(__name__)

_UNSPLASH_BASE = "https://api.unsplash.com"


class UnsplashService:
    """Unsplash 图片服务类。"""

    def __init__(self) -> None:
        settings = get_settings()
        self.access_key = settings.unsplash_access_key
        self.base_url = _UNSPLASH_BASE

    @property
    def enabled(self) -> bool:
        return bool(self.access_key)

    def search_photos(self, query: str, per_page: int = 5) -> list[dict[str, Any]]:
        """搜索图片；未配置密钥或失败时返回空列表。"""
        if not self.enabled:
            logger.debug("Unsplash 未配置 ACCESS_KEY，跳过图片搜索")
            return []

        def _call() -> list[dict[str, Any]]:
            response = httpx.get(
                f"{self.base_url}/search/photos",
                params={"query": query, "per_page": per_page, "client_id": self.access_key},
                timeout=10.0,
            )
            response.raise_for_status()
            results = response.json().get("results", [])
            return [
                {
                    "id": photo.get("id"),
                    "url": photo.get("urls", {}).get("regular"),
                    "thumb": photo.get("urls", {}).get("thumb"),
                    "description": photo.get("description") or photo.get("alt_description"),
                    "photographer": photo.get("user", {}).get("name"),
                }
                for photo in results
            ]

        try:
            return retry_sync(_call, attempts=2, base_delay=0.5, exceptions=(httpx.HTTPError,))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Unsplash 搜索失败 '%s': %s", query, exc)
            return []

    def get_photo_url(self, query: str) -> str | None:
        """获取单张图片 URL。"""
        photos = self.search_photos(query, per_page=1)
        if photos:
            return photos[0].get("url")
        return None


# 全局服务实例
_unsplash_service: UnsplashService | None = None


def get_unsplash_service() -> UnsplashService:
    """获取 Unsplash 服务实例（单例模式）。"""
    global _unsplash_service
    if _unsplash_service is None:
        _unsplash_service = UnsplashService()
    return _unsplash_service
