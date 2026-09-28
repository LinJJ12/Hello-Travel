"""数据模型定义"""


from pydantic import BaseModel, ConfigDict, Field, field_validator

# ============ 请求模型 ============

class TripRequest(BaseModel):
    """旅行规划请求"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "city": "北京",
                "destinations": ["北京"],
                "start_date": "2025-06-01",
                "end_date": "2025-06-03",
                "travel_days": 3,
                "transportation": "公共交通",
                "accommodation": "经济型酒店",
                "preferences": ["历史文化", "美食"],
                "budget_per_person": 3000,
                "travel_pace": "适中",
                "companions": "情侣",
                "dietary_restrictions": "不吃海鲜",
                "free_text_input": "希望多安排一些博物馆",
            }
        }
    )

    city: str = Field(..., description="目的地城市", examples=["北京"])
    destinations: list[str] = Field(default_factory=list, description="多城市目的地列表", examples=[["杭州", "苏州", "上海"]])
    start_date: str = Field(..., description="开始日期 YYYY-MM-DD", examples=["2025-06-01"])
    end_date: str = Field(..., description="结束日期 YYYY-MM-DD", examples=["2025-06-03"])
    travel_days: int = Field(..., description="旅行天数", ge=1, le=30, examples=[3])
    transportation: str = Field(..., description="交通方式", examples=["公共交通"])
    accommodation: str = Field(..., description="住宿偏好", examples=["经济型酒店"])
    preferences: list[str] = Field(default_factory=list, description="旅行偏好标签", examples=[["历史文化", "美食"]])
    budget_per_person: int | None = Field(default=None, description="人均预算(元)", ge=0, examples=[3000])
    travel_pace: str | None = Field(default="适中", description="旅行节奏: 轻松/适中/紧凑", examples=["适中"])
    companions: str | None = Field(default="独自/不限", description="同行人群", examples=["情侣"])
    dietary_restrictions: str | None = Field(default="", description="饮食禁忌或偏好", examples=["不吃海鲜"])
    free_text_input: str | None = Field(default="", description="额外要求", examples=["希望多安排一些博物馆"])


class POISearchRequest(BaseModel):
    """POI搜索请求"""

    keywords: str = Field(..., description="搜索关键词", examples=["故宫"])
    city: str = Field(..., description="城市", examples=["北京"])
    citylimit: bool = Field(default=True, description="是否限制在城市范围内")


class RouteRequest(BaseModel):
    """路线规划请求"""

    origin_address: str = Field(..., description="起点地址", examples=["北京市朝阳区阜通东大街6号"])
    destination_address: str = Field(..., description="终点地址", examples=["北京市海淀区上地十街10号"])
    origin_city: str | None = Field(default=None, description="起点城市")
    destination_city: str | None = Field(default=None, description="终点城市")
    route_type: str = Field(default="walking", description="路线类型: walking/driving/transit")


# ============ 响应模型 ============

class Location(BaseModel):
    """地理位置"""
    longitude: float = Field(..., description="经度")
    latitude: float = Field(..., description="纬度")


class Attraction(BaseModel):
    """景点信息"""
    name: str = Field(..., description="景点名称")
    address: str = Field(..., description="地址")
    location: Location = Field(..., description="经纬度坐标")
    visit_duration: int = Field(..., description="建议游览时间(分钟)")
    description: str = Field(..., description="景点描述")
    category: str | None = Field(default="景点", description="景点类别")
    rating: float | None = Field(default=None, description="评分")
    photos: list[str] | None = Field(default_factory=list, description="景点图片URL列表")
    poi_id: str | None = Field(default="", description="POI ID")
    image_url: str | None = Field(default=None, description="图片URL")
    ticket_price: int = Field(default=0, description="门票价格(元)")
    needs_reservation: bool = Field(default=False, description="是否需要提前预约")
    reservation_note: str | None = Field(default="", description="预约提示")


class Meal(BaseModel):
    """餐饮信息"""
    type: str = Field(..., description="餐饮类型: breakfast/lunch/dinner/snack")
    name: str = Field(..., description="餐饮名称")
    address: str | None = Field(default=None, description="地址")
    location: Location | None = Field(default=None, description="经纬度坐标")
    description: str | None = Field(default=None, description="描述")
    estimated_cost: int = Field(default=0, description="预估费用(元)")


class Hotel(BaseModel):
    """酒店信息"""
    name: str = Field(..., description="酒店名称")
    address: str = Field(default="", description="酒店地址")
    location: Location | None = Field(default=None, description="酒店位置")
    price_range: str = Field(default="", description="价格范围")
    rating: str = Field(default="", description="评分")
    distance: str = Field(default="", description="距离景点距离")
    type: str = Field(default="", description="酒店类型")
    estimated_cost: int = Field(default=0, description="预估费用(元/晚)")


class DayPlan(BaseModel):
    """单日行程"""
    date: str = Field(..., description="日期 YYYY-MM-DD")
    day_index: int = Field(..., description="第几天(从0开始)")
    description: str = Field(..., description="当日行程描述")
    transportation: str = Field(..., description="交通方式")
    accommodation: str = Field(..., description="住宿")
    hotel: Hotel | None = Field(default=None, description="推荐酒店")
    attractions: list[Attraction] = Field(default_factory=list, description="景点列表")
    meals: list[Meal] = Field(default_factory=list, description="餐饮列表")


class WeatherInfo(BaseModel):
    """天气信息"""
    date: str = Field(..., description="日期 YYYY-MM-DD")
    day_weather: str = Field(default="", description="白天天气")
    night_weather: str = Field(default="", description="夜间天气")
    day_temp: int | str = Field(default=0, description="白天温度")
    night_temp: int | str = Field(default=0, description="夜间温度")
    wind_direction: str = Field(default="", description="风向")
    wind_power: str = Field(default="", description="风力")

    @field_validator('day_temp', 'night_temp', mode='before')
    @classmethod
    def parse_temperature(cls, v):
        """解析温度,移除°C等单位"""
        if isinstance(v, str):
            # 移除°C, ℃等单位符号
            v = v.replace('°C', '').replace('℃', '').replace('°', '').strip()
            try:
                return int(v)
            except ValueError:
                return 0
        return v


class Budget(BaseModel):
    """预算信息"""
    total_attractions: int = Field(default=0, description="景点门票总费用")
    total_hotels: int = Field(default=0, description="酒店总费用")
    total_meals: int = Field(default=0, description="餐饮总费用")
    total_transportation: int = Field(default=0, description="交通总费用")
    total: int = Field(default=0, description="总费用")


class TripPlan(BaseModel):
    """旅行计划"""
    city: str = Field(..., description="目的地城市")
    start_date: str = Field(..., description="开始日期")
    end_date: str = Field(..., description="结束日期")
    days: list[DayPlan] = Field(..., description="每日行程")
    weather_info: list[WeatherInfo] = Field(default_factory=list, description="天气信息")
    overall_suggestions: str = Field(..., description="总体建议")
    budget: Budget | None = Field(default=None, description="预算信息")


class TripPlanResponse(BaseModel):
    """旅行计划响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(default="", description="消息")
    data: TripPlan | None = Field(default=None, description="旅行计划数据")


class GraphNode(BaseModel):
    """知识图谱节点"""
    id: str = Field(..., description="节点ID")
    label: str = Field(..., description="显示名称")
    category: str = Field(..., description="节点类型")
    value: int | float | str | None = Field(default=None, description="节点值")


class GraphEdge(BaseModel):
    """知识图谱边"""
    source: str = Field(..., description="起点ID")
    target: str = Field(..., description="终点ID")
    relation: str = Field(..., description="关系")


class KnowledgeGraphResponse(BaseModel):
    """知识图谱响应"""
    success: bool = Field(default=True, description="是否成功")
    nodes: list[GraphNode] = Field(default_factory=list, description="节点列表")
    edges: list[GraphEdge] = Field(default_factory=list, description="边列表")


class TripChatRequest(BaseModel):
    """行程伴游问答请求"""
    question: str = Field(..., description="用户问题")
    trip_plan: TripPlan = Field(..., description="当前行程上下文")


class TripChatResponse(BaseModel):
    """行程伴游问答响应"""
    success: bool = Field(default=True, description="是否成功")
    answer: str = Field(default="", description="回答内容")


class POIInfo(BaseModel):
    """POI信息"""
    id: str = Field(..., description="POI ID")
    name: str = Field(..., description="名称")
    type: str = Field(..., description="类型")
    address: str = Field(..., description="地址")
    location: Location = Field(..., description="经纬度坐标")
    tel: str | None = Field(default=None, description="电话")


class POISearchResponse(BaseModel):
    """POI搜索响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(default="", description="消息")
    data: list[POIInfo] = Field(default_factory=list, description="POI列表")


class RouteInfo(BaseModel):
    """路线信息"""
    distance: float = Field(..., description="距离(米)")
    duration: int = Field(..., description="时间(秒)")
    route_type: str = Field(..., description="路线类型")
    description: str = Field(..., description="路线描述")


class RouteResponse(BaseModel):
    """路线规划响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(default="", description="消息")
    data: RouteInfo | None = Field(default=None, description="路线信息")


class WeatherResponse(BaseModel):
    """天气查询响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(default="", description="消息")
    data: list[WeatherInfo] = Field(default_factory=list, description="天气信息")


# ============ 错误响应 ============

class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = Field(default=False, description="是否成功")
    message: str = Field(..., description="错误消息")
    error_code: str | None = Field(default=None, description="错误代码")
