"""
统一 API 响应格式

定义所有 API 端点使用的标准响应结构。
"""

from typing import Generic, TypeVar, Optional, List, Any
from pydantic import BaseModel, Field


T = TypeVar('T')


class ApiResponse(BaseModel, Generic[T]):
    """
    统一 API 响应格式

    Attributes:
        success: 请求是否成功
        data: 响应数据（成功时）
        error: 错误信息（失败时）
        message: 提示信息
    """

    success: bool = Field(..., description="请求是否成功")
    data: Optional[T] = Field(None, description="响应数据")
    error: Optional[dict] = Field(None, description="错误详情")
    message: Optional[str] = Field(None, description="提示信息")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {"id": 1, "name": "示例"},
                "message": "操作成功"
            }
        }


class PaginatedData(BaseModel, Generic[T]):
    """
    分页数据

    Attributes:
        items: 数据项列表
        total: 总记录数
        page: 当前页码
        page_size: 每页数量
        total_pages: 总页数
    """

    items: List[T] = Field(default_factory=list, description="数据项列表")
    total: int = Field(..., description="总记录数", ge=0)
    page: int = Field(..., description="当前页码", ge=1)
    page_size: int = Field(..., description="每页数量", ge=1, le=100)
    total_pages: int = Field(..., description="总页数", ge=0)

    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedData[T]":
        """
        创建分页数据

        Args:
            items: 数据项列表
            total: 总记录数
            page: 当前页码
            page_size: 每页数量

        Returns:
            分页数据对象
        """
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


class ErrorDetail(BaseModel):
    """
    错误详情

    Attributes:
        code: 错误代码
        message: 错误消息
        details: 详细信息
    """

    code: str = Field(..., description="错误代码")
    message: str = Field(..., description="错误消息")
    details: Optional[dict] = Field(None, description="详细信息")


class ErrorResponse(BaseModel):
    """
    错误响应

    Attributes:
        success: 固定为 False
        error: 错误详情
    """

    success: bool = Field(False, description="请求是否成功")
    error: ErrorDetail = Field(..., description="错误详情")


# 预定义的常用响应类型
class EmptyResponse(BaseModel):
    """空响应（用于 DELETE 等操作）"""

    success: bool = True
    message: Optional[str] = "操作成功"
