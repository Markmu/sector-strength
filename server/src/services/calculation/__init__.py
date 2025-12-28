"""
计算引擎服务模块

提供均线计算、趋势分析和强度评分功能。
"""

from .base_calculator import BaseCalculator, CalculationResult
from .moving_average_calculator import MovingAverageCalculator
from .trend_analyzer import TrendAnalyzer, TrendDirection
from .strength_calculator import StrengthCalculator
from .batch_processor import BatchProcessor, BatchCalculationResult
from .result_saver import CalculationResultSaver

__all__ = [
    # 基础类
    "BaseCalculator",
    "CalculationResult",
    # 均线计算
    "MovingAverageCalculator",
    # 趋势分析
    "TrendAnalyzer",
    "TrendDirection",
    # 强度计算
    "StrengthCalculator",
    # 批量处理
    "BatchProcessor",
    "BatchCalculationResult",
    # 结果保存
    "CalculationResultSaver",
]
