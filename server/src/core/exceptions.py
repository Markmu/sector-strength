"""自定义异常类"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class BaseCustomException(Exception):
    """基础自定义异常"""

    def __init__(
        self,
        status_code: int,
        detail: str,
        headers: Optional[Dict[str, Any]] = None,
    ):
        self.status_code = status_code
        self.detail = detail
        self.headers = headers


class DatabaseError(BaseCustomException):
    """数据库操作异常"""

    def __init__(self, detail: str = "数据库操作失败"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )


class ValidationError(BaseCustomException):
    """数据验证异常"""

    def __init__(self, detail: str = "数据验证失败"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


class NotFoundError(BaseCustomException):
    """资源未找到异常"""

    def __init__(self, detail: str = "资源未找到"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )


class ConflictError(BaseCustomException):
    """资源冲突异常"""

    def __init__(self, detail: str = "资源冲突"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail
        )


class UnauthorizedError(BaseCustomException):
    """未授权异常"""

    def __init__(self, detail: str = "未授权访问"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class ForbiddenError(BaseCustomException):
    """禁止访问异常"""

    def __init__(self, detail: str = "禁止访问"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


class AuthenticationError(BaseCustomException):
    """认证异常"""

    def __init__(self, detail: str = "认证失败"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail
        )


class RateLimitExceeded(BaseCustomException):
    """速率限制 exceeded 异常"""

    def __init__(self, detail: str = "请求频率过高，请稍后再试"):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail
        )


class AccountLockedError(BaseCustomException):
    """账户锁定异常"""

    def __init__(self, detail: str = "账户已被锁定"):
        super().__init__(
            status_code=status.HTTP_423_LOCKED,
            detail=detail
        )


def setup_exception_handlers(app):
    """设置异常处理器"""
    from fastapi import Request
    from fastapi.responses import JSONResponse
    from fastapi.exceptions import RequestValidationError
    from starlette.exceptions import HTTPException as StarletteHTTPException
    import logging

    logger = logging.getLogger(__name__)

    def _make_json_safe(value):
        """Convert nested validation payloads to JSON-serializable structures."""
        if isinstance(value, dict):
            return {k: _make_json_safe(v) for k, v in value.items()}
        if isinstance(value, list):
            return [_make_json_safe(v) for v in value]
        if isinstance(value, tuple):
            return [_make_json_safe(v) for v in value]
        try:
            import json
            json.dumps(value)
            return value
        except Exception:
            return str(value)

    @app.exception_handler(BaseCustomException)
    async def custom_exception_handler(request: Request, exc: BaseCustomException):
        """处理自定义异常"""
        logger.error(f"Custom exception: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "error": {
                    "type": exc.__class__.__name__,
                    "message": exc.detail,
                    "status_code": exc.status_code
                }
            },
            headers=exc.headers
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """处理 HTTP 异常"""
        logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "error": {
                    "type": "HTTPException",
                    "message": exc.detail,
                    "status_code": exc.status_code
                }
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """处理请求验证异常"""
        safe_errors = _make_json_safe(exc.errors())
        logger.warning(f"Validation error: {safe_errors}")
        return JSONResponse(
            status_code=422,
            content={
                "detail": safe_errors,
                "error": {
                    "type": "ValidationError",
                    "message": "Invalid request data",
                    "details": safe_errors,
                    "status_code": 422
                }
            }
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """处理通用异常"""
        logger.error(f"Unhandled exception: {type(exc).__name__} - {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "type": "InternalServerError",
                    "message": "Internal server error",
                    "status_code": 500
                }
            }
        )
