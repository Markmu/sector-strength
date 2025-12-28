"""
趋势分析器

实现价格趋势方向判定和趋势强度分析。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from enum import IntEnum

from .base_calculator import BaseCalculator, CalculationResult


class TrendDirection(IntEnum):
    """
    趋势方向枚举

    Attributes:
        UP: 上升趋势 (1)
        NEUTRAL: 横盘/中性 (0)
        DOWN: 下降趋势 (-1)
    """
    UP = 1
    NEUTRAL = 0
    DOWN = -1


class TrendAnalyzer(BaseCalculator):
    """
    趋势分析器

    根据价格和均线关系判定趋势方向。
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化趋势分析器

        Args:
            config: 配置参数
        """
        super().__init__(config)
        # 短期、中期、长期均线周期阈值
        self.short_term_periods = config.get("short_term_periods", [5]) if config else [5]
        self.medium_term_periods = config.get("medium_term_periods", [10, 20]) if config else [10, 20]
        self.long_term_periods = config.get("long_term_periods", [30, 60]) if config else [30, 60]

    async def calculate(
        self,
        current_price: float,
        ma_values: Dict[int, float],
    ) -> CalculationResult:
        """
        判定趋势方向

        Args:
            current_price: 当前价格
            ma_values: 各周期均线值，如 {5: 100.5, 10: 98.2, 20: 95.0, 30: 92.0, 60: 90.0}

        Returns:
            CalculationResult: 包含趋势方向的结果
        """
        if not self.validate_input(current_price):
            return CalculationResult(
                success=False,
                error="当前价格无效"
            )

        try:
            trend = self.determine_trend(current_price, ma_values)
            return CalculationResult(success=True, data=trend)
        except Exception as e:
            return CalculationResult(success=False, error=f"趋势判定失败: {str(e)}")

    def determine_trend(
        self,
        current_price: float,
        ma_values: Dict[int, float],
    ) -> TrendDirection:
        """
        判定价格趋势方向

        判定规则:
        - 上升趋势: 当前价格 > 短期均线 > 中期均线 > 长期均线 (多头排列)
        - 下降趋势: 当前价格 < 短期均线 < 中期均线 < 长期均线 (空头排列)
        - 横盘: 其他情况

        Args:
            current_price: 当前价格
            ma_values: 各周期均线值

        Returns:
            TrendDirection: 趋势方向

        Examples:
            >>> analyzer = TrendAnalyzer()
            >>> # 多头排列 - 上升趋势
            >>> ma = {5: 105, 10: 102, 20: 100, 30: 98, 60: 95}
            >>> analyzer.determine_trend(110, ma)
            <TrendDirection.UP: 1>
            >>> # 空头排列 - 下降趋势
            >>> ma = {5: 95, 10: 98, 20: 100, 30: 102, 60: 105}
            >>> analyzer.determine_trend(90, ma)
            <TrendDirection.DOWN: -1>
        """
        if not ma_values or len(ma_values) < 3:
            return TrendDirection.NEUTRAL

        # 按周期排序获取均线值
        sorted_periods = sorted(ma_values.keys())
        sorted_ma_values = [ma_values[p] for p in sorted_periods]

        # 检查是否有无效值
        if any(v is None or v <= 0 for v in sorted_ma_values):
            return TrendDirection.NEUTRAL

        # 检查多头排列（上升趋势）
        # 价格 > 所有均线，且均线呈多头排列
        is_bullish = (
            current_price > sorted_ma_values[0] and
            all(sorted_ma_values[i] >= sorted_ma_values[i + 1] - 0.01  # 允许微小误差
                for i in range(len(sorted_ma_values) - 1))
        )

        if is_bullish:
            return TrendDirection.UP

        # 检查空头排列（下降趋势）
        # 价格 < 所有均线，且均线呈空头排列
        is_bearish = (
            current_price < sorted_ma_values[0] and
            all(sorted_ma_values[i] <= sorted_ma_values[i + 1] + 0.01
                for i in range(len(sorted_ma_values) - 1))
        )

        if is_bearish:
            return TrendDirection.DOWN

        return TrendDirection.NEUTRAL

    def determine_trend_simple(
        self,
        current_price: float,
        short_ma: float,
        medium_ma: float,
        long_ma: float,
    ) -> TrendDirection:
        """
        简化版趋势判定（三均线模型）

        Args:
            current_price: 当前价格
            short_ma: 短期均线（如 5日）
            medium_ma: 中期均线（如 20日）
            long_ma: 长期均线（如 60日）

        Returns:
            TrendDirection: 趋势方向
        """
        # 检查有效值
        for value in [current_price, short_ma, medium_ma, long_ma]:
            if value is None or not np.isfinite(value):
                return TrendDirection.NEUTRAL

        # 多头排列
        if current_price > short_ma > medium_ma > long_ma:
            return TrendDirection.UP

        # 空头排列
        if current_price < short_ma < medium_ma < long_ma:
            return TrendDirection.DOWN

        return TrendDirection.NEUTRAL

    def calculate_trend_strength(
        self,
        prices: pd.Series,
        window: int = 5,
    ) -> float:
        """
        计算趋势强度（基于连续上涨/下跌天数）

        Args:
            prices: 价格序列（最近 N 天）
            window: 计算窗口

        Returns:
            趋势强度 (-1 到 1 之间)
            * 正值表示上升趋势强度
            * 负值表示下降趋势强度
            * 0 表示无明确趋势
        """
        if len(prices) < window:
            return 0.0

        # 计算价格变化
        recent_prices = prices.tail(window)
        changes = recent_prices.diff().dropna()

        if len(changes) == 0:
            return 0.0

        # 上涨天数占比
        up_days = (changes > 0).sum()
        down_days = (changes < 0).sum()
        total_days = len(changes)

        if total_days == 0:
            return 0.0

        # 趋势强度 = (上涨天数 - 下跌天数) / 总天数
        strength = (up_days - down_days) / total_days
        return float(strength)

    def analyze_price_position(
        self,
        current_price: float,
        ma_values: Dict[int, float],
    ) -> Dict[str, any]:
        """
        分析价格相对于均线位置

        Args:
            current_price: 当前价格
            ma_values: 各周期均线值

        Returns:
            包含分析结果的字典
        """
        if not ma_values:
            return {
                "position": "unknown",
                "above_count": 0,
                "below_count": 0,
                "total_count": 0,
            }

        above_count = sum(1 for ma in ma_values.values() if ma and current_price > ma)
        below_count = sum(1 for ma in ma_values.values() if ma and current_price < ma)
        total_count = len(ma_values)

        # 判断价格位置
        if above_count == total_count:
            position = "far_above"  # 远高于所有均线
        elif above_count >= total_count * 0.7:
            position = "above"  # 高于大部分均线
        elif below_count == total_count:
            position = "far_below"  # 远低于所有均线
        elif below_count >= total_count * 0.7:
            position = "below"  # 低于大部分均线
        else:
            position = "middle"  # 在均线之间震荡

        return {
            "position": position,
            "above_count": above_count,
            "below_count": below_count,
            "total_count": total_count,
        }

    def get_trend_description(self, trend: TrendDirection) -> str:
        """
        获取趋势方向的中文描述

        Args:
            trend: 趋势方向

        Returns:
            趋势描述字符串
        """
        descriptions = {
            TrendDirection.UP: "上升",
            TrendDirection.NEUTRAL: "横盘",
            TrendDirection.DOWN: "下降",
        }
        return descriptions.get(trend, "未知")
