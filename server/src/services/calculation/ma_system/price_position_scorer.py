"""
价格位置得分计算器

计算当前价格相对于各条均线的位置得分。
"""

import logging
from typing import Dict, Optional

from src.config.ma_system import MA_WEIGHTS

logger = logging.getLogger(__name__)


class PricePositionScorer:
    """
    价格位置得分计算器

    根据价格相对于均线的位置比率计算得分。
    """

    def __init__(self, weights: Optional[Dict[int, float]] = None):
        """
        初始化价格位置得分计算器

        Args:
            weights: 均线权重配置，默认使用 MA_WEIGHTS
        """
        self.weights = weights or MA_WEIGHTS

    def calculate_score(self, ratio: float) -> float:
        """
        根据价格位置比率计算得分

        评分标准：
        - ratio > +5%:  100分
        - ratio > +3%:  90-100分
        - ratio > +1%:  75-90分
        - ratio > +0.5%: 60-75分
        - ratio ∈ [-0.5%, +0.5%]: 50分
        - ratio < -0.5%: 40分
        - ratio < -1%:  25分
        - ratio < -3%:  10分
        - ratio < -5%:  0分

        Args:
            ratio: 价格与均线的比率百分比 (如 5.0 表示 +5%)

        Returns:
            得分 (0-100)
        """
        try:
            if ratio > 5:
                return 100.0
            elif ratio > 3:
                return 90.0 + (ratio - 3) * 5  # 90-100
            elif ratio > 1:
                return 75.0 + (ratio - 1) * 7.5  # 75-90
            elif ratio > 0.5:
                return 60.0 + (ratio - 0.5) * 30  # 60-75
            elif ratio > -0.5:
                return 50.0
            elif ratio > -1:
                return 40.0 + (ratio + 1) * 20  # 40-50
            elif ratio > -3:
                return 25.0 + (ratio + 3) * 7.5  # 25-40
            elif ratio > -5:
                return 10.0 + (ratio + 5) * 7.5  # 10-25
            else:
                return max(0.0, (ratio + 5) * 2)  # 0-10
        except Exception as e:
            logger.error(f"价格位置得分计算失败: {e}")
            return 50.0

    def calculate_weighted_score(
        self,
        price: float,
        ma_values: Dict[int, float]
    ) -> float:
        """
        计算加权平均价格位置得分

        根据价格相对于各条均线的位置，计算加权平均得分。

        Args:
            price: 当前价格
            ma_values: 均线值字典 {周期: 均线值}，如 {5: 100.0, 10: 98.5, ...}

        Returns:
            加权平均得分 (0-100)
        """
        if not ma_values or price is None:
            return 50.0

        try:
            total_weight = 0.0
            weighted_score = 0.0

            for period, ma_value in ma_values.items():
                if ma_value and ma_value > 0:
                    # 计算价格与均线的比率百分比
                    ratio = (price - ma_value) / ma_value * 100

                    # 获取该周期的权重
                    weight = self.weights.get(period, 0.0)

                    # 计算该周期的得分
                    score = self.calculate_score(ratio)

                    # 累加加权得分
                    weighted_score += score * weight
                    total_weight += weight

            # 归一化到 0-100
            if total_weight > 0:
                return weighted_score / total_weight
            else:
                return 50.0

        except Exception as e:
            logger.error(f"加权价格位置得分计算失败: {e}")
            return 50.0

    def calculate_price_ratios(
        self,
        price: float,
        ma_values: Dict[int, float]
    ) -> Dict[int, float]:
        """
        计算价格相对于各条均线的比率

        Args:
            price: 当前价格
            ma_values: 均线值字典

        Returns:
            价格比率字典 {周期: 比率百分比}
        """
        ratios = {}
        for period, ma_value in ma_values.items():
            if ma_value and ma_value > 0:
                ratios[period] = (price - ma_value) / ma_value * 100
        return ratios

    def calculate_individual_scores(
        self,
        price: float,
        ma_values: Dict[int, float]
    ) -> Dict[int, float]:
        """
        计算价格相对于各条均线的单独得分

        Args:
            price: 当前价格
            ma_values: 均线值字典

        Returns:
            各周期得分字典 {周期: 得分}
        """
        ratios = self.calculate_price_ratios(price, ma_values)
        scores = {}
        for period, ratio in ratios.items():
            scores[period] = self.calculate_score(ratio)
        return scores
