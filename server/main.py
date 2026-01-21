from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging
from contextlib import asynccontextmanager
from typing import Callable

from src.core.settings import settings
from src.core.exceptions import setup_exception_handlers
from src.api.router import router as api_router
from src.api.exceptions import APIError, api_error_handler, generic_error_handler
from src.db.database import engine
from src.api.v1.error_handlers import register_classification_exception_handlers

# 导入任务执行器
from src.services.task_executor import init_task_executor, start_task_executor, stop_task_executor

# 导入任务处理器（必须导入以执行装饰器注册）
from src.services import task_handlers  # noqa: F401

# 导入定时任务管理器
from src.services.scheduler.job_manager import get_job_manager

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("Starting up Sector Strength API...")

    # 启动任务执行器
    init_task_executor(poll_interval=5.0, max_concurrent_tasks=2)
    start_task_executor()
    logger.info("TaskExecutor started")

    # 启动定时任务调度器
    job_manager = get_job_manager()
    job_manager.start()
    logger.info("JobManager started - scheduled tasks active")

    yield
    # 关闭时执行
    logger.info("Shutting down Sector Strength API...")

    # 停止任务执行器
    stop_task_executor()
    logger.info("TaskExecutor stopped")

    # 停止定时任务调度器
    job_manager.shutdown(wait=True)
    logger.info("JobManager stopped")

# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    openapi_url=f"/api/v1/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 设置异常处理器
setup_exception_handlers(app)

# 添加 API 异常处理器
app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(Exception, generic_error_handler)

# 注册分类异常处理器
register_classification_exception_handlers(app)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注释掉 TrustedHostMiddleware 以避免事件循环冲突问题
# 在生产环境中应通过反向代理（如 Nginx）来控制主机头验证
# app.add_middleware(
#     TrustedHostMiddleware,
#     allowed_hosts=["localhost", "127.0.0.1", settings.API_HOST]
# )

# 注册 API 路由
app.include_router(api_router, prefix="/api")

# 根路径
@app.get("/")
async def root():
    return {
        "message": "Sector Strength API is running",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }

# 健康检查端点
@app.get("/health")
async def health_check():
    """服务健康检查"""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "version": settings.APP_VERSION,
        "timestamp": time.time()
    }

@app.get("/health/db")
async def database_health_check():
    """数据库健康检查"""
    try:
        # TODO: 实现实际的数据库连接检查
        return {
            "status": "healthy",
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e)
            }
        )


# 创建自定义 ASGI 中间件来添加请求时间头，避免 BaseHTTPMiddleware 的事件循环冲突
class ProcessTimeMiddleware:
    """
    添加请求处理时间的 ASGI 中间件

    使用纯 ASGI 中间件而不是 BaseHTTPMiddleware，避免事件循环冲突问题。
    """
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # 记录开始时间
        start_time = time.time()

        # 包装 send 函数来添加响应头
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                # 计算处理时间
                process_time = time.time() - start_time

                # 添加处理时间到响应头
                headers = dict(message.get("headers", []))
                headers[b"x-process-time"] = str(process_time).encode()
                message["headers"] = [(k, v) for k, v in headers.items()]

            await send(message)

        await self.app(scope, receive, send_wrapper)

# 将应用包装在自定义中间件中（必须在所有路由注册之后）
app = ProcessTimeMiddleware(app)