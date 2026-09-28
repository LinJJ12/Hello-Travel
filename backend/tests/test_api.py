"""API 层集成测试（用 monkeypatch 替换外部依赖，不触网）。"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
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
        start_date="2026-10-01",
        end_date="2026-10-01",
        days=[
            DayPlan(
                date="2026-10-01",
                day_index=0,
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


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def test_root_and_global_health(client: TestClient):
    root = client.get("/")
    assert root.status_code == 200
    assert root.json()["status"] == "running"

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "healthy"


def test_trip_health_endpoint_does_not_crash(client: TestClient, monkeypatch):
    """回归测试：原实现访问了不存在的 agent.agent 属性导致 AttributeError。"""
    fake_agent = SimpleNamespace(
        llm=SimpleNamespace(model="test-model"),
        amap_service=SimpleNamespace(api_key="k"),
    )
    monkeypatch.setattr("app.api.routes.trip.get_trip_planner_agent", lambda: fake_agent)

    resp = client.get("/api/trip/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["llm_model"] == "test-model"


def test_map_health_endpoint_does_not_crash(client: TestClient, monkeypatch):
    """回归测试：原实现访问了不存在的 service.mcp_tool 属性导致 AttributeError。"""
    fake_service = SimpleNamespace(api_key="k", _cache={})
    monkeypatch.setattr("app.api.routes.map.get_amap_service", lambda: fake_service)

    resp = client.get("/api/map/health")
    assert resp.status_code == 200
    assert resp.json()["amap_configured"] is True


def test_map_route_empty_result_returns_success_false(client: TestClient, monkeypatch):
    """回归测试：原实现在解析失败时返回空 dict，触发响应模型校验错误。"""
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


def test_plan_endpoint_returns_plan(client: TestClient, monkeypatch):
    fake_agent = SimpleNamespace(plan_trip=lambda request: _sample_plan())
    monkeypatch.setattr("app.api.routes.trip.get_trip_planner_agent", lambda: fake_agent)

    resp = client.post(
        "/api/trip/plan",
        json={
            "city": "杭州",
            "start_date": "2026-10-01",
            "end_date": "2026-10-01",
            "travel_days": 1,
            "transportation": "公共交通",
            "accommodation": "舒适型酒店",
            "preferences": ["自然风光"],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["city"] == "杭州"


def test_plan_validation_error_is_structured(client: TestClient):
    resp = client.post("/api/trip/plan", json={"city": "杭州"})  # 缺少必填字段
    assert resp.status_code == 422
    body = resp.json()
    assert body["success"] is False
    assert body["error_code"] == "VALIDATION_ERROR"


def test_knowledge_graph_endpoint(client: TestClient):
    resp = client.post("/api/assistant/knowledge-graph", json=_sample_plan().model_dump())
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert any(node["category"] == "attraction" for node in body["nodes"])


def test_assistant_chat_endpoint(client: TestClient, monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.assistant.get_llm",
        lambda: SimpleNamespace(generate=lambda *a, **k: "建议早上前往西湖。"),
    )
    resp = client.post(
        "/api/assistant/chat",
        json={"question": "几点去西湖合适？", "trip_plan": _sample_plan().model_dump()},
    )
    assert resp.status_code == 200
    assert resp.json()["answer"] == "建议早上前往西湖。"


def test_async_plan_job_flow(client: TestClient, monkeypatch):
    fake_agent = SimpleNamespace(plan_trip=lambda request: _sample_plan())
    monkeypatch.setattr("app.api.routes.trip.get_trip_planner_agent", lambda: fake_agent)

    submit = client.post(
        "/api/trip/plan_async",
        json={
            "city": "杭州",
            "start_date": "2026-10-01",
            "end_date": "2026-10-01",
            "travel_days": 1,
            "transportation": "公共交通",
            "accommodation": "舒适型酒店",
            "preferences": [],
        },
    )
    assert submit.status_code == 200
    job_id = submit.json()["job_id"]
    assert job_id

    # TestClient 是同步的，后台任务在请求结束后已执行完毕
    result = client.get(f"/api/trip/plan_result/{job_id}")
    assert result.status_code == 200
    assert result.json()["data"]["city"] == "杭州"


def test_unknown_job_returns_404(client: TestClient):
    resp = client.get("/api/trip/plan_result/does-not-exist")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "NOT_FOUND"
