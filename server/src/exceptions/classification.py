"""
缠论板块分类自定义异常类

定义板块分类计算过程中的所有异常类型。
"""

from typing import Optional, List, Dict, Any


class ClassificationError(Exception):
    """分类计算基础异常

    所有分类相关异常的基类。

    Attributes:
        message: 错误消息
        code: 错误码
        sector_id: 板块ID
        sector_name: 板块名称
    """

    def __init__(
        self,
        message: str,
        code: str,
        sector_id: Optional[int] = None,
        sector_name: Optional[str] = None
    ):
        self.message = message
        self.code = code
        self.sector_id = sector_id
        self.sector_name = sector_name
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式

        用于 API 错误响应。

        Returns:
            包含错误信息的字典
        """
        return {
            "code": self.code,
            "message": self.message,
            "sector_id": self.sector_id,
            "sector_name": self.sector_name
        }


class MissingMADataError(ClassificationError):
    """均线数据缺失异常

    当所需的均线数据缺失时抛出。

    Attributes:
        sector_id: 板块ID
        sector_name: 板块名称
        missing_fields: 缺失的均线字段列表
    """

    def __init__(
        self,
        sector_id: int,
        sector_name: Optional[str] = None,
        missing_fields: Optional[List[str]] = None
    ):
        message = f"板块 {sector_name or sector_id} 的均线数据缺失"
        if missing_fields:
            message += f"（缺失字段: {', '.join(missing_fields)}）"

        super().__init__(
            message=message,
            code="MISSING_MA_DATA",
            sector_id=sector_id,
            sector_name=sector_name
        )
        self.missing_fields = missing_fields

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，包含缺失字段信息"""
        result = super().to_dict()
        if self.missing_fields:
            result["missing_fields"] = self.missing_fields
        return result


class ClassificationFailedError(ClassificationError):
    """分类计算失败异常

    当分类计算过程失败时抛出。

    Attributes:
        sector_id: 板块ID
        sector_name: 板块名称
        reason: 失败原因
    """

    def __init__(
        self,
        sector_id: int,
        sector_name: Optional[str] = None,
        reason: str = "未知错误"
    ):
        message = f"板块 {sector_name or sector_id} 分类计算失败: {reason}"

        super().__init__(
            message=message,
            code="CLASSIFICATION_FAILED",
            sector_id=sector_id,
            sector_name=sector_name
        )
        self.reason = reason


class InvalidPriceError(ClassificationError):
    """价格数据无效异常

    当价格数据无效或缺失时抛出。

    Attributes:
        sector_id: 板块ID
        sector_name: 板块名称
        reason: 无效原因
    """

    def __init__(
        self,
        sector_id: int,
        sector_name: Optional[str] = None,
        reason: str = "价格数据无效"
    ):
        message = f"板块 {sector_name or sector_id} 的价格数据无效: {reason}"

        super().__init__(
            message=message,
            code="INVALID_PRICE",
            sector_id=sector_id,
            sector_name=sector_name
        )
        self.reason = reason


# 导出 __init__ 用于 from src.exceptions.classification import *
__all__ = [
    "ClassificationError",
    "MissingMADataError",
    "ClassificationFailedError",
    "InvalidPriceError"
]
