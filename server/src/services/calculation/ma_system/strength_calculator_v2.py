"""
均线系统综合强度计算器

整合价格位置得分和均线排列得分，计算综合强度。
"""

import logging
from typing import Dict, Optional, List

from src.config.ma_system import (
    TERM_GROUPS,
    get_strength_grade,
    get_ma_alignment_state_name,
    MIN_DATA_DAYS
)
from .price_position_scorer import PricePositionScorer
from .ma_alignment_scorer import MAAlignmentScorer

logger = logging.getLogger(__name__)


class StrengthCalculatorV2:
    """
    均线系统综合强度计算器

    使用两维度（价格位置 + 均线排列）计算综合强度得分。
    """

    def __init__(self):
        """初始化综合强度计算器"""
        self.price_scorer = PricePositionScorer()
        self.alignment_scorer = MAAlignmentScorer()

    def calculate_composite_strength(
        self,
        price: float,
        ma_values: Dict[int, float]
    ) -> Dict:
        """
        计算综合强度

        综合公式：composite = (price_position_score + ma_alignment_score) / 2

        Args:
            price: 当前价格
            ma_values: 均线值字典 {周期: 均线值}

        Returns:
            包含所有强度计算结果的字典
        """
        if not ma_values or price is None:
            return self._get_empty_result("价格或均线数据无效")

        try:
            # 1. 价格位置得分
            price_position_score = self.price_scorer.calculate_weighted_score(
                price, ma_values
            )

            # 2. 均线排列得分
            ma_alignment_score, alignment_state = self.alignment_scorer.calculate_score(
                price, ma_values
            )

            # 3. 综合得分
            composite = (price_position_score + ma_alignment_score) / 2

            # 4. 短中长期强度
            short_term_score = self._calculate_term_score(
                price, ma_values, TERM_GROUPS['short']
            )
            medium_term_score = self._calculate_term_score(
                price, ma_values, TERM_GROUPS['medium']
            )
            long_term_score = self._calculate_term_score(
                price, ma_values, TERM_GROUPS['long']
            )

            # 5. 强度等级
            strength_grade = get_strength_grade(composite)

            # 6. 价格相对均线位置（8个位置）
            price_positions = self._calculate_price_positions(price, ma_values)

            # 7. 价格是否高于各均线（0/1 标记）
            price_above_flags = self._get_price_above_flags(price, ma_values)

            return {
                'composite_score': round(composite, 2),
                'price_position_score': round(price_position_score, 2),
                'ma_alignment_score': round(ma_alignment_score, 2),
                'ma_alignment_state': alignment_state,
                'short_term_score': round(short_term_score, 2),
                'medium_term_score': round(medium_term_score, 2),
                'long_term_score': round(long_term_score, 2),
                'strength_grade': strength_grade,
                'price_positions': price_positions,
                'price_above_flags': price_above_flags,
                'ma_values': ma_values,
                'current_price': price,
            }

        except Exception as e:
            logger.error(f"综合强度计算失败: {e}")
            return self._get_empty_result(str(e))

    def _calculate_term_score(
        self,
        price: float,
        ma_values: Dict[int, float],
        periods: List[int]
    ) -> float:
        """
        计算特定周期的强度得分

        Args:
            price: 当前价格
            ma_values: 均线值字典
            periods: 周期列表

        Returns:
            该周期的强度得分
        """
        if not periods:
            return 0.0

        # 筛选可用均线
        available_mas = {
            p: ma_values[p] for p in periods
            if p in ma_values and ma_values[p] is not None
        }

        if not available_mas:
            return 0.0

        # 计算价格位置得分
        return self.price_scorer.calculate_weighted_score(price, available_mas)

    def _calculate_price_positions(
        self,
        price: float,
        ma_values: Dict[int, float]
    ) -> Dict[str, float]:
        """
        计算价格相对各条均线的位置百分比

        Args:
            price: 当前价格
            ma_values: 均线值字典

        Returns:
            价格位置字典 {above_maX: 百分比}
        """
        positions = {}
        for period, ma_value in ma_values.items():
            if ma_value and ma_value > 0:
                positions[f"above_ma{period}"] = round(
                    (price - ma_value) / ma_value * 100, 2
                )
        return positions

    def _get_price_above_flags(
        self,
        price: float,
        ma_values: Dict[int, float]
    ) -> Dict[str, int]:
        """
        获取价格是否高于各均线的标记

        Args:
            price: 当前价格
            ma_values: 均线值字典

        Returns:
            0/1 标记字典
        """
        flags = {}
        for period, ma_value in ma_values.items():
            if ma_value is not None:
                flags[f"above_ma{period}"] = 1 if price > ma_value else 0
        return flags

    def _get_empty_result(self, reason: str) -> Dict:
        """
        返回空结果

        Args:
            reason: 原因

        Returns:
            空结果字典
        """
        return {
            'composite_score': 0.0,
            'price_position_score': 0.0,
            'ma_alignment_score': 0.0,
            'ma_alignment_state': 'perfect_bear',
            'short_term_score': 0.0,
            'medium_term_score': 0.0,
            'long_term_score': 0.0,
            'strength_grade': 'D',
            'price_positions': {},
            'price_above_flags': {},
            'ma_values': {},
            'current_price': 0.0,
            'error': reason
        }

    def calculate_with_insufficient_data(
        self,
        price: float,
        ma_values: Dict[int, float],
        available_days: int
    ) -> Dict:
        """
        渐近式计算：处理数据不足情况

        Args:
            price: 当前价格
            ma_values: 可用的均线值字典
            available_days: 可用天数

        Returns:
            计算结果字典
        """
        if available_days < MIN_DATA_DAYS:
            return self._get_empty_result(f"数据不足（{available_days}天），至少需要{MIN_DATA_DAYS}天")

        # 使用可用数据进行计算
        result = self.calculate_composite_strength(price, ma_values)

        # 添加警告信息
        result['warning'] = f"仅使用{available_days}天数据进行计算，部分均线不可用"
        result['available_days'] = available_days

        return result
