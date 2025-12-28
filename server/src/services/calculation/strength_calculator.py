"""
强度得分计算器

实现基于多周期均线的综合强度评分算法。
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import date

from .base_calculator import BaseCalculator, CalculationResult
from .trend_analyzer import TrendDirection, TrendAnalyzer
from .moving_average_calculator import MovingAverageCalculator


class StrengthCalculator(BaseCalculator):
    """
    强度得分计算器

    根据价格与多个周期均线的比率，计算综合强度得分。
    """

    # 默认强度得分范围
    SCORE_MIN = 0.0
    SCORE_MAX = 100.0

    # 默认价格比率范围（用于归一化）
    RATIO_MIN = -10.0  # -10%
    RATIO_MAX = 10.0   # +10%

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化强度计算器

        Args:
            config: 配置参数，可包含:
                - weights: 各周期权重 {'5d': 0.15, '10d': 0.20, ...}
                - score_min: 最小得分
                - score_max: 最大得分
                - ratio_min: 最小价格比率
                - ratio_max: 最大价格比率
        """
        super().__init__(config)
        self.weights = config.get("weights", {}) if config else {}
        self.score_min = config.get("score_min", self.SCORE_MIN) if config else self.SCORE_MIN
        self.score_max = config.get("score_max", self.SCORE_MAX) if config else self.SCORE_MAX
        self.ratio_min = config.get("ratio_min", self.RATIO_MIN) if config else self.RATIO_MIN
        self.ratio_max = config.get("ratio_max", self.RATIO_MAX) if config else self.RATIO_MAX

        # 初始化辅助计算器
        self.ma_calculator = MovingAverageCalculator()
        self.trend_analyzer = TrendAnalyzer()

    async def calculate(
        self,
        price_ratios: Dict[str, float],
        weights: Optional[Dict[str, float]] = None,
    ) -> CalculationResult:
        """
        计算综合强度得分

        Args:
            price_ratios: 各周期价格比率，如 {'5d': 2.5, '10d': 1.8, ...}
            weights: 各周期权重（可选，默认使用初始化时的权重）

        Returns:
            CalculationResult: 包含强度得分的结果
        """
        if not self.validate_input(price_ratios):
            return CalculationResult(
                success=False,
                error="价格比率数据无效"
            )

        try:
            effective_weights = weights or self.weights
            score = self.calculate_strength_score(price_ratios, effective_weights)
            return CalculationResult(success=True, data=score)
        except Exception as e:
            return CalculationResult(success=False, error=f"强度计算失败: {str(e)}")

    def calculate_strength_score(
        self,
        price_ratios: Dict[str, float],
        weights: Dict[str, float],
    ) -> float:
        """
        计算加权综合强度得分

        算法:
        1. 计算加权原始得分: Σ(Ratio[period] × Weight[period])
        2. 归一化到目标范围

        Args:
            price_ratios: 各周期价格比率，如 {'5d': 2.5, '10d': 1.8, ...}
            weights: 各周期权重，如 {'5d': 0.15, '10d': 0.20, ...}

        Returns:
            综合强度得分（0-100 范围）

        Examples:
            >>> calculator = StrengthCalculator()
            >>> ratios = {'5d': 5.0, '10d': 3.0, '20d': 1.0, '30d': -1.0, '60d': -2.0}
            >>> weights = {'5d': 0.15, '10d': 0.20, '20d': 0.25, '30d': 0.20, '60d': 0.20}
            >>> score = calculator.calculate_strength_score(ratios, weights)
            >>> # 得分在 0-100 之间
        """
        if not price_ratios or not weights:
            return 50.0  # 默认中间值

        # 计算加权原始得分
        raw_score = 0.0
        total_weight = 0.0

        for period, ratio in price_ratios.items():
            weight = weights.get(period, 0.0)
            if weight > 0:
                # 限制比率在合理范围内
                clamped_ratio = max(self.ratio_min, min(self.ratio_max, ratio))
                raw_score += clamped_ratio * weight
                total_weight += weight

        # 如果权重总和不为 1，进行归一化
        if total_weight > 0 and abs(total_weight - 1.0) > 0.01:
            raw_score = raw_score / total_weight

        # 归一化到目标范围
        # 假设合理范围是 [RATIO_MIN, RATIO_MAX]
        ratio_range = self.ratio_max - self.ratio_min
        if ratio_range > 0:
            normalized = (raw_score - self.ratio_min) / ratio_range
            normalized = normalized * (self.score_max - self.score_min) + self.score_min
        else:
            normalized = (self.score_max + self.score_min) / 2

        # 确保结果在范围内
        return float(max(self.score_min, min(self.score_max, normalized)))

    def calculate_entity_strength(
        self,
        prices: pd.Series,
        current_price: float,
        period_configs: List[Dict],
    ) -> Dict[str, any]:
        """
        计算单个实体（股票或板块）的完整强度数据

        渐近式计算：根据可用数据动态计算可用周期的均线

        Args:
            prices: 历史价格序列
            current_price: 当前价格
            period_configs: 周期配置列表，如:
                [{'period': '5d', 'days': 5, 'weight': 0.15}, ...]

        Returns:
            包含强度数据、趋势方向、均线值的字典
        """
        if not self.validate_input(prices, min_length=5):
            return {
                "strength_score": None,
                "trend_direction": TrendDirection.NEUTRAL,
                "error": "历史数据严重不足（至少需要 5 天）",
            }

        try:
            # 渐近式计算：根据可用数据筛选可计算的周期
            data_length = len(prices)
            available_configs = [
                pc for pc in period_configs
                if pc["days"] <= data_length
            ]

            if not available_configs:
                return {
                    "strength_score": None,
                    "trend_direction": TrendDirection.NEUTRAL,
                    "error": f"数据不足以计算任何周期（当前 {data_length} 天，最小需要 {min(pc['days'] for pc in period_configs)} 天）",
                }

            # 提取可用周期配置
            periods = [pc["days"] for pc in available_configs]
            weights = {pc["period"]: pc["weight"] for pc in period_configs}

            # 计算各周期均线
            ma_series_dict = self.ma_calculator.calculate_multiple_periods(prices, periods)

            # 获取最新均线值
            latest_ma_values = {}
            for period, ma_series in ma_series_dict.items():
                latest_ma = self.ma_calculator.get_latest_ma_value(ma_series)
                if latest_ma is not None:
                    latest_ma_values[period] = latest_ma

            # 过滤无效均线值
            valid_ma_values = {
                k: v for k, v in latest_ma_values.items()
                if v is not None and np.isfinite(v)
            }

            if not valid_ma_values:
                return {
                    "strength_score": None,
                    "trend_direction": TrendDirection.NEUTRAL,
                    "error": "无法计算有效的均线值",
                }

            # 计算价格比率
            price_ratios = {}
            for period, ma_value in latest_ma_values.items():
                if ma_value and ma_value > 0:
                    ratio = self.ma_calculator.calculate_price_ratio(current_price, ma_value)
                    price_ratios[f"{period}d"] = ratio

            # 计算强度得分
            strength_score = self.calculate_strength_score(price_ratios, weights)

            # 判定趋势方向
            trend_direction = self.trend_analyzer.determine_trend(
                current_price, latest_ma_values
            )

            return {
                "strength_score": strength_score,
                "trend_direction": int(trend_direction),
                "price_ratios": price_ratios,
                "ma_values": latest_ma_values,
                "current_price": current_price,
                "available_periods": list(latest_ma_values.keys()),
                "partial_calculation": len(available_configs) < len(period_configs),
            }

        except Exception as e:
            return {
                "strength_score": None,
                "trend_direction": TrendDirection.NEUTRAL,
                "error": f"计算失败: {str(e)}",
            }

    def calculate_sector_strength_from_stocks(
        self,
        stock_strengths: Dict[str, float],
        market_caps: Dict[str, float],
    ) -> float:
        """
        计算板块强度（成分股市值加权平均）

        Args:
            stock_strengths: 成分股强度得分 {stock_id: score}
            market_caps: 成分股市值 {stock_id: market_cap}

        Returns:
            板块强度得分
        """
        if not stock_strengths:
            return 0.0

        # 如果没有市值数据，使用简单平均
        if not market_caps:
            return sum(stock_strengths.values()) / len(stock_strengths)

        # 计算总市值
        valid_stocks = {
            stock_id: cap
            for stock_id, cap in market_caps.items()
            if stock_id in stock_strengths and cap and cap > 0
        }

        if not valid_stocks:
            return sum(stock_strengths.values()) / len(stock_strengths)

        total_cap = sum(valid_stocks.values())
        if total_cap == 0:
            # 如果没有市值数据，使用简单平均
            return sum(stock_strengths.values()) / len(stock_strengths)

        # 市值加权平均
        weighted_strength = sum(
            stock_strengths[stock_id] * valid_stocks[stock_id]
            for stock_id in valid_stocks
            if stock_id in stock_strengths
        )

        return float(weighted_strength / total_cap)

    def normalize_score(self, raw_score: float) -> float:
        """
        归一化原始得分到 0-100 范围

        Args:
            raw_score: 原始得分

        Returns:
            归一化后的得分
        """
        normalized = (raw_score - self.ratio_min) / (self.ratio_max - self.ratio_min)
        normalized = normalized * (self.score_max - self.score_min) + self.score_min
        return float(max(self.score_min, min(self.score_max, normalized)))

    def get_strength_level(self, score: float) -> str:
        """
        获取强度等级描述

        Args:
            score: 强度得分

        Returns:
            强度等级字符串
        """
        if score is None:
            return "未知"
        if score >= 80:
            return "非常强势"
        elif score >= 65:
            return "强势"
        elif score >= 50:
            return "偏强"
        elif score >= 35:
            return "中性"
        elif score >= 20:
            return "偏弱"
        elif score >= 10:
            return "弱势"
        else:
            return "非常弱势"
