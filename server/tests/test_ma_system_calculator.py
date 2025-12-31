"""
均线系统强度计算器单元测试
"""

import pytest
from datetime import date

from src.config.ma_system import (
    MA_WEIGHTS,
    get_strength_grade,
    get_available_periods
)
from src.services.calculation.ma_system.price_position_scorer import PricePositionScorer
from src.services.calculation.ma_system.ma_alignment_scorer import MAAlignmentScorer
from src.services.calculation.ma_system.strength_calculator_v2 import StrengthCalculatorV2


class TestPricePositionScorer:
    """价格位置得分计算器测试"""

    def setup_method(self):
        """测试前置设置"""
        self.scorer = PricePositionScorer()

    def test_calculate_score_extreme_high(self):
        """测试极端高比率 (+10%)"""
        score = self.scorer.calculate_score(10.0)
        assert score == 100.0

    def test_calculate_score_high(self):
        """测试高比率 (+4%)"""
        score = self.scorer.calculate_score(4.0)
        assert 90.0 <= score <= 100.0

    def test_calculate_score_medium_high(self):
        """测试中高比率 (+2%)"""
        score = self.scorer.calculate_score(2.0)
        assert 75.0 <= score <= 90.0

    def test_calculate_score_neutral(self):
        """测试中性比率 (0%)"""
        score = self.scorer.calculate_score(0.0)
        assert score == 50.0

    def test_calculate_score_medium_low(self):
        """测试中低比率 (-2%)"""
        score = self.scorer.calculate_score(-2.0)
        assert 25.0 <= score <= 40.0

    def test_calculate_score_extreme_low(self):
        """测试极端低比率 (-10%)"""
        score = self.scorer.calculate_score(-10.0)
        assert 0.0 <= score <= 10.0

    def test_calculate_weighted_score_basic(self):
        """测试加权得分计算"""
        price = 100.0
        ma_values = {
            5: 95.0,   # 价格 +5.26%
            10: 98.0,  # 价格 +2.04%
            20: 99.0,  # 价格 +1.01%
        }

        score = self.scorer.calculate_weighted_score(price, ma_values)
        assert 0.0 <= score <= 100.0

    def test_calculate_weighted_score_empty_ma(self):
        """测试空均线数据"""
        score = self.scorer.calculate_weighted_score(100.0, {})
        assert score == 50.0

    def test_calculate_weighted_score_none_price(self):
        """测试 None 价格"""
        score = self.scorer.calculate_weighted_score(None, {5: 100.0})
        assert score == 50.0

    def test_calculate_price_ratios(self):
        """测试价格比率计算"""
        price = 105.0
        ma_values = {5: 100.0, 10: 95.0}

        ratios = self.scorer.calculate_price_ratios(price, ma_values)
        assert ratios[5] == 5.0
        assert abs(ratios[10] - 10.53) < 0.1

    def test_calculate_individual_scores(self):
        """测试单独得分计算"""
        price = 105.0
        ma_values = {5: 100.0, 10: 95.0}

        scores = self.scorer.calculate_individual_scores(price, ma_values)
        assert 5 in scores
        assert 10 in scores
        assert all(0 <= s <= 100 for s in scores.values())


class TestMAAlignmentScorer:
    """均线排列评分器测试"""

    def setup_method(self):
        """测试前置设置"""
        self.scorer = MAAlignmentScorer()

    def test_perfect_bull_alignment(self):
        """测试完美多头排列"""
        price = 110.0
        ma_values = {
            5: 105.0,
            10: 100.0,
            20: 95.0,
            30: 90.0,
            60: 85.0,
            90: 80.0,
            120: 75.0,
            240: 70.0,
        }

        score, state = self.scorer.calculate_score(price, ma_values)
        assert score == 100.0
        assert state == "perfect_bull"

    def test_perfect_bear_alignment(self):
        """测试完美空头排列"""
        price = 70.0
        ma_values = {
            5: 75.0,
            10: 80.0,
            20: 85.0,
            30: 90.0,
            60: 95.0,
            90: 100.0,
            120: 105.0,
            240: 110.0,
        }

        score, state = self.scorer.calculate_score(price, ma_values)
        assert state == "perfect_bear"

    def test_strong_bull_alignment(self):
        """测试强势多头排列"""
        price = 105.0
        ma_values = {
            5: 100.0,
            10: 99.0,
            20: 98.0,
            30: 97.0,
            60: 96.0,
            90: 95.0,
            120: 94.0,
            240: 100.0,  # 这里破坏了完美排列
        }

        score, state = self.scorer.calculate_score(price, ma_values)
        assert 80.0 <= score < 100.0
        assert state == "strong_bull"

    def test_neutral_alignment(self):
        """测试中性排列"""
        price = 100.0
        ma_values = {
            5: 100.0,
            10: 100.0,
            20: 100.0,
            30: 100.0,
            60: 100.0,
            90: 100.0,
            120: 100.0,
            240: 100.0,
        }

        score, state = self.scorer.calculate_score(price, ma_values)
        assert 0.0 <= score <= 100.0

    def test_partial_data_alignment(self):
        """测试部分数据排列"""
        price = 105.0
        ma_values = {
            5: 100.0,
            10: 98.0,
            20: 96.0,
        }

        score, state = self.scorer.calculate_score(price, ma_values)
        assert 0.0 <= score <= 100.0

    def test_empty_data_alignment(self):
        """测试空数据"""
        score, state = self.scorer.calculate_score(100.0, {})
        assert score == 0.0
        assert state == "perfect_bear"

    def test_get_alignment_details(self):
        """测试获取详细排列信息"""
        price = 110.0
        ma_values = {
            5: 105.0,
            10: 100.0,
            20: 95.0,
        }

        details = self.scorer.get_alignment_details(price, ma_values)
        assert "score" in details
        assert "state" in details
        assert "checks" in details
        assert "bull_count" in details
        assert "total_checks" in details


class TestStrengthCalculatorV2:
    """综合强度计算器测试"""

    def setup_method(self):
        """测试前置设置"""
        self.calculator = StrengthCalculatorV2()

    def test_calculate_composite_strength_bullish(self):
        """测试多头行情计算"""
        price = 110.0
        ma_values = {
            5: 105.0,
            10: 100.0,
            20: 95.0,
            30: 90.0,
            60: 85.0,
            90: 80.0,
            120: 75.0,
            240: 70.0,
        }

        result = self.calculator.calculate_composite_strength(price, ma_values)
        assert result["composite_score"] >= 80.0
        assert result["strength_grade"] in ["A+", "S", "S+"]
        assert "price_position_score" in result
        assert "ma_alignment_score" in result
        assert "short_term_score" in result
        assert "medium_term_score" in result
        assert "long_term_score" in result

    def test_calculate_composite_strength_bearish(self):
        """测试空头行情计算"""
        price = 70.0
        ma_values = {
            5: 75.0,
            10: 80.0,
            20: 85.0,
            30: 90.0,
            60: 95.0,
            90: 100.0,
            120: 105.0,
            240: 110.0,
        }

        result = self.calculator.calculate_composite_strength(price, ma_values)
        assert result["composite_score"] <= 50.0
        assert result["strength_grade"] in ["D", "D+", "C"]

    def test_calculate_composite_strength_neutral(self):
        """测试中性行情计算"""
        price = 100.0
        ma_values = {
            5: 100.0,
            10: 100.0,
            20: 100.0,
            30: 100.0,
            60: 100.0,
            90: 100.0,
            120: 100.0,
            240: 100.0,
        }

        result = self.calculator.calculate_composite_strength(price, ma_values)
        assert 0.0 <= result["composite_score"] <= 100.0

    def test_calculate_composite_strength_empty_data(self):
        """测试空数据"""
        result = self.calculator.calculate_composite_strength(100.0, {})
        assert result["composite_score"] == 0.0
        assert "error" in result

    def test_short_medium_long_term_scores(self):
        """测试短中长期得分"""
        price = 110.0
        ma_values = {
            5: 105.0,
            10: 100.0,
            20: 95.0,
            30: 90.0,
            60: 85.0,
            90: 80.0,
            120: 75.0,
            240: 70.0,
        }

        result = self.calculator.calculate_composite_strength(price, ma_values)
        assert 0.0 <= result["short_term_score"] <= 100.0
        assert 0.0 <= result["medium_term_score"] <= 100.0
        assert 0.0 <= result["long_term_score"] <= 100.0

    def test_price_positions_calculation(self):
        """测试价格位置计算"""
        price = 105.0
        ma_values = {
            5: 100.0,
            10: 95.0,
        }

        result = self.calculator.calculate_composite_strength(price, ma_values)
        assert "price_positions" in result
        assert "above_ma5" in result["price_positions"]
        assert "above_ma10" in result["price_positions"]

    def test_price_above_flags(self):
        """测试价格是否高于均线标记"""
        price = 105.0
        ma_values = {
            5: 100.0,
            10: 110.0,
        }

        result = self.calculator.calculate_composite_strength(price, ma_values)
        assert "price_above_flags" in result
        assert result["price_above_flags"]["above_ma5"] == 1
        assert result["price_above_flags"]["above_ma10"] == 0

    def test_calculate_with_insufficient_data(self):
        """测试数据不足计算"""
        price = 105.0
        ma_values = {
            5: 100.0,
            10: 98.0,
        }

        result = self.calculator.calculate_with_insufficient_data(price, ma_values, 20)
        assert "composite_score" in result
        assert "warning" in result
        assert "available_days" in result

    def test_calculate_with_insufficient_data_reject(self):
        """测试数据严重不足"""
        result = self.calculator.calculate_with_insufficient_data(100.0, {}, 3)
        assert result["composite_score"] == 0.0
        assert "error" in result


class TestConfigModule:
    """配置模块测试"""

    def test_get_strength_grade(self):
        """测试强度等级获取"""
        assert get_strength_grade(95) == "S+"
        assert get_strength_grade(87) == "S"
        assert get_strength_grade(80) == "A+"
        assert get_strength_grade(70) == "A"
        assert get_strength_grade(60) == "B+"
        assert get_strength_grade(50) == "B"
        assert get_strength_grade(40) == "C+"
        assert get_strength_grade(30) == "C"
        assert get_strength_grade(20) == "D+"
        assert get_strength_grade(10) == "D"
        assert get_strength_grade(0) == "D"

    def test_get_strength_grade_none(self):
        """测试 None 得分"""
        assert get_strength_grade(None) == "D"

    def test_get_available_periods(self):
        """测试可用周期获取"""
        assert get_available_periods(240) == [5, 10, 20, 30, 60, 90, 120, 240]
        assert get_available_periods(60) == [5, 10, 20, 30, 60]
        assert get_available_periods(20) == [5, 10, 20]
        assert get_available_periods(5) == [5]
        assert get_available_periods(3) == []

    def test_ma_weights_sum(self):
        """测试均线权重总和"""
        total = sum(MA_WEIGHTS.values())
        assert abs(total - 1.0) < 0.01  # 允许小数误差


class TestBoundaryConditions:
    """边界条件测试"""

    def setup_method(self):
        """测试前置设置"""
        self.scorer = PricePositionScorer()
        self.calculator = StrengthCalculatorV2()

    def test_price_exactly_at_ma(self):
        """测试价格正好等于均线"""
        score = self.scorer.calculate_score(0.0)
        assert score == 50.0

    def test_extreme_ratio_values(self):
        """测试极端比率值"""
        assert self.scorer.calculate_score(1000.0) == 100.0
        assert self.scorer.calculate_score(-1000.0) == 0.0

    def test_single_ma_available(self):
        """测试只有一条均线可用"""
        result = self.calculator.calculate_composite_strength(105.0, {5: 100.0})
        assert 0.0 <= result["composite_score"] <= 100.0

    def test_all_mas_equal(self):
        """测试所有均线相等"""
        price = 100.0
        ma_values = {p: 100.0 for p in [5, 10, 20, 30, 60, 90, 120, 240]}
        result = self.calculator.calculate_composite_strength(price, ma_values)
        assert 0.0 <= result["composite_score"] <= 100.0
