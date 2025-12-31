"""
均线排列评分器

检测并计算均线的多头/空头排列状态和得分。
"""

import logging
from typing import Dict, List, Tuple

from src.config.ma_system import MA_PERIODS

logger = logging.getLogger(__name__)


class MAAlignmentScorer:
    """
    均线排列评分器

    检测8条均线的排列状态，判断多头/空头排列强度。
    """

    # 均线周期顺序（从短期到长期）
    PERIODS = [5, 10, 20, 30, 60, 90, 120, 240]

    def __init__(self):
        """初始化均线排列评分器"""
        pass

    def calculate_score(
        self,
        price: float,
        ma_values: Dict[int, float]
    ) -> Tuple[float, str]:
        """
        计算均线排列得分和状态

        检测8个关系：
        1. 价格 > MA5
        2. MA5 > MA10
        3. MA10 > MA20
        4. MA20 > MA30
        5. MA30 > MA60
        6. MA60 > MA90
        7. MA90 > MA120
        8. MA120 > MA240

        评分标准：
        - 8/8 符合 → 100分, 状态 = "perfect_bull"
        - 6-7/8 符合 → 80-90分, 状态 = "strong_bull"
        - 4-5/8 符合 → 60-70分, 状态 = "bull"
        - 3-4/8 符合 → 40-50分, 状态 = "neutral"
        - 1-2/8 符合 → 10-30分, 状态 = "bear"
        - 0/8 符合 → 0分, 状态 = "perfect_bear"

        Args:
            price: 当前价格
            ma_values: 均线值字典 {周期: 均线值}

        Returns:
            (得分, 状态) 元组
        """
        if not ma_values or price is None:
            return 0.0, "perfect_bear"

        try:
            checks = []

            # 检测1: 价格 > MA5
            if 5 in ma_values and ma_values[5] is not None:
                checks.append(1 if price > ma_values[5] else 0)

            # 检测2-8: MA5 > MA10 > ... > MA240
            for i in range(len(self.PERIODS) - 1):
                short_period = self.PERIODS[i]
                long_period = self.PERIODS[i + 1]

                if (short_period in ma_values and long_period in ma_values
                        and ma_values[short_period] is not None
                        and ma_values[long_period] is not None):
                    checks.append(1 if ma_values[short_period] > ma_values[long_period] else 0)

            if not checks:
                return 0.0, "perfect_bear"

            # 统计符合数量
            bull_count = sum(checks)
            total = len(checks)

            # 根据符合数量计算得分和状态
            return self._get_score_by_count(bull_count, total)

        except Exception as e:
            logger.error(f"均线排列得分计算失败: {e}")
            return 0.0, "perfect_bear"

    def _get_score_by_count(self, bull_count: int, total: int) -> Tuple[float, str]:
        """
        根据多头排列符合数量计算得分和状态

        Args:
            bull_count: 符合多头排列的数量
            total: 总检查数量

        Returns:
            (得分, 状态) 元组
        """
        if bull_count == total:
            # 8/8 全部符合
            return 100.0, "perfect_bull"
        elif bull_count >= total * 0.75:
            # 6-7/8 符合
            score = 80.0 + (bull_count - total * 0.75) * 10
            return score, "strong_bull"
        elif bull_count >= total * 0.5:
            # 4-5/8 符合
            score = 60.0 + (bull_count - total * 0.5) * 10
            return score, "bull"
        elif bull_count >= total * 0.25:
            # 3-4/8 符合
            score = 40.0 + (bull_count - total * 0.25) * 10
            return score, "neutral"
        elif bull_count > 0:
            # 1-2/8 符合
            return float(bull_count * 10), "bear"
        else:
            # 0/8 符合
            return 0.0, "perfect_bear"

    def get_alignment_details(
        self,
        price: float,
        ma_values: Dict[int, float]
    ) -> Dict:
        """
        获取详细的均线排列信息

        Args:
            price: 当前价格
            ma_values: 均线值字典

        Returns:
            包含详细排列信息的字典
        """
        if not ma_values or price is None:
            return {
                "score": 0.0,
                "state": "perfect_bear",
                "checks": {},
                "bull_count": 0,
                "total_checks": 0
            }

        checks = {}

        # 检测1: 价格 > MA5
        if 5 in ma_values and ma_values[5] is not None:
            checks["price_above_ma5"] = price > ma_values[5]

        # 检测2-8: 均线排列
        for i in range(len(self.PERIODS) - 1):
            short_period = self.PERIODS[i]
            long_period = self.PERIODS[i + 1]
            key = f"ma{short_period}_above_ma{long_period}"

            if (short_period in ma_values and long_period in ma_values
                    and ma_values[short_period] is not None
                    and ma_values[long_period] is not None):
                checks[key] = ma_values[short_period] > ma_values[long_period]

        bull_count = sum(1 for v in checks.values() if v)
        total = len(checks)

        score, state = self._get_score_by_count(bull_count, total)

        return {
            "score": score,
            "state": state,
            "checks": checks,
            "bull_count": bull_count,
            "total_checks": total
        }

    def is_bullish_alignment(self, ma_values: Dict[int, float]) -> bool:
        """
        判断是否为多头排列

        Args:
            ma_values: 均线值字典

        Returns:
            是否为多头排列
        """
        if not ma_values:
            return False

        for i in range(len(self.PERIODS) - 1):
            short_period = self.PERIODS[i]
            long_period = self.PERIODS[i + 1]

            if (short_period in ma_values and long_period in ma_values
                    and ma_values[short_period] is not None
                    and ma_values[long_period] is not None):
                if ma_values[short_period] <= ma_values[long_period]:
                    return False

        return True

    def is_bearish_alignment(self, ma_values: Dict[int, float]) -> bool:
        """
        判断是否为空头排列

        Args:
            ma_values: 均线值字典

        Returns:
            是否为空头排列
        """
        if not ma_values:
            return False

        for i in range(len(self.PERIODS) - 1):
            short_period = self.PERIODS[i]
            long_period = self.PERIODS[i + 1]

            if (short_period in ma_values and long_period in ma_values
                    and ma_values[short_period] is not None
                    and ma_values[long_period] is not None):
                if ma_values[short_period] >= ma_values[long_period]:
                    return False

        return True
