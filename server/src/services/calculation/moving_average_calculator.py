"""
移动平均线计算器

实现简单移动平均线(SMA)和价格比率计算。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import date

from .base_calculator import BaseCalculator, CalculationResult


class MovingAverageCalculator(BaseCalculator):
    """
    移动平均线计算器

    计算指定周期的简单移动平均线和价格比率。
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化均线计算器

        Args:
            config: 配置参数，可包含 min_periods (最小计算周期)
        """
        super().__init__(config)
        self.min_periods = config.get("min_periods", 2) if config else 2

    async def calculate(
        self,
        prices: pd.Series,
        period: int,
    ) -> CalculationResult:
        """
        计算简单移动平均线

        Args:
            prices: 价格序列（收盘价），索引为日期
            period: 均线周期（5, 10, 20, 30, 60）

        Returns:
            CalculationResult: 包含均线值序列的结果对象
        """
        if not self.validate_input(prices, period):
            return CalculationResult(
                success=False,
                error=f"数据长度不足：需要至少 {period} 个数据点，实际 {len(prices) if prices is not None else 0}"
            )

        try:
            ma_values = self.calculate_sma(prices, period)
            return CalculationResult(success=True, data=ma_values)
        except Exception as e:
            return CalculationResult(success=False, error=f"计算失败: {str(e)}")

    def calculate_sma(self, prices: pd.Series, period: int) -> pd.Series:
        """
        计算简单移动平均线

        Args:
            prices: 价格序列
            period: 均线周期

        Returns:
            均线值序列

        Examples:
            >>> prices = pd.Series([10, 11, 12, 13, 14, 15])
            >>> calculator = MovingAverageCalculator()
            >>> ma = calculator.calculate_sma(prices, 3)
            >>> # 前3个值将是 NaN，第4个值是 (10+11+12)/3 = 11
        """
        return prices.rolling(window=period, min_periods=period).mean()

    def calculate_ema(self, prices: pd.Series, period: int) -> pd.Series:
        """
        计算指数移动平均线（可选）

        Args:
            prices: 价格序列
            period: 均线周期

        Returns:
            EMA 值序列
        """
        return prices.ewm(span=period, adjust=False).mean()

    def calculate_price_ratio(
        self,
        current_price: float,
        ma_value: float,
    ) -> float:
        """
        计算价格与均线的比率

        比率 = (当前价格 - 均线值) / 均线值 * 100
        正值表示价格在均线之上，负值表示在均线之下。

        Args:
            current_price: 当前价格
            ma_value: 均线值

        Returns:
            价格比率百分比

        Examples:
            >>> calculator = MovingAverageCalculator()
            >>> # 价格 105, 均线 100, 比率 = 5%
            >>> calculator.calculate_price_ratio(105, 100)
            5.0
            >>> # 价格 95, 均线 100, 比率 = -5%
            >>> calculator.calculate_price_ratio(95, 100)
            -5.0
        """
        if ma_value == 0 or not np.isfinite(ma_value):
            return 0.0
        if not np.isfinite(current_price):
            return 0.0
        return ((current_price - ma_value) / ma_value) * 100

    def calculate_multiple_periods(
        self,
        prices: pd.Series,
        periods: List[int],
    ) -> Dict[int, pd.Series]:
        """
        计算多个周期的均线

        Args:
            prices: 价格序列
            periods: 周期列表，如 [5, 10, 20, 30, 60]

        Returns:
            字典，键为周期，值为均线序列
        """
        results = {}
        for period in periods:
            ma = self.calculate_sma(prices, period)
            results[period] = ma
        return results

    def get_latest_ma_value(
        self,
        ma_series: pd.Series,
    ) -> Optional[float]:
        """
        获取最新的有效均线值

        Args:
            ma_series: 均线序列

        Returns:
            最新的有效均线值，如果没有则返回 None
        """
        # 过滤 NaN 值，取最后一个有效值
        valid_values = ma_series.dropna()
        if len(valid_values) == 0:
            return None
        return float(valid_values.iloc[-1])

    def calculate_price_ratios_for_periods(
        self,
        current_price: float,
        ma_values: Dict[int, Optional[float]],
    ) -> Dict[int, float]:
        """
        计算当前价格对多个周期的价格比率

        Args:
            current_price: 当前价格
            ma_values: 各周期的均线值字典

        Returns:
            各周期的价格比率字典
        """
        ratios = {}
        for period, ma_value in ma_values.items():
            if ma_value is not None and ma_value > 0:
                ratios[period] = self.calculate_price_ratio(current_price, ma_value)
            else:
                ratios[period] = 0.0
        return ratios
