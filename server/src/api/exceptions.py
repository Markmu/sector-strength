"""
API 异常处理

定义自定义 API 异常和统一错误处理器。
"""

from typing import Optional, Dict, Any
from fastapi import Request, status
from fastapi.responses import JSONResponse

from .schemas.response import ErrorDetail, ErrorResponse


class APIError(Exception):
    """
    自定义 API 错误

    Attributes:
        message: 错误消息
        code: 错误代码
        status_code: HTTP 状态码
        details: 详细信息
    """

    def __init__(
        self,
        message: str,
        code: str = "API_ERROR",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class NotFoundError(APIError):
    """资源未找到错误"""

    def __init__(self, message: str = "资源未找到", details: Optional[Dict] = None):
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class ValidationError(APIError):
    """数据验证错误"""

    def __init__(self, message: str = "数据验证失败", details: Optional[Dict] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class ConflictError(APIError):
    """冲突错误"""

    def __init__(self, message: str = "资源冲突", details: Optional[Dict] = None):
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """
    API 错误处理器

    将自定义 API 错误转换为统一的 JSON 响应。

    Args:
        request: FastAPI 请求对象
        exc: API 错误实例

    Returns:
        JSONResponse: 统一格式的错误响应
    """
    error_detail = ErrorDetail(
        code=exc.code,
        message=exc.message,
        details=exc.details,
    )

    response = ErrorResponse(error=error_detail)

    return JSONResponse(
        status_code=exc.status_code,
        content=response.model_dump(),
    )


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    通用错误处理器

    处理未被特定处理器捕获的异常。

    Args:
        request: FastAPI 请求对象
        exc: 异常实例

    Returns:
        JSONResponse: 统一格式的错误响应
    """
    import logging
    import traceback

    logger = logging.getLogger(__name__)
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    error_detail = ErrorDetail(
        code="INTERNAL_ERROR",
        message=str(exc) if len(str(exc)) < 100 else "服务器内部错误",
        details={"traceback": traceback.format_exc()} if logger.isEnabledFor(logging.DEBUG) else None,
    )

    response = ErrorResponse(error=error_detail)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=response.model_dump(),
    )
