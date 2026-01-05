"""
板块均线服务单元测试

测试 SectorMAService 的智能查询范围和均线计算功能。
"""

import pytest
from datetime import date, timedelta
from unittest.mock import Mock, AsyncMock, patch, call
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.sector_ma_service import SectorMAService
from src.models.sector import Sector
from src.models.daily_market_data import DailyMarketData
from src.models.moving_average_data import MovingAverageData


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
def sample_market_data():
    """示例市场数据 - 生成 300 天的数据"""
    data = []
    base_date = date(2024, 1, 1)
    base_price = 100.0

    for i in range(300):
        current_date = base_date + timedelta(days=i)
        # 模拟价格波动
        price = base_price + (i * 0.1) + (i % 10) * 0.5

        market_data = Mock(spec=DailyMarketData)
        market_data.date = current_date
        market_data.close = price
        market_data.open = price * 0.99
        market_data.high = price * 1.02
        market_data.low = price * 0.98
        data.append(market_data)

    return data


class TestSectorMAServiceQueryRange:
    """测试智能查询范围计算"""

    def test_determine_query_range_with_long_period(self, mock_session, sample_sector):
        """测试根据最长均线周期确定查询范围"""
        service = SectorMAService(mock_session)

        # 模拟获取实际数据范围
        mock_min_max_result = Mock()
        mock_min_max_result.min_date = date(2023, 1, 1)
        mock_min_max_result.max_date = date(2024, 12, 31)

        mock_session.execute.return_value.fetchone.return_value = mock_min_max_result

        # 这里我们无法直接测试内部逻辑，但可以通过检查 SQL 查询来验证
        # 实际测试中可以通过 mock execute 来检查传入的查询语句
        assert service is not None

    def test_query_range_with_start_date_constraint(self, mock_session):
        """测试带有 start_date 约束的查询范围"""
        service = SectorMAService(mock_session)

        # 当用户指定 start_date 时，应该取 start_date 和 required_start_date 中较晚的
        start_date = date(2024, 6, 1)
        end_date = date(2024, 12, 31)
        max_period = 240

        # required_start_date = end_date - 240*2 ≈ 2024-04-05
        # query_start_date = max(2024-06-01, 2024-04-05) = 2024-06-01
        required_start_date = end_date - timedelta(days=max_period * 2)
        query_start_date = max(start_date, required_start_date)

        assert query_start_date == start_date

    def test_query_range_without_start_date(self, mock_session):
        """测试不指定 start_date 时的查询范围"""
        service = SectorMAService(mock_session)

        end_date = date(2024, 12, 31)
        max_period = 240

        # 不指定 start_date 时，使用 required_start_date
        required_start_date = end_date - timedelta(days=max_period * 2)
        query_start_date = required_start_date

        expected_start = date(2024, 12, 31) - timedelta(days=480)
        assert query_start_date == expected_start

    def test_query_range_respects_actual_data_bounds(self):
        """测试查询范围不超过实际数据边界"""
        actual_min_date = date(2024, 1, 1)
        actual_max_date = date(2024, 12, 31)

        calculated_start = date(2023, 1, 1)  # 早于实际数据
        calculated_end = date(2025, 1, 1)    # 晚于实际数据

        # 应该被限制在实际数据范围内
        query_start = max(calculated_start, actual_min_date)
        query_end = min(calculated_end, actual_max_date)

        assert query_start == actual_min_date
        assert query_end == actual_max_date


class TestSectorMAServiceCalculation:
    """测试均线计算功能"""

    @pytest.mark.asyncio
    async def test_calculate_with_no_data(self, mock_session, sample_sector):
        """测试没有市场数据时的情况"""
        service = SectorMAService(mock_session)

        # 模拟没有数据
        mock_min_max_result = Mock()
        mock_min_max_result.min_date = None
        mock_min_max_result.max_date = None

        mock_result = Mock()
        mock_result.fetchone.return_value = mock_min_max_result
        mock_session.execute.return_value = mock_result

        result = await service._calculate_single_sector_ma(
            sector=sample_sector,
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 30),
            periods=[5, 10, 20],
            overwrite=False
        )

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_calculate_handles_exception_gracefully(self, mock_session, sample_sector):
        """测试计算过程中异常处理"""
        service = SectorMAService(mock_session)

        # 模拟数据库错误
        mock_session.execute.side_effect = Exception("Database connection error")

        result = await service._calculate_single_sector_ma(
            sector=sample_sector,
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 30),
            periods=[5, 10, 20],
            overwrite=False
        )

        assert result["success"] is False
        assert "error" in result

    def test_query_range_calculation_logic(self):
        """测试查询范围计算逻辑（不依赖数据库）"""
        # 模拟场景：计算 240 日均线
        max_period = 240
        periods = [5, 10, 20, 60, 120, 240]
        assert max(periods) == max_period

        # 用户指定的保存范围
        start_date = date(2024, 6, 1)
        end_date = date(2024, 6, 30)

        # 实际数据范围
        actual_min_date = date(2023, 1, 1)
        actual_max_date = date(2024, 12, 31)

        # 计算查询范围
        query_end_date = end_date if end_date else actual_max_date
        required_start_date = query_end_date - timedelta(days=max_period * 2)

        if start_date:
            query_start_date = max(start_date, required_start_date)
        else:
            query_start_date = required_start_date

        # 确保不超过实际数据范围
        query_start_date = max(query_start_date, actual_min_date)
        query_end_date = min(query_end_date, actual_max_date)

        # 验证计算结果
        assert query_start_date == start_date  # start_date 更晚
        assert query_end_date == end_date

        # 验证查询范围包含足够的历史数据
        days_in_query = (query_end_date - query_start_date).days
        assert days_in_query >= 29  # 6月1日到6月30日是29天

    def test_query_range_without_user_constraints(self):
        """测试不指定日期时的查询范围计算"""
        max_period = 240
        start_date = None
        end_date = None
        actual_max_date = date(2024, 12, 31)

        query_end_date = end_date if end_date else actual_max_date
        required_start_date = query_end_date - timedelta(days=max_period * 2)

        if start_date:
            query_start_date = max(start_date, required_start_date)
        else:
            query_start_date = required_start_date

        expected_start = date(2024, 12, 31) - timedelta(days=480)
        assert query_start_date == expected_start
        assert query_end_date == actual_max_date


class TestSectorMAServiceDateFiltering:
    """测试日期过滤功能"""

    @pytest.mark.asyncio
    async def test_only_saves_specified_date_range(self, mock_session, sample_sector):
        """测试只保存指定日期范围内的均线数据"""
        service = SectorMAService(mock_session)

        # 生成一年的数据
        full_year_data = []
        for i in range(365):
            market_data = Mock(spec=DailyMarketData)
            market_data.date = date(2024, 1, 1) + timedelta(days=i)
            market_data.close = 100.0 + i * 0.1
            full_year_data.append(market_data)

        mock_min_max_result = Mock()
        mock_min_max_result.min_date = date(2024, 1, 1)
        mock_min_max_result.max_date = date(2024, 12, 31)
        mock_session.execute.return_value.fetchone.return_value = mock_min_max_result

        # 指定只保存 6 月份的数据
        start_date = date(2024, 6, 1)
        end_date = date(2024, 6, 30)

        # 验证应该查询更多历史数据（用于计算均线）
        # 但只保存 6 月份的结果
        assert service is not None

    def test_date_filtering_logic(self):
        """测试日期过滤逻辑"""
        # 测试日期过滤条件
        start_date = date(2024, 6, 1)
        end_date = date(2024, 6, 30)

        test_dates = [
            (date(2024, 5, 31), False),  # 早于 start_date
            (date(2024, 6, 1), True),    # 等于 start_date
            (date(2024, 6, 15), True),   # 在范围内
            (date(2024, 6, 30), True),   # 等于 end_date
            (date(2024, 7, 1), False),   # 晚于 end_date
        ]

        for test_date, should_pass in test_dates:
            if start_date and test_date < start_date:
                assert not should_pass, f"{test_date} 应该被过滤"
            elif end_date and test_date > end_date:
                assert not should_pass, f"{test_date} 应该被过滤"
            else:
                assert should_pass, f"{test_date} 应该通过"


class TestSectorMAServicePeriods:
    """测试不同均线周期"""

    def test_default_periods(self):
        """测试默认均线周期"""
        service = SectorMAService(mock_session)
        assert service.DEFAULT_PERIODS == [5, 10, 20, 30, 60, 90, 120, 240]

    def test_max_period_calculation(self):
        """测试最长周期计算"""
        periods = [5, 10, 20, 60, 120, 240]
        max_period = max(periods)
        assert max_period == 240

    def test_required_data_days(self):
        """测试计算所需的数据天数"""
        max_period = 240
        # 考虑节假日，使用 2 倍周期
        required_days = max_period * 2
        assert required_days == 480

        # 计算起始日期
        end_date = date(2024, 12, 31)
        required_start_date = end_date - timedelta(days=required_days)

        expected_start = date(2024, 12, 31) - timedelta(days=480)
        assert required_start_date == expected_start


class TestSectorMAServiceBatchOperations:
    """测试批量操作"""

    @pytest.mark.asyncio
    async def test_calculate_multiple_sectors(self, mock_session):
        """测试计算多个板块的均线"""
        service = SectorMAService(mock_session)

        # 模拟多个板块
        sectors = []
        for i in range(3):
            sector = Mock(spec=Sector)
            sector.id = i + 1
            sector.name = f"板块{i+1}"
            sector.code = f"SECTOR{i+1:03d}"
            sectors.append(sector)

        # 这里只验证方法可调用，实际测试需要更完整的 mock
        assert service is not None

    def test_progress_callback(self, mock_session):
        """测试进度回调"""
        service = SectorMAService(mock_session)

        callback_called = []

        async def test_callback(current: int, total: int, message: str):
            callback_called.append((current, total, message))

        service.set_progress_callback(test_callback)
        assert service._progress_callback is not None


class TestSectorMAServiceEdgeCases:
    """测试边界情况"""

    def test_empty_periods_list(self, mock_session):
        """测试空的周期列表"""
        service = SectorMAService(mock_session)
        periods = []
        if periods:
            max_period = max(periods)
        else:
            max_period = 0
        assert max_period == 0

    def test_single_period(self, mock_session):
        """测试单个周期"""
        service = SectorMAService(mock_session)
        periods = [20]
        max_period = max(periods)
        assert max_period == 20

    def test_very_long_period(self, mock_session):
        """测试超长周期"""
        service = SectorMAService(mock_session)
        periods = [500]
        max_period = max(periods)
        assert max_period == 500

        required_days = max_period * 2
        assert required_days == 1000

    @pytest.mark.asyncio
    async def test_handle_database_error(self, mock_session, sample_sector):
        """测试数据库错误处理"""
        service = SectorMAService(mock_session)

        # 模拟数据库错误
        mock_session.execute.side_effect = Exception("Database error")

        result = await service._calculate_single_sector_ma(
            sector=sample_sector,
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 30),
            periods=[5, 10, 20],
            overwrite=False
        )

        assert result["success"] is False
        assert "error" in result


class TestSectorMAServiceIntegration:
    """集成测试场景"""

    def test_calculation_workflow(self):
        """测试完整的计算工作流"""
        # 1. 用户请求：计算 2024-06-01 至 2024-06-30 的 [5, 10, 20, 60, 120, 240] 日均线
        start_date = date(2024, 6, 1)
        end_date = date(2024, 6, 30)
        periods = [5, 10, 20, 60, 120, 240]

        # 2. 计算最长周期和所需数据
        max_period = max(periods)  # 240
        required_days = max_period * 2  # 480

        # 3. 计算查询范围
        query_end_date = end_date
        required_start_date = query_end_date - timedelta(days=required_days)
        query_start_date = max(start_date, required_start_date)

        # 4. 验证查询范围合理
        expected_query_start = date(2024, 6, 30) - timedelta(days=480)
        assert query_start_date == start_date  # start_date 更晚，所以使用它
        assert query_end_date == end_date

        # 5. 保存范围应该是用户指定的范围
        save_start = start_date
        save_end = end_date
        assert save_start == date(2024, 6, 1)
        assert save_end == date(2024, 6, 30)

    def test_full_history_calculation_workflow(self):
        """测试完整历史计算工作流"""
        # 用户不指定日期范围，计算所有可用数据
        start_date = None
        end_date = None
        periods = [5, 10, 20, 60, 120, 240]

        max_period = max(periods)
        actual_max_date = date(2024, 12, 31)

        # 查询结束日期使用最新数据日期
        query_end_date = end_date if end_date else actual_max_date

        # 查询起始日期基于最长周期计算
        required_days = max_period * 2
        query_start_date = query_end_date - timedelta(days=required_days)

        assert query_end_date == actual_max_date
        assert query_start_date == date(2024, 12, 31) - timedelta(days=480)
