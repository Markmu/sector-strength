"""
数据获取服务自定义异常

定义数据源操作相关的异常类型。
"""

from typing import Optional


class DataSourceError(Exception):
    """数据源基础异常类"""

    def __init__(self, message: str, source: Optional[str] = None, original_error: Optional[Exception] = None):
        """
        初始化数据源异常

        Args:
            message: 错误消息
            source: 数据源名称（如 "AkShare"）
            original_error: 原始异常对象
        """
        self.message = message
        self.source = source
        self.original_error = original_error

        if source:
            full_message = f"[{source}] {message}"
        else:
            full_message = message

        super().__init__(full_message)


class DataFetchError(DataSourceError):
    """数据获取失败异常"""

    def __init__(
        self,
        message: str,
        source: Optional[str] = None,
        endpoint: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        """
        初始化数据获取异常

        Args:
            message: 错误消息
            source: 数据源名称
            endpoint: API 端点或方法名
            original_error: 原始异常对象
        """
        self.endpoint = endpoint
        super().__init__(message, source, original_error)


class DataValidationError(DataSourceError):
    """数据验证失败异常"""

    def __init__(
        self,
        message: str,
        source: Optional[str] = None,
        field_name: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        """
        初始化数据验证异常

        Args:
            message: 错误消息
            source: 数据源名称
            field_name: 验证失败的字段名
            original_error: 原始异常对象
        """
        self.field_name = field_name
        super().__init__(message, source, original_error)


class RetryExhaustedError(DataSourceError):
    """重试次数耗尽异常"""

    def __init__(
        self,
        message: str,
        source: Optional[str] = None,
        attempts: int = 0,
        original_error: Optional[Exception] = None,
    ):
        """
        初始化重试耗尽异常

        Args:
            message: 错误消息
            source: 数据源名称
            attempts: 已尝试次数
            original_error: 原始异常对象
        """
        self.attempts = attempts
        super().__init__(message, source, original_error)


class DataSourceTimeoutError(DataSourceError):
    """请求超时异常（避免与内置 TimeoutError 冲突）"""

    def __init__(
        self,
        message: str,
        source: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        original_error: Optional[Exception] = None,
    ):
        """
        初始化超时异常

        Args:
            message: 错误消息
            source: 数据源名称
            timeout_seconds: 超时时长（秒）
            original_error: 原始异常对象
        """
        self.timeout_seconds = timeout_seconds
        super().__init__(message, source, original_error)
