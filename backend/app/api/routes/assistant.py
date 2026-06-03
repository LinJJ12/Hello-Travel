"""行程增强能力 API：知识图谱与伴游问答"""

from fastapi import APIRouter, HTTPException
from ...models.schemas import (
    GraphEdge,
    GraphNode,
    KnowledgeGraphResponse,
    TripChatRequest,
    TripChatResponse,
    TripPlan,
)
from ...services.llm_service import get_llm

router = APIRouter(prefix="/assistant", tags=["行程增强"])


def _node_id(*parts: object) -> str:
    return "-".join(str(part).replace(" ", "_") for part in parts)


def build_knowledge_graph(plan: TripPlan) -> KnowledgeGraphResponse:
    """把行程计划转换成前端可视化知识图谱。"""
    nodes = [
        GraphNode(id="trip", label=f"{plan.city}旅行计划", category="trip"),
    ]
    edges = []

    if plan.budget:
        nodes.append(GraphNode(id="budget", label=f"预算 ¥{plan.budget.total}", category="budget", value=plan.budget.total))
        edges.append(GraphEdge(source="trip", target="budget", relation="预估费用"))

    for day in plan.days:
        day_id = _node_id("day", day.day_index)
        nodes.append(GraphNode(id=day_id, label=f"第{day.day_index + 1}天", category="day", value=day.date))
        edges.append(GraphEdge(source="trip", target=day_id, relation="包含"))

        if day.hotel:
            hotel_id = _node_id("hotel", day.day_index)
            nodes.append(GraphNode(id=hotel_id, label=day.hotel.name, category="hotel", value=day.hotel.estimated_cost))
            edges.append(GraphEdge(source=day_id, target=hotel_id, relation="住宿"))

        for index, attraction in enumerate(day.attractions):
            attraction_id = _node_id("attraction", day.day_index, index)
            nodes.append(
                GraphNode(
                    id=attraction_id,
                    label=attraction.name,
                    category="attraction",
                    value=attraction.visit_duration,
                )
            )
            edges.append(GraphEdge(source=day_id, target=attraction_id, relation="游览"))

        for meal in day.meals:
            meal_id = _node_id("meal", day.day_index, meal.type)
            nodes.append(GraphNode(id=meal_id, label=meal.name, category="meal", value=meal.estimated_cost))
            edges.append(GraphEdge(source=day_id, target=meal_id, relation=meal.type))

    return KnowledgeGraphResponse(nodes=nodes, edges=edges)


@router.post("/knowledge-graph", response_model=KnowledgeGraphResponse, summary="生成行程知识图谱")
async def knowledge_graph(plan: TripPlan):
    return build_knowledge_graph(plan)


@router.post("/chat", response_model=TripChatResponse, summary="行程伴游问答")
async def trip_chat(request: TripChatRequest):
    try:
        plan = request.trip_plan
        itinerary = []
        for day in plan.days:
            names = "、".join(item.name for item in day.attractions)
            meals = "、".join(item.name for item in day.meals)
            hotel = day.hotel.name if day.hotel else "未指定"
            itinerary.append(f"第{day.day_index + 1}天 {day.date}: 景点 {names}; 餐饮 {meals}; 住宿 {hotel}")

        prompt = f"""你是专业旅行伴游助手。请基于当前行程回答用户问题，回答要具体、可执行、简洁。

城市: {plan.city}
日期: {plan.start_date} 至 {plan.end_date}
总体建议: {plan.overall_suggestions}
行程:
{chr(10).join(itinerary)}

用户问题: {request.question}
"""

        llm = get_llm()
        answer = llm.generate(prompt, temperature=0.3, max_tokens=800)
        return TripChatResponse(answer=answer)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"伴游问答失败: {exc}")
