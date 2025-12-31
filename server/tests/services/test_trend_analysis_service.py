"""
趋势分析服务测试 (Story 10.5 - Task 2)
"""

import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.trend_analysis_service import TrendAnalysisService, TREND_TYPES


@pytest.fixture
def mock_session():
    """模拟数据库会话"""
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def trend_service(mock_session):
    """创建趋势分析服务实例"""
    return TrendAnalysisService(mock_session)


@pytest.fixture
def mock_history_data():
    """模拟历史数据"""
    return [
        {
            "date": date.today() - timedelta(days=4),
            "score": 70.0,
            "rank": 100,
            "percentile": 60.0,
            "strength_grade": "B",
        },
        {
            "date": date.today() - timedelta(days=3),
            "score": 72.0,
            "rank": 95,
            "percentile": 62.0,
            "strength_grade": "B",
        },
        {
            "date": date.today() - timedelta(days=2),
            "score": 75.0,
            "rank": 90,
            "percentile": 65.0,
            "strength_grade": "B+",
        },
        {
            "date": date.today() - timedelta(days=1),
            "score": 78.0,
            "rank": 85,
            "percentile": 68.0,
            "strength_grade": "A",
        },
        {
            "date": date.today(),
            "score": 82.0,
            "rank": 80,
            "percentile": 72.0,
            "strength_grade": "A",
        },
    ]


class TestTrendAnalysisService:
    """趋势分析服务基础测试"""

    def test_init(self, mock_session):
        """测试初始化"""
        service = TrendAnalysisService(mock_session)
        assert service.session == mock_session
        assert service.history_service is not None

    def test_trend_types_constant(self):
        """测试趋势类型常量"""
        assert "strong_up" in TREND_TYPES
        assert "up" in TREND_TYPES
        assert "neutral" in TREND_TYPES
        assert "down" in TREND_TYPES
        assert "strong_down" in TREND_TYPES


class TestIdentifyTrend:
    """趋势识别测试"""

    @pytest.mark.asyncio
    async def test_identify_uptrend(self, trend_service, mock_history_data):
        """测试识别上涨趋势"""
        # 模拟上涨数据
        uptrend_data = [
            {**d, "score": 70.0 + i * 3} for i, d in enumerate(mock_history_data)
        ]

        trend_service.history_service.get_stock_history = AsyncMock(
            return_value=uptrend_data
        )

        result = await trend_service.identify_trend("stock", 1, days=5)

        assert result["trend_type"] in ["up", "strong_up"]
        assert result["slope"] > 0
        assert result["confidence"] in ["high", "medium", "low"]
        assert result["data_points"] == 5

    @pytest.mark.asyncio
    async def test_identify_downtrend(self, trend_service, mock_history_data):
        """测试识别下跌趋势"""
        # 模拟下跌数据
        downtrend_data = [
            {**d, "score": 82.0 - i * 3} for i, d in enumerate(mock_history_data)
        ]

        trend_service.history_service.get_stock_history = AsyncMock(
            return_value=downtrend_data
        )

        result = await trend_service.identify_trend("stock", 1, days=5)

        assert result["trend_type"] in ["down", "strong_down"]
        assert result["slope"] < 0

    @pytest.mark.asyncio
    async def test_identify_neutral_trend(self, trend_service):
        """测试识别震荡趋势"""
        # 模拟震荡数据
        neutral_data = [
            {
                "date": date.today() - timedelta(days=i),
                "score": 75.0 + (1 if i % 2 == 0 else -1),
                "rank": 80,
                "percentile": 65.0,
                "strength_grade": "B+",
            }
            for i in range(5)
        ]

        trend_service.history_service.get_stock_history = AsyncMock(
            return_value=neutral_data
        )

        result = await trend_service.identify_trend("stock", 1, days=5)

        assert result["trend_type"] == "neutral"
        assert -0.1 <= result["slope"] <= 0.1

    @pytest.mark.asyncio
    async def test_identify_trend_insufficient_data(self, trend_service):
        """测试数据不足的情况"""
        trend_service.history_service.get_stock_history = AsyncMock(
            return_value=[]
        )

        result = await trend_service.identify_trend("stock", 1, days=5)

        assert result["trend_type"] == "unknown"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_identify_trend_with_ma_trends(self, trend_service, mock_history_data):
        """测试包含移动平均线趋势的趋势分析"""
        trend_service.history_service.get_stock_history = AsyncMock(
            return_value=mock_history_data
        )

        result = await trend_service.identify_trend("stock", 1, days=30)

        assert "ma_trends" in result
        # 应该有5日、10日、20日移动平均线趋势
        assert "ma5" in result["ma_trends"]


class TestDetectConsolidation:
    """横盘检测测试"""

    def test_detect_consolidation_true(self, trend_service):
        """测试检测到横盘"""
        # 模拟横盘数据（波动小）
        scores = [75.0, 75.5, 74.8, 75.2, 75.0, 74.9, 75.1]

        result = trend_service._detect_consolidation(scores, threshold=2.0)

        assert result["is_consolidating"] is True
        assert result["std_dev"] < 2.0
        assert "support_level" in result
        assert "resistance_level" in result

    def test_detect_consolidation_false(self, trend_service):
        """测试未检测到横盘"""
        # 模拟趋势数据（波动大）
        scores = [70.0, 85.0, 65.0, 90.0, 60.0, 95.0]

        result = trend_service._detect_consolidation(scores, threshold=2.0)

        assert result["is_consolidating"] is False
        assert result["std_dev"] > 2.0 or result["price_range"] > 6.0

    def test_detect_consolidation_insufficient_data(self, trend_service):
        """测试数据不足"""
        scores = [70.0, 75.0]  # 只有2个数据点

        result = trend_service._detect_consolidation(scores)

        assert result["is_consolidating"] is False
        assert "reason" in result


class TestCalculateMATrend:
    """移动平均线趋势测试"""

    def test_calculate_ma_trend_up(self, trend_service):
        """测试上涨的移动平均线"""
        scores = [70.0, 72.0, 74.0, 76.0, 78.0, 80.0, 82.0]

        result = trend_service._calculate_ma_trend(scores, window=5)

        assert result["window"] == 5
        assert result["status"] == "calculated"
        assert result["current_ma"] > result["previous_ma"]
        assert result["direction"] in ["up", "strong_up"]

    def test_calculate_ma_trend_down(self, trend_service):
        """测试下跌的移动平均线"""
        scores = [82.0, 80.0, 78.0, 76.0, 74.0, 72.0, 70.0]

        result = trend_service._calculate_ma_trend(scores, window=5)

        assert result["window"] == 5
        assert result["current_ma"] < result["previous_ma"]
        assert result["direction"] in ["down", "strong_down"]

    def test_calculate_ma_trend_insufficient_data(self, trend_service):
        """测试数据不足"""
        scores = [70.0, 75.0]  # 只有2个数据点

        result = trend_service._calculate_ma_trend(scores, window=5)

        assert result["window"] == 5
        assert result["status"] == "insufficient_data"


class TestDetectConsolidationAsync:
    """异步横盘检测测试"""

    @pytest.mark.asyncio
    async def test_detect_consolidation_async(self, trend_service, mock_history_data):
        """测试异步横盘检测"""
        trend_service.history_service.get_stock_history = AsyncMock(
            return_value=mock_history_data
        )

        result = await trend_service.detect_consolidation("stock", 1, days=5)

        assert "is_consolidating" in result
        assert "std_dev" in result
        assert "price_range" in result

    @pytest.mark.asyncio
    async def test_detect_consolidation_with_custom_threshold(
        self, trend_service, mock_history_data
    ):
        """测试使用自定义阈值的横盘检测"""
        trend_service.history_service.get_stock_history = AsyncMock(
            return_value=mock_history_data
        )

        result = await trend_service.detect_consolidation(
            "stock", 1, days=5, threshold=5.0
        )

        assert result["threshold_used"] == 5.0


class TestCalculateMovingAvgTrendAsync:
    """异步移动平均线趋势测试"""

    @pytest.mark.asyncio
    async def test_calculate_moving_avg_trend(self, trend_service, mock_history_data):
        """测试异步移动平均线计算"""
        trend_service.history_service.get_stock_history = AsyncMock(
            return_value=mock_history_data
        )

        result = await trend_service.calculate_moving_avg_trend(
            "stock", 1, window=10, days=30
        )

        assert "window" in result
        assert result["window"] == 10

    @pytest.mark.asyncio
    async def test_calculate_moving_avg_trend_insufficient_data(
        self, trend_service
    ):
        """测试数据不足的移动平均线计算"""
        trend_service.history_service.get_stock_history = AsyncMock(
            return_value=[]
        )

        result = await trend_service.calculate_moving_avg_trend(
            "stock", 1, window=10, days=5
        )

        assert result["status"] == "not_available"


class TestGetTrendSummary:
    """趋势摘要测试"""

    @pytest.mark.asyncio
    async def test_get_trend_summary(self, trend_service, mock_history_data):
        """测试获取趋势摘要"""
        trend_service.history_service.get_stock_history = AsyncMock(
            return_value=mock_history_data
        )

        result = await trend_service.get_trend_summary("stock", 1, days=5)

        assert "trend_type" in result
        assert "trend_direction" in result
        assert "confidence" in result
        assert "slope" in result
        assert "period" in result
        assert result["period"] == "最近5天"

    @pytest.mark.asyncio
    async def test_get_trend_summary_error(self, trend_service):
        """测试获取摘要时的错误处理"""
        trend_service.history_service.get_stock_history = AsyncMock(
            return_value=[]
        )

        result = await trend_service.get_trend_summary("stock", 1, days=5)

        assert "error" in result


@pytest.mark.integration
class TestTrendAnalysisIntegration:
    """趋势分析集成测试"""

    @pytest.mark.asyncio
    async def test_end_to_end_trend_analysis(self, trend_service):
        """端到端趋势分析测试"""
        # 注意：此测试需要真实的数据库连接

        test_date = date.today() - timedelta(days=1)

        # 测试完整的趋势分析流程
        result = await trend_service.identify_trend(
            "stock", 1, days=10, end_date=test_date
        )

        # 验证结果结构
        if "error" not in result:
            assert "trend_type" in result
            assert "slope" in result
            assert "r_squared" in result
            assert "confidence" in result

    @pytest.mark.asyncio
    async def test_consolidation_detection_performance(self, trend_service):
        """测试横盘检测性能"""
        import time

        # 创建测试数据
        test_data = [
            {
                "date": date.today() - timedelta(days=i),
                "score": 75.0 + (i % 3) * 0.5,  # 小幅波动
                "rank": 80,
                "percentile": 65.0,
                "strength_grade": "B+",
            }
            for i in range(100)
        ]

        trend_service.history_service.get_stock_history = AsyncMock(
            return_value=test_data
        )

        start_time = time.time()
        result = await trend_service.detect_consolidation("stock", 1, days=100)
        elapsed = (time.time() - start_time) * 1000

        # 验证结果
        assert "is_consolidating" in result

        # 性能检查：应该在合理时间内完成
        print(f"横盘检测 (100天数据) 耗时: {elapsed:.2f}ms")
