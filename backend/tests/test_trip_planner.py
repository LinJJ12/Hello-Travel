"""行程规划 Agent 的对齐 / 兜底逻辑测试（不依赖网络与真实密钥）。"""

from __future__ import annotations

from app.agents.trip_planner_agent import MultiAgentTripPlanner
from app.models.schemas import Location, POIInfo, TripRequest


def _poi(poi_id: str, name: str, lng: float = 116.4, lat: float = 39.9, type_: str = "风景名胜") -> POIInfo:
    return POIInfo(
        id=poi_id,
        name=name,
        type=type_,
        address=f"{name}地址",
        location=Location(longitude=lng, latitude=lat),
    )


def _planner(attractions=None, hotels=None) -> MultiAgentTripPlanner:
    """构造一个跳过 __init__ 的实例，仅用于测试纯逻辑方法。"""
    planner = object.__new__(MultiAgentTripPlanner)
    planner._real_attractions = attractions or []
    planner._real_weather = []
    planner._real_hotels = hotels or []
    return planner


def test_attractions_aligned_to_search_results():
    planner = _planner(attractions=[_poi("A1", "故宫博物院"), _poi("A2", "天坛公园")])
    data = {
        "days": [
            {
                "attractions": [
                    {"name": "故宫博物院", "address": "旧地址", "location": {"longitude": 0, "latitude": 0},
                     "description": "很棒", "ticket_price": 60},
                    {"name": "天坛公园", "address": "x", "location": {"longitude": 0, "latitude": 0}},
                ]
            }
        ]
    }
    planner._enforce_attractions_from_search_results(data, planner._real_attractions)

    names = [a["name"] for a in data["days"][0]["attractions"]]
    assert names == ["故宫博物院", "天坛公园"]
    # 坐标被替换为真实值
    assert data["days"][0]["attractions"][0]["location"] == {"longitude": 116.4, "latitude": 39.9}
    # 保留 LLM 的文案与费用
    assert data["days"][0]["attractions"][0]["description"] == "很棒"
    assert data["days"][0]["attractions"][0]["ticket_price"] == 60
    # 地址被真实地址覆盖
    assert data["days"][0]["attractions"][0]["address"] == "故宫博物院地址"


def test_invented_attraction_replaced_by_real_poi():
    planner = _planner(attractions=[_poi("A1", "西湖"), _poi("A2", "灵隐寺")])
    data = {"days": [{"attractions": [{"name": "某个不存在的景点", "location": {"longitude": 1, "latitude": 1}}]}]}
    planner._enforce_attractions_from_search_results(data, planner._real_attractions)

    result = data["days"][0]["attractions"]
    assert len(result) == 1
    assert result[0]["name"] in {"西湖", "灵隐寺"}
    assert result[0]["poi_id"] in {"A1", "A2"}


def test_duplicate_attraction_across_days_deduped():
    planner = _planner(attractions=[_poi("A1", "西湖"), _poi("A2", "灵隐寺")])
    data = {
        "days": [
            {"attractions": [{"name": "西湖"}]},
            {"attractions": [{"name": "西湖"}]},
        ]
    }
    planner._enforce_attractions_from_search_results(data, planner._real_attractions)

    day0 = {a["name"] for a in data["days"][0]["attractions"]}
    day1 = {a["name"] for a in data["days"][1]["attractions"]}
    assert day0 == {"西湖"}
    # 第二天不应再重复西湖，而是回填另一个未使用的真实景点
    assert "西湖" not in day1
    assert day1 == {"灵隐寺"}


def test_reservation_flag_detected():
    assert MultiAgentTripPlanner._needs_reservation("故宫博物院") is True
    assert MultiAgentTripPlanner._needs_reservation("秦始皇兵马俑博物馆") is True
    assert MultiAgentTripPlanner._needs_reservation("西湖") is False


def test_hotels_forced_to_search_results():
    hotels = [_poi("H1", "如家酒店(王府井店)", type_="住宿服务")]
    planner = _planner(hotels=hotels)
    data = {"days": [{"hotel": {"name": "如家快捷酒店", "estimated_cost": 300}}]}
    planner._enforce_hotels_from_search_results(data, hotels)

    hotel = data["days"][0]["hotel"]
    assert hotel["name"] == "如家酒店(王府井店)"
    assert hotel["estimated_cost"] == 300  # LLM 估算保留


def test_ensure_budget_computed_when_missing():
    data = {
        "days": [
            {
                "attractions": [{"ticket_price": 60}, {"ticket_price": 40}],
                "meals": [{"estimated_cost": 30}, {"estimated_cost": 50}, {"estimated_cost": 80}],
                "hotel": {"estimated_cost": 400},
            }
        ]
    }
    MultiAgentTripPlanner._ensure_budget(data)
    assert data["budget"]["total_attractions"] == 100
    assert data["budget"]["total_meals"] == 160
    assert data["budget"]["total_hotels"] == 400
    assert data["budget"]["total"] == 660


def test_ensure_budget_keeps_existing():
    data = {"days": [], "budget": {"total": 999}}
    MultiAgentTripPlanner._ensure_budget(data)
    assert data["budget"]["total"] == 999


def test_fallback_plan_uses_real_pois():
    planner = _planner(
        attractions=[_poi("A1", "西湖"), _poi("A2", "灵隐寺"), _poi("A3", "雷峰塔")],
        hotels=[_poi("H1", "杭州某酒店", type_="住宿服务")],
    )
    request = TripRequest(
        city="杭州",
        start_date="2026-10-01",
        end_date="2026-10-02",
        travel_days=2,
        transportation="公共交通",
        accommodation="舒适型酒店",
    )
    plan = planner._create_fallback_plan(request)

    assert plan.city == "杭州"
    assert len(plan.days) == 2
    # 兜底也应使用真实景点名称，而不是 "杭州景点1"
    all_names = [a.name for day in plan.days for a in day.attractions]
    assert all_names
    assert all("景点1" not in name for name in all_names)
    assert plan.days[0].hotel is not None
