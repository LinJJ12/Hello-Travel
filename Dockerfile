# ============================================================
# 旅途星辰 TripStar — 单镜像部署（前端构建产物 + FastAPI 后端）
#
# 合并说明：保留 TripStar 的「前端构建 → 后端托管 SPA」单镜像形态
# （因为运行时还需要 Node.js 执行小红书签名引擎、需要 uvx 启动
# amap-mcp-server），同时吸收 Hello-Travel 的容器工程化改进：
#   - 依赖层前置，充分利用 Docker 层缓存
#   - 非 root 用户运行
#   - 内置 HEALTHCHECK
#   - .dockerignore 排除测试 / 本地数据 / 密钥
# ============================================================

# ================================
# 阶段一：构建前端
# ================================
FROM node:22-slim AS frontend-builder

WORKDIR /build

# 依赖层单独缓存：package.json / lock 未变时不重复安装
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --registry=https://registry.npmmirror.com

# 复制前端源码并构建
COPY frontend/ ./

# 接收构建参数
ARG VITE_AMAP_WEB_JS_KEY
ARG VITE_AMAP_SECURITY_JS_CODE

# API 使用相对路径（同源部署，由后端托管 SPA）
ENV VITE_API_BASE_URL=""
ENV VITE_AMAP_WEB_JS_KEY=${VITE_AMAP_WEB_JS_KEY:-}
ENV VITE_AMAP_SECURITY_JS_CODE=${VITE_AMAP_SECURITY_JS_CODE:-}

# 跳过 vue-tsc 类型检查（镜像构建只关心产物；类型检查在 CI / 本地执行）
RUN npm run build:only


# ================================
# 阶段二：运行时
# ================================
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_CACHE_DIR=/home/appuser/.cache/uv \
    NODE_ENV=production

# 系统依赖：
#   nodejs / npm —— 小红书签名引擎通过 PyExecJS 调用 Node 执行 JS
#   curl         —— 调试与健康检查
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl nodejs npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 依赖层前置，利用 Docker 层缓存
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 生产进程管理：gunicorn + uvicorn worker
RUN pip install --no-cache-dir gunicorn "uvicorn[standard]"

# 非 root 用户
RUN useradd --create-home --shell /bin/bash appuser

# 预下载 amap-mcp-server 并预热 uv 缓存，避免首次请求时现下载导致超时
RUN uvx amap-mcp-server --help >/dev/null 2>&1 || true

# 后端源码 + 小红书签名引擎所需的 Node 依赖
COPY backend/ ./backend/
RUN cd backend && npm install --omit=dev --registry=https://registry.npmmirror.com

# 前端构建产物（由 FastAPI 托管）
COPY --from=frontend-builder /build/dist ./frontend/dist

# 启动脚本
COPY start.sh ./start.sh
RUN sed -i 's/\r$//' ./start.sh \
    && chmod +x ./start.sh \
    && chown -R appuser:appuser /app /home/appuser

USER appuser

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:7860/health', timeout=3).status==200 else 1)"

CMD ["./start.sh"]
