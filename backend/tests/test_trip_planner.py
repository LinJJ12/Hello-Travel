"""行程规划 Agent 的解析 / 查询构建 / 兜底逻辑测试（不依赖网络与真实密钥）。"""

from __future__ import annotations

import json

from app.agents.trip_planner_agent import MultiAgentTripPlanner
from app.models.schemas import CityStay, TripRequest
from app.services.knowledge_graph_service import build_knowledge_graph


def _bare_planner() -> MultiAgentTripPlanner:
    """构造一个跳过 __init__ 的实例，仅用于测试纯逻辑方法。

    ``__init__`` 需要真实 LLM 与地图工具，这里不触碰。
    """
    return object.__new__(MultiAgentTripPlanner)


def _request() -> TripRequest:
    return TripRequest(
        city="杭州",
        start_date="2026-10-01",
        end_date="2026-10-01",
        travel_days=1,
        transportation="步行",
        accommodation="舒适型酒店",
    )


def _plan_dict() -> dict:
    return {
        "city": "杭州",
        "cities": ["杭州"],
        "start_date": "2026-10-01",
        "end_date": "2026-10-01",
        "days": [
            {
                "date": "2026-10-01",
                "day_index": 0,
                "city": "杭州",
                "description": "西湖一日游",
                "transportation": "步行",
                "accommodation": "舒适型酒店",
                "attractions": [
                    {
                        "name": "西湖",
                        "address": "杭州市西湖区",
                        "location": {"longitude": 120.15, "latitude": 30.25},
                        "visit_duration": 180,
                        "description": "著名景区",
                        "ticket_price": 0,
                    }
                ],
                "meals": [],
            }
        ],
        "weather_info": [],
        "overall_suggestions": "注意防晒",
        "budget": {
            "total_attractions": 0,
            "total_hotels": 400,
            "total_meals": 160,
            "total_transportation": 0,
            "total_inter_city_transport": 0,
            "total": 560,
        },
    }


def _raw_json() -> str:
    return json.dumps(_plan_dict(), ensure_ascii=False)


# --------------------------------------------------------------------------- #
# _parse_response：第一道防线 extract_json（app.core.json_utils）
# --------------------------------------------------------------------------- #
def test_parse_response_handles_fenced_json():
    planner = _bare_planner()
    plan = planner._parse_response(f"```json\n{_raw_json()}\n```", _request())
    assert plan.city == "杭州"
    assert len(plan.days) == 1
    assert plan.days[0].attractions[0].name == "西湖"


def test_parse_response_handles_leading_and_trailing_prose():
    planner = _bare_planner()
    raw = f"好的，以下是为您规划的行程：\n{_raw_json()}\n希望对您有帮助！"
    plan = planner._parse_response(raw, _request())
    assert plan.city == "杭州"


def test_parse_response_handles_trailing_comma():
    planner = _bare_planner()
    # 真正的「尾逗号」：在最后一个 } 之前多出一个逗号
    broken = _raw_json()[:-1] + ",}"
    plan = planner._parse_response(broken, _request())
    assert plan.overall_suggestions == "注意防晒"


def test_parse_response_handles_duplicate_comma():
    """LLM 偶发双逗号（",,"）时也应能正常解析。

    注：此处刻意在中间字段后追加逗号，形成 `,,`；原用例误把这种输入当成
    「尾逗号」场景，导致断言的是错误行为。
    """
    planner = _bare_planner()
    broken = _raw_json().replace(
        '"overall_suggestions": "注意防晒"',
        '"overall_suggestions": "注意防晒",',
    )
    assert ",," in broken
    plan = planner._parse_response(broken, _request())
    assert plan.overall_suggestions == "注意防晒"


def test_parse_response_handles_truncated_output():
    """max_tokens 截断导致末尾括号不闭合时，应能自动补齐。"""
    planner = _bare_planner()
    truncated = _raw_json()[: _raw_json().rfind("}")]
    plan = planner._parse_response(truncated, _request())
    assert plan.city == "杭州"
    assert plan.days[0].attractions[0].name == "西湖"


# --------------------------------------------------------------------------- #
# 各修复工具
# --------------------------------------------------------------------------- #
def test_sanitize_json_str_fixes_arithmetic_budget():
    """LLM 把预算写成算术表达式时应取等号后的最终结果。"""
    planner = _bare_planner()
    cleaned = planner._sanitize_json_str('{"budget": {"total": 30+54+120+120=324}}')
    assert json.loads(cleaned)["budget"]["total"] == 324


def test_sanitize_json_str_fixes_trailing_comma_and_line_comment():
    planner = _bare_planner()
    cleaned = planner._sanitize_json_str('{"a": 1, // 这是注释\n "b": 2,}')
    assert json.loads(cleaned) == {"a": 1, "b": 2}


def test_fix_unescaped_quotes():
    planner = _bare_planner()
    fixed = planner._fix_unescaped_quotes('{"description": "这是"好的"景点"}')
    assert json.loads(fixed)["description"] == "这是'好的'景点"


def test_repair_truncated_json_closes_brackets():
    planner = _bare_planner()
    repaired = planner._repair_truncated_json('{"days": [{"attractions": [{"name": "故宫"')
    data = json.loads(repaired)
    assert data["days"][0]["attractions"][0]["name"] == "故宫"


# --------------------------------------------------------------------------- #
# 查询构建
# --------------------------------------------------------------------------- #
def test_build_planner_query_includes_all_cities_and_memory():
    planner = _bare_planner()
    request = TripRequest(
        city="北京",
        cities=[CityStay(city="北京", days=2), CityStay(city="西安", days=3)],
        start_date="2026-10-01",
        end_date="2026-10-05",
        travel_days=5,
        transportation="公共交通",
        accommodation="经济型酒店",
        preferences=["历史文化"],
    )

    query = planner._build_planner_query(
        request,
        {"北京": "故宫", "西安": "兵马俑"},
        {"北京": "晴", "西安": "多云"},
        {"北京": "某酒店", "西安": "另一酒店"},
        "用户历史偏好：偏爱博物馆",
    )

    assert "北京" in query and "西安" in query
    assert "故宫" in query and "兵马俑" in query
    assert "用户历史偏好：偏爱博物馆" in query
    # 多城市时要求模型输出城际交通预算字段
    assert "total_inter_city_transport" in query


def test_build_planner_query_single_city_has_no_intercity_block():
    planner = _bare_planner()
    query = planner._build_planner_query(
        _request(),
        {"杭州": "西湖"},
        {"杭州": "晴"},
        {"杭州": "某酒店"},
    )
    assert "西湖" in query
    assert "**多城市特殊要求:**" not in query


# --------------------------------------------------------------------------- #
# 兜底计划
# --------------------------------------------------------------------------- #
def test_create_fallback_plan_generates_one_day_per_travel_day():
    planner = _bare_planner()
    request = TripRequest(
        city="杭州",
        start_date="2026-10-01",
        end_date="2026-10-03",
        travel_days=3,
        transportation="公共交通",
        accommodation="舒适型酒店",
    )

    plan = planner._create_fallback_plan(request)
    assert plan.city == "杭州"
    assert len(plan.days) == 3
    assert plan.days[0].date == "2026-10-01"
    assert plan.days[2].date == "2026-10-03"
    assert all(day.meals for day in plan.days)


# --------------------------------------------------------------------------- #
# 知识图谱
# --------------------------------------------------------------------------- #
def test_knowledge_graph_contains_city_day_and_attraction_nodes():
    from app.models.schemas import TripPlan

    graph = build_knowledge_graph(TripPlan(**_plan_dict()), language="zh")

    assert graph["nodes"], "图谱节点不应为空"
    assert graph["edges"], "图谱边不应为空"

    names = {node["name"] for node in graph["nodes"]}
    assert "杭州" in names
    assert "西湖" in names
    assert any(node["name"].startswith("第1天") for node in graph["nodes"])


def test_knowledge_graph_supports_english_labels():
    from app.models.schemas import TripPlan

    graph = build_knowledge_graph(TripPlan(**_plan_dict()), language="en")
    names = {node["name"] for node in graph["nodes"]}
    assert "Day 1" in names
    assert "杭州" in names  # 城市名保持原文


def test_knowledge_graph_multi_city_uses_root_node():
    """多城市行程应生成「A → B」根节点，并把预算/建议挂到根节点上。

    该分支曾疑似存在 ``root_id`` 未定义的 NameError（仅在多城市 + 有预算时触发），
    核实后确认已正确赋值，这里用测试锁住行为，防止后续回归。
    """
    from app.models.schemas import TripPlan

    plan_dict = _plan_dict()
    plan_dict["cities"] = ["杭州", "苏州"]
    plan_dict["days"][0]["city"] = "杭州"
    plan_dict["days"].append(
        {**plan_dict["days"][0], "date": "2026-10-02", "day_index": 1, "city": "苏州"}
    )

    graph = build_knowledge_graph(TripPlan(**plan_dict), language="zh")

    ids = {node["id"] for node in graph["nodes"]}
    names = {node["name"] for node in graph["nodes"]}
    edges = {(e["source"], e["target"]) for e in graph["edges"]}

    assert "杭州 → 苏州" in names, "多城市应生成合并根节点"
    assert "trip_root" in ids
    assert "city_杭州" in ids
    assert "city_苏州" in ids
    assert ("trip_root", "city_杭州") in edges
    assert ("trip_root", "city_苏州") in edges
    # 有预算时预算节点挂到根节点——这正是原 NameError 的触发路径
    assert ("trip_root", "budget_total") in edges


def test_knowledge_graph_single_city_has_no_root_node():
    """单城市不应生成 trip_root，城市自身即根节点。"""
    from app.models.schemas import TripPlan

    graph = build_knowledge_graph(TripPlan(**_plan_dict()), language="zh")
    ids = {node["id"] for node in graph["nodes"]}
    assert "trip_root" not in ids
    assert "city_杭州" in ids
