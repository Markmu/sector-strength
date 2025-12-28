"""
基础计算器抽象类

定义计算引擎的通用接口和抽象方法。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import date


class BaseCalculator(ABC):
    """
    基础计算器抽象类

    所有计算器都必须继承此类并实现核心计算方法。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化计算器

        Args:
            config: 计算器配置参数
        """
        self.config = config or {}

    @abstractmethod
    async def calculate(self, *args, **kwargs) -> Any:
        """
        执行计算

        必须由子类实现。

        Returns:
            计算结果
        """
        pass

    def validate_input(self, data: Any, min_length: int = 1) -> bool:
        """
        验证输入数据

        Args:
            data: 输入数据
            min_length: 最小数据长度

        Returns:
            是否有效
        """
        if data is None:
            return False
        if hasattr(data, '__len__'):
            return len(data) >= min_length
        return True


class CalculationResult:
    """
    计算结果封装类

    用于统一返回计算结果和元数据。
    """

    def __init__(
        self,
        success: bool,
        data: Optional[Any] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化计算结果

        Args:
            success: 是否成功
            data: 结果数据
            error: 错误信息
            metadata: 元数据
        """
        self.success = success
        self.data = data
        self.error = error
        self.metadata = metadata or {}

    def __repr__(self) -> str:
        if self.success:
            return f"<CalculationResult(success=True, data={self.data})>"
        return f"<CalculationResult(success=False, error={self.error})>"
