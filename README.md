<div align="center" style="display: flex; justify-content: center; align-items: center; gap: 2px;">
  <img width="400" alt="brand" src="https://github.com/user-attachments/assets/50c490da-9042-4661-bf8f-f7fd8084a506" />
</div>
<p align="center">
  <img src="https://img.shields.io/badge/license-GPL--2.0-orange">
  <img src="https://img.shields.io/badge/version-v2.2.0-green">
  <img src="https://img.shields.io/badge/Docker-Build-blue?logo=docker">
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg">
  <img src="https://img.shields.io/badge/vue-3.x-brightgreen.svg">
  <img src="https://img.shields.io/badge/FastAPI-0.100+-teal.svg">
</p>

<div align="center">

[🇨🇳 中文](README.md) | [🇺🇸 English](README_en.md) | [🇯🇵 日本語](README_ja.md)


# 旅途星辰 - AI 旅行智能体
**基于 HelloAgents 框架打造的多智能体协作文旅规划平台**
</div>



> [!IMPORTANT]
> 
> 本地部署可直接体验项目，完整体验项目功能需配置好相关的key，探索丰富功能， 
> 其中包括：旅行计划、景点地图概览、预算明细、每日行程：行程描述、交通方式、住宿推荐、景点安排（地址、游览时长、景点描述、预约提醒）、餐饮安排、天气信息、知识图谱可视化、沉浸式伴游 AI 问答......

## 项目简介

**旅途星辰 (TripStar)** 是一个创新的 AI 文旅智能体应用，基于 HelloAgents 框架打造的多智能体协作文旅规划平台，旨在解决用户在规划旅行时面临的"信息过载"和"决策疲劳"问题。

有别于传统的旅游攻略网站，本项目采用了基于 **大语言模型 (LLM)** 和 **多智能体 (Multi-Agent)** 协作架构的创新模式。它能像一位经验丰富的人类旅行管家一样，全面考虑用户的个性化需求（偏好设置：交通方式、住宿风格、旅行兴趣、特殊需求等），自动搜索旅行信息、查询当地天气、精选酒店并规划最优景点路线，以**快速完成旅游攻略**。

### 核心亮点

* **小红书深度集成**: 景点推荐与攻略数据直接来源于小红书真实用户游记，通过 LLM 智能提纯，获取最真实的避坑指南与打卡建议。景点图片也通过小红书实时搜索获取，确保展示的是网友最新实拍的真实风景照。
* **景点预约提醒**: 智能识别小红书游记中提及的需要提前预约的景点（如故宫、陕西历史博物馆等），在行程卡片中醒目标注预约提示与预约渠道信息，防止白跑一趟。
* **多语言与国际化支持**: 深度集成 Vue I18n，同时在 LLM 提示词层及知识图谱底层实现语言自适应适配。系统界面及 AI 问答全程支持多语言（中/英/日）无缝切换，连同生成的旅行规划数据会自动翻译为目标语言，为全球旅行者打造无障碍的行程规划体验。
* **双地图引擎高定互动展现**: 深度集成并支持 **Google Maps** 与 **高德地图 (AMap)** 双引擎的无缝切换与自动回退。国外使用 Google Maps，国内回退高德。动态绘制"起点-景点-终点"的真实经纬度打卡路线，提供高级定制底图配色，一眼预览景点位置方便安排行程。
* **精准预算明细面板**: 智能汇总门票、餐饮、住宿与交通等多维度花销账单，提供直观的财务面板报表，让出行预算尽在掌握。
* **多智能体协作协同**: 采用分工明确的多个 Agent（如天气预报员、酒店推荐专家），通过工作流 (Workflow) 协同完成复杂的旅行规划任务。
* **知识图谱可视化**: 将生成的行程数据实时转换为节点关系图，直观展示"城市-天数-行程节点-预算"的空间结构。
* **沉浸式伴游 AI 问答**: 在生成报告后，提供悬浮式 AI 问答窗口（左下角），AI 拥有完整行程的上下文记忆，用户可随时针对行程细节（如票价、适宜性）进行追问。
* **多城市行程规划**: 支持在一次旅行中规划多个城市，动态添加城市并设置停留天数，系统自动计算总行程天数。城际移动日智能标注交通建议，预算面板独立统计城际交通费用，天气面板按城市分别展示，知识图谱以多城市拓扑呈现完整路线。
* **用户偏好记忆模块**: 内置分权重的用户专属旅行偏好记忆库，支持遗忘机制与 TOP-K 召回。开启后会在行程生成成功后自动提取稳定偏好并打分入库，下次规划时将高权重偏好注入 Agent Prompt，让推荐持续贴合用户习惯。
* **奢华暗黑玻璃拟物风**: 全新设计的暗黑系玻璃拟物化 (Dark Luxury Glassmorphism) 界面，提供极具沉浸感的高级视觉体验。

## 工程化增强（v2.2.0 合并优化）

本版本以 TripStar 为主干，合并了同框架项目 [LinJJ12/Hello-Travel](https://github.com/LinJJ12/Hello-Travel) 的工程化改进，并修复了主干中若干「必然报错」的实现缺陷。详见 [`MERGE_REPORT.md`](MERGE_REPORT.md)。

**修复的真实 Bug**

| 位置 | 问题 | 现状 |
| --- | --- | --- |
| `services/amap_service.py` | `AmapService` 是 MCP 桩代码，`search_poi` / `get_weather` / `plan_route` / `geocode` **全部返回空**，`/api/map/*` 实际不可用 | 改为直连 `restapi.amap.com` 的真实 REST 实现，带 TTL 缓存与指数退避重试 |
| `api/routes/map.py` `/map/health` | 访问并不存在的 `service.mcp_tool._available_tools` → 必然 500 | 改为返回 `amap_configured` 与缓存条目数 |
| `services/xhs_sign/sign_util.py` | 在**模块导入时**编译签名 JS，缺少 Node.js 时整个后端（含不依赖小红书的功能）都无法启动 | 改为惰性加载，失败仅影响小红书功能并抛出可读的 `XHSSignError` |
| `api/routes/map.py` `/map/route` | 路线解析失败返回 `{}`，而响应模型 `data: Optional[RouteInfo]` 不接受空对象 → 校验错误 | 显式返回 `success=False, data=None` |

**新增基础设施层 `app/core/`**

| 模块 | 作用 |
| --- | --- |
| `logging.py` | 统一结构化日志，替换散落的 `print`；压制 httpx/openai 等第三方库噪音 |
| `cache.py` | 线程安全 TTL 缓存，供高德 POI / 天气 / 地理编码复用（`AMAP_CACHE_TTL` 可调） |
| `retry.py` | 同步 + 异步指数退避重试（不引入 tenacity，保持依赖精简） |
| `json_utils.py` | **多级降级 JSON 解析**：剥围栏 → 括号配平截取 → 修注释/尾逗号 → 补截断括号 → 逐级 `json.loads` |
| `job_store.py` | 带 TTL 回收 + 容量上限的任务存储，替换原「裸 dict 永不清理」的内存任务表 |
| `constants.py` | 语义化 `ErrorCode` 枚举、超时 / 重试 / 缓存常量 |

**其他改进**

- **统一异常响应**：新增 `RequestValidationError` 与兜底 `Exception` 处理器，统一返回 `{success, error_code, message, detail}`；废弃 `@app.on_event`，改用 `lifespan`。
- **文档按环境隐藏**：非 `local/dev/staging` 环境自动关闭 `/docs`、`/redoc`、`openapi.json`。
- **LLM 输出容错**：`_parse_response` 前置 `extract_json()` 快速通道，显著降低「格式略有偏差就退化成占位数据」的概率。
- **前端按需引入**：移除 `app.use(Antd)` 全量注册，改用 `unplugin-vue-components` + `AntDesignVueResolver`，只打包模板中真正用到的组件（ant-design-vue v4 为 CSS-in-JS，无需再按组件引入样式）。
- **可测试性**：新增 `tests/`（含地图服务与 health 端点的回归用例）、`requirements-dev.txt`、`pyproject.toml`（ruff + pytest 配置）。

---
> 举个例子：到中国——西安玩耍，只需要填写地点、日期、偏好设置，即可等待行程规划的结果，一眼预览如何安排旅游景点（步行路线、驾车路线等）
<img width="1236" height="545" alt="image" src="https://github.com/user-attachments/assets/f99c6d23-d0ac-447f-a683-b2133f918159" />
<img width="1243" height="538" alt="image" src="https://github.com/user-attachments/assets/fc31d735-66be-4c5c-b266-5f4806241bea" />



## 系统架构

本项目采用标准的前后端分离架构，分为前端 Vue 交互层、后端 FastAPI 服务层和 LLM/Agents 的智能推理层。

```mermaid
sequenceDiagram
    autonumber
    
    participant Client as Frontend (User)
    participant Route as api/routes/trip.py
    participant Planner as trip_planner_agent.py
    participant XHS as xhs_service.py
    participant Maps as map_dispatcher.py
    participant LLM as llm_service.py
    participant POI as api/routes/poi.py
    participant KG as knowledge_graph_service.py

    Client->>Route: POST /api/trip/plan (城市,天数,偏好)
    Route-->>Client: 返回 task_id & ws_url
    Route->>Planner: 启动异步任务 _run_trip_planning(request)
    Client->>Route: WebSocket 订阅 /ws/{task_id}
    Note right of Route: 通过 WebSocket 实时推送任务 processing/progress 状态
    
    rect rgb(240, 248, 255)
        Note over Planner, LLM: 并发阶段 (asyncio.gather 优化) 
        
        par [1/3] 景点搜索：小红书原生接口提纯
            Planner->>XHS: search_xhs_attractions(city, keywords, lang)
            XHS->>XHS: XhsNativeClient 原生签名直连 / SSR 备用爬取
            XHS->>LLM: 抛入游记杂文，Prompt 要求提纯出景点JSON数组
            LLM-->>XHS: [{"name": "故宫", "duration": 120, ...}]
            
            loop 为每个提纯出的景点补齐坐标
                XHS->>Maps: geocode_unified(name, city)
                Note right of Maps: Google 地理编码优先，失败降级高德 REST
                Maps-->>XHS: 经纬度 {longitude, latitude}
            end
            XHS-->>Planner: 拼接整理好的小红书景点候选文本
            
        and [2/3] 天气搜索：智能体调用 Tool
            Planner->>Planner: weather_agent.run()
            Planner->>Maps: 代理调用 Google/AMap MCP Weather Tool
            Maps-->>Planner: 返回未来天气数据
            Note right of Planner: Google API若失败，自动回退请求高德天气REST接口
            
        and [3/3] 酒店搜索：智能体调用 Tool
            Planner->>Planner: hotel_agent.run()
            Planner->>Maps: 代理调用 Google/AMap MCP POI Text Search
            Maps-->>Planner: 返回酒店列表
        end
    end
    
    rect rgb(255, 240, 245)
        Note over Planner, LLM: 串行聚合阶段：最终规划融合
        Planner->>LLM: 拼接景点、天气、酒店上下文进入终极 Planner Prompt
        LLM-->>Planner: 【高危操作】返回包含行程、预算等复杂嵌套的 JSON 字符串
        
        Planner->>Planner: _parse_response() 容错解析
        Note right of Planner: 1. 清理杂乱字符<br>2. 修复未转义引号<br>3. 截断修复(补齐括号)<br>4. 暴力提取<br>5. 若均失败再求助 LLM 修补
    end

    Planner->>KG: build_knowledge_graph(trip_plan, lang)
    Note right of KG: 提取城市、日程、景点、预算、建议的节点与关联边，并按多语言翻译标签
    KG-->>Planner: graph_data (nodes, edges, categories)

    Planner-->>Route: 返回完整 TripPlanResponse 结构
    Route->>Route: _update_task_state(status="completed")持久化至磁盘
    Route-->>Client: WebSocket 推送成功结果 (含 plan JSON 及 graph 拓扑)
    
    rect rgb(240, 255, 240)
        Note over Client, XHS: 异步前端懒加载：景点图片搜图
        Client->>POI: GET /api/poi/photo?name=xxx
        POI->>XHS: get_photo_from_xhs(keyword)
        XHS->>XHS: 原生搜索 "xxx 风景" 获取首个有效笔记的第一张图 URL
        XHS-->>POI: photo_url
        POI-->>Client: 图片加载成功
    end
```

---

## 核心功能与工作流

### 1. 异步轮询任务系统 (解决网关超时)

针对 LLM 生成超长文本易导致 504 Gateway Timeout 的痛点，重构了后端的任务调度机制。

* **`POST /api/trip/plan`**: 立即返回 `task_id`，将长达数分钟的推理任务推入后台 `asyncio.create_task`。
* **`GET /api/trip/status/{task_id}`**: 前端每 3 秒发起一次轻量请求，实时获取当前处理进度（如"🔍 正在搜索景点..."），直至状态变为 `completed`。

### 2. 多智能体架构 (Agentic Workflow)

主控 Agent 接收到用户自然语言指令后，基于 React 模式拆解任务：

1. **小红书景点提取**: 搜索城市旅游攻略帖，通过 SSR 页面抓取获取帖子正文内容，再由 LLM 从长文游记中提纯出景点名称、真实评价、游玩时长以及是否需要提前预约等结构化信息，最后通过高德 POI 搜索接口补齐精准经纬度坐标。
2. **天气与酒店**: 天气管家查询目标日期的气候状况；酒店专员根据预算寻找合适落脚点。
3. **路线编排**: 主控 Agent 收集三方数据，进行统筹优化，计算两两景点间的距离和最优游玩顺序，避免行程折返跑。
4. **景点搜图 (前端驱动)**: 行程生成完毕后，前端根据每个景点名称独立调用 `/api/poi/photo` 接口，后端以景点名搜索小红书最新发布的帖子，通过 SSR 抓取帖子首张图片直链，确保展示的是真实的风景实拍照。
5. **结果聚合**: 最终输出包含预算明细、逐日行程、预约提醒、防坑指南等详细参数的结构化 JSON。

### 3. 数据驱动的动态组件渲染

前端不再是写死的静态展示，而是通过响应式变量读取 JSON 数据：

* **高德地图 JS API 2.0 组件**: 动态读取 POI 经纬度，绘制连线与标记。
* **ECharts 知识图谱组件**: 将树状的旅行层级转化为关系网络（图数据库雏形）。

---

## 快速部署与运行指北

### 环境准备

* Python 3.10+
* Node.js 18+
* 大模型 API Key（推荐使用兼容 OpenAI 格式的服务商，如豆包）
* 高德地图两种 Key：Web 服务 Key（后端 REST 服务）与 Web端(JS API) Key（前端地图渲染）。AMap JS API 2.0 的安全密钥 JSCode 仍然必须填写，但填写到 `.env` / Docker 根目录 `.env` 的 `VITE_AMAP_SECURITY_JS_CODE`，构建或启动前端开发服务时会自动替换 `index.html` 里的占位符，不要把真实密钥直接手写进 `index.html`。（[高德 API](https://lbs.amap.com/)）
* [Google Maps API Key](https://developers.google.com/maps/apis-by-platform)（若要使用 Google 地图引擎，必须在 Google Cloud 控制台中开通：**Geocoding API, Places API (New), Directions API, Maps JavaScript API, Weather API**，需要绑卡）
* 小红书Cookie（[小红书](https://www.xiaohongshu.com/) 网页端登录后从浏览器开发者工具复制）
* 安装 `uv` 包管理器

### Docker / Compose 配置约定

推荐通过 docker-compose 一键启动项目（包含前端和后端环境），在运行之前，先复制根目录配置模板并填补 `.env` 里的环境变量：

```bash
cp .env.example .env
```

* 容器启动时不再读取项目目录里的 `backend/.env`，请确保将配置以环境变量的形式传入。
* `docker-compose.yaml` 中显式配置了必要的运行时代理和 API keys，支持传入 `GOOGLE_MAPS_API_KEY` 与 `GOOGLE_MAPS_PROXY` 等变量；其中 `GOOGLE_MAPS_PROXY` 只用于后端 Google Maps 服务，不会影响 LLM、小红书或高德请求。
* 前端构建期变量 `VITE_AMAP_WEB_JS_KEY` 与 `VITE_AMAP_SECURITY_JS_CODE` 会通过 `build.args` 自动注入前端；修改后需要重新构建镜像。
* 前端设置页可修改后端运行时配置（LLM、小红书、高德 Web 服务 Key、Google Maps Key/代理等）。敏感字段会被遮罩返回，保存遮罩值时后端会保持原密钥不变。

根目录 `.env` 示例：

```env
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://your-openai-compatible-endpoint/v1
LLM_MODEL_ID=your_model
XHS_COOKIE="a1=xxx; web_session=xxx"
VITE_AMAP_WEB_KEY=your_amap_web_service_key
VITE_AMAP_WEB_JS_KEY=your_amap_web_js_key
VITE_AMAP_SECURITY_JS_CODE=your_amap_security_js_code
GOOGLE_MAPS_API_KEY=
GOOGLE_MAPS_PROXY=
```

本地开发仍可按下面步骤分别配置和启动 `backend/.env` 和 `frontend/.env`。

### 本地开发

#### 1. 后端启动

```bash
# 进入后端主目录
cd backend

# 安装小红书签名引擎的 Node.js 依赖
npm install

# 使用 uv 创建虚拟环境并安装依赖
uv venv .venv

# 激活虚拟环境
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装项目依赖包
uv pip install -r requirements.txt

# 复制配置文件并填入相应的 API KEY
cp .env.example .env
# [必填] LLM_API_KEY, LLM_BASE_URL, LLM_MODEL_ID（选择有结构化输出能力的模型）
# [必填] VITE_AMAP_WEB_KEY (高德地图 web服务 类型的key)
# [必填] XHS_COOKIE（小红书网页端登录后的Cookie）
# [选填] GOOGLE_MAPS_API_KEY, GOOGLE_MAPS_PROXY（如果需要支持 Google 地图引擎）
#         GOOGLE_MAPS_PROXY 只作用于 Google Maps 后端服务，不影响 LLM/小红书/高德。

# 启动 FastAPI (推荐通过 uvicorn)
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
```

API 启动后，您可以访问 `http://localhost:8000/docs` 查看互动文档。

#### 2. 前端启动

```bash
# 进入前端主目录
cd frontend

# 使用 npm (或 pnpm/yarn) 安装依赖
npm install

# 复制配置文件并填入相应的 Key
cp .env.example .env
# [必填] VITE_AMAP_WEB_JS_KEY 必须是 Web端(JS API) 类型的key
# [必填] VITE_AMAP_SECURITY_JS_CODE 为 Web端(JS API) 安全密钥 JSCode
# [可选] VITE_API_BASE_URL 默认为 http://localhost:8000；同源部署可留空

# 启动 Vite 开发服务器
npm run dev
```



---

## 开发与验证

后端已内置单元 + 集成测试与静态检查配置（测试通过 `monkeypatch` 替换外部依赖，**不触网**）：

```bash
cd backend

# 安装开发依赖（pytest / ruff 等）
pip install -r requirements-dev.txt

# 运行测试
python -m pytest -q

# 静态检查
python -m ruff check .
```

前端类型检查与构建：

```bash
cd frontend

# 类型检查（vue-tsc --noEmit）
npm run type-check

# 构建（先类型检查再打包）
npm run build
```

端到端冒烟测试（对运行中的实例发真实 HTTP / WebSocket 请求）：

```bash
cd backend

# 先启动服务
python -m uvicorn app.api.main:app --port 18080

# 另开终端执行（覆盖健康检查、SPA 托管、配置读写、地图/POI 接口、
# 行程任务提交-轮询-WebSocket、404/422 错误路径、路径穿越防护）
python scripts/e2e_check.py
```

浏览器端渲染验证（`vue-tsc` / `vite build` 通过 ≠ 页面能渲染，这一步补上真实渲染与运行时错误检查）：

```bash
cd backend
# 用应用自身的模型生成一份「已完成」的多城市行程，无需 LLM 与任何密钥
python scripts/seed_demo_task.py          # 输出 task_id，例如 e2e00001

cd ..
# 通过 Chrome DevTools Protocol 打开页面、截图，并汇总控制台错误 / 未捕获异常 / 失败请求
node scripts/browser_check.mjs "http://127.0.0.1:18080/" .verify/landing.png
node scripts/browser_check.mjs "http://127.0.0.1:18080/result?plan_id=e2e00001" .verify/graph.png 知识图谱
```

**当前验证状态**：`ruff check .` 全通过 · `pytest -q` **73 passed** ·
`vue-tsc --noEmit` 无错误 · `npm run build` 成功且 **0 告警** ·
HTTP/WebSocket 端到端冒烟 **47/47 通过** ·
浏览器渲染验证（首页 + 结果页 6 个分区）**零控制台错误 / 零未捕获异常 / 零失败请求**。
详见 [MERGE_REPORT.md](MERGE_REPORT.md) 第九节。

---

## 目录结构与关键代码导读

```text
TripStar/
├── backend/                       # Python FastAPI 后端
│   ├── app/
│   │   ├── core/                  # 工程化基础设施 (logging / cache / retry / json_utils / job_store / constants)
│   │   ├── api/routes/            # 核心路由 (trip.py, poi.py, chat.py)
│   │   ├── agents/                # 多智能体定义与编排 (trip_planner_agent.py 并发核心)
│   │   ├── services/              # 业务逻辑封装
│   │   │   ├── amap_service.py    # 高德 REST 服务（POI/天气/地理编码/路线，带缓存与重试）
│   │   │   ├── xhs_service.py     # 小红书搜索/SSR抓取/LLM提纯/搜图
│   │   │   ├── llm_service.py     # LLM 客户端封装
│   │   │   └── knowledge_graph_service.py  # 知识图谱构建
│   │   └── models/                # Pydantic 类型定义 (schemas.py)
│   ├── tests/                     # pytest 单元 + 集成测试（不触网）
│   ├── pyproject.toml             # ruff + pytest 配置
│   └── .env                       # 本地开发环境变量载体（Docker 部署时不打进镜像）
│
├── frontend/                      # Vue 3 互动前端
│   ├── src/
│   │   ├── views/                 # 主路由视图 (Home.vue 表单输入; Result.vue 路书展示)
│   │   ├── components/            # 独立复用的 UI / 背景组件
│   │   └── services/              # Axios 异步轮询及配置重试逻辑 (api.ts)
│   ├── index.html                 # 入口挂载及高德地图 SecurityKey 占位符
│   ├── .env                       # 本地前端开发环境变量（Docker 构建时忽略）
│   └── package.json
│
├── Dockerfile                     # 通用生产发布容器脚本
├── docker-compose.yaml            # 一键容器编排
└── README.md
```

> 下面是部分运行结果，丰富的功能探索中...

<img width="1600" height="799" alt="image" src="https://github.com/user-attachments/assets/20221707-c115-4da7-aa49-80eec772bc33" />
<img width="1598" height="801" alt="image" src="https://github.com/user-attachments/assets/1b4b745e-98f1-4868-a6dd-d32909077713" />
<img width="1649" height="805" alt="image" src="https://github.com/user-attachments/assets/fe775f15-7a1e-467e-a1c4-f97361e13d95" />
<img width="1599" height="823" alt="image" src="https://github.com/user-attachments/assets/a262a33d-4dbc-4f5a-b392-9b2d0ab66a31" />
<img width="1599" height="741" alt="image" src="https://github.com/user-attachments/assets/2c236df0-6ad2-44a0-8976-93d84ea14b1f" />




## 后续优化方向
- [x] ~~接入小红书，获得高质量计划~~
- [x] ~~景点图片改为从小红书获取~~
- [x] ~~景点提前预约提示~~
- [x] ~~接入 Google Maps，实现国内外双引擎自动降级回退~~
- [x] ~~模型返回语言国际化适配及底层知识图谱多语言支持~~
- [x] ~~可查看历史计划支持，通过任务和后端持久化解决~~
- [x] ~~支持代理配置 (HTTP/SOCKS5) 以确保国内可用 Google 服务~~
- [x] ~~修改导出图片的外观，增加地图，提高可读性~~
- [x] ~~支持多城市旅行~~
- [x] ~~后端工程化加固：结构化日志 / TTL 缓存 / 指数退避重试 / 容错 JSON 解析 / 任务 TTL 回收~~
- [x] ~~修复高德服务静默失效、地图 health 500、路线校验冲突、签名引擎拖垮启动等问题~~
- [x] ~~补齐后端自动化测试与静态检查（pytest + ruff）~~
- [x] ~~前端 antd 改为按需自动引入，消除大 chunk 构建告警~~
- [ ] 添加小红书链接以及美食推荐增强
- [ ] 前端优化
- [ ] 车程信息
- [ ] 服务器在线部署



## Star History

<a href="https://www.star-history.com/?repos=1sdv%2Ftripstar&type=date&legend=bottom-right">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=1sdv/tripstar&type=date&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=1sdv/tripstar&type=date&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=1sdv/tripstar&type=date&legend=top-left" />
 </picture>
</a>


## 贡献者

<a href="https://github.com/1sdv/TripStar/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=1sdv/TripStar" />
</a>


## 🙏 致谢
感谢 [linuxdo](https://linux.do/) 社区的交流、分享与反馈，让 TripStar 的迭代更高效，同时欢迎大家进群交流反馈
<img width="431" height="411" alt="image" src="https://github.com/user-attachments/assets/118d46c0-a8e9-42fb-8110-c233fc4f6277" />

