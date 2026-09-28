"""生成一份用于浏览器/端到端验证的「已完成」行程任务。

不依赖 LLM 与任何外部密钥：直接用应用自身的 pydantic 模型构造一份**多城市**行程，
再调用真实的 ``build_knowledge_graph`` 生成图谱，最后按 ``trip.py`` 的持久化格式
写入 ``backend/data/trip_tasks/<task_id>.json``。

这样浏览器访问 ``/result?plan_id=<task_id>`` 时，结果页会通过
``GET /api/trip/status/<task_id>`` 读到它，从而真实渲染 Result 页与 ECharts 知识图谱。

用法::

    python scripts/seed_demo_task.py [task_id]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.schemas import (  # noqa: E402
    Attraction,
    Budget,
    DayPlan,
    Hotel,
    Location,
    Meal,
    TripPlan,
    TripPlanResponse,
    WeatherInfo,
)
from app.services.knowledge_graph_service import build_knowledge_graph  # noqa: E402

DEFAULT_TASK_ID = "e2e00001"
DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "trip_tasks"


def _loc(lng: float, lat: float) -> Location:
    return Location(longitude=lng, latitude=lat)


def build_plan() -> TripPlan:
    """北京 2 天 + 西安 1 天的多城市行程（刻意触发多城市图谱分支）。"""
    return TripPlan(
        city="北京",
        cities=["北京", "西安"],
        start_date="2026-10-01",
        end_date="2026-10-03",
        days=[
            DayPlan(
                date="2026-10-01",
                day_index=0,
                city="北京",
                description="抵达北京，游览故宫与天安门广场",
                transportation="公共交通",
                accommodation="经济型酒店",
                hotel=Hotel(
                    name="北京王府井智选假日酒店",
                    address="北京市东城区王府井大街",
                    location=_loc(116.4108, 39.9151),
                    price_range="¥400-600",
                    rating="4.6",
                    distance="距故宫 1.2km",
                    type="经济型酒店",
                    estimated_cost=480,
                ),
                attractions=[
                    Attraction(
                        name="故宫博物院",
                        address="北京市东城区景山前街4号",
                        location=_loc(116.3972, 39.9163),
                        visit_duration=180,
                        description="明清两代皇家宫殿，世界现存规模最大的木质结构古建筑群",
                        category="历史文化",
                        rating=4.9,
                        ticket_price=60,
                        reservation_required=True,
                        reservation_tips="需提前 7 天在官网实名预约",
                    ),
                    Attraction(
                        name="天安门广场",
                        address="北京市东城区长安街",
                        location=_loc(116.3975, 39.9087),
                        visit_duration=60,
                        description="世界最大的城市中心广场",
                        category="历史文化",
                        rating=4.8,
                        ticket_price=0,
                    ),
                ],
                meals=[
                    Meal(type="lunch", name="四季民福烤鸭店", address="北京市东城区",
                         location=_loc(116.4000, 39.9200), description="北京烤鸭",
                         estimated_cost=180),
                    Meal(type="dinner", name="护国寺小吃", address="北京市西城区",
                         location=_loc(116.3800, 39.9300), description="老北京小吃",
                         estimated_cost=60),
                ],
            ),
            DayPlan(
                date="2026-10-02",
                day_index=1,
                city="北京",
                description="游览颐和园与南锣鼓巷",
                transportation="公共交通",
                accommodation="经济型酒店",
                hotel=Hotel(
                    name="北京王府井智选假日酒店",
                    address="北京市东城区王府井大街",
                    location=_loc(116.4108, 39.9151),
                    price_range="¥400-600",
                    rating="4.6",
                    distance="距颐和园 15km",
                    type="经济型酒店",
                    estimated_cost=480,
                ),
                attractions=[
                    Attraction(
                        name="颐和园",
                        address="北京市海淀区新建宫门路19号",
                        location=_loc(116.2755, 39.9999),
                        visit_duration=150,
                        description="中国现存规模最大的皇家园林",
                        category="自然风光",
                        rating=4.8,
                        ticket_price=30,
                    ),
                ],
                meals=[
                    Meal(type="lunch", name="海淀食堂", address="北京市海淀区",
                         location=_loc(116.2800, 39.9950), description="家常菜",
                         estimated_cost=50),
                ],
            ),
            DayPlan(
                date="2026-10-03",
                day_index=2,
                city="西安",
                is_transfer_day=True,
                transfer_info="北京西站 → 西安北站，高铁约 4.5 小时",
                description="高铁前往西安，游览兵马俑与回民街",
                transportation="高铁",
                accommodation="舒适型酒店",
                hotel=Hotel(
                    name="西安钟楼亚朵酒店",
                    address="西安市碑林区钟楼南大街",
                    location=_loc(108.9450, 34.2610),
                    price_range="¥500-700",
                    rating="4.7",
                    distance="距回民街 0.8km",
                    type="舒适型酒店",
                    estimated_cost=600,
                ),
                attractions=[
                    Attraction(
                        name="秦始皇兵马俑博物馆",
                        address="西安市临潼区秦陵北路",
                        location=_loc(109.2785, 34.3841),
                        visit_duration=180,
                        description="世界第八大奇迹",
                        category="历史文化",
                        rating=4.9,
                        ticket_price=120,
                        reservation_required=True,
                        reservation_tips="建议提前 3 天预约",
                    ),
                ],
                meals=[
                    Meal(type="dinner", name="回民街老孙家泡馍", address="西安市莲湖区",
                         location=_loc(108.9400, 34.2650), description="羊肉泡馍",
                         estimated_cost=80),
                ],
            ),
        ],
        weather_info=[
            WeatherInfo(date="2026-10-01", city="北京", day_weather="晴", night_weather="多云",
                        day_temp=22, night_temp=12, wind_direction="北风", wind_power="3级"),
            WeatherInfo(date="2026-10-02", city="北京", day_weather="多云", night_weather="阴",
                        day_temp=21, night_temp=13, wind_direction="东风", wind_power="2级"),
            WeatherInfo(date="2026-10-03", city="西安", day_weather="小雨", night_weather="阴",
                        day_temp=19, night_temp=14, wind_direction="西风", wind_power="2级"),
        ],
        overall_suggestions=(
            "故宫与兵马俑均需提前实名预约，请务必先预约再出行；"
            "北京至西安建议选择早班高铁以保留下午游览时间；"
            "10 月初昼夜温差较大，建议携带薄外套。"
        ),
        budget=Budget(
            total_attractions=210,
            total_hotels=1560,
            total_meals=370,
            total_transportation=120,
            total_inter_city_transport=1030,
            total=3290,
        ),
    )


def main() -> int:
    task_id = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TASK_ID

    plan = build_plan()
    graph = build_knowledge_graph(plan, language="zh")

    response = TripPlanResponse(
        success=True,
        message="旅行计划生成成功",
        plan_id=task_id,
        data=plan,
        graph_data=graph,
    )

    payload = {
        "task_id": task_id,
        "plan_id": task_id,
        "status": "completed",
        "stage": "completed",
        "progress": 100,
        "message": "旅行计划生成成功",
        "result": response.model_dump(mode="json"),
        "error": None,
        "request_payload": {
            "city": plan.city,
            "cities": [{"city": c, "days": 1} for c in plan.cities],
            "start_date": plan.start_date,
            "end_date": plan.end_date,
            "travel_days": len(plan.days),
            "transportation": "公共交通",
            "accommodation": "经济型酒店",
            "preferences": ["历史文化", "美食"],
            "free_text_input": "",
            "language": "zh",
        },
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    target = DATA_DIR / f"{task_id}.json"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    print(f"✅ 已写入 {target}")
    print(f"   多城市={plan.cities}  天数={len(plan.days)}")
    print(f"   图谱节点={len(nodes)}  边={len(edges)}  分类={len(graph.get('categories', []))}")
    print(f"   访问： http://127.0.0.1:18080/result?plan_id={task_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
