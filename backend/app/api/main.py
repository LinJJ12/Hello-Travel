"""FastAPI 主应用。

在 TripStar 原有实现之上合并了 Hello-Travel 的工程化改进：

- 用 ``lifespan`` 取代已废弃的 ``@app.on_event``；
- 启动即初始化统一结构化日志（替代裸 ``print``）；
- 新增 ``RequestValidationError`` 与兜底 ``Exception`` 处理器，统一返回
  ``{success, error_code, message, detail}`` 结构；
- 非公开环境（``settings.docs_enabled`` 为假）自动关闭 ``/docs``、``/redoc``
  与 ``openapi.json``。

保留了 TripStar 的两项部署适配：
- ``intercept_proxy_path`` 中间件：兼容云平台在路径前拼接动态 ID 的代理；
- 前端构建产物存在时，由后端直接托管 SPA（单容器部署）。
"""

import os
import sys

# 强制 stdout/stderr 使用 UTF-8，防止非 UTF-8 控制台（如 cp932）输出中文时崩溃
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from contextlib import asynccontextmanager  # noqa: E402
from pathlib import Path  # noqa: E402

from fastapi import FastAPI, HTTPException, Request  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from ..config import init_config, log_config_summary, validate_config  # noqa: E402
from ..core.constants import ErrorCode  # noqa: E402
from ..core.logging import get_logger  # noqa: E402
from .routes import (  # noqa: E402
    chat,
    memory_routes,
    poi,
    trip,  # noqa: E402
)
from .routes import map as map_routes  # noqa: E402
from .routes import settings as settings_routes  # noqa: E402

# 初始化日志并获取配置
settings = init_config()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时校验配置，关闭时释放资源。"""
    logger.info("=" * 60)
    logger.info("🚀 %s v%s 启动中", settings.app_name, settings.app_version)
    logger.info("=" * 60)

    log_config_summary(settings)

    try:
        validate_config(settings)
        logger.info("✅ 配置检查完成")
    except ValueError as exc:
        logger.error("❌ 配置验证失败:\n%s", exc)
        raise

    if settings.docs_enabled:
        logger.info("📚 API 文档: http://localhost:%s/docs", settings.port)
    logger.info("=" * 60)

    yield

    logger.info("👋 应用正在关闭...")


# 非公开环境下隐藏交互文档
_docs_kwargs = {} if settings.docs_enabled else {
    "docs_url": None,
    "redoc_url": None,
    "openapi_url": None,
}

# 创建 FastAPI 应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="基于HelloAgents框架的智能旅行规划助手API",
    lifespan=lifespan,
    **_docs_kwargs,
)


@app.middleware("http")
async def intercept_proxy_path(request: Request, call_next):
    """
    解决云部署环境或前端代理会在路径前拼接一段动态 ID 的问题。
    例如自动将 /5985f5334705698/api/trip/plan 重写为后端的真实路径 /api/trip/plan
    """
    path = request.scope.get("path", "")
    if "/api/" in path and not path.startswith("/api/"):
        api_index = path.find("/api/")
        request.scope["path"] = path[api_index:]

    return await call_next(request)


# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------- 全局异常处理：统一返回结构化错误 ----------------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """请求参数校验失败 → 422 + 语义化错误码。"""
    logger.warning("请求校验失败 %s: %s", request.url.path, exc.errors())
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error_code": ErrorCode.VALIDATION_ERROR,
            "message": "请求参数校验失败",
            "detail": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """兜底异常处理，避免把堆栈直接抛给前端。"""
    logger.exception("未处理异常 %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error_code": ErrorCode.UPSTREAM_ERROR,
            "message": "服务内部错误",
            "detail": str(exc) if settings.debug else None,
        },
    )


# 注册路由
app.include_router(trip.router, prefix="/api")
app.include_router(poi.router, prefix="/api")
app.include_router(map_routes.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(settings_routes.router, prefix="/api")
app.include_router(memory_routes.router, prefix="/api")


@app.get("/")
async def root():
    """根路径 - 生产环境返回前端页面，开发环境返回API信息"""
    # 检查前端构建产物是否存在（Docker 部署时会有）
    dist_index = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "dist" / "index.html"
    if dist_index.exists():
        return FileResponse(str(dist_index))
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs" if settings.docs_enabled else None,
        "redoc": "/redoc" if settings.docs_enabled else None,
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


# 挂载前端静态文件（生产环境 Docker 部署时）
_frontend_dist = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "dist"
if _frontend_dist.exists():
    # 挂载 assets 目录
    _assets_dir = _frontend_dist / "assets"
    if _assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="assets")
    # SPA catch-all: 未匹配的前端路由一律返回 index.html
    _dist_root = _frontend_dist.resolve()

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """SPA 前端路由 fallback"""
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")

        candidate = (_dist_root / full_path).resolve()
        if candidate.is_file() and candidate.is_relative_to(_dist_root):
            return FileResponse(str(candidate))
        return FileResponse(str(_dist_root / "index.html"))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
