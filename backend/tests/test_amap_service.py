"""高德 REST 服务层的单元测试（monkeypatch httpx，不触网）。

覆盖合并后的 ``AmapService``（原 TripStar 版本是返回空值的 MCP 桩）：
- 未配置 Key 时优雅降级为空结果，而不是抛错；
- POI / 天气 / 地理编码 / 路线 / POI 详情 的解析与缓存；
- 接口返回失败状态码时不崩溃。
"""

from __future__ import annotations

import httpx
import pytest

from app.config import settings
from app.services import amap_service as amap_module
from app.services.amap_service import AmapService, reset_amap_service


class _FakeResponse:
    def __init__(self, payload, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "boom",
                request=httpx.Request("GET", "https://restapi.amap.com"),
                response=None,
            )


def _install_fake_http(monkeypatch, routes: dict):
    """替换 httpx.get，按 path 返回预设 payload，并记录调用。"""
    calls: list[tuple[str, dict]] = []

    def fake_get(url, params=None, timeout=None, trust_env=None):
        path = url.replace("https://restapi.amap.com", "")
        calls.append((path, dict(params or {})))
        if path not in routes:
            raise AssertionError(f"未预期的请求: {path}")
        handler = routes[path]
        return _FakeResponse(handler(params) if callable(handler) else handler)

    monkeypatch.setattr(amap_module.httpx, "get", fake_get)
    return calls


@pytest.fixture(autouse=True)
def _reset_singleton():
    reset_amap_service()
    yield
    reset_amap_service()


# --------------------------------------------------------------------------- #
# 未配置 Key
# --------------------------------------------------------------------------- #
def test_unconfigured_service_degrades_gracefully(monkeypatch):
    monkeypatch.setattr(settings, "vite_amap_web_key", "")
    svc = AmapService()

    assert svc.configured is False
    assert svc.search_poi("故宫", "北京") == []
    assert svc.get_weather("北京") == []
    assert svc.geocode("故宫") is None
    assert svc.plan_route("A", "B") == {}
    assert svc.get_poi_detail("B1") == {}


# --------------------------------------------------------------------------- #
# POI
# --------------------------------------------------------------------------- #
def test_search_poi_parses_and_caches(monkeypatch):
    routes = {
        "/v3/place/text": {
            "status": "1",
            "pois": [
                {
                    "id": "B1",
                    "name": "故宫博物院",
                    "type": "风景名胜;博物馆",
                    "address": "景山前街4号",
                    "location": "116.397,39.918",
                    "tel": ["010-85007421"],
                }
            ],
        }
    }
    calls = _install_fake_http(monkeypatch, routes)
    svc = AmapService()

    pois = svc.search_poi("故宫", "北京")
    assert len(pois) == 1
    assert pois[0].name == "故宫博物院"
    assert pois[0].location.longitude == pytest.approx(116.397)
    assert pois[0].tel == "010-85007421"

    # 第二次应命中缓存，不再发起 HTTP 请求
    hits_before = len(calls)
    svc.search_poi("故宫", "北京")
    assert len(calls) == hits_before


def test_search_poi_skips_items_without_location(monkeypatch):
    routes = {
        "/v3/place/text": {
            "status": "1",
            "pois": [
                {"id": "X", "name": "无坐标点", "location": ""},
                {"id": "Y", "name": "有坐标点", "location": "120.1,30.2"},
            ],
        }
    }
    _install_fake_http(monkeypatch, routes)
    pois = AmapService().search_poi("任意", "杭州")
    assert [p.name for p in pois] == ["有坐标点"]


def test_search_poi_returns_empty_on_api_error(monkeypatch):
    """高德返回 status=0（如配额/Key 无效）时应降级为空列表，而不是抛异常。"""
    _install_fake_http(monkeypatch, {"/v3/place/text": {"status": "0", "info": "INVALID_USER_KEY"}})
    assert AmapService().search_poi("故宫", "北京") == []


def test_search_pois_multi_dedupes(monkeypatch):
    def handler(params):
        keyword = params.get("keywords")
        return {
            "status": "1",
            "pois": [
                {"id": "SAME", "name": "西湖", "location": "120.1,30.2"},
                {"id": keyword, "name": f"{keyword}专属", "location": "120.2,30.3"},
            ],
        }

    _install_fake_http(monkeypatch, {"/v3/place/text": handler})
    pois = AmapService().search_pois_multi(["自然风光", "历史文化"], "杭州")

    ids = [p.id for p in pois]
    assert ids.count("SAME") == 1  # 跨关键词去重
    assert "自然风光" in ids and "历史文化" in ids


# --------------------------------------------------------------------------- #
# 天气
# --------------------------------------------------------------------------- #
def test_get_weather_uses_adcode_and_parses_casts(monkeypatch):
    def weather_handler(params):
        # 应优先使用地理编码得到的 adcode
        assert params["city"] == "110000"
        return {
            "status": "1",
            "forecasts": [
                {
                    "casts": [
                        {
                            "date": "2026-10-01",
                            "dayweather": "晴",
                            "nightweather": "多云",
                            "daytemp": "25",
                            "nighttemp": "15",
                            "daywind": "南",
                            "daypower": "1-3",
                        }
                    ]
                }
            ],
        }

    _install_fake_http(
        monkeypatch,
        {
            "/v3/geocode/geo": {
                "status": "1",
                "geocodes": [{"location": "116.4,39.9", "adcode": "110000"}],
            },
            "/v3/weather/weatherInfo": weather_handler,
        },
    )

    weather = AmapService().get_weather("北京")
    assert len(weather) == 1
    assert weather[0].city == "北京"
    assert weather[0].day_weather == "晴"
    assert weather[0].day_temp == 25  # 字符串 "25" 已被解析为整数
    assert weather[0].night_temp == 15


# --------------------------------------------------------------------------- #
# 地理编码
# --------------------------------------------------------------------------- #
def test_geocode_parses_location(monkeypatch):
    _install_fake_http(
        monkeypatch,
        {"/v3/geocode/geo": {"status": "1", "geocodes": [{"location": "120.15,30.25"}]}},
    )
    location = AmapService().geocode("西湖", "杭州")
    assert location is not None
    assert (location.longitude, location.latitude) == (120.15, 30.25)


def test_geocode_returns_none_when_no_result(monkeypatch):
    _install_fake_http(monkeypatch, {"/v3/geocode/geo": {"status": "1", "geocodes": []}})
    assert AmapService().geocode("不存在的地方") is None


# --------------------------------------------------------------------------- #
# 路线
# --------------------------------------------------------------------------- #
def test_plan_route_returns_empty_when_geocode_fails(monkeypatch):
    _install_fake_http(monkeypatch, {"/v3/geocode/geo": {"status": "1", "geocodes": []}})
    assert AmapService().plan_route("A", "B", route_type="walking") == {}


def test_plan_route_success(monkeypatch):
    def geo_handler(params):
        address = params["address"]
        location = "116.40,39.90" if address == "A" else "116.50,39.95"
        return {"status": "1", "geocodes": [{"location": location}]}

    _install_fake_http(
        monkeypatch,
        {
            "/v3/geocode/geo": geo_handler,
            "/v3/direction/walking": {
                "status": "1",
                "route": {"paths": [{"distance": "1200", "duration": "900"}]},
            },
        },
    )

    route = AmapService().plan_route("A", "B", route_type="walking")
    assert route["distance"] == 1200.0
    assert route["duration"] == 900
    assert route["route_type"] == "walking"


# --------------------------------------------------------------------------- #
# POI 详情
# --------------------------------------------------------------------------- #
def test_get_poi_detail_cached(monkeypatch):
    calls = _install_fake_http(
        monkeypatch,
        {"/v5/place/detail": {"status": "1", "id": "B1", "name": "故宫"}},
    )
    svc = AmapService()
    assert svc.get_poi_detail("B1")["name"] == "故宫"

    hits_before = len(calls)
    svc.get_poi_detail("B1")
    assert len(calls) == hits_before
