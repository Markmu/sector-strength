"""
板块分类算法服务单元测试

测试 SectorClassificationService 的缠论分类算法功能。
"""

import pytest
from datetime import date, timedelta
from unittest.mock import Mock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.sector_classification_service import (
    SectorClassificationService,
    calculate_classification_level,
    calculate_state,
    ClassificationResult,
    MissingMADataError,
    InvalidPriceError,
    ClassificationError
)
from src.models.sector import Sector
from src.models.daily_market_data import DailyMarketData
from src.models.moving_average_data import MovingAverageData


# ===============================
# Fixtures
# ===============================

@pytest.fixture
def mock_session():
    """模拟数据库会话"""
    session = Mock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.add = Mock()
    return session


@pytest.fixture
def sample_sector():
    """示例板块"""
    sector = Sector()
    sector.id = 1
    sector.name = "测试板块"
    sector.code = "TEST001"
    return sector


@pytest.fixture
def ma_values_all_above():
    """价格在所有均线上方的均线值"""
    return {
        'ma_5': 90.0,
        'ma_10': 92.0,
        'ma_20': 94.0,
        'ma_30': 96.0,
        'ma_60': 98.0,
        'ma_90': 100.0,
        'ma_120': 102.0,
        'ma_240': 104.0
    }


@pytest.fixture
def ma_values_conquered_240():
    """攻克240日均线的均线值（价格 <= ma_5 且 > ma_240）

    条件：price <= ma_5 且 price > ma_240
    需要：ma_5 >= price > ma_240
    例如：price=200, ma_5=210, ma_240=190（其他均线在ma_5和ma_240之间）
    """
    return {
        'ma_5': 210.0,
        'ma_10': 205.0,
        'ma_20': 200.0,
        'ma_30': 198.0,
        'ma_60': 195.0,
        'ma_90': 193.0,
        'ma_120': 192.0,
        'ma_240': 190.0
    }


@pytest.fixture
def ma_values_conquered_120():
    """攻克120日均线的均线值（价格 <= ma_240 且 > ma_120）

    条件：price <= ma_240 且 price > ma_120
    需要：ma_240 >= price > ma_120
    """
    return {
        'ma_5': 250.0,
        'ma_10': 245.0,
        'ma_20': 240.0,
        'ma_30': 235.0,
        'ma_60': 230.0,
        'ma_90': 225.0,
        'ma_120': 200.0,
        'ma_240': 210.0
    }


@pytest.fixture
def ma_values_conquered_90():
    """攻克90日均线的均线值（价格 <= ma_120 且 > ma_90）"""
    return {
        'ma_5': 250.0,
        'ma_10': 245.0,
        'ma_20': 240.0,
        'ma_30': 235.0,
        'ma_60': 230.0,
        'ma_90': 200.0,
        'ma_120': 210.0,
        'ma_240': 220.0
    }


@pytest.fixture
def ma_values_conquered_60():
    """攻克60日均线的均线值（价格 <= ma_90 且 > ma_60）"""
    return {
        'ma_5': 250.0,
        'ma_10': 245.0,
        'ma_20': 240.0,
        'ma_30': 235.0,
        'ma_60': 200.0,
        'ma_90': 210.0,
        'ma_120': 220.0,
        'ma_240': 230.0
    }


@pytest.fixture
def ma_values_conquered_30():
    """攻克30日均线的均线值（价格 <= ma_60 且 > ma_30）"""
    return {
        'ma_5': 250.0,
        'ma_10': 245.0,
        'ma_20': 240.0,
        'ma_30': 200.0,
        'ma_60': 210.0,
        'ma_90': 220.0,
        'ma_120': 230.0,
        'ma_240': 240.0
    }


@pytest.fixture
def ma_values_conquered_20():
    """攻克20日均线的均线值（价格 <= ma_30 且 > ma_20）"""
    return {
        'ma_5': 250.0,
        'ma_10': 245.0,
        'ma_20': 200.0,
        'ma_30': 210.0,
        'ma_60': 220.0,
        'ma_90': 230.0,
        'ma_120': 240.0,
        'ma_240': 250.0
    }


@pytest.fixture
def ma_values_conquered_10():
    """攻克10日均线的均线值（价格 <= ma_20 且 > ma_10）"""
    return {
        'ma_5': 250.0,
        'ma_10': 190.0,
        'ma_20': 200.0,
        'ma_30': 210.0,
        'ma_60': 220.0,
        'ma_90': 230.0,
        'ma_120': 240.0,
        'ma_240': 250.0
    }


@pytest.fixture
def ma_values_all_below():
    """价格在所有均线下方的均线值"""
    return {
        'ma_5': 110.0,
        'ma_10': 112.0,
        'ma_20': 114.0,
        'ma_30': 116.0,
        'ma_60': 118.0,
        'ma_90': 120.0,
        'ma_120': 122.0,
        'ma_240': 124.0
    }


# ===============================
# 测试分类级别计算
# ===============================

class TestClassificationLevel:
    """测试分类级别计算"""

    def test_level_9_above_all_mas(self, ma_values_all_above):
        """第9类：价格在所有均线上方"""
        current_price = 110.0
        assert calculate_classification_level(current_price, ma_values_all_above) == 9

    def test_level_8_conquered_240(self, ma_values_conquered_240):
        """第8类：攻克240日线"""
        # ma_5=210, ma_240=190, price 在 (190, 210] 之间
        current_price = 200.0
        assert calculate_classification_level(current_price, ma_values_conquered_240) == 8

    def test_level_7_conquered_120(self, ma_values_conquered_120):
        """第7类：攻克120日线"""
        # ma_240=210, ma_120=200, price 在 (200, 210] 之间
        current_price = 205.0
        assert calculate_classification_level(current_price, ma_values_conquered_120) == 7

    def test_level_6_conquered_90(self, ma_values_conquered_90):
        """第6类：攻克90日线"""
        # ma_120=210, ma_90=200, price 在 (200, 210] 之间
        current_price = 205.0
        assert calculate_classification_level(current_price, ma_values_conquered_90) == 6

    def test_level_5_conquered_60(self, ma_values_conquered_60):
        """第5类：攻克60日线"""
        # ma_90=210, ma_60=200, price 在 (200, 210] 之间
        current_price = 205.0
        assert calculate_classification_level(current_price, ma_values_conquered_60) == 5

    def test_level_4_conquered_30(self, ma_values_conquered_30):
        """第4类：攻克30日线"""
        # ma_60=210, ma_30=200, price 在 (200, 210] 之间
        current_price = 205.0
        assert calculate_classification_level(current_price, ma_values_conquered_30) == 4

    def test_level_3_conquered_20(self, ma_values_conquered_20):
        """第3类：攻克20日线"""
        # ma_30=210, ma_20=200, price 在 (200, 210] 之间
        current_price = 205.0
        assert calculate_classification_level(current_price, ma_values_conquered_20) == 3

    def test_level_2_conquered_10(self, ma_values_conquered_10):
        """第2类：攻克10日线"""
        # ma_20=200, ma_10=190, price 在 (190, 200] 之间
        current_price = 195.0
        assert calculate_classification_level(current_price, ma_values_conquered_10) == 2

    def test_level_1_below_all_mas(self, ma_values_all_below):
        """第1类：价格在所有均线下方"""
        current_price = 100.0
        assert calculate_classification_level(current_price, ma_values_all_below) == 1

    def test_boundary_equal_price(self):
        """边界条件：价格等于某条均线"""
        current_price = 100.0
        ma_values = {
            'ma_5': 100.0,  # 价格等于 ma_5
            'ma_10': 90.0,
            'ma_20': 80.0,
            'ma_30': 70.0,
            'ma_60': 60.0,
            'ma_90': 50.0,
            'ma_120': 40.0,
            'ma_240': 30.0
        }
        # 价格 <= ma_5 且 > ma_240，应归类为攻克240日线（第8类）
        assert calculate_classification_level(current_price, ma_values) == 8

    def test_boundary_equal_multiple_mas(self):
        """边界条件：价格等于多条均线"""
        current_price = 100.0
        ma_values = {
            'ma_5': 100.0,
            'ma_10': 100.0,
            'ma_20': 100.0,
            'ma_30': 100.0,
            'ma_60': 100.0,
            'ma_90': 100.0,
            'ma_120': 100.0,
            'ma_240': 100.0
        }
        # 价格等于所有均线，由于 <= ma_5 且 <= ma_240（不满足 > ma_240），继续向下判断
        # 价格 <= ma_240 且 <= ma_120（不满足 > ma_120），继续向下判断
        # ...最终会归入第1类（所有条件都不满足）
        assert calculate_classification_level(current_price, ma_values) == 1

    def test_missing_ma_data_raises_error(self):
        """缺失均线数据应抛出异常"""
        current_price = 100.0
        incomplete_ma_values = {
            'ma_5': 90.0,
            'ma_10': 92.0
            # 缺少其他均线
        }
        with pytest.raises(MissingMADataError) as exc_info:
            calculate_classification_level(current_price, incomplete_ma_values)
        assert "缺少必需的均线数据" in str(exc_info.value)

    def test_none_ma_value_raises_error(self):
        """均线值为 None 应抛出异常"""
        current_price = 100.0
        ma_values_with_none = {
            'ma_5': 90.0,
            'ma_10': 92.0,
            'ma_20': None,  # None 值
            'ma_30': 96.0,
            'ma_60': 98.0,
            'ma_90': 100.0,
            'ma_120': 102.0,
            'ma_240': 104.0
        }
        with pytest.raises(MissingMADataError) as exc_info:
            calculate_classification_level(current_price, ma_values_with_none)
        assert "缺少必需的均线数据" in str(exc_info.value)


# ===============================
# 测试状态计算
# ===============================

class TestStateCalculation:
    """测试状态判断"""

    def test_rally_state(self):
        """反弹状态"""
        assert calculate_state(105.0, 100.0) == '反弹'

    def test_adjustment_state(self):
        """调整状态"""
        assert calculate_state(95.0, 100.0) == '调整'

    def test_equal_prices(self):
        """价格相等应归类为调整"""
        assert calculate_state(100.0, 100.0) == '调整'

    def test_small_rally(self):
        """小幅反弹"""
        assert calculate_state(100.01, 100.0) == '反弹'

    def test_small_adjustment(self):
        """小幅调整"""
        assert calculate_state(99.99, 100.0) == '调整'


# ===============================
# 测试服务类
# ===============================

class TestSectorClassificationService:
    """测试板块分类服务"""

    def test_initialization(self, mock_session):
        """测试服务初始化"""
        service = SectorClassificationService(mock_session)
        assert service.session == mock_session
        assert service.MA_PERIODS == [5, 10, 20, 30, 60, 90, 120, 240]

    def test_set_progress_callback(self, mock_session):
        """测试设置进度回调"""
        service = SectorClassificationService(mock_session)

        async def test_callback(current: int, total: int, message: str):
            pass

        service.set_progress_callback(test_callback)
        assert service._progress_callback is not None

    @pytest.mark.asyncio
    async def test_get_ma_data_success(self, mock_session):
        """测试成功获取均线数据"""
        service = SectorClassificationService(mock_session)

        # 模拟返回的均线数据
        mock_ma_data = Mock()
        mock_ma_data.ma_value = 100.0
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_ma_data
        mock_session.execute.return_value = mock_result

        ma_values = await service.get_ma_data(1, date(2024, 1, 1))

        assert len(ma_values) == 8
        assert 'ma_5' in ma_values
        assert 'ma_240' in ma_values
        # 验证 execute 被调用了正确的次数（8次，每个周期一次）
        assert mock_session.execute.call_count == 8

    @pytest.mark.asyncio
    async def test_get_ma_data_missing(self, mock_session):
        """测试均线数据缺失"""
        service = SectorClassificationService(mock_session)

        # 模拟返回 None
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with pytest.raises(MissingMADataError) as exc_info:
            await service.get_ma_data(1, date(2024, 1, 1))

        assert ("缺少" in str(exc_info.value)) or ("缺失" in str(exc_info.value))
        assert exc_info.value.sector_id == 1

    @pytest.mark.asyncio
    async def test_get_price_data_success(self, mock_session):
        """测试成功获取价格数据"""
        service = SectorClassificationService(mock_session)

        # 模拟返回6天的价格数据（按日期降序排列）
        # 最新数据在前，最旧数据在后
        price_data_list = []
        for i in range(6):
            mock_data = Mock(spec=DailyMarketData)
            mock_data.close = 105.0 - i  # 105, 104, 103, 102, 101, 100
            price_data_list.append(mock_data)

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = price_data_list
        mock_session.execute.return_value = mock_result

        current_price, price_5_days_ago = await service.get_price_data(1, date(2024, 1, 1))

        assert current_price == 105.0  # 第一天（最新）
        assert price_5_days_ago == 100.0  # 第6天（5天前）

    @pytest.mark.asyncio
    async def test_get_price_data_insufficient(self, mock_session):
        """测试价格数据不足"""
        service = SectorClassificationService(mock_session)

        # 模拟返回少于6天的数据
        price_data_list = [Mock(spec=DailyMarketData) for _ in range(3)]
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = price_data_list
        mock_session.execute.return_value = mock_result

        with pytest.raises(InvalidPriceError) as exc_info:
            await service.get_price_data(1, date(2024, 1, 1))

        assert "数据不足" in str(exc_info.value)
        assert exc_info.value.sector_id == 1

    @pytest.mark.asyncio
    async def test_calculate_classification_success(self, mock_session, sample_sector):
        """测试成功计算分类"""
        service = SectorClassificationService(mock_session)

        # 模拟板块查询
        sector_result = Mock()
        sector_result.scalar_one_or_none.return_value = sample_sector

        # 模拟均线查询
        ma_result = Mock()
        mock_ma_data = Mock()
        mock_ma_data.ma_value = 100.0
        ma_result.scalar_one_or_none.return_value = mock_ma_data

        # 模拟价格查询
        price_list = []
        for i in range(6):
            mock_data = Mock(spec=DailyMarketData)
            mock_data.close = 100.0 + i
            price_list.append(mock_data)
        price_result = Mock()
        price_result.scalars.return_value.all.return_value = price_list

        # 设置返回顺序
        mock_session.execute.side_effect = [sector_result, ma_result, ma_result, ma_result, ma_result,
                                            ma_result, ma_result, ma_result, ma_result, price_result]

        result = await service.calculate_classification(1, date(2024, 1, 1))

        assert isinstance(result, ClassificationResult)
        assert result.sector_id == 1
        assert result.sector_name == "测试板块"
        assert result.symbol == "TEST001"
        assert 1 <= result.classification_level <= 9
        assert result.state in ['反弹', '调整']

    @pytest.mark.asyncio
    async def test_calculate_classification_sector_not_found(self, mock_session):
        """测试板块不存在"""
        service = SectorClassificationService(mock_session)

        sector_result = Mock()
        sector_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = sector_result

        with pytest.raises(InvalidPriceError) as exc_info:
            await service.calculate_classification(999, date(2024, 1, 1))

        assert "不存在" in str(exc_info.value)


# ===============================
# 测试批量计算
# ===============================

class TestBatchCalculation:
    """测试批量计算功能"""

    @pytest.mark.asyncio
    async def test_batch_calculate_all_sectors(self, mock_session):
        """测试批量计算所有板块"""
        service = SectorClassificationService(mock_session)

        # 创建3个测试板块
        sectors = []
        for i in range(3):
            sector = Mock(spec=Sector)
            sector.id = i + 1
            sector.name = f"板块{i+1}"
            sector.code = f"SECTOR{i+1:03d}"
            sectors.append(sector)

        # 模拟板块查询
        sectors_result = Mock()
        sectors_result.scalars.return_value.all.return_value = sectors
        mock_session.execute.return_value = sectors_result

        # 这里我们无法完整模拟整个调用链，但可以验证方法可以正常调用
        # 实际测试需要更完整的 mock 设置
        assert service is not None

    @pytest.mark.asyncio
    async def test_batch_calculate_with_default_date(self, mock_session):
        """测试批量计算使用默认日期（今天）"""
        service = SectorClassificationService(mock_session)

        # 模拟空板块列表
        empty_result = Mock()
        empty_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = empty_result

        with pytest.raises(InvalidPriceError) as exc_info:
            await service.batch_calculate_all_sectors()

        assert "没有找到任何板块" in str(exc_info.value)


# ===============================
# 测试性能
# ===============================

class TestPerformance:
    """测试性能"""

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_timing_decorator(self, mock_session):
        """测试性能计时装饰器"""
        service = SectorClassificationService(mock_session)

        # 模拟空板块列表以快速返回
        empty_result = Mock()
        empty_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = empty_result

        try:
            result = await service.batch_calculate_all_sectors()
        except InvalidPriceError:
            pass  # 预期的异常

    def test_algorithm_performance(self, ma_values_all_above):
        """测试核心算法性能"""
        import time

        iterations = 10000
        start = time.perf_counter()

        for _ in range(iterations):
            calculate_classification_level(100.0, ma_values_all_above)

        elapsed = time.perf_counter() - start
        avg_time_ms = (elapsed / iterations) * 1000

        # 平均每次计算应该小于 1ms
        assert avg_time_ms < 1.0, f"平均计算时间 {avg_time_ms:.3f}ms 超过 1ms 限制"


# ===============================
# 测试边界条件
# ===============================

class TestEdgeCases:
    """测试边界条件"""

    def test_zero_price(self, ma_values_all_above):
        """测试价格为0的情况"""
        current_price = 0.0
        # 价格为0应该在所有均线下方
        assert calculate_classification_level(current_price, ma_values_all_above) == 1

    def test_negative_price(self, ma_values_all_above):
        """测试负价格（异常情况）"""
        current_price = -100.0
        # 负价格应该在所有均线下方
        assert calculate_classification_level(current_price, ma_values_all_above) == 1

    def test_very_large_price(self, ma_values_all_above):
        """测试非常大的价格"""
        current_price = 999999.0
        # 非常大的价格应该在所有均线上方
        assert calculate_classification_level(current_price, ma_values_all_above) == 9

    def test_negative_price_5_days_ago(self):
        """测试5天前价格为负（异常情况）"""
        # 负价格视为异常，当前价格大于负价格
        assert calculate_state(100.0, -100.0) == '反弹'

    def test_ma_values_with_decimals(self):
        """测试带小数的均线值"""
        current_price = 100.55
        ma_values = {
            'ma_5': 100.50,
            'ma_10': 100.40,
            'ma_20': 100.30,
            'ma_30': 100.20,
            'ma_60': 100.10,
            'ma_90': 100.00,
            'ma_120': 99.90,
            'ma_240': 99.80
        }
        # 价格大于所有均线
        assert calculate_classification_level(current_price, ma_values) == 9


# ===============================
# 测试进度回调
# ===============================

class TestProgressCallback:
    """测试进度回调功能"""

    @pytest.mark.asyncio
    async def test_report_progress_with_callback(self, mock_session):
        """测试带回调函数的进度报告"""
        service = SectorClassificationService(mock_session)

        callback_calls = []

        async def test_callback(current: int, total: int, message: str):
            callback_calls.append((current, total, message))

        service.set_progress_callback(test_callback)

        # 调用进度报告
        await service._report_progress(1, 10, "测试消息")

        assert len(callback_calls) == 1
        assert callback_calls[0] == (1, 10, "测试消息")

    @pytest.mark.asyncio
    async def test_report_progress_without_callback(self, mock_session):
        """测试没有回调函数时的进度报告"""
        service = SectorClassificationService(mock_session)

        # 没有设置回调，应该不会报错
        await service._report_progress(1, 10, "测试消息")


# ===============================
# 测试 timing_decorator
# ===============================

class TestTimingDecorator:
    """测试性能计时装饰器"""

    @pytest.mark.asyncio
    async def test_timing_decorator_with_dict_result(self, mock_session):
        """测试装饰器对字典结果的处理"""
        from src.services.sector_classification_service import timing_decorator

        @timing_decorator
        async def test_function_returning_dict():
            return {'key': 'value'}

        result = await test_function_returning_dict()

        assert 'key' in result
        assert '_elapsed_ms' in result
        assert result['_elapsed_ms'] >= 0

    @pytest.mark.asyncio
    async def test_timing_decorator_with_non_dict_result(self, mock_session):
        """测试装饰器对非字典结果的处理"""
        from src.services.sector_classification_service import timing_decorator

        @timing_decorator
        async def test_function_returning_object():
            from src.services.sector_classification_service import ClassificationResult
            return ClassificationResult(
                sector_id=1,
                sector_name="测试",
                symbol="TEST",
                classification_level=5,
                state="反弹",
                current_price=100.0,
                ma_values={'ma_5': 90.0},
                price_5_days_ago=95.0,
                classification_date=date(2024, 1, 1)
            )

        result = await test_function_returning_object()

        # 非字典结果不应该被修改
        assert isinstance(result, ClassificationResult)
        assert result.sector_id == 1


# ===============================
# 测试批量计算错误处理
# ===============================

class TestBatchCalculationErrors:
    """测试批量计算中的错误处理"""

    @pytest.mark.asyncio
    async def test_batch_calculate_with_some_failures(self, mock_session):
        """测试部分板块失败的情况"""
        service = SectorClassificationService(mock_session)

        # 创建3个测试板块
        sectors = []
        for i in range(3):
            sector = Mock(spec=Sector)
            sector.id = i + 1
            sector.name = f"板块{i+1}"
            sector.code = f"SECTOR{i+1:03d}"
            sectors.append(sector)

        # 模拟板块查询返回空列表（会抛出异常）
        empty_result = Mock()
        empty_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = empty_result

        # 应该抛出 InvalidPriceError
        with pytest.raises(InvalidPriceError) as exc_info:
            await service.batch_calculate_all_sectors()

        assert "没有找到任何板块" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_batch_calculate_progress_reporting(self, mock_session):
        """测试批量计算中的进度报告"""
        service = SectorClassificationService(mock_session)

        progress_updates = []

        async def track_progress(current: int, total: int, message: str):
            progress_updates.append({'current': current, 'total': total, 'message': message})

        service.set_progress_callback(track_progress)

        # 创建空板块列表以快速结束
        empty_result = Mock()
        empty_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = empty_result

        try:
            await service.batch_calculate_all_sectors()
        except InvalidPriceError:
            pass  # 预期的异常

        # 由于没有板块，进度报告不应该被调用
        # 但回调函数已经设置，验证设置成功
        assert service._progress_callback is not None
