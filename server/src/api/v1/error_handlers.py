"""
板块分类 API 异常处理器

处理分类计算过程中的自定义异常，提供统一的错误响应格式。
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import logging

from src.exceptions.classification import (
    ClassificationError,
    MissingMADataError,
    ClassificationFailedError,
    InvalidPriceError
)

logger = logging.getLogger(__name__)


async def classification_error_handler(
    request: Request,
    exc: ClassificationError
) -> JSONResponse:
    """处理分类计算异常

    将自定义分类异常转换为标准的 JSON 错误响应。

    Args:
        request: FastAPI 请求对象
        exc: 分类异常实例

    Returns:
        包含错误信息的 JSONResponse
    """
    # 记录错误日志
    logger.error(
        f"分类错误: {exc.code} - {exc.message}",
        extra={
            "sector_id": exc.sector_id,
            "sector_name": exc.sector_name,
            "error_code": exc.code
        }
    )

    # 构建标准错误响应
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "timestamp": datetime.now().isoformat()
            }
        }
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """处理通用异常

    捕获未处理的异常，返回服务器错误响应。

    Args:
        request: FastAPI 请求对象
        exc: 异常实例

    Returns:
        包含错误信息的 JSONResponse
    """
    logger.error(
        f"未处理的异常: {type(exc).__name__} - {str(exc)}",
        exc_info=True
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "服务器内部错误，请稍后重试",
                "timestamp": datetime.now().isoformat()
            }
        }
    )


async def sqlalchemy_error_handler(
    request: Request,
    exc: SQLAlchemyError
) -> JSONResponse:
    """处理数据库异常

    Args:
        request: FastAPI 请求对象
        exc: SQLAlchemy 异常实例

    Returns:
        包含错误信息的 JSONResponse
    """
    logger.error(f"数据库错误: {str(exc)}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "DATABASE_ERROR",
                "message": "数据库错误，请稍后重试",
                "timestamp": datetime.now().isoformat()
            }
        }
    )


def register_classification_exception_handlers(app):
    """注册分类异常处理器到 FastAPI 应用

    Args:
        app: FastAPI 应用实例
    """
    app.add_exception_handler(ClassificationError, classification_error_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)

    # 注意：不要在这里注册通用 Exception 处理器，
    # 因为全局异常处理器已经在 src/core/exceptions.py 中设置

    logger.info("分类异常处理器已注册")


__all__ = [
    "classification_error_handler",
    "generic_exception_handler",
    "sqlalchemy_error_handler",
    "register_classification_exception_handlers"
]
