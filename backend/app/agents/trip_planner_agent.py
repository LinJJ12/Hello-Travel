"""多智能体旅行规划系统"""

import json
from typing import Dict, Any, List, Optional
from hello_agents import HelloAgentsLLM
from ..services.llm_service import get_llm
from ..services.amap_service import get_amap_service
from ..models.schemas import TripRequest, TripPlan, DayPlan, Attraction, Meal, WeatherInfo, Location, Hotel, POIInfo
from ..config import get_settings

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


class MultiAgentTripPlanner:
    """多智能体旅行规划系统 - 使用 amap_service 直接调用，不依赖 MCPTool"""

    def __init__(self):
        """初始化旅行规划系统"""
        print("🔄 开始初始化旅行规划系统...")

        try:
            settings = get_settings()
            self.llm = get_llm()
            self.amap_service = get_amap_service()

            print(f"✅ 旅行规划系统初始化成功")
            print(f"   LLM 提供商: {self.llm.provider}")
            print(f"   LLM 模型: {self.llm.model}")
            print(f"   地图服务: 已连接")

        except Exception as e:
            print(f"❌ 旅行规划系统初始化失败: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    def plan_trip(self, request: TripRequest) -> TripPlan:
        """
        使用多智能体协作生成旅行计划

        Args:
            request: 旅行请求

        Returns:
            旅行计划
        """
        try:
            print(f"\n{'='*60}")
            print(f"🚀 开始多智能体协作规划旅行...")
            print(f"目的地: {request.city}")
            print(f"日期: {request.start_date} 至 {request.end_date}")
            print(f"天数: {request.travel_days}天")
            print(f"偏好: {', '.join(request.preferences) if request.preferences else '无'}")
            print(f"{'='*60}\n")

            # 步骤1: 搜索景点(获取真实坐标)
            print("📍 步骤1: 搜索景点...")
            try:
                attraction_keywords = request.preferences[0] if request.preferences else "景点"
                print(f"   关键词: {attraction_keywords}, 城市: {request.city}")
                real_attractions = self.amap_service.search_poi(attraction_keywords, request.city)
                attraction_response = json.dumps([a.model_dump() for a in real_attractions], ensure_ascii=False)
                print(f"✅ 景点搜索结果: 找到 {len(real_attractions)} 个景点\n")
                if len(real_attractions) == 0:
                    print(f"⚠️  警告: 没有找到景点,将使用LLM生成的景点信息")
                self._real_attractions = real_attractions  # 保存真实景点数据
            except Exception as e:
                print(f"❌ 景点搜索步骤异常: {str(e)}")
                import traceback
                traceback.print_exc()
                self._real_attractions = []
                attraction_response = "[]"

            # 步骤2: 查询天气
            print("🌤️  步骤2: 查询天气...")
            real_weather = self.amap_service.get_weather(request.city)
            weather_response = json.dumps([w.model_dump() for w in real_weather], ensure_ascii=False)
            print(f"天气查询结果: 获得 {len(real_weather)} 天天气数据\n")
            self._real_weather = real_weather  # 保存真实天气数据

            # 步骤3: 搜索酒店
            print("🏨 步骤3: 搜索酒店...")
            hotel_keywords = request.accommodation or "酒店"
            real_hotels = self.amap_service.search_poi(f"{hotel_keywords} 酒店", request.city)
            hotel_response = json.dumps([h.model_dump() for h in real_hotels], ensure_ascii=False)
            print(f"酒店搜索结果: 找到 {len(real_hotels)} 个酒店\n")
            self._real_hotels = real_hotels  # 保存真实酒店数据

            # 步骤4: 生成行程计划
            print("📋 步骤4: 生成行程计划...")
            planner_query = self._build_planner_query(request, attraction_response, weather_response, hotel_response)
            planner_response = self._generate_plan_text(planner_query)
            print(f"行程规划结果: {planner_response[:300]}...\n")

            # 解析最终计划
            trip_plan = self._parse_response(planner_response, request)
            
            # 校验行程中的景点/酒店是否与高德搜索结果一致
            self._validate_plan_against_poi_search(trip_plan)

            print(f"{'='*60}")
            print(f"✅ 旅行计划生成完成!")
            print(f"{'='*60}\n")

            return trip_plan

        except Exception as e:
            print(f"❌ 生成旅行计划失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return self._create_fallback_plan(request)

    def _generate_plan_text(self, planner_query: str) -> str:
        """使用 LLM 生成行程计划文本"""
        return self.llm.generate(
            planner_query,
            system_prompt=PLANNER_AGENT_PROMPT,
            temperature=0.4,
            max_tokens=4096,
        )
    
    @staticmethod
    def _match_hotel_poi(llm_name: str, hotel_by_name: Dict[str, POIInfo], real_hotels: List[POIInfo]) -> Optional[POIInfo]:
        """按名称匹配搜索结果中的酒店 POI：先精确匹配，再允许单向子串匹配（对齐轻微改写）。"""
        name = (llm_name or "").strip()
        if not name:
            return None
        if name in hotel_by_name:
            return hotel_by_name[name]
        for poi in real_hotels:
            if name in poi.name or poi.name in name:
                return poi
        return None

    @staticmethod
    def _hotel_dict_from_poi(poi: POIInfo, existing: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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

    def _enforce_hotels_from_search_results(self, data: Dict[str, Any], real_hotels: List[POIInfo]) -> None:
        """强制每日 hotel 对应搜索结果中的 POI；无法匹配则按天轮换回填并打日志。"""
        if not real_hotels or "days" not in data:
            return

        hotel_by_name = {p.name: p for p in real_hotels}

        for day_idx, day in enumerate(data.get("days", [])):
            slot = real_hotels[day_idx % len(real_hotels)]
            raw = day.get("hotel")

            if not raw:
                day["hotel"] = self._hotel_dict_from_poi(slot)
                print(f"   ⚠️  第{day_idx + 1}天: 缺少 hotel 字段,已填入搜索结果「{slot.name}」")
                continue

            llm_name = raw.get("name") or ""
            matched = self._match_hotel_poi(llm_name, hotel_by_name, real_hotels)

            if matched is None:
                print(f"   ⚠️  第{day_idx + 1}天: 酒店名称「{llm_name}」无法匹配搜索结果,已替换为「{slot.name}」")
                day["hotel"] = self._hotel_dict_from_poi(slot, raw)
            else:
                if matched.name != llm_name.strip():
                    print(f"   ℹ️  第{day_idx + 1}天: 酒店名称「{llm_name}」已对齐为搜索结果「{matched.name}」")
                day["hotel"] = self._hotel_dict_from_poi(matched, raw)

    def _validate_plan_against_poi_search(self, trip_plan: TripPlan) -> bool:
        """
        校验行程中的景点与酒店是否与高德搜索结果一致（严格酒店名称集合、景点名称与坐标合理性）。
        """
        issues: List[str] = []
        real_attractions = getattr(self, "_real_attractions", [])
        real_hotels = getattr(self, "_real_hotels", [])
        real_attraction_names = {attr.name for attr in real_attractions}
        real_hotel_names = {h.name for h in real_hotels}

        for day_idx, day in enumerate(trip_plan.days, 1):
            for attr_idx, attraction in enumerate(day.attractions, 1):
                if attraction.location:
                    lng = attraction.location.longitude
                    lat = attraction.location.latitude

                    if not (73 <= lng <= 136 and 18 <= lat <= 54):
                        issues.append(f"第{day_idx}天景点{attr_idx}「{attraction.name}」: 坐标超出中国大陆常见范围 ({lng}, {lat})")

                    if lng == 116.397128 and lat == 39.916527:
                        issues.append(f"第{day_idx}天景点{attr_idx}「{attraction.name}」: 使用了模板默认北京坐标,可能不准确")

                    if real_attraction_names and attraction.name not in real_attraction_names:
                        matched = False
                        for real_name in real_attraction_names:
                            if attraction.name in real_name or real_name in attraction.name:
                                matched = True
                                break
                        if not matched:
                            issues.append(
                                f"第{day_idx}天景点{attr_idx}「{attraction.name}」: 不在景点搜索结果中,坐标可能被错误补填"
                            )

            if real_hotel_names:
                if day.hotel is None:
                    issues.append(f"第{day_idx}天: 缺少酒店推荐,但本次已有酒店搜索结果")
                elif day.hotel.name not in real_hotel_names:
                    issues.append(f"第{day_idx}天酒店「{day.hotel.name}」: 不在本次高德酒店搜索结果名称集合中")

        if issues:
            print("⚠️  POI 一致性检查结果:")
            for issue in issues[:12]:
                print(f"   {issue}")
            if len(issues) > 12:
                print(f"   ... 还有 {len(issues) - 12} 条")
            return False

        if real_hotels:
            print("✅ POI 校验通过: 景点坐标合理,且每日酒店均来自本次酒店搜索结果")
        else:
            print("✅ POI 校验通过: 景点坐标合理(本次无酒店搜索结果,未校验酒店)")
        return True
    
    def _build_planner_query(self, request: TripRequest, attractions: str, weather: str, hotels: str = "") -> str:
        """构建行程规划查询"""
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
    
    def _parse_response(self, response: str, request: TripRequest) -> TripPlan:
        """
        解析Agent响应,并用真实坐标补填
        
        Args:
            response: Agent响应文本
            request: 原始请求
            
        Returns:
            旅行计划
        """
        try:
            # 尝试从响应中提取JSON
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            elif "```" in response:
                json_start = response.find("```") + 3
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            elif "{" in response and "}" in response:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]
            else:
                raise ValueError("响应中未找到JSON数据")
            
            # 解析JSON
            data = json.loads(json_str)
            
            # 使用真实坐标补填景点信息
            real_attractions = getattr(self, "_real_attractions", [])
            real_hotels = getattr(self, "_real_hotels", [])
            
            # 调试: 打印数据信息
            print(f"\n🔍 坐标补填调试信息:")
            print(f"   真实景点数: {len(real_attractions)}")
            print(f"   LLM生成景点数: {sum(len(d.get('attractions', [])) for d in data.get('days', []))}")
            
            if real_attractions and "days" in data:
                # 构建景点名称到真实坐标的映射,用于更准确的匹配
                attraction_map = {attr.name: attr for attr in real_attractions}
                
                # 按顺序将真实景点坐标填充到行程中
                attraction_idx = 0
                for day_idx, day in enumerate(data.get("days", [])):
                    for attr_idx, attraction in enumerate(day.get("attractions", [])):
                        if attraction_idx < len(real_attractions):
                            real_attr = real_attractions[attraction_idx]
                            
                            # 尝试按名称匹配,如果找到则用匹配的坐标
                            matched_attr = attraction_map.get(attraction.get("name"))
                            if matched_attr:
                                real_attr = matched_attr
                                print(f"   ✅ 第{day_idx+1}天景点{attr_idx+1}: 按名称匹配到 '{attraction['name']}'")
                            else:
                                print(f"   ⚠️  第{day_idx+1}天景点{attr_idx+1}: '{attraction['name']}' 使用第{attraction_idx+1}个搜索结果")
                            
                            # 保留LLM生成的描述,替换坐标为真实值
                            attraction["location"] = {
                                "longitude": real_attr.location.longitude,
                                "latitude": real_attr.location.latitude
                            }
                            # 如果景点名字完全匹配,也使用真实地址
                            if not attraction.get("address") or attraction["address"] == "详细地址":
                                attraction["address"] = real_attr.address
                            attraction_idx += 1
            
            # 酒店必须与高德搜索结果名称/地址/坐标一致（无法匹配则按天回填）
            print(f"   真实酒店数: {len(real_hotels)}")
            self._enforce_hotels_from_search_results(data, real_hotels)
            
            print()  # 空行便于日志阅读
            
            # 转换为TripPlan对象
            trip_plan = TripPlan(**data)
            
            return trip_plan
            
        except Exception as e:
            print(f"⚠️  解析响应失败: {str(e)}")
            print(f"   将使用备用方案生成计划")
            return self._create_fallback_plan(request)
    
    def _create_fallback_plan(self, request: TripRequest) -> TripPlan:
        """创建备用计划(当Agent失败时)"""
        from datetime import datetime, timedelta
        
        # 解析日期
        start_date = datetime.strptime(request.start_date, "%Y-%m-%d")
        
        # 创建每日行程
        days = []
        for i in range(request.travel_days):
            current_date = start_date + timedelta(days=i)
            
            day_plan = DayPlan(
                date=current_date.strftime("%Y-%m-%d"),
                day_index=i,
                description=f"第{i+1}天行程",
                transportation=request.transportation,
                accommodation=request.accommodation,
                attractions=[
                    Attraction(
                        name=f"{request.city}景点{j+1}",
                        address=f"{request.city}市",
                        location=Location(longitude=116.4 + i*0.01 + j*0.005, latitude=39.9 + i*0.01 + j*0.005),
                        visit_duration=120,
                        description=f"这是{request.city}的著名景点",
                        category="景点"
                    )
                    for j in range(2)
                ],
                meals=[
                    Meal(type="breakfast", name=f"第{i+1}天早餐", description="当地特色早餐"),
                    Meal(type="lunch", name=f"第{i+1}天午餐", description="午餐推荐"),
                    Meal(type="dinner", name=f"第{i+1}天晚餐", description="晚餐推荐")
                ]
            )
            days.append(day_plan)
        
        return TripPlan(
            city=request.city,
            start_date=request.start_date,
            end_date=request.end_date,
            days=days,
            weather_info=[],
            overall_suggestions=f"这是为您规划的{request.city}{request.travel_days}日游行程,建议提前查看各景点的开放时间。"
        )


# 全局多智能体系统实例
_multi_agent_planner = None


def get_trip_planner_agent() -> MultiAgentTripPlanner:
    """获取多智能体旅行规划系统实例(单例模式)"""
    global _multi_agent_planner

    if _multi_agent_planner is None:
        _multi_agent_planner = MultiAgentTripPlanner()

    return _multi_agent_planner
