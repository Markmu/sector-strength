"""
强度服务异常定义

定义强度计算和服务层的所有异常类型。
"""


class StrengthServiceError(Exception):
    """强度服务基础异常"""
    pass


class InsufficientDataError(StrengthServiceError):
    """数据不足异常

    当实体可用数据不足以进行计算时抛出。

    Attributes:
        entity_id: 实体ID
        entity_type: 实体类型 ('stock' 或 'sector')
        available_days: 可用数据天数
        required_days: 需要的数据天数
    """

    def __init__(
        self,
        entity_id: int,
        entity_type: str,
        available_days: int,
        required_days: int
    ):
        self.entity_id = entity_id
        self.entity_type = entity_type
        self.available_days = available_days
        self.required_days = required_days
        super().__init__(
            f"{entity_type} {entity_id} 数据不足："
            f"可用 {available_days} 天，需要 {required_days} 天"
        )


class CalculationError(StrengthServiceError):
    """计算失败异常

    当强度计算过程失败时抛出。

    Attributes:
        entity_id: 实体ID
        entity_type: 实体类型
        reason: 失败原因
    """

    def __init__(self, entity_id: int, entity_type: str, reason: str):
        self.entity_id = entity_id
        self.entity_type = entity_type
        self.reason = reason
        super().__init__(
            f"{entity_type} {entity_id} 计算失败: {reason}"
        )


class DataNotFoundError(StrengthServiceError):
    """数据不存在异常

    当请求的数据不存在时抛出。

    Attributes:
        entity_id: 实体ID
        entity_type: 实体类型
        date: 查询日期
    """

    def __init__(self, entity_id: int, entity_type: str, date):
        self.entity_id = entity_id
        self.entity_type = entity_type
        self.date = date
        super().__init__(
            f"{entity_type} {entity_id} 在 {date} 的强度数据不存在"
        )


class BatchCalculationError(StrengthServiceError):
    """批量计算异常

    批量计算过程中的整体异常。

    Attributes:
        total_count: 总数
        success_count: 成功数
        error_count: 错误数
        errors: 错误列表
    """

    def __init__(
        self,
        total_count: int,
        success_count: int,
        error_count: int,
        errors: list
    ):
        self.total_count = total_count
        self.success_count = success_count
        self.error_count = error_count
        self.errors = errors
        super().__init__(
            f"批量计算完成: {success_count}/{total_count} 成功, "
            f"{error_count} 失败"
        )
