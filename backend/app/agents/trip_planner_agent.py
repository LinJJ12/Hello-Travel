"""多智能体旅行规划系统。

改进点（参考 TripStar / TripMate 等开源实现）：
- 景点 / 天气 / 酒店三路数据采集改为 **并发** 执行（原实现串行等待）
- 景点支持 **多关键词召回 + 去重**，不再只取第一个偏好标签
- 用容错 JSON 解析替代脆弱的 ``find("```json")``
- 景点与酒店都 **强制对齐** 高德搜索结果，剔除模型虚构的名称与坐标
- 识别需要提前预约的景点并给出提示
- 统一使用 logging，替换散落的 ``print`` 调试输出
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any

from hello_agents import HelloAgentsLLM

from ..core.constants import CHINA_LAT_RANGE, CHINA_LNG_RANGE
from ..core.json_utils import extract_json
from ..core.logging import get_logger
from ..models.schemas import (
    Attraction,
    DayPlan,
    Hotel,
    Meal,
    POIInfo,
    TripPlan,
    TripRequest,
    WeatherInfo,
)
from ..services.amap_service import get_amap_service
from ..services.llm_service import get_llm

logger = get_logger(__name__)

# ============ 行程规划提示词 ============

PLANNER_AGENT_PROMPT = """你是行程规划专家。你的任务是根据景点信息和天气信息,生成详细的旅行计划。

请严格按照以下JSON格式返回旅行计划:
```json
{
  "city": "城市名称",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "days": [
    {
      "date": "YYYY-MM-DD",
      "day_index": 0,
      "description": "第1天行程概述",
      "transportation": "交通方式",
      "accommodation": "住宿类型",
      "hotel": {
        "name": "酒店名称",
        "address": "酒店地址",
        "location": {"longitude": 116.397128, "latitude": 39.916527},
        "price_range": "300-500元",
        "rating": "4.5",
        "distance": "距离景点2公里",
        "type": "经济型酒店",
        "estimated_cost": 400
      },
      "attractions": [
        {
          "name": "景点名称",
          "address": "详细地址",
          "location": {"longitude": 116.397128, "latitude": 39.916527},
          "visit_duration": 120,
          "description": "景点详细描述",
          "category": "景点类别",
          "ticket_price": 60
        }
      ],
      "meals": [
        {"type": "breakfast", "name": "早餐推荐", "description": "早餐描述", "estimated_cost": 30},
        {"type": "lunch", "name": "午餐推荐", "description": "午餐描述", "estimated_cost": 50},
        {"type": "dinner", "name": "晚餐推荐", "description": "晚餐描述", "estimated_cost": 80}
      ]
    }
  ],
  "weather_info": [
    {
      "date": "YYYY-MM-DD",
      "day_weather": "晴",
      "night_weather": "多云",
      "day_temp": 25,
      "night_temp": 15,
      "wind_direction": "南风",
      "wind_power": "1-3级"
    }
  ],
  "overall_suggestions": "总体建议",
  "budget": {
    "total_attractions": 180,
    "total_hotels": 1200,
    "total_meals": 480,
    "total_transportation": 200,
    "total": 2060
  }
}
```

**重要提示:**
1. weather_info数组必须包含每一天的天气信息
2. 温度必须是纯数字(不要带°C等单位)
3. 每天安排2-3个景点
4. 考虑景点之间的距离和游览时间
5. 每天必须包含早中晚三餐
6. 提供实用的旅行建议
7. **必须包含预算信息**:
   - 景点门票价格(ticket_price)
   - 餐饮预估费用(estimated_cost)
   - 酒店预估费用(estimated_cost)
   - 预算汇总(budget)包含各项总费用
8. **酒店名称必须与「可用酒店列表」中的 name 字段完全一致(逐字复制,禁止改写、缩写或增删字)**；address、location 必须与列表中对应项完全一致；price_range、rating、distance、estimated_cost 可由你合理预估。
"""

# 通常需要提前实名预约 / 抢票的热门景点关键词（用于给出预约提醒）
_RESERVATION_KEYWORDS = (
    "故宫",
    "国家博物馆",
    "中国国家博物馆",
    "陕西历史博物馆",
    "上海博物馆",
    "苏州博物馆",
    "敦煌",
    "莫高窟",
    "布达拉宫",
    "兵马俑",
    "秦始皇",
    "长城",
    "环球影城",
    "迪士尼",
    "科技馆",
    "天文馆",
)


class MultiAgentTripPlanner:
    """多智能体旅行规划系统 - 直接调用 amap_service，不依赖 MCPTool。"""

    def __init__(self) -> None:
        logger.info("开始初始化旅行规划系统...")
        try:
            self.llm: HelloAgentsLLM = get_llm()
            self.amap_service = get_amap_service()
            logger.info(
                "旅行规划系统初始化成功 (LLM=%s/%s)",
                self.llm.provider,
                self.llm.model,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("旅行规划系统初始化失败: %s", exc)
            raise

        self._real_attractions: list[POIInfo] = []
        self._real_weather: list[WeatherInfo] = []
        self._real_hotels: list[POIInfo] = []

    # ------------------------------------------------------------------ #
    # 主流程
    # ------------------------------------------------------------------ #
    def plan_trip(self, request: TripRequest) -> TripPlan:
        """生成旅行计划（并发采集数据 → LLM 编排 → 校验对齐）。"""
        logger.info(
            "开始规划: %s | %s → %s | %s天 | 偏好=%s",
            request.city,
            request.start_date,
            request.end_date,
            request.travel_days,
            request.preferences or "无",
        )

        try:
            attractions, weather, hotels = self._gather_context(request)

            planner_query = self._build_planner_query(
                request,
                self._dump(attractions),
                self._dump(weather),
                self._dump(hotels),
            )
            raw_response = self.llm.generate(
                planner_query,
                system_prompt=PLANNER_AGENT_PROMPT,
                temperature=0.4,
                max_tokens=4096,
            )
            logger.debug("LLM 原始输出前 300 字: %s", raw_response[:300])

            trip_plan = self._parse_response(raw_response, request)
            self._validate_plan_against_poi_search(trip_plan)

            logger.info("旅行计划生成完成: %s (%s 天)", trip_plan.city, len(trip_plan.days))
            return trip_plan

        except Exception as exc:  # noqa: BLE001
            logger.exception("生成旅行计划失败，使用兜底方案: %s", exc)
            return self._create_fallback_plan(request)

    def _gather_context(
        self, request: TripRequest
    ) -> tuple[list[POIInfo], list[WeatherInfo], list[POIInfo]]:
        """并发采集景点 / 天气 / 酒店三类上下文。"""
        with ThreadPoolExecutor(max_workers=3, thread_name_prefix="ctx") as pool:
            future_attractions = pool.submit(self._search_attractions, request)
            future_weather = pool.submit(self._search_weather, request)
            future_hotels = pool.submit(self._search_hotels, request)

            self._real_attractions = self._safe_result(future_attractions, "景点搜索", [])
            self._real_weather = self._safe_result(future_weather, "天气查询", [])
            self._real_hotels = self._safe_result(future_hotels, "酒店搜索", [])

        logger.info(
            "上下文采集完成: 景点 %s / 天气 %s / 酒店 %s",
            len(self._real_attractions),
            len(self._real_weather),
            len(self._real_hotels),
        )
        return self._real_attractions, self._real_weather, self._real_hotels

    @staticmethod
    def _safe_result(future, label: str, default: Any) -> Any:
        """获取并发任务结果，异常时降级为默认值。"""
        try:
            return future.result()
        except Exception as exc:  # noqa: BLE001
            logger.error("%s 步骤异常: %s", label, exc)
            return default

    def _search_attractions(self, request: TripRequest) -> list[POIInfo]:
        keywords: Sequence[str] = request.preferences[:4] if request.preferences else ["景点"]
        return self.amap_service.search_pois_multi(keywords, request.city, per_keyword=8)

    def _search_weather(self, request: TripRequest) -> list[WeatherInfo]:
        return self.amap_service.get_weather(request.city)

    def _search_hotels(self, request: TripRequest) -> list[POIInfo]:
        hotel_keywords = request.accommodation or "酒店"
        return self.amap_service.search_poi(f"{hotel_keywords} 酒店", request.city)

    @staticmethod
    def _dump(items: Sequence[Any]) -> str:
        """把 Pydantic 对象序列化为 JSON 文本，供提示词使用。"""
        return json.dumps([item.model_dump() for item in items], ensure_ascii=False)

    # ------------------------------------------------------------------ #
    # 提示词构建
    # ------------------------------------------------------------------ #
    def _build_planner_query(
        self, request: TripRequest, attractions: str, weather: str, hotels: str = ""
    ) -> str:
        destinations = request.destinations or [request.city]
        destination_text = " → ".join(destinations)
        query = f"""请根据以下信息生成{destination_text}的{request.travel_days}天旅行计划:

**基本信息:**
- 城市: {request.city}
- 多城市路线: {destination_text}
- 日期: {request.start_date} 至 {request.end_date}
- 天数: {request.travel_days}天
- 交通方式: {request.transportation}
- 住宿: {request.accommodation}
- 偏好: {', '.join(request.preferences) if request.preferences else '无'}
- 人均预算: {f'{request.budget_per_person}元' if request.budget_per_person else '未指定'}
- 旅行节奏: {request.travel_pace or '适中'}
- 同行人群: {request.companions or '未指定'}
- 饮食禁忌/偏好: {request.dietary_restrictions or '无'}

**可用景点列表 (从下列景点中选择,必须使用完全相同的名称和坐标):**
{attractions}

**天气信息:**
{weather}

**可用酒店列表 (从下列酒店中选择,必须使用完全相同的名称和坐标):**
{hotels}

**严格要求:**
1. ✅ 必须从上面提供的景点列表中选择景点
2. ✅ 景点的"name"字段必须完全复制列表中的名称,不能修改、缩写或改写
3. ✅ 景点的"address"和"location"必须完全来自列表,不能改动
4. ✅ 不能创建新景点或虚构景点名称
5. ✅ 每天安排2-3个景点
6. ✅ 每天必须包含早中晚三餐
7. ✅ 每天推荐一个具体的酒店:必须从酒店列表中选择,**hotel 的 name、address、location 与列表中该条 POI 完全一致**,逐字复制 name,不得改写
8. ✅ 返回完整的JSON格式数据
9. ✅ 必须包含预算信息:
   - 景点门票价格(ticket_price)
   - 餐饮预估费用(estimated_cost)
   - 酒店预估费用(estimated_cost)
   - 预算汇总(budget)包含各项总费用
10. ✅ 必须考虑用户的人均预算、旅行节奏、同行人群和饮食禁忌；如果预算有限,优先选择低成本景点、餐饮和交通。
11. ✅ 如果是多城市路线,必须按顺序分配每天所在城市,并在 overall_suggestions 中给出城际交通建议。

**错误示例 ❌ (不要这样做):**
列表中有: {{"name": "鼓浪屿", "address": "厦门市思明区鼓浪屿", "location": {{"longitude": 117.956, "latitude": 24.429}}}}
错误的用法: {{"name": "鼓浪屿岛", "address": "厦门鼓浪屿", "location": {{"longitude": 117.96, "latitude": 24.43}}}}  ← 改动了名称、地址和坐标

**正确示例 ✅ (必须这样做):**
列表中有: {{"name": "鼓浪屿", "address": "厦门市思明区鼓浪屿", "location": {{"longitude": 117.956, "latitude": 24.429}}}}
正确的用法: {{"name": "鼓浪屿", "address": "厦门市思明区鼓浪屿", "location": {{"longitude": 117.956, "latitude": 24.429}}}}  ← 完全相同

**酒店错误示例 ❌:** 列表 name 为「如家酒店(XX路店)」,却写成「如家快捷酒店」或删减括号内容 —— 禁止。

**酒店正确示例 ✅:** hotel.name、hotel.address、hotel.location 与列表中选定条目完全一致,仅 price_range/rating/distance/estimated_cost 可自拟。
"""
        if request.free_text_input:
            query += f"\n**额外要求:** {request.free_text_input}"

        return query

    # ------------------------------------------------------------------ #
    # 响应解析与校验
    # ------------------------------------------------------------------ #
    def _parse_response(self, response: str, request: TripRequest) -> TripPlan:
        """解析 LLM 响应，并把景点 / 酒店对齐到真实 POI。"""
        try:
            data = extract_json(response)
        except ValueError as exc:
            logger.warning("解析 LLM 响应失败(%s)，使用兜底方案", exc)
            return self._create_fallback_plan(request)

        if not isinstance(data, dict) or "days" not in data:
            logger.warning("LLM 响应结构不合法(缺少 days)，使用兜底方案")
            return self._create_fallback_plan(request)

        self._enforce_attractions_from_search_results(data, self._real_attractions)
        self._enforce_hotels_from_search_results(data, self._real_hotels)
        self._ensure_budget(data)

        try:
            return TripPlan(**data)
        except Exception as exc:  # noqa: BLE001
            logger.warning("TripPlan 校验失败(%s)，使用兜底方案", exc)
            return self._create_fallback_plan(request)

    # ---------- 景点对齐 ---------- #
    @staticmethod
    def _match_poi(name: str, by_name: dict[str, POIInfo], pool: list[POIInfo]) -> POIInfo | None:
        """按名称匹配 POI：先精确，再允许单向子串匹配（容忍轻微改写）。"""
        name = (name or "").strip()
        if not name:
            return None
        if name in by_name:
            return by_name[name]
        for poi in pool:
            if name in poi.name or poi.name in name:
                return poi
        return None

    @staticmethod
    def _poi_to_attraction_dict(poi: POIInfo, existing: dict[str, Any] | None = None) -> dict[str, Any]:
        """用真实 POI 固定景点名称 / 地址 / 坐标，保留 LLM 的文案与费用估算。"""
        existing = existing or {}
        loc = poi.location
        return {
            "name": poi.name,
            "address": poi.address or existing.get("address") or "",
            "location": {"longitude": loc.longitude, "latitude": loc.latitude},
            "visit_duration": existing.get("visit_duration") or 120,
            "description": existing.get("description") or f"{poi.name}，{poi.type or '热门景点'}",
            "category": existing.get("category") or (poi.type or "景点"),
            "ticket_price": existing.get("ticket_price") or 0,
            "poi_id": poi.id or "",
            "needs_reservation": MultiAgentTripPlanner._needs_reservation(poi.name),
            "reservation_note": (
                "该景点通常需要提前实名预约或抢票，请尽早预约。"
                if MultiAgentTripPlanner._needs_reservation(poi.name)
                else ""
            ),
        }

    @staticmethod
    def _needs_reservation(name: str) -> bool:
        return any(keyword in (name or "") for keyword in _RESERVATION_KEYWORDS)

    def _enforce_attractions_from_search_results(
        self, data: dict[str, Any], real_attractions: list[POIInfo]
    ) -> None:
        """强制每日景点来自搜索结果：能匹配则对齐，匹配不上或重复则回填未使用的真实景点。"""
        if not real_attractions or "days" not in data:
            return

        by_name = {poi.name: poi for poi in real_attractions}
        used_keys: set[str] = set()
        replaced = 0
        aligned = 0
        dropped = 0

        def key_of(poi: POIInfo) -> str:
            return poi.id or poi.name

        for day in data.get("days", []):
            raw_attractions = day.get("attractions") or []
            cleaned: list[dict[str, Any]] = []

            for raw in raw_attractions:
                if not isinstance(raw, dict):
                    continue
                name = (raw.get("name") or "").strip()
                matched = self._match_poi(name, by_name, real_attractions)

                # 已在本行程中使用过的景点视为重复，需要换一个
                if matched is not None and key_of(matched) in used_keys:
                    matched = None

                if matched is None:
                    matched = next((poi for poi in real_attractions if key_of(poi) not in used_keys), None)
                    if matched is None:
                        # 没有更多可用真实景点，丢弃重复项，避免同一景点反复出现
                        dropped += 1
                        continue
                    replaced += 1
                elif matched.name != name:
                    aligned += 1

                used_keys.add(key_of(matched))
                cleaned.append(self._poi_to_attraction_dict(matched, raw))

            day["attractions"] = cleaned

        logger.info("景点对齐: 修正名称 %s 处，替换虚构/重复景点 %s 处，丢弃 %s 处", aligned, replaced, dropped)

    # ---------- 酒店对齐 ---------- #
    def _enforce_hotels_from_search_results(self, data: dict[str, Any], real_hotels: list[POIInfo]) -> None:
        """强制每日 hotel 对应搜索结果中的 POI；无法匹配则按天轮换回填。"""
        if not real_hotels or "days" not in data:
            return

        by_name = {poi.name: poi for poi in real_hotels}

        for day_idx, day in enumerate(data.get("days", [])):
            slot = real_hotels[day_idx % len(real_hotels)]
            raw = day.get("hotel")

            if not raw:
                day["hotel"] = self._hotel_dict_from_poi(slot)
                continue

            matched = self._match_poi(raw.get("name") or "", by_name, real_hotels)
            if matched is None:
                logger.debug("第%s天酒店「%s」未匹配，替换为「%s」", day_idx + 1, raw.get("name"), slot.name)
                day["hotel"] = self._hotel_dict_from_poi(slot, raw)
            else:
                day["hotel"] = self._hotel_dict_from_poi(matched, raw)

    @staticmethod
    def _hotel_dict_from_poi(poi: POIInfo, existing: dict[str, Any] | None = None) -> dict[str, Any]:
        """用高德 POI 固定酒店名称、地址与坐标；其余字段保留 LLM 估算。"""
        existing = existing or {}
        loc = poi.location
        return {
            "name": poi.name,
            "address": poi.address or existing.get("address") or "",
            "location": {"longitude": loc.longitude, "latitude": loc.latitude},
            "price_range": existing.get("price_range") or "",
            "rating": existing.get("rating") or "",
            "distance": existing.get("distance") or "",
            "type": (poi.type or existing.get("type") or ""),
            "estimated_cost": existing.get("estimated_cost") or 0,
        }

    # ---------- 预算 ---------- #
    @staticmethod
    def _ensure_budget(data: dict[str, Any]) -> None:
        """LLM 未返回预算时，根据每日明细自动汇总一份，避免前端出现空预算。"""
        if data.get("budget"):
            return

        total_attractions = 0
        total_meals = 0
        total_hotels = 0
        for day in data.get("days", []):
            for attraction in day.get("attractions", []) or []:
                total_attractions += int(attraction.get("ticket_price") or 0)
            for meal in day.get("meals", []) or []:
                total_meals += int(meal.get("estimated_cost") or 0)
            hotel = day.get("hotel") or {}
            total_hotels += int(hotel.get("estimated_cost") or 0)

        total = total_attractions + total_meals + total_hotels
        if total > 0:
            data["budget"] = {
                "total_attractions": total_attractions,
                "total_hotels": total_hotels,
                "total_meals": total_meals,
                "total_transportation": 0,
                "total": total,
            }

    # ------------------------------------------------------------------ #
    # 校验
    # ------------------------------------------------------------------ #
    def _validate_plan_against_poi_search(self, trip_plan: TripPlan) -> bool:
        """校验行程中的景点与酒店是否与高德搜索结果一致。"""
        issues: list[str] = []
        real_attraction_names = {attr.name for attr in self._real_attractions}
        real_hotel_names = {hotel.name for hotel in self._real_hotels}

        for day_idx, day in enumerate(trip_plan.days, 1):
            for attr_idx, attraction in enumerate(day.attractions, 1):
                if not attraction.location:
                    continue
                lng = attraction.location.longitude
                lat = attraction.location.latitude

                if not (CHINA_LNG_RANGE[0] <= lng <= CHINA_LNG_RANGE[1]
                        and CHINA_LAT_RANGE[0] <= lat <= CHINA_LAT_RANGE[1]):
                    issues.append(f"第{day_idx}天景点{attr_idx}「{attraction.name}」坐标超出常见范围 ({lng}, {lat})")

                if real_attraction_names and attraction.name not in real_attraction_names:
                    issues.append(f"第{day_idx}天景点{attr_idx}「{attraction.name}」不在搜索结果中")

            if real_hotel_names:
                if day.hotel is None:
                    issues.append(f"第{day_idx}天缺少酒店推荐")
                elif day.hotel.name not in real_hotel_names:
                    issues.append(f"第{day_idx}天酒店「{day.hotel.name}」不在搜索结果中")

        if issues:
            logger.warning("POI 一致性检查发现 %s 处问题:", len(issues))
            for issue in issues[:12]:
                logger.warning("  %s", issue)
            return False

        logger.info("POI 校验通过: 景点坐标合理，酒店均来自本次搜索结果")
        return True

    # ------------------------------------------------------------------ #
    # 兜底
    # ------------------------------------------------------------------ #
    def _create_fallback_plan(self, request: TripRequest) -> TripPlan:
        """创建兜底计划：优先使用真实景点 / 酒店，避免出现 "景点1/2/3" 占位。"""
        try:
            start_date = datetime.strptime(request.start_date, "%Y-%m-%d")
        except ValueError:
            start_date = datetime.now()

        days: list[DayPlan] = []
        for i in range(request.travel_days):
            current_date = start_date + timedelta(days=i)

            attractions: list[Attraction] = []
            for j in range(2):
                idx = i * 2 + j
                if idx < len(self._real_attractions):
                    poi = self._real_attractions[idx]
                    attractions.append(
                        Attraction(
                            name=poi.name,
                            address=poi.address,
                            location=poi.location,
                            visit_duration=120,
                            description=f"{poi.name}，{poi.type or '热门景点'}",
                            category=poi.type or "景点",
                            poi_id=poi.id,
                            needs_reservation=self._needs_reservation(poi.name),
                        )
                    )

            hotel = None
            if self._real_hotels:
                poi = self._real_hotels[i % len(self._real_hotels)]
                hotel = Hotel(
                    name=poi.name,
                    address=poi.address,
                    location=poi.location,
                    type=poi.type or "",
                )

            days.append(
                DayPlan(
                    date=current_date.strftime("%Y-%m-%d"),
                    day_index=i,
                    description=f"第{i + 1}天行程",
                    transportation=request.transportation,
                    accommodation=request.accommodation,
                    hotel=hotel,
                    attractions=attractions,
                    meals=[
                        Meal(type="breakfast", name="当地特色早餐", description="推荐本地早餐"),
                        Meal(type="lunch", name="本地餐厅午餐", description="推荐当地人气午餐"),
                        Meal(type="dinner", name="特色晚餐", description="推荐当地特色晚餐"),
                    ],
                )
            )

        return TripPlan(
            city=request.city,
            start_date=request.start_date,
            end_date=request.end_date,
            days=days,
            weather_info=list(self._real_weather),
            overall_suggestions=(
                f"这是为您规划的{request.city}{request.travel_days}日游行程。"
                "由于智能规划服务暂时不可用，已基于地图搜索结果生成基础行程，建议出行前再核实开放时间与预约要求。"
            ),
        )


# 全局多智能体系统实例
_multi_agent_planner: MultiAgentTripPlanner | None = None


def get_trip_planner_agent() -> MultiAgentTripPlanner:
    """获取多智能体旅行规划系统实例（单例模式）。"""
    global _multi_agent_planner
    if _multi_agent_planner is None:
        _multi_agent_planner = MultiAgentTripPlanner()
    return _multi_agent_planner
