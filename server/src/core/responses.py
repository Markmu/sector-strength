"""统一响应格式"""

from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    """基础响应模型"""

    success: bool = True
    message: str = "操作成功"
    data: Optional[T] = None
    error_code: Optional[str] = None
    timestamp: Optional[str] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应模型"""

    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class ErrorResponse(BaseModel):
    """错误响应模型"""

    success: bool = False
    message: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None


class HealthResponse(BaseModel):
    """健康检查响应模型"""

    status: str
    version: str
    environment: str
    database_status: str
    timestamp: str