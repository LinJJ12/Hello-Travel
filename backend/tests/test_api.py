"""API 层集成测试（monkeypatch 外部依赖，不触网）。"""

from __future__ import annotations

import time
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.core.cache import TTLCache
from app.models.schemas import (
    Attraction,
    Budget,
    DayPlan,
    Location,
    TripPlan,
)


def _sample_plan() -> TripPlan:
    return TripPlan(
        city="杭州",
        cities=["杭州"],
        start_date="2026-10-01",
        end_date="2026-10-01",
        days=[
            DayPlan(
                date="2026-10-01",
                day_index=0,
                city="杭州",
                description="西湖一日游",
                transportation="公共交通",
                accommodation="舒适型酒店",
                attractions=[
                    Attraction(
                        name="西湖",
                        address="杭州市西湖区",
                        location=Location(longitude=120.15, latitude=30.25),
                        visit_duration=180,
                        description="著名景区",
                        ticket_price=0,
                    )
                ],
            )
        ],
        weather_info=[],
        overall_suggestions="注意防晒",
        budget=Budget(total_attractions=0, total_hotels=400, total_meals=160, total_transportation=0, total=560),
    )


def _plan_payload() -> dict:
    return {
        "city": "杭州",
        "start_date": "2026-10-01",
        "end_date": "2026-10-01",
        "travel_days": 1,
        "transportation": "公共交通",
        "accommodation": "舒适型酒店",
        "preferences": ["自然风光"],
    }


class _FakeAgent:
    """替身 Agent：立即返回样例计划，避免真实 LLM 调用。"""

    async def plan_trip(self, request, progress_callback=None):
        if progress_callback is not None:
            await progress_callback("planning", "正在生成旅行计划...", 85)
        return _sample_plan()


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


# --------------------------------------------------------------------------- #
# 基础端点
# --------------------------------------------------------------------------- #
def test_root_and_global_health(client: TestClient):
    root = client.get("/")
    assert root.status_code == 200

    health = client.get("/health")
    assert health.status_code == 200
    body = health.json()
    assert body["status"] == "healthy"
    assert body["environment"] == "local"


# --------------------------------------------------------------------------- #
# 地图服务（回归：原实现访问不存在的 service.mcp_tool 导致 500）
# --------------------------------------------------------------------------- #
def test_map_health_reports_configuration(client: TestClient, monkeypatch):
    fake_service = SimpleNamespace(configured=True, _cache=TTLCache(ttl=60))
    monkeypatch.setattr("app.api.routes.map.get_amap_service", lambda: fake_service)

    resp = client.get("/api/map/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["amap_configured"] is True


def test_map_health_when_not_configured(client: TestClient, monkeypatch):
    fake_service = SimpleNamespace(configured=False, _cache=TTLCache(ttl=60))
    monkeypatch.setattr("app.api.routes.map.get_amap_service", lambda: fake_service)

    resp = client.get("/api/map/health")
    assert resp.status_code == 200
    assert resp.json()["amap_configured"] is False


def test_map_poi_endpoint_uses_service(client: TestClient, monkeypatch):
    fake_service = SimpleNamespace(search_poi=lambda *a, **k: [])
    monkeypatch.setattr("app.api.routes.map.get_amap_service", lambda: fake_service)

    resp = client.get("/api/map/poi", params={"keywords": "故宫", "city": "北京"})
    assert resp.status_code == 200
    assert resp.json()["success"] is False


def test_map_route_empty_result_returns_success_false(client: TestClient, monkeypatch):
    """回归：解析失败时返回空 dict，不能直接塞进 data（会触发响应模型校验错误）。"""
    fake_service = SimpleNamespace(plan_route=lambda **kwargs: {})
    monkeypatch.setattr("app.api.routes.map.get_amap_service", lambda: fake_service)

    resp = client.post(
        "/api/map/route",
        json={"origin_address": "A", "destination_address": "B", "route_type": "walking"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert body["data"] is None


def test_map_route_success(client: TestClient, monkeypatch):
    fake_service = SimpleNamespace(
        plan_route=lambda **kwargs: {
            "distance": 1200.0,
            "duration": 900,
            "route_type": "walking",
            "description": "walking路线规划结果",
        }
    )
    monkeypatch.setattr("app.api.routes.map.get_amap_service", lambda: fake_service)

    resp = client.post(
        "/api/map/route",
        json={"origin_address": "A", "destination_address": "B", "route_type": "walking"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["distance"] == 1200.0


# --------------------------------------------------------------------------- #
# 旅行规划
# --------------------------------------------------------------------------- #
def test_trip_health_endpoint(client: TestClient, monkeypatch):
    fake_agent = SimpleNamespace(
        planner_agent=SimpleNamespace(name="行程规划专家"),
        weather_agent=SimpleNamespace(list_tools=lambda: [1, 2]),
        hotel_agent=SimpleNamespace(list_tools=lambda: [1]),
    )
    monkeypatch.setattr("app.api.routes.trip.get_trip_planner_agent", lambda: fake_agent)

    resp = client.get("/api/trip/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["agent_name"] == "行程规划专家"
    assert body["tools_count"] == 3


def test_plan_validation_error_is_structured(client: TestClient):
    resp = client.post("/api/trip/plan", json={"city": "杭州"})  # 缺少必填字段
    assert resp.status_code == 422
    body = resp.json()
    assert body["success"] is False
    assert body["error_code"] == "VALIDATION_ERROR"


def test_plan_flow_via_status_polling(client: TestClient, monkeypatch):
    """提交任务 → 轮询状态 → 拿到完成的行程与知识图谱。"""
    monkeypatch.setattr("app.api.routes.trip.get_trip_planner_agent", lambda: _FakeAgent())

    submit = client.post("/api/trip/plan", json=_plan_payload())
    assert submit.status_code == 200
    task_id = submit.json()["task_id"]
    assert task_id

    body = None
    for _ in range(100):
        body = client.get(f"/api/trip/status/{task_id}").json()
        if body["status"] in {"completed", "failed"}:
            break
        time.sleep(0.05)

    assert body is not None, "未获取到任务状态"
    assert body["status"] == "completed", body
    assert body["result"]["data"]["city"] == "杭州"
    # 知识图谱由真实实现构建，应包含景点节点
    graph = body["result"]["graph_data"]
    assert graph["nodes"], "知识图谱不应为空"


def test_trip_history_endpoint_is_empty_on_fresh_storage(client: TestClient):
    resp = client.get("/api/trip/history")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


def test_unknown_task_status_returns_404(client: TestClient):
    resp = client.get("/api/trip/status/does-not-exist")
    assert resp.status_code == 404


# --------------------------------------------------------------------------- #
# 运行时配置 / 记忆
# --------------------------------------------------------------------------- #
def test_settings_get_masks_secrets(client: TestClient):
    resp = client.get("/api/settings")
    assert resp.status_code == 200
    data = resp.json()["data"]

    # 机密字段以掩码返回，绝不回传明文
    assert "test-llm-key" not in data["openai_api_key"]
    assert data["openai_api_key"]
    # 非机密字段原样返回
    assert data["openai_model"] == "test-model"


def test_memory_list_disabled_by_default(client: TestClient):
    resp = client.get("/api/memory/list", params={"user_id": "u1"})
    assert resp.status_code == 200
    assert resp.json()["code"] == 400
