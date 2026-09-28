"""FastAPI主应用。"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ..config import init_config, log_config_summary, validate_config
from ..core.constants import ErrorCode
from ..core.logging import get_logger
from .routes import assistant, poi, trip
from .routes import map as map_routes

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
        logger.info("✅ 配置验证通过")
    except ValueError as exc:
        logger.error("❌ 配置验证失败:\n%s", exc)
        raise

    if settings.docs_enabled:
        logger.info("📚 API 文档: http://localhost:%s/docs", settings.port)
    logger.info("=" * 60)

    yield

    logger.info("👋 应用正在关闭...")


# 非公开环境下隐藏交互文档
_docs_kwargs = {} if settings.docs_enabled else {"docs_url": None, "redoc_url": None, "openapi_url": None}

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="基于HelloAgents框架的智能旅行规划助手API",
    lifespan=lifespan,
    **_docs_kwargs,
)

# 配置CORS
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
app.include_router(assistant.router, prefix="/api")


@app.get("/")
async def root() -> dict:
    """根路径。"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs" if settings.docs_enabled else None,
    }


@app.get("/health")
async def health() -> dict:
    """全局健康检查。"""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.api.main:app", host=settings.host, port=settings.port, reload=True)
