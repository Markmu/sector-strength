"""
计算引擎单元测试

测试均线计算、趋势分析和强度评分功能。
"""

import pytest
from datetime import date, datetime, timedelta
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.calculation.base_calculator import BaseCalculator, CalculationResult
from services.calculation.moving_average_calculator import MovingAverageCalculator
from services.calculation.trend_analyzer import TrendAnalyzer, TrendDirection
from services.calculation.strength_calculator import StrengthCalculator
from services.calculation.batch_processor import BatchProcessor, BatchCalculationResult
from config.calculation import (
    DEFAULT_PERIOD_CONFIGS,
    PERIOD_WEIGHTS,
    get_strength_level,
    get_trend_name,
    is_valid_score,
)


# 具体实现用于测试 BaseCalculator 的非抽象方法
class ConcreteCalculator(BaseCalculator):
    """用于测试的具体计算器实现"""
    async def calculate(self, *args, **kwargs):
        return CalculationResult(success=True, data="test_result")


class TestBaseCalculator:
    """基础计算器测试"""

    def test_validate_input_valid_data(self):
        """测试有效数据验证"""
        calc = ConcreteCalculator()
        assert calc.validate_input([1, 2, 3])
        assert calc.validate_input("test")
        assert calc.validate_input(100)

    def test_validate_input_none(self):
        """测试 None 数据验证"""
        calc = ConcreteCalculator()
        assert not calc.validate_input(None)

    def test_validate_input_min_length(self):
        """测试最小长度验证"""
        calc = ConcreteCalculator()
        assert calc.validate_input([1, 2, 3], min_length=3)
        assert not calc.validate_input([1, 2], min_length=3)

    def test_calculation_result_success(self):
        """测试成功结果"""
        result = CalculationResult(success=True, data={"score": 75})
        assert result.success
        assert result.data == {"score": 75}
        assert result.error is None

    def test_calculation_result_failure(self):
        """测试失败结果"""
        result = CalculationResult(success=False, error="计算失败")
        assert not result.success
        assert result.error == "计算失败"
        assert result.data is None


class TestMovingAverageCalculator:
    """均线计算器测试"""

    @pytest.fixture
    def calculator(self):
        return MovingAverageCalculator()

    @pytest.fixture
    def sample_prices(self):
        """创建示例价格序列"""
        dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
        values = [100 + i * 0.1 for i in range(100)]  # 递增序列
        return pd.Series(values, index=dates)

    def test_calculate_sma(self, calculator, sample_prices):
        """测试简单移动平均线计算"""
        ma = calculator.calculate_sma(sample_prices, 5)

        # 验证返回类型
        assert isinstance(ma, pd.Series)
        assert len(ma) == len(sample_prices)

        # 验证前4个值为 NaN
        assert pd.isna(ma.iloc[0])
        assert pd.isna(ma.iloc[3])

        # 验证第5个值
        expected_ma5 = (100 + 100.1 + 100.2 + 100.3 + 100.4) / 5
        assert abs(ma.iloc[4] - expected_ma5) < 0.01

    def test_calculate_sma_period_10(self, calculator, sample_prices):
        """测试 10 日均线计算"""
        ma = calculator.calculate_sma(sample_prices, 10)
        assert pd.isna(ma.iloc[8])  # 前9个为 NaN
        assert not pd.isna(ma.iloc[9])  # 第10个有值

    def test_calculate_ema(self, calculator, sample_prices):
        """测试指数移动平均线计算"""
        ema = calculator.calculate_ema(sample_prices, 5)

        # EMA 第一个值应该等于第一个价格
        assert ema.iloc[0] == sample_prices.iloc[0]

        # EMA 应该有值（不同于 SMA）
        assert not pd.isna(ema.iloc[4])

    def test_calculate_price_ratio_above_ma(self, calculator):
        """测试价格在均线之上的比率"""
        ratio = calculator.calculate_price_ratio(105, 100)
        assert ratio == 5.0  # (105 - 100) / 100 * 100

    def test_calculate_price_ratio_below_ma(self, calculator):
        """测试价格在均线之下的比率"""
        ratio = calculator.calculate_price_ratio(95, 100)
        assert ratio == -5.0  # (95 - 100) / 100 * 100

    def test_calculate_price_ratio_zero_ma(self, calculator):
        """测试均线为 0 的情况"""
        ratio = calculator.calculate_price_ratio(100, 0)
        assert ratio == 0.0

    def test_calculate_multiple_periods(self, calculator, sample_prices):
        """测试多周期均线计算"""
        periods = [5, 10, 20]
        ma_dict = calculator.calculate_multiple_periods(sample_prices, periods)

        assert len(ma_dict) == 3
        assert 5 in ma_dict
        assert 10 in ma_dict
        assert 20 in ma_dict

    def test_get_latest_ma_value(self, calculator):
        """测试获取最新均线值"""
        ma_series = pd.Series([1, 2, 3, 4, 5])
        latest = calculator.get_latest_ma_value(ma_series)
        assert latest == 5.0

    def test_get_latest_ma_value_with_nan(self, calculator):
        """测试带 NaN 的均线序列"""
        ma_series = pd.Series([np.nan, np.nan, 3, 4, 5])
        latest = calculator.get_latest_ma_value(ma_series)
        assert latest == 5.0

    def test_get_latest_ma_value_all_nan(self, calculator):
        """测试全 NaN 序列"""
        ma_series = pd.Series([np.nan, np.nan])
        latest = calculator.get_latest_ma_value(ma_series)
        assert latest is None

    def test_calculate_price_ratios_for_periods(self, calculator):
        """测试多周期价格比率计算"""
        current_price = 105
        ma_values = {5: 100, 10: 98, 20: 95}

        ratios = calculator.calculate_price_ratios_for_periods(
            current_price, ma_values
        )

        assert ratios[5] == 5.0
        assert abs(ratios[10] - 7.14) < 0.1
        assert abs(ratios[20] - 10.53) < 0.1


class TestTrendAnalyzer:
    """趋势分析器测试"""

    @pytest.fixture
    def analyzer(self):
        return TrendAnalyzer()

    def test_determine_trend_bullish(self, analyzer):
        """测试上升趋势判定（多头排列）"""
        current_price = 110
        ma_values = {5: 105, 10: 102, 20: 100, 30: 98, 60: 95}

        trend = analyzer.determine_trend(current_price, ma_values)
        assert trend == TrendDirection.UP

    def test_determine_trend_bearish(self, analyzer):
        """测试下降趋势判定（空头排列）"""
        current_price = 90
        ma_values = {5: 95, 10: 98, 20: 100, 30: 102, 60: 105}

        trend = analyzer.determine_trend(current_price, ma_values)
        assert trend == TrendDirection.DOWN

    def test_determine_trend_neutral(self, analyzer):
        """测试横盘判定"""
        current_price = 100
        ma_values = {5: 102, 10: 98, 20: 100, 30: 101, 60: 99}

        trend = analyzer.determine_trend(current_price, ma_values)
        assert trend == TrendDirection.NEUTRAL

    def test_determine_trend_simple_bullish(self, analyzer):
        """测试简化版上升趋势判定"""
        trend = analyzer.determine_trend_simple(110, 105, 100, 95)
        assert trend == TrendDirection.UP

    def test_determine_trend_simple_bearish(self, analyzer):
        """测试简化版下降趋势判定"""
        trend = analyzer.determine_trend_simple(90, 95, 100, 105)
        assert trend == TrendDirection.DOWN

    def test_determine_trend_simple_neutral(self, analyzer):
        """测试简化版横盘判定"""
        trend = analyzer.determine_trend_simple(100, 102, 98, 95)
        assert trend == TrendDirection.NEUTRAL

    def test_calculate_trend_strength_up(self, analyzer):
        """测试上升趋势强度"""
        prices = pd.Series([100, 101, 102, 103, 104, 105])
        strength = analyzer.calculate_trend_strength(prices, window=5)
        assert strength > 0  # 上涨趋势

    def test_calculate_trend_strength_down(self, analyzer):
        """测试下降趋势强度"""
        prices = pd.Series([105, 104, 103, 102, 101, 100])
        strength = analyzer.calculate_trend_strength(prices, window=5)
        assert strength < 0  # 下跌趋势

    def test_analyze_price_position_above_all(self, analyzer):
        """测试价格在所有均线之上"""
        current_price = 110
        ma_values = {5: 105, 10: 100, 20: 95}

        result = analyzer.analyze_price_position(current_price, ma_values)
        assert result["position"] == "far_above"
        assert result["above_count"] == 3

    def test_analyze_price_position_below_all(self, analyzer):
        """测试价格在所有均线之下"""
        current_price = 90
        ma_values = {5: 95, 10: 100, 20: 105}

        result = analyzer.analyze_price_position(current_price, ma_values)
        assert result["position"] == "far_below"
        assert result["below_count"] == 3

    def test_get_trend_description(self, analyzer):
        """测试趋势描述"""
        assert analyzer.get_trend_description(TrendDirection.UP) == "上升"
        assert analyzer.get_trend_description(TrendDirection.NEUTRAL) == "横盘"
        assert analyzer.get_trend_description(TrendDirection.DOWN) == "下降"


class TestStrengthCalculator:
    """强度计算器测试"""

    @pytest.fixture
    def calculator(self):
        return StrengthCalculator(config={"weights": PERIOD_WEIGHTS})

    @pytest.fixture
    def sample_prices(self):
        """创建示例价格序列"""
        dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
        values = [100 + i * 0.1 for i in range(100)]
        return pd.Series(values, index=dates)

    def test_calculate_strength_score_high(self, calculator):
        """测试高强度得分计算"""
        # 所有比率都是正值（强势）
        price_ratios = {
            "5d": 5.0,
            "10d": 4.0,
            "20d": 3.0,
            "30d": 2.0,
            "60d": 1.0,
        }
        score = calculator.calculate_strength_score(price_ratios, PERIOD_WEIGHTS)
        assert score > 60  # 应该是比较高的分数

    def test_calculate_strength_score_low(self, calculator):
        """测试低强度得分计算"""
        # 所有比率都是负值（弱势）
        price_ratios = {
            "5d": -5.0,
            "10d": -4.0,
            "20d": -3.0,
            "30d": -2.0,
            "60d": -1.0,
        }
        score = calculator.calculate_strength_score(price_ratios, PERIOD_WEIGHTS)
        assert score < 40  # 应该是比较低的分数

    def test_calculate_strength_score_neutral(self, calculator):
        """测试中性得分计算"""
        # 比率有正有负（中性）
        price_ratios = {
            "5d": 1.0,
            "10d": 0.5,
            "20d": -0.5,
            "30d": -1.0,
            "60d": -2.0,
        }
        score = calculator.calculate_strength_score(price_ratios, PERIOD_WEIGHTS)
        assert 40 <= score <= 60  # 中等分数

    def test_calculate_entity_strength(self, calculator, sample_prices):
        """测试完整实体强度计算"""
        current_price = 109.9  # 序列最后一个价格
        result = calculator.calculate_entity_strength(
            prices=sample_prices,
            current_price=current_price,
            period_configs=DEFAULT_PERIOD_CONFIGS,
        )

        assert "strength_score" in result
        assert "trend_direction" in result
        assert result["strength_score"] is not None
        assert 0 <= result["strength_score"] <= 100

    def test_calculate_entity_strength_insufficient_data(self, calculator):
        """测试数据不足的情况"""
        short_prices = pd.Series([100, 101, 102])
        result = calculator.calculate_entity_strength(
            prices=short_prices,
            current_price=102,
            period_configs=DEFAULT_PERIOD_CONFIGS,
        )

        assert result["strength_score"] is None
        assert "error" in result

    def test_calculate_sector_strength_from_stocks(self, calculator):
        """测试板块强度计算"""
        stock_strengths = {"stock1": 80, "stock2": 60, "stock3": 40}
        market_caps = {"stock1": 1000, "stock2": 500, "stock3": 200}

        # 加权平均: (80*1000 + 60*500 + 40*200) / (1000+500+200)
        # = (80000 + 30000 + 8000) / 1700 = 118000 / 1700 ≈ 69.41
        sector_strength = calculator.calculate_sector_strength_from_stocks(
            stock_strengths, market_caps
        )

        assert abs(sector_strength - 69.41) < 0.5

    def test_calculate_sector_strength_no_market_caps(self, calculator):
        """测试无市值数据时的板块强度（简单平均）"""
        stock_strengths = {"stock1": 80, "stock2": 60, "stock3": 40}

        sector_strength = calculator.calculate_sector_strength_from_stocks(
            stock_strengths, {}
        )

        # 简单平均: (80 + 60 + 40) / 3 = 60
        assert abs(sector_strength - 60) < 0.1

    def test_get_strength_level(self, calculator):
        """测试强度等级获取"""
        assert calculator.get_strength_level(90) == "非常强势"
        assert calculator.get_strength_level(70) == "强势"
        assert calculator.get_strength_level(55) == "偏强"
        assert calculator.get_strength_level(40) == "中性"
        assert calculator.get_strength_level(25) == "偏弱"
        assert calculator.get_strength_level(15) == "弱势"
        assert calculator.get_strength_level(5) == "非常弱势"
        assert calculator.get_strength_level(None) == "未知"


class TestBatchProcessor:
    """批量处理器测试"""

    @pytest.fixture
    def processor(self):
        return BatchProcessor(config={
            "weights": PERIOD_WEIGHTS,
            "batch_size": 10,
            "max_concurrent": 2,
        })

    @pytest.fixture
    def sample_entities_data(self):
        """创建示例实体数据"""
        entities = {}
        for i in range(20):
            dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
            values = [100 + j * 0.1 + i for j in range(100)]
            entities[f"stock_{i}"] = {
                "prices": pd.Series(values, index=dates),
                "current_price": 100 + 99 * 0.1 + i,
            }
        return entities

    def test_prepare_prices_series(self, processor):
        """测试价格序列准备"""
        price_data = [
            {"date": "2024-01-01", "close": 100.0},
            {"date": "2024-01-02", "close": 101.0},
            {"date": "2024-01-03", "close": 102.0},
        ]

        prices = processor.prepare_prices_series(price_data)

        assert len(prices) == 3
        assert prices.iloc[0] == 100.0
        assert prices.iloc[-1] == 102.0

    def test_validate_data_sufficiency_sufficient(self, processor):
        """测试数据充足性验证（充足）"""
        prices = pd.Series([100] * 100)
        result = processor.validate_data_sufficiency(prices, [5, 10, 20, 30, 60])

        assert result["is_sufficient"]
        assert result["data_length"] == 100
        assert result["missing_days"] == 0

    def test_validate_data_sufficiency_insufficient(self, processor):
        """测试数据充足性验证（不足）"""
        prices = pd.Series([100] * 30)
        result = processor.validate_data_sufficiency(prices, [5, 10, 20, 30, 60])

        assert not result["is_sufficient"]
        assert result["missing_days"] == 30

    def test_validate_data_sufficiency_partial(self, processor):
        """测试部分数据可用"""
        prices = pd.Series([100] * 25)
        result = processor.validate_data_sufficiency(prices, [5, 10, 20, 30, 60])

        assert not result["is_sufficient"]
        assert result["can_calculate_partial"]  # 可以计算部分周期


class TestConfigModule:
    """配置模块测试"""

    def test_default_period_configs(self):
        """测试默认周期配置"""
        assert len(DEFAULT_PERIOD_CONFIGS) == 8
        assert DEFAULT_PERIOD_CONFIGS[0]["period"] == "5d"
        assert DEFAULT_PERIOD_CONFIGS[0]["days"] == 5

    def test_period_weights(self):
        """测试周期权重"""
        assert "5d" in PERIOD_WEIGHTS
        assert abs(sum(PERIOD_WEIGHTS.values()) - 1.0) < 0.01  # 权重和应为 1

    def test_get_strength_level(self):
        """测试强度等级函数"""
        assert get_strength_level(90) == "非常强势"
        assert get_strength_level(50) == "偏强"
        assert get_strength_level(0) == "非常弱势"

    def test_get_trend_name(self):
        """测试趋势名称函数"""
        assert get_trend_name(1) == "上升"
        assert get_trend_name(0) == "横盘"
        assert get_trend_name(-1) == "下降"

    def test_is_valid_score(self):
        """测试得分验证函数"""
        assert is_valid_score(50)
        assert is_valid_score(0)
        assert is_valid_score(100)
        assert not is_valid_score(-1)
        assert not is_valid_score(101)
        assert not is_valid_score(None)


class TestCalculationIntegration:
    """集成测试"""

    @pytest.fixture
    def calculator(self):
        return StrengthCalculator(config={"weights": PERIOD_WEIGHTS})

    def test_full_calculation_workflow(self, calculator):
        """测试完整计算流程"""
        # 1. 准备测试数据
        dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
        # 创建上升趋势的价格序列
        prices = pd.Series([100 + i * 0.2 for i in range(100)], index=dates)
        current_price = 100 + 99 * 0.2

        # 2. 计算强度
        result = calculator.calculate_entity_strength(
            prices=prices,
            current_price=current_price,
            period_configs=DEFAULT_PERIOD_CONFIGS,
        )

        # 3. 验证结果
        assert "strength_score" in result
        assert "trend_direction" in result
        assert "price_ratios" in result
        assert "ma_values" in result

        # 上升趋势应该有较高的强度得分
        assert result["strength_score"] >= 50

    def test_edge_case_empty_prices(self, calculator):
        """测试空价格序列"""
        empty_prices = pd.Series(dtype=float)

        result = calculator.calculate_entity_strength(
            prices=empty_prices,
            current_price=100,
            period_configs=DEFAULT_PERIOD_CONFIGS,
        )

        assert result["strength_score"] is None
        assert "error" in result

    def test_edge_case_single_price(self, calculator):
        """测试单一价格点"""
        single_price = pd.Series([100], index=[pd.Timestamp("2024-01-01")])

        result = calculator.calculate_entity_strength(
            prices=single_price,
            current_price=100,
            period_configs=DEFAULT_PERIOD_CONFIGS,
        )

        assert result["strength_score"] is None
        assert "error" in result

    def test_nan_handling(self, calculator):
        """测试 NaN 值处理"""
        dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
        prices = pd.Series([100] * 100, index=dates)
        prices.iloc[50] = np.nan  # 插入一个 NaN

        result = calculator.calculate_entity_strength(
            prices=prices,
            current_price=100,
            period_configs=DEFAULT_PERIOD_CONFIGS,
        )

        # 应该能够处理 NaN 值
        assert result["strength_score"] is not None

    def test_partial_calculation_with_limited_data(self, calculator):
        """测试渐近式计算 - 数据只有 25 天，只能计算部分周期"""
        dates = pd.date_range(start="2024-01-01", periods=25, freq="D")
        prices = pd.Series([100 + i * 0.1 for i in range(25)], index=dates)
        current_price = 100 + 24 * 0.1

        result = calculator.calculate_entity_strength(
            prices=prices,
            current_price=current_price,
            period_configs=DEFAULT_PERIOD_CONFIGS,
        )

        # 应该能够计算（渐近式）
        assert result["strength_score"] is not None
        assert result["partial_calculation"] is True  # 标记为部分计算
        # 只有 5d, 10d, 20d 可用
        assert len(result["available_periods"]) == 3
        assert 5 in result["available_periods"]
        assert 10 in result["available_periods"]
        assert 20 in result["available_periods"]

    def test_partial_calculation_minimal_data(self, calculator):
        """测试渐近式计算 - 最少 5 天数据"""
        dates = pd.date_range(start="2024-01-01", periods=5, freq="D")
        prices = pd.Series([100 + i * 0.1 for i in range(5)], index=dates)
        current_price = 100 + 4 * 0.1

        result = calculator.calculate_entity_strength(
            prices=prices,
            current_price=current_price,
            period_configs=DEFAULT_PERIOD_CONFIGS,
        )

        # 应该能够计算（只有 5d 周期可用）
        assert result["strength_score"] is not None
        assert result["partial_calculation"] is True
        assert len(result["available_periods"]) == 1
        assert 5 in result["available_periods"]

    def test_partial_calculation_insufficient_min_data(self, calculator):
        """测试渐近式计算 - 数据不足 5 天应返回错误"""
        dates = pd.date_range(start="2024-01-01", periods=3, freq="D")
        prices = pd.Series([100, 101, 102], index=dates)

        result = calculator.calculate_entity_strength(
            prices=prices,
            current_price=102,
            period_configs=DEFAULT_PERIOD_CONFIGS,
        )

        # 数据严重不足
        assert result["strength_score"] is None
        assert "error" in result
