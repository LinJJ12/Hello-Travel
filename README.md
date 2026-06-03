# 智能旅行规划助手 🌍✈️

基于 OpenAI 兼容 LLM 构建的智能旅行规划助手，集成高德地图开放平台 API，提供个性化的旅行计划生成、行程伴游和历史记录管理。

## ✨ 功能特点

- 🤖 **AI驱动的旅行规划**: 支持 OpenAI、DeepSeek 等 LLM 提供商，智能生成详细的多日旅程
- 🗺️ **高德地图集成**: 直接调用高德地图 HTTP API，支持景点搜索、路线规划、天气查询、地理编码等功能
- 🧠 **智能 Agent**: 可扩展的 Agent 框架，支持多步骤协作生成行程
- 💬 **行程伴游聊天**: 基于生成的行程进行智能问答，提供实时旅游建议
- 📜 **历史记录**: 保存和管理历史旅行计划
- 📸 **图片展示**: 集成 Unsplash API，为景点提供精美图片
- 📄 **PDF导出**: 支持将旅行计划导出为PDF文件
- 🎨 **现代化前端**: Vue3 + TypeScript + Vite + Ant Design Vue，响应式设计，流畅的用户体验
- 📱 **完整功能**: 包含住宿、交通、餐饮和景点游览时间推荐

## 🏗️ 技术栈

### 后端
- **LLM**: OpenAI 兼容接口 (OpenAI, DeepSeek 等)
- **API**: FastAPI
- **地图服务**: 高德地图开放平台 HTTP API
- **图片服务**: Unsplash API
- **Agent 框架**: 本地 SimpleAgent 实现
- **HTTP 客户端**: httpx, aiohttp
- **数据验证**: Pydantic

### 前端
- **框架**: Vue 3 + TypeScript
- **路由**: Vue Router
- **构建工具**: Vite
- **UI组件库**: Ant Design Vue
- **地图服务**: 高德地图 JavaScript API
- **HTTP客户端**: Axios
- **PDF导出**: html2canvas + jspdf

## 📁 项目结构

```
helloagents-trip-planner/
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── agents/            # Agent实现
│   │   │   ├── __init__.py
│   │   │   └── trip_planner_agent.py
│   │   ├── api/               # FastAPI路由
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   └── routes/
│   │   │       ├── __init__.py
│   │   │       ├── assistant.py    # 行程伴游
│   │   │       ├── trip.py         # 旅行规划
│   │   │       ├── poi.py          # POI搜索
│   │   │       └── map.py          # 地图服务
│   │   ├── services/          # 服务层
│   │   │   ├── __init__.py
│   │   │   ├── amap_service.py    # 高德地图服务
│   │   │   ├── llm_service.py     # LLM服务
│   │   │   └── unsplash_service.py # Unsplash图片服务
│   │   ├── models/            # 数据模型
│   │   │   ├── __init__.py
│   │   │   └── schemas.py
│   │   ├── config.py          # 配置管理
│   │   └── __init__.py
│   ├── hello_agents/          # HelloAgents框架
│   │   ├── __init__.py
│   │   └── tools.py
│   ├── requirements.txt
│   ├── .env
│   ├── .gitignore
│   └── run.py                 # 启动脚本
├── frontend/                   # 前端应用
│   ├── src/
│   │   ├── views/             # 页面视图
│   │   │   ├── Home.vue       # 首页
│   │   │   ├── Result.vue     # 结果页
│   │   │   ├── History.vue    # 历史记录
│   │   │   └── Explore.vue    # 探索页
│   │   ├── services/          # API服务
│   │   │   ├── api.ts
│   │   │   └── history.ts
│   │   ├── types/             # TypeScript类型
│   │   │   └── index.ts
│   │   ├── App.vue
│   │   └── main.ts
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── .env
│   ├── .gitignore
│   └── index.html
└── README.md
```

## 🚀 快速开始

### 前提条件

- Python 3.10+
- Node.js 16+
- 高德地图API密钥 (Web服务API和Web端(JS API))
- LLM API密钥 (OpenAI/DeepSeek等)
- Unsplash API密钥 (可选，用于景点图片)

### 后端安装

1. 进入后端目录
```bash
cd backend
```

2. 创建虚拟环境
```bash
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/Mac: source venv/bin/activate
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

4. 配置环境变量

创建 `.env` 文件并配置以下变量:
```env
# 高德地图API Key
AMAP_API_KEY=your_amap_api_key

# LLM配置
LLM_API_KEY=your_llm_api_key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_ID=gpt-4

# Unsplash API (可选)
UNSPLASH_ACCESS_KEY=your_unsplash_access_key
UNSPLASH_SECRET_KEY=your_unsplash_secret_key

# 服务器配置
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
```

5. 启动后端服务
```bash
python run.py
```

### 前端安装

1. 进入前端目录
```bash
cd frontend
```

2. 安装依赖
```bash
npm install
```

3. 配置环境变量

创建 `.env` 文件:
```env
VITE_AMAP_JS_KEY=your_amap_js_api_key
VITE_API_BASE_URL=http://localhost:8000
```

4. 启动开发服务器
```bash
npm run dev
```

5. 打开浏览器访问 `http://localhost:5173`

## 📝 使用指南

1. **创建旅行计划**:
   - 在首页填写旅行信息: 目的地城市、旅行日期和天数、交通方式偏好、住宿偏好、旅行风格标签等
   - 可设置预算、旅行节奏、同行人群、饮食禁忌等个性化选项

2. **生成计划**:
   - 点击"生成旅行计划"按钮
   - 系统调用 LLM Agent 生成初步计划
   - Agent 自动调用高德地图 API 搜索景点、查询天气
   - 获取路线规划和交通信息
   - 整合所有信息生成完整行程

3. **查看结果**:
   - 每日详细行程
   - 景点信息与地图标记
   - 交通路线规划
   - 天气预报
   - 餐饮推荐
   - 预算估算

4. **行程伴游**:
   - 基于生成的行程进行智能问答
   - 获取实时旅游建议

5. **历史记录**:
   - 保存和管理历史旅行计划
   - 导出PDF分享

## 🔧 核心实现

### Agent 架构

```python
from hello_agents import SimpleAgent, HelloAgentsLLM

# 创建旅行规划Agent
agent = SimpleAgent(
    name="旅行规划助手",
    llm=HelloAgentsLLM(),
    system_prompt="你是一个专业的旅行规划助手..."
)
```

### 高德地图 API 调用

系统支持以下高德地图开放 API:
- **POI 搜索**: `/v3/place/text` - 搜索景点
- **天气查询**: `/v3/weather/weatherInfo` - 查询天气
- **路线规划**: `/v3/direction/{walking|driving|transit/integrated}` - 规划路线
- **地理编码**: `/v3/geocode/geo` - 地址转坐标
- **POI 详情**: `/v5/place/detail` - 获取POI详情

## 📄 API文档

启动后端服务后，访问 `http://localhost:8000/docs` 查看完整的API文档。

主要端点:
- `POST /api/trip/plan` - 生成旅行计划
- `POST /api/assistant/chat` - 行程伴游聊天
- `GET /api/poi/search` - 搜索POI
- `GET /api/map/weather` - 查询天气
- `POST /api/map/route` - 规划路线
- `GET /health` - 健康检查

## 🤝 贡献指南

欢迎提交Pull Request或Issue!

## 📜 开源协议

CC BY-NC-SA 4.0

## 🙏 致谢

- [HelloAgents](https://github.com/datawhalechina/Hello-Agents) - 智能体教程
- [OpenAI](https://openai.com/) - LLM 服务
- [DeepSeek](https://www.deepseek.com/) - 开源 LLM
- [高德地图开放平台](https://lbs.amap.com/) - 地图服务
- [Unsplash](https://unsplash.com/) - 图片服务
- [FastAPI](https://fastapi.tiangolo.com/) - Web 框架
- [Vue 3](https://vuejs.org/) - 前端框架
- [Ant Design Vue](https://antdv.com/) - UI组件库

---

**智能旅行规划助手** - 让旅行计划变得简单而智能 🌈

