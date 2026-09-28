# Hello-Travel 改进优化报告

> 本文档记录一次针对本项目（智能旅行规划助手）的调研、诊断与改造过程。
> 调研对象为 GitHub 上同类开源项目与工程实践，改造范围覆盖后端、前端与部署。

---

## 一、调研：参考了哪些开源项目

| 项目 | 与本项目的关系 | 借鉴点 |
| --- | --- | --- |
| [1sdv/TripStar（旅途星辰）](https://github.com/1sdv/TripStar) | **同为 HelloAgents 框架**的 AI 文旅智能体，最直接的对标 | 三路数据并发采集（`asyncio.gather`）、多级降级 JSON 解析、异步任务 + 状态轮询、Docker 一键部署、景点预约提醒、多级 fallback（地图/天气/解析） |
| [AmanXk/AI-Travel-Planning-System（TripMate AI）](https://github.com/AmanXk/AI-Travel-Planning-System) | LangGraph 多智能体旅行规划 | 按子问题拆分专职 Agent、Append-only 共享状态避免相互覆盖、"研究"与"格式化交付"职责分离、CLI 测试入口 |
| [zhanymkanov/fastapi-best-practices](https://github.com/zhanymkanov/fastapi-best-practices) | FastAPI 生产级最佳实践 | **async 路由里写阻塞 I/O 是反模式**（应使用同步 `def` 或 `run_in_threadpool`）、依赖注入 + `dependency_overrides` 测试、从第 0 天搭好 async 测试客户端、语义化异常与错误码 |

**结论**：本项目原本是"能跑通"的教学级实现，但在**并发、容错、可观测性、可测试性、部署**五个维度上与成熟开源项目有明显差距。本次改造即围绕这五点展开。

---

## 二、诊断：改造前发现的真实缺陷

### 2.1 会直接报错的 Bug

| # | 位置 | 问题 |
| --- | --- | --- |
| 1 | `app/api/routes/trip.py` `/api/trip/health` | 访问 `agent.agent.name` / `agent.agent.list_tools()`，但 `MultiAgentTripPlanner` **根本没有 `agent` 属性** → 该端点必然 500 |
| 2 | `app/api/routes/map.py` `/api/map/health` | 访问 `service.mcp_tool._available_tools`，但 `AmapService` **没有 `mcp_tool` 属性** → 该端点必然 500 |
| 3 | `app/services/unsplash_service.py` | 使用 `requests`，但 `requirements.txt` **从未声明该依赖** → 景点配图功能运行即 ImportError |
| 4 | `frontend/vite.config.ts` | `manualChunks` 引用 `@ant-design/icons-vue`，但 `package.json` 未声明 → 依赖传递侥幸可用，一旦 antd 版本变化即构建失败 |
| 5 | `frontend/src/views/*.vue` | 读取 `import.meta.env.VITE_AMAP_WEB_JS_KEY`，而 `.env.example` 写的是 `VITE_AMAP_JS_KEY` → **地图永远加载不出来** |
| 6 | `frontend/src/views/Result.vue` | `fetch('http://localhost:8000/api/poi/photo')` 硬编码后端地址，绕过统一 axios 封装 → 非本地部署时配图全部失败 |
| 7 | `app/api/routes/map.py` `/api/map/route` | 路线解析失败时返回 `{}`，而响应模型 `data: Optional[RouteInfo]` 不接受空对象 → 触发 Pydantic 校验错误 |

### 2.2 架构与性能问题

- **三路数据串行采集**：景点 → 天气 → 酒店依次等待，白白浪费两个 RTT 的时间。
- **景点只取 `preferences[0]` 一个关键词**，召回面窄。
- **`async def` 路由里跑同步阻塞 I/O**（高德 `httpx.get`、OpenAI 同步客户端、`requests`），会卡死事件循环。`/api/trip/plan`、`/api/map/*`、`/api/poi/*`、`/api/assistant/chat` 全部中招。
- **`_job_store` 是裸 dict，永不清理** → 长时间运行内存持续增长。
- **JSON 解析极其脆弱**：只做 `find("```json")`，模型一旦输出带注释/尾逗号/被 `max_tokens` 截断，就整体失败并退化成"景点1/景点2"占位数据。
- **景点校验只打印不修复**：`_validate_plan_against_poi_search` 发现问题仅 `print` 日志，虚构景点仍会带着错误坐标返回给前端（酒店有强制对齐，景点没有）。

### 2.3 前端问题

- **内存泄漏**：`Result.vue` / `Explore.vue` **没有 `onUnmounted`**，高德地图实例从不 `destroy`；`Home.vue` 的 `setInterval` 在组件提前卸载时不会清理。
- **大量重复代码**：`initMap`、InfoWindow HTML、html2canvas 导出配置在多个视图里几乎逐字复制。
- **`console.log` 泄露**：请求拦截器把每次请求/响应打进控制台。
- **`any` 泛滥**、`history.ts` 写入无 try/catch（存储配额满会抛错中断保存）。

---

## 三、改进内容

### 3.1 后端 · 新增基础设施层 `app/core/`

| 模块 | 作用 |
| --- | --- |
| `logging.py` | 统一结构化日志，替换满屏 `print`；压制第三方库噪音 |
| `cache.py` | 线程安全 TTL 缓存，供高德 POI / 天气 / 地理编码复用 |
| `retry.py` | 同步 + 异步指数退避重试（不引入 tenacity，保持依赖精简） |
| `json_utils.py` | **五级降级 JSON 解析**：剥围栏 → 括号配平截取 → 修注释/尾逗号 → 补截断括号 → 逐级 `json.loads` |
| `job_store.py` | 带 TTL 回收 + 容量上限的任务存储，替换裸 dict |
| `constants.py` | 语义化 `ErrorCode` 枚举、经纬度合理范围、超时与缓存常量 |

### 3.2 后端 · 性能

- **三路并发采集**：`plan_trip` 用 `ThreadPoolExecutor(max_workers=3)` 同时发起景点 / 天气 / 酒店查询，端到端耗时约降为原来的 1/3（取决于最慢的那一路）。
- **多关键词景点召回**：新增 `AmapService.search_pois_multi()`，把最多 4 个偏好标签并行检索并按 `POI id / 名称+地址` 去重。
- **高德结果缓存**：POI / 天气 / 地理编码统一走 TTL 缓存（默认 600s，`AMAP_CACHE_TTL` 可调），重复请求与配额消耗显著下降。
- **阻塞 I/O 归位**：所有会调用阻塞外部服务的路由改为同步 `def`，由 FastAPI 自动丢进线程池；`/plan_async` 保持 `asyncio.to_thread`。这直接对应 fastapi-best-practices 的核心规则。

### 3.3 后端 · 健壮性

- **容错解析**：LLM 输出经 `extract_json()` 多级修复，显著降低"退化成占位数据"的概率。
- **景点强制对齐**（对齐 TripStar 的做法）：名称能匹配则对齐真实 POI 的 name/address/location；匹配不上或跨天重复则**回填尚未使用的真实景点**；无可用景点时丢弃重复项，不再产生虚构坐标。
- **自动补预算**：LLM 漏返回 `budget` 时，按每日门票/餐饮/酒店明细自动汇总。
- **预约提醒**：识别故宫、国博、陕历博、兵马俑、莫高窟等热门景点，标记 `needs_reservation` 并给出提示文案。
- **外部调用重试**：高德接口与 LLM 调用均带指数退避；LLM 客户端显式设置超时与 `max_retries=0`（由我们自己的重试统一控制）。
- **生命周期与全局异常**：废弃 `@app.on_event`，改用 `lifespan`；新增 `RequestValidationError` 与兜底 `Exception` 处理器，统一返回 `{success, error_code, message, detail}` 结构。
- **文档按环境隐藏**：非 `local/dev/staging` 环境自动关闭 `/docs`、`/redoc`、`openapi.json`。

### 3.4 后端 · 可测试性

- 新增 `tests/`：**37 个用例全部通过**，覆盖容错 JSON 解析（含截断、注释、嵌套引号等边界）、TTL 缓存过期、重试成功/耗尽/不误捕异常、景点与酒店对齐、预算汇总、兜底计划，以及 API 集成测试（用 `monkeypatch` 替换外部依赖，**不触网**）。
- 其中 3 个用例是**针对本次修复 Bug 的回归测试**（两个 health 端点、`/map/route` 空结果）。
- 新增 `requirements-dev.txt`、`pyproject.toml`（含 ruff 与 pytest 配置）。

### 3.5 前端 · 工程化

| 新增 | 作用 |
| --- | --- |
| `config/index.ts` | 集中管理环境变量（**兼容两种高德 Key 命名**）、地图默认中心/缩放、历史条数上限 |
| `utils/logger.ts` | 环境分级日志，生产环境只输出 warn/error，不再泄露请求地址 |
| `utils/format.ts` | 时间 / 时长 / 距离 / 金额格式化 |
| `utils/image.ts` | 占位图生成（改用 `TextEncoder` 替代废弃的 `unescape+btoa`）+ 图片兜底 |
| `utils/export.ts` | 图片 / PDF / 文本导出，消除 html2canvas 配置重复 |
| `composables/useAMap.ts` | **统一地图封装**：init / markers / InfoWindow / 折线，并在 `onUnmounted` 自动 `destroy`，一处修复两个视图的内存泄漏 |
| `services/api.ts` | 新增 `fetchAttractionPhoto()` 与 `extractErrorMessage()`，消除硬编码 `localhost:8000` |
| `vite-env.d.ts` | 补齐 `ImportMetaEnv` 类型声明 |

- **内存泄漏修复**：`Result.vue`、`Explore.vue` 的地图与折线随组件卸载自动销毁；`Home.vue` 的 `setInterval` / `setTimeout` 统一由 `clearTimers()` + `onUnmounted` 管理。
- **错误处理**：`history.ts` 写入加 try/catch 并在配额满时降级裁剪；`History.vue` 删除/清空加异常捕获。
- **依赖补齐**：`package.json` 显式声明 `@ant-design/icons-vue`、`dayjs`；新增 `type-check` / `build:only` 脚本。

### 3.6 前端 · 打包体积优化

原实现用 `app.use(Antd)` 全量注册组件库，导致 antd 被打成单个 **1.45 MB** 的 chunk，构建时持续告警。

改为官方推荐的按需引入方案：

- 引入 `unplugin-vue-components` + `AntDesignVueResolver`
- `main.ts` 移除 `app.use(Antd)`（ant-design-vue v4 使用 CSS-in-JS，无需按组件引入样式）
- `vite.config.ts` 移除 `antd` 的 `manualChunks`（否则会把整个 barrel 重新捆在一起）

**收益（实测）**：

| 指标 | 优化前 | 优化后 | 变化 |
| --- | --- | --- | --- |
| 最大 JS chunk | 1.45 MB（antd） | 388 KB（jspdf，按需异步加载） | ↓ 73% |
| JS 总量（未压缩） | 2.79 MB | 1.74 MB | ↓ 38% |
| `dist` 总体积 | 2.5 MB | 1.9 MB | ↓ 24% |
| 构建告警 | chunk > 500 kB | 无 | — |

> **附带收益**：按需引入后 `components.d.ts` 提供了 antd 组件的**真实类型**，使 `vue-tsc` 暴露出 3 处此前被掩盖的类型错误（`DatePicker` 的 `null` 值、`Tabs` 的 `key` 类型），已一并修复——类型检查从"形同虚设"变为真正有效。

### 3.7 部署

- `backend/Dockerfile` + `.dockerignore`：依赖层缓存、非 root 运行、内置 healthcheck。
- `frontend/Dockerfile` + `nginx.conf`：多阶段构建（Node 构建 → Nginx 托管），gzip、静态资源长缓存、SPA 路由回退、`/api` 反向代理（读写超时放宽到 600s 以适配长耗时行程生成）。
- `docker-compose.yml`：一键起前后端，`frontend` 等待 `backend` 健康后再启动。

### 3.8 仓库卫生

- 原仓库把两个一次性调试脚本 `diagnose_coordinates.py`、`test_poi_fix.py` 直接放在 `backend/` 根目录。其中 `test_poi_fix.py` 会被 pytest 的默认 `test_*.py` 规则**误认为测试用例**（当前靠 `testpaths=["tests"]` 侥幸避开，一旦有人显式执行 `pytest test_poi_fix.py` 或改写 `testpaths`，就会在收集阶段执行模块级代码并真实请求高德接口）。
- 处理：统一移入 `backend/scripts/`，并将 `test_poi_fix.py` 重命名为 `check_poi_fix.py`，彻底消除 `test_` 前缀歧义；同步修正脚本内 `sys.path` 计算（`parent` → `parent.parent`，因为层级下移了一层）。
- `run.py` 重写为 `main()` 入口，补齐模块 docstring 并说明生产环境应直接用 uvicorn 拉起（与 Dockerfile 保持一致）。
- `ruff` 配置新增 `scripts/*` 的 `E402` 豁免（脚本必须先 `sys.path.insert` 再 import，属合法写法）。
- 结果：`ruff check .` 从"仅对 `app`/`hello_agents`/`tests` 三个目录绿"扩展为**整个 backend 全绿**（清理 51 处告警：尾部空白、未用导入、导入未排序、无占位符 f-string）。

---

## 四、验证结果

```bash
# 后端单元 + 集成测试
cd backend && .venv/Scripts/python -m pytest -q
# → 37 passed

# 后端静态检查（覆盖 backend 全量，含 scripts/）
cd backend && .venv/Scripts/python -m ruff check .
# → All checks passed!

# 前端类型检查与构建
cd frontend && npm run type-check && npm run build
# → 通过，无 chunk 体积告警
```

**按需引入的验证**：构建产物中，抽样检查 12 个「已使用」组件的 `name` 字面量**全部命中**，10 个「未使用」组件（Transfer / Carousel / Mentions / Cascader / Tree / Table / Upload / Calendar / Steps / Timeline）**全部为 0 命中**，确认 tree-shaking 生效且未误删。

**真实浏览器验证**：用 `vite preview` 托管构建产物，经真实 Chromium 加载三个页面（`/`、`/history`、`/explore`）并截图确认：布局、卡片、表单控件、日期选择器、分段控件、进度条、空状态等 antd 组件**样式与交互均正常**，控制台无报错——排除了"按需引入导致样式丢失"的风险。

> 说明：不使用 `console.log` 或 `print` 作为验证手段，以上结论均来自可复现的命令输出。

---

## 五、后续可继续演进的方向

1. **持久化**：`JobStore` 与历史记录目前仍在内存 / localStorage，可接入 SQLite/PostgreSQL 与 Alembic 迁移。
2. **流式输出**：行程生成改用 SSE 或 WebSocket 推送阶段进度与 token 流，替代固定间隔轮询。
3. **Agent 职责拆分**：参照 TripMate，把"景点研究 / 天气 / 酒店 / 编排 / 格式化"拆成独立 Agent 与共享状态。
4. **限流与鉴权**：为对外 API 增加速率限制与 API Key 校验。
5. **前端组件拆分**：`Result.vue`（2200+ 行）可继续拆出 `DayBoard`、`WeatherPanel`、`BudgetRail` 等子组件。
6. **可观测性**：接入 OpenTelemetry 或结构化日志采集，补充指标与链路追踪。
