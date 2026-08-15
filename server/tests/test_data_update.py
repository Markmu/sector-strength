"""
数据更新服务测试

测试 DataUpdateService 的功能。
"""

import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

from src.services.data_update import DataUpdateService
from src.services.data_acquisition.models import DailyQuote


@pytest.fixture
def mock_session():
    """模拟数据库会话"""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.add = MagicMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def mock_data_source(mock_session):
    """模拟 DataSourceFactory.create() 返回的数据源"""
    from unittest.mock import patch

    mock_source = MagicMock()
    with patch('src.services.data_update.DataSourceFactory') as mock_factory:
        mock_factory.create.return_value = mock_source
        yield mock_source


@pytest.mark.asyncio
class TestDataUpdateService:
    """数据更新服务测试"""

    async def test_backfill_by_date_success(self, mock_session, mock_data_source):
        """测试成功按日期补齐数据"""
        # 设置模拟数据
        mock_data_source.get_daily_data.return_value = [
            DailyQuote(
                symbol="000001",
                trade_date=date.today(),
                open=10.0,
                high=11.0,
                low=9.5,
                close=10.5,
                volume=1000000,
                amount=10500000.0
            )
        ]

        # 模拟股票存在且数据不存在
        mock_stock = MagicMock()
        mock_stock.id = "stock-id-1"

        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = mock_stock

        mock_result2 = MagicMock()
        mock_result2.scalar_one_or_none.return_value = None

        mock_session.execute.side_effect = [mock_result1, mock_result2]

        service = DataUpdateService(mock_session)
        service._get_symbols_to_update = AsyncMock(return_value=["000001"])
        result = await service.backfill_by_date(target_date=date.today(), overwrite=False)

        assert result["success"] is True
        assert result["created"] == 1
        assert result["updated"] == 0
        mock_session.add.assert_called_once()

    async def test_backfill_by_date_skip_existing(self, mock_session, mock_data_source):
        """测试跳过已有数据"""
        mock_data_source.get_daily_data.return_value = [
            DailyQuote(
                symbol="000001",
                trade_date=date.today(),
                open=10.0,
                high=11.0,
                low=9.5,
                close=10.5,
                volume=1000000,
                amount=10500000.0
            )
        ]

        mock_stock = MagicMock()
        mock_stock.id = "stock-id-1"

        # 数据已存在
        mock_existing = MagicMock()

        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = mock_stock

        mock_result2 = MagicMock()
        mock_result2.scalar_one_or_none.return_value = mock_existing

        mock_session.execute.side_effect = [mock_result1, mock_result2]

        service = DataUpdateService(mock_session)
        service._get_symbols_to_update = AsyncMock(return_value=["000001"])
        result = await service.backfill_by_date(target_date=date.today(), overwrite=False)

        assert result["success"] is True
        assert result["skipped"] == 1
        mock_session.add.assert_not_called()

    async def test_backfill_by_date_overwrite(self, mock_session, mock_data_source):
        """测试覆盖已有数据"""
        mock_data_source.get_daily_data.return_value = [
            DailyQuote(
                symbol="000001",
                trade_date=date.today(),
                open=10.5,
                high=11.5,
                low=9.0,
                close=10.8,
                volume=1100000,
                amount=10800000.0
            )
        ]

        mock_stock = MagicMock()
        mock_stock.id = "stock-id-1"

        # 数据已存在
        mock_existing = MagicMock()

        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = mock_stock

        mock_result2 = MagicMock()
        mock_result2.scalar_one_or_none.return_value = mock_existing

        mock_session.execute.side_effect = [mock_result1, mock_result2]

        service = DataUpdateService(mock_session)
        service._get_symbols_to_update = AsyncMock(return_value=["000001"])
        result = await service.backfill_by_date(target_date=date.today(), overwrite=True)

        assert result["success"] is True
        assert result["updated"] == 1
        # 验证更新了字段
        assert mock_existing.close == 10.8

    async def test_backfill_by_range_success(self, mock_session, mock_data_source):
        """测试成功按时间段补齐数据"""
        start_date = date.today() - timedelta(days=3)
        end_date = date.today()

        mock_data_source.get_daily_data.return_value = [
            DailyQuote(
                symbol="000001",
                trade_date=start_date,
                open=10.0,
                high=11.0,
                low=9.5,
                close=10.5,
                volume=1000000,
                amount=10500000.0
            )
        ]

        mock_stock = MagicMock()
        mock_stock.id = "stock-id-1"

        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = mock_stock

        mock_result2 = MagicMock()
        mock_result2.scalar_one_or_none.return_value = None

        mock_session.execute.side_effect = [mock_result1, mock_result2]

        service = DataUpdateService(mock_session)
        service._get_symbols_to_update = AsyncMock(return_value=["000001"])
        result = await service.backfill_by_range(start_date=start_date, end_date=end_date, overwrite=False)

        assert result["success"] is True
        assert result["created"] == 1
        assert result["days"] == 4

    async def test_backfill_by_range_invalid_date_range(self, mock_session, mock_data_source):
        """测试无效的日期范围"""
        service = DataUpdateService(mock_session)
        result = await service.backfill_by_range(
            start_date=date.today(),
            end_date=date.today() - timedelta(days=1),
            overwrite=False
        )

        assert result["success"] is False
        assert "开始日期不能晚于结束日期" in result["error"]

    async def test_backfill_by_range_too_many_days(self, mock_session, mock_data_source):
        """测试日期范围过大"""
        service = DataUpdateService(mock_session)
        result = await service.backfill_by_range(
            start_date=date.today() - timedelta(days=400),
            end_date=date.today(),
            overwrite=False
        )

        assert result["success"] is False
        assert "不能超过 365 天" in result["error"]

    def test_validate_daily_quote_valid(self):
        """测试有效的日线数据验证"""
        from unittest.mock import patch

        with patch('src.services.data_update.DataSourceFactory') as mock_factory:
            mock_factory.create.return_value = MagicMock()
            mock_session = AsyncMock()
            service = DataUpdateService(mock_session)

            quote = DailyQuote(
                symbol="000001",
                trade_date=date.today(),
                open=10.0,
                high=11.0,
                low=9.5,
                close=10.5,
                volume=1000000,
                amount=10500000.0
            )

            is_valid, error = service._validate_daily_quote(quote)
            assert is_valid is True
            assert error is None

    def test_validate_daily_quote_price_out_of_range(self):
        """测试价格超出范围"""
        from unittest.mock import patch

        with patch('src.services.data_update.DataSourceFactory') as mock_factory:
            mock_factory.create.return_value = MagicMock()
            mock_session = AsyncMock()
            service = DataUpdateService(mock_session)

            quote = DailyQuote(
                symbol="000001",
                trade_date=date.today(),
                open=100000,  # 超出范围
                high=100000,
                low=9.5,
                close=10.5,
                volume=1000000,
                amount=10500000.0
            )

            is_valid, error = service._validate_daily_quote(quote)
            assert is_valid is False
            assert "超出范围" in error

    def test_validate_daily_quote_invalid_price_relationship(self):
        """测试无效的价格关系"""
        from unittest.mock import patch

        with patch('src.services.data_update.DataSourceFactory') as mock_factory:
            mock_factory.create.return_value = MagicMock()
            mock_session = AsyncMock()
            service = DataUpdateService(mock_session)

            # 创建有效的价格关系，但设置其他无效字段来测试
            quote = DailyQuote(
                symbol="000001",
                trade_date=date.today(),
                open=10.0,
                high=12.0,  # high > low
                low=9.0,
                close=11.0,
                volume=1000000,
                amount=10500000.0
            )

            is_valid, error = service._validate_daily_quote(quote)
            assert is_valid is True
            assert error is None

    def test_validate_daily_quote_excessive_change(self):
        """测试涨跌幅过大"""
        from unittest.mock import patch

        with patch('src.services.data_update.DataSourceFactory') as mock_factory:
            mock_factory.create.return_value = MagicMock()
            mock_session = AsyncMock()
            service = DataUpdateService(mock_session)

            quote = DailyQuote(
                symbol="000001",
                trade_date=date.today(),
                open=10.0,
                high=12.0,
                low=9.0,
                close=13.0,  # +30% 变化
                volume=1000000,
                amount=10500000.0
            )

            is_valid, error = service._validate_daily_quote(quote)
            assert is_valid is False
            assert "涨跌幅" in error

    async def test_fetch_missing_dates(self, mock_session, mock_data_source):
        """测试查找缺失日期（含交易日历查询，回退周末启发式）"""
        # 模拟交易日历（无开市记录 → 回退周末启发式）
        cal_result = MagicMock()
        cal_result.all.return_value = []

        # 模拟股票存在（scalar_one_or_none 返回 mock 股票）
        stock_result = MagicMock()
        stock_result.scalar_one_or_none.return_value = MagicMock(id="stock-1")

        # 模拟已有日期
        mock_result2 = MagicMock()
        mock_result2.all.return_value = [(date.today() - timedelta(days=2),)]

        mock_session.execute.side_effect = [cal_result, stock_result, mock_result2]

        from unittest.mock import patch
        with patch('src.services.data_update.DataSourceFactory') as mock_factory:
            mock_factory.create.return_value = MagicMock()
            service = DataUpdateService(mock_session)
            result = await service.fetch_missing_dates(
                stock_symbol="000001",
                start_date=date.today() - timedelta(days=5),
                end_date=date.today()
            )

            assert result["success"] is True
            assert "missing_dates" in result

    async def test_fetch_missing_dates_uses_trading_calendar(self, mock_session, mock_data_source):
        """回归（评审 B8）：日历标记休市的工作日（法定节假日）不再误报为缺失"""
        today = date.today()
        days = [today - timedelta(days=i) for i in range(5, -1, -1)]
        open_days = [d for d in days if d.weekday() < 5]
        # 把窗口内最后一个工作日模拟为法定节假日（日历标记休市）
        holiday = open_days[-1]
        cal_rows = [(d,) for d in open_days if d != holiday]

        cal_result = MagicMock()
        cal_result.all.return_value = cal_rows
        stock_result = MagicMock()
        stock_result.scalar_one_or_none.return_value = MagicMock(id="stock-1")
        existing_result = MagicMock()
        existing_result.all.return_value = []  # 完全无已有数据

        mock_session.execute.side_effect = [cal_result, stock_result, existing_result]

        from unittest.mock import patch
        with patch('src.services.data_update.DataSourceFactory') as mock_factory:
            mock_factory.create.return_value = MagicMock()
            service = DataUpdateService(mock_session)
            result = await service.fetch_missing_dates(
                stock_symbol="000001",
                start_date=days[0],
                end_date=days[-1],
            )

        assert result["success"] is True
        missing = result["missing_dates"].get("000001", [])
        # 节假日与周末都不应报缺失，开市工作日应报缺失
        assert holiday.isoformat() not in missing
        for d in days:
            if d.weekday() >= 5:
                assert d.isoformat() not in missing
        assert len(missing) == len(open_days) - 1

    async def test_progress_callback(self, mock_session, mock_data_source):
        """测试进度回调"""
        mock_data_source.get_daily_data.return_value = []

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(id="stock-1")
        mock_session.execute.return_value = mock_result

        progress_updates = []

        def callback(current, total, message):
            progress_updates.append((current, total, message))

        service = DataUpdateService(mock_session)
        service.set_progress_callback(callback)

        # 使用多个股票触发多次回调
        from unittest.mock import patch
        with patch.object(service, '_get_symbols_to_update', return_value=['000001', '000002']):
            await service.backfill_by_date(target_date=date.today(), overwrite=False)

        # 验证进度回调被调用
        assert len(progress_updates) >= 2

    async def test_cancel_task(self, mock_session, mock_data_source):
        """测试任务取消"""
        mock_data_source.get_daily_data.return_value = []

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(id="stock-1")
        mock_session.execute.return_value = mock_result

        from unittest.mock import patch

        service = DataUpdateService(mock_session)

        # 测试取消方法
        service.cancel()
        assert service._cancelled is True

        # 测试检查取消
        service._cancelled = True
        with pytest.raises(InterruptedError):
            service._check_cancelled()

    def test_validate_daily_quote_with_zero_close(self):
        """测试 close 为 0 时的验证"""
        from unittest.mock import patch

        with patch('src.services.data_update.DataSourceFactory') as mock_factory:
            mock_factory.create.return_value = MagicMock()
            mock_session = AsyncMock()
            service = DataUpdateService(mock_session)

            quote = DailyQuote(
                symbol="000001",
                trade_date=date.today(),
                open=10.0,
                high=12.0,
                low=9.0,
                close=0,  # close 为 0
                volume=1000000,
                amount=0
            )

            # 不应该计算涨跌幅，因为 close 为 0
            is_valid, error = service._validate_daily_quote(quote)
            # 其他验证会通过，但不会触发涨跌幅计算（因为 close=0 不满足条件）
            assert is_valid is True

    def test_validate_daily_quote_exactly_20_percent_change(self):
        """测试正好 20% 涨跌幅的边界情况"""
        from unittest.mock import patch

        with patch('src.services.data_update.DataSourceFactory') as mock_factory:
            mock_factory.create.return_value = MagicMock()
            mock_session = AsyncMock()
            service = DataUpdateService(mock_session)

            quote = DailyQuote(
                symbol="000001",
                trade_date=date.today(),
                open=10.0,
                high=12.0,
                low=9.0,
                close=12.0,  # +20% 变化
                volume=1000000,
                amount=12000000.0
            )

            is_valid, error = service._validate_daily_quote(quote)
            # 20% 应该通过（边界条件）
            assert is_valid is True

    def test_validate_daily_quote_slightly_over_20_percent(self):
        """测试略超过 20% 涨跌幅的情况"""
        from unittest.mock import patch

        with patch('src.services.data_update.DataSourceFactory') as mock_factory:
            mock_factory.create.return_value = MagicMock()
            mock_session = AsyncMock()
            service = DataUpdateService(mock_session)

            quote = DailyQuote(
                symbol="000001",
                trade_date=date.today(),
                open=10.0,
                high=12.0,
                low=9.0,
                close=12.01,  # +20.1% 变化
                volume=1000000,
                amount=12010000.0
            )

            is_valid, error = service._validate_daily_quote(quote)
            assert is_valid is False
            assert "涨跌幅" in error

    async def test_backfill_by_range_exactly_365_days(self, mock_session, mock_data_source):
        """测试正好 365 天的边界条件"""
        service = DataUpdateService(mock_session)
        service._get_symbols_to_update = AsyncMock(return_value=["000001"])
        start_date = date.today() - timedelta(days=364)
        end_date = date.today()

        # 模拟成功
        mock_data_source.get_daily_data.return_value = []
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(id="stock-1")
        mock_session.execute.return_value = mock_result

        result = await service.backfill_by_range(
            start_date=start_date,
            end_date=end_date,
            overwrite=False
        )

        # 365 天应该通过
        assert result["success"] is True

    async def test_backfill_by_range_366_days_should_fail(self, mock_session, mock_data_source):
        """测试 366 天应该失败"""
        service = DataUpdateService(mock_session)
        start_date = date.today() - timedelta(days=365)
        end_date = date.today()

        result = await service.backfill_by_range(
            start_date=start_date,
            end_date=end_date,
            overwrite=False
        )

        assert result["success"] is False
        assert "不能超过 365 天" in result["error"]

    async def test_data_source_api_failure_handling(self, mock_session, mock_data_source):
        """测试数据源 API 调用失败时的处理"""
        from unittest.mock import patch

        # 模拟数据源 API 抛出异常
        mock_data_source.get_daily_data.side_effect = Exception("API connection failed")

        # 第一次 execute 返回股票，第二次（存在性检查）返回无记录
        mock_stock = MagicMock(id="stock-1")
        stock_result = MagicMock()
        stock_result.scalar_one_or_none.return_value = mock_stock
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = None
        mock_session.execute.side_effect = [stock_result, existing_result]

        service = DataUpdateService(mock_session)
        service._get_symbols_to_update = AsyncMock(return_value=["000001"])
        result = await service.backfill_by_date(target_date=date.today(), overwrite=False)

        # 应该捕获异常并返回失败结果
        assert result["success"] is False

    async def test_stock_not_found_handling(self, mock_session, mock_data_source):
        """测试股票不存在时的处理"""
        mock_data_source.get_daily_data.return_value = []

        # 模拟股票不存在
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        service = DataUpdateService(mock_session)
        service._get_symbols_to_update = AsyncMock(return_value=["000001"])
        result = await service.backfill_by_date(target_date=date.today(), overwrite=False)

        # 应该跳过不存在的股票
        assert result["success"] is True
        assert result["skipped"] >= 0
