"""
数据更新服务测试

测试数据收集器的功能。
"""

import pytest
from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.data_updater.collector import DataCollector
from src.services.data_acquisition.models import SectorInfo, StockInfo, DailyQuote


@pytest.fixture
def data_collector():
    """创建数据收集器实例，mock 数据源避免依赖真实 API"""
    with patch('src.services.data_updater.collector.DataSourceFactory') as mock_factory:
        mock_source = MagicMock()
        mock_factory.create.return_value = mock_source
        collector = DataCollector()
        collector._mock_source = mock_source
    return collector


class TestDataCollector:
    """数据收集器测试"""

    @pytest.mark.asyncio
    async def test_is_trading_day_weekday(self, data_collector):
        """测试判断交易日 - 工作日"""
        trading_days = [date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 10)]
        with patch.object(data_collector._trading_calendar, '_get_trading_days', new_callable=AsyncMock, return_value=trading_days):
            is_trading, reason = await data_collector._is_trading_day(date(2024, 1, 10))
        assert is_trading is True
        assert reason is None

    @pytest.mark.asyncio
    async def test_is_trading_day_weekend(self, data_collector):
        """测试判断交易日 - 周末"""
        trading_days = [date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 10)]
        with patch.object(data_collector._trading_calendar, '_get_trading_days', new_callable=AsyncMock, return_value=trading_days):
            is_trading, reason = await data_collector._is_trading_day(date(2024, 1, 13))
        assert is_trading is False
        assert reason == "周末"

    @pytest.mark.asyncio
    async def test_is_trading_day_holiday(self, data_collector):
        """测试判断交易日 - 节假日"""
        trading_days = [date(2024, 1, 2), date(2024, 1, 3)]
        with patch.object(data_collector._trading_calendar, '_get_trading_days', new_callable=AsyncMock, return_value=trading_days):
            is_trading, reason = await data_collector._is_trading_day(date(2024, 1, 1))
        assert is_trading is False
        assert reason == "节假日"

    @pytest.mark.asyncio
    async def test_run_daily_update_trading_day(self, data_collector):
        """测试执行每日更新 - 交易日（plan-05：本地日历守卫）"""
        cal_repo = MagicMock()
        cal_repo.refresh_range = AsyncMock(return_value=(1, 0))  # open_count=1 → 交易日
        with patch('src.services.data_updater.collector.TradingCalendarRepository', return_value=cal_repo), \
             patch.object(data_collector, '_update_sectors', new_callable=AsyncMock, return_value=10), \
             patch.object(data_collector, '_update_stocks', new_callable=AsyncMock, return_value=100), \
             patch.object(data_collector, '_update_market_data', new_callable=AsyncMock, return_value=100), \
             patch.object(data_collector, '_update_market_metrics', new_callable=AsyncMock, return_value=1), \
             patch.object(data_collector, '_run_calculations', new_callable=AsyncMock, return_value=100), \
             patch.object(data_collector, '_clear_cache', new_callable=AsyncMock, return_value=10), \
             patch.object(data_collector, '_update_sector_fund_flow', new_callable=AsyncMock, return_value=0), \
             patch.object(data_collector, '_update_etf_daily', new_callable=AsyncMock, return_value=0), \
             patch.object(data_collector, '_update_index_daily', new_callable=AsyncMock, return_value=0), \
             patch.object(data_collector, '_save_update_log', new_callable=AsyncMock):

            result = await data_collector.run_daily_update()

            assert result['success'] is True
            assert result['sectors_updated'] == 10
            assert result['stocks_updated'] == 100
            assert result['market_data_updated'] == 100
            assert result['market_metrics_updated'] == 1

    @pytest.mark.asyncio
    async def test_run_daily_update_non_trading_day(self, data_collector):
        """测试执行每日更新 - 非交易日（plan-05：open_count=0 → skipped，不调 Provider）"""
        cal_repo = MagicMock()
        cal_repo.refresh_range = AsyncMock(return_value=(0, 1))  # open_count=0 → 休市
        with patch('src.services.data_updater.collector.TradingCalendarRepository', return_value=cal_repo), \
             patch.object(data_collector, '_update_sectors', new_callable=AsyncMock) as mock_sectors, \
             patch.object(data_collector, '_update_market_metrics', new_callable=AsyncMock) as mock_metrics, \
             patch.object(data_collector, '_save_update_log', new_callable=AsyncMock):

            result = await data_collector.run_daily_update()

            assert result['success'] is True
            assert '跳过更新' in result['message']
            # 休市日不调后续 Provider 步骤（AC-09）
            mock_sectors.assert_not_awaited()
            mock_metrics.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_run_daily_update_calendar_refresh_failure_fails(self, data_collector):
        """日历刷新失败 → 日更失败，不用旧行冒充（AC-08）"""
        cal_repo = MagicMock()
        cal_repo.refresh_range = AsyncMock(side_effect=ValueError("日历校验失败"))
        with patch('src.services.data_updater.collector.TradingCalendarRepository', return_value=cal_repo), \
             patch.object(data_collector, '_update_sectors', new_callable=AsyncMock) as mock_sectors, \
             patch.object(data_collector, '_save_update_log', new_callable=AsyncMock):

            result = await data_collector.run_daily_update()

            assert result['success'] is False
            assert result['market_metrics_updated'] == 0
            mock_sectors.assert_not_awaited()  # 日历失败不继续后续步骤

    @pytest.mark.asyncio
    async def test_run_daily_update_metrics_failure_does_not_block(self, data_collector):
        """指标步骤失败 → errors 有记录、market_metrics_updated=0，不阻断 index 步骤（AC-08）"""
        cal_repo = MagicMock()
        cal_repo.refresh_range = AsyncMock(return_value=(1, 0))
        with patch('src.services.data_updater.collector.TradingCalendarRepository', return_value=cal_repo), \
             patch.object(data_collector, '_update_sectors', new_callable=AsyncMock, return_value=10), \
             patch.object(data_collector, '_update_stocks', new_callable=AsyncMock, return_value=100), \
             patch.object(data_collector, '_update_market_data', new_callable=AsyncMock, return_value=100), \
             patch.object(data_collector, '_update_market_metrics', new_callable=AsyncMock, side_effect=RuntimeError("指标失败")), \
             patch.object(data_collector, '_run_calculations', new_callable=AsyncMock, return_value=100), \
             patch.object(data_collector, '_clear_cache', new_callable=AsyncMock, return_value=10), \
             patch.object(data_collector, '_update_sector_fund_flow', new_callable=AsyncMock, return_value=0), \
             patch.object(data_collector, '_update_etf_daily', new_callable=AsyncMock, return_value=0), \
             patch.object(data_collector, '_update_index_daily', new_callable=AsyncMock, return_value=5) as mock_index, \
             patch.object(data_collector, '_save_update_log', new_callable=AsyncMock):

            result = await data_collector.run_daily_update()

            # 指标失败不阻断主流程
            assert result['success'] is True
            assert result['market_metrics_updated'] == 0
            assert any('market_metrics' in e for e in result['errors'])
            # index 步骤仍执行（不被指标失败阻断）
            mock_index.assert_awaited_once()
            assert result['index_daily_updated'] == 5

    @pytest.mark.asyncio
    async def test_update_sectors(self, data_collector):
        """测试更新板块数据"""
        data_collector._data_source.get_sector_list.return_value = [
            SectorInfo(code='BK0001', name='测试板块', type='concept')
        ]

        count = await data_collector._update_sectors()
        assert count >= 0

    @pytest.mark.asyncio
    async def test_update_stocks(self, data_collector):
        """测试更新股票生命周期数据（plan-05：调 build_lifecycle_snapshot，一次 preflight）"""
        from src.services.market_metrics_service import LifecycleSnapshot
        fake_snapshot = MagicMock(spec=LifecycleSnapshot)
        fake_snapshot.records = ("A", "B", "C")
        with patch('src.services.data_updater.collector.build_lifecycle_snapshot',
                   new_callable=AsyncMock, return_value=fake_snapshot) as mock_build:
            with patch('src.services.data_updater.collector.get_session') as mock_session_getter:
                mock_session = AsyncMock()
                mock_session_getter.return_value.__aenter__.return_value = mock_session

                count = await data_collector._update_stocks()

                assert count == 3
                assert data_collector._lifecycle_snapshot is fake_snapshot
                mock_build.assert_awaited_once()  # 生命周期 preflight 仅一次

    @pytest.mark.asyncio
    async def test_update_market_data(self, data_collector):
        """测试更新行情数据"""
        mock_quote = DailyQuote(
            symbol='000001',
            trade_date=date(2024, 1, 10),
            open=10.0, high=11.0, low=9.5, close=10.5, volume=1000.0
        )
        mock_sector = MagicMock()
        mock_sector.id = 1
        mock_sector.code = 'BK0001'
        mock_sector.name = '测试板块'
        mock_sector.type = 'concept'
        mock_stock = MagicMock()
        mock_stock.id = 1
        mock_stock.symbol = '000001'

        data_collector._data_source.get_sector_daily_data.return_value = []
        data_collector._data_source.get_daily_data.return_value = [mock_quote]

        with patch('src.services.data_updater.collector.get_session') as mock_session_getter:
            mock_session = AsyncMock()
            sector_result = MagicMock()
            sector_result.scalars.return_value.all.return_value = [mock_sector]
            stock_result = MagicMock()
            stock_result.scalars.return_value.all.return_value = [mock_stock]
            # First 2 calls: sector/stock queries; rest: insert statements (return value unused)
            mock_session.execute.side_effect = [sector_result, stock_result] + [MagicMock()] * 10
            mock_session_getter.return_value.__aenter__.return_value = mock_session

            count = await data_collector._update_market_data()

            assert count >= 0

    @pytest.mark.asyncio
    async def test_run_calculations(self, data_collector):
        """测试运行计算任务"""
        with patch('src.services.data_updater.collector.CalculationOrchestrator') as mock_orchestrator_class:
            mock_orchestrator = AsyncMock()
            mock_orchestrator.run_all_calculations.return_value = 110
            mock_orchestrator_class.return_value = mock_orchestrator

            count = await data_collector._run_calculations()

            assert count == 110

    @pytest.mark.asyncio
    async def test_clear_cache(self, data_collector):
        """测试清除缓存"""
        with patch('src.services.data_updater.collector.get_cache_manager') as mock_get_cache:
            mock_cache = AsyncMock()
            mock_cache.clear_all.return_value = 50
            mock_get_cache.return_value = mock_cache

            count = await data_collector._clear_cache()

            assert count == 50

    @pytest.mark.asyncio
    async def test_save_update_log(self, data_collector):
        """测试保存更新日志"""
        log_data = {
            'success': True,
            'sectors_updated': 10,
            'stocks_updated': 100,
            'market_data_updated': 100,
            'entities_calculated': 110,
            'cache_cleared': 50,
        }

        with patch('src.services.data_updater.collector.get_session') as mock_session_getter:
            mock_session = AsyncMock()
            mock_session_getter.return_value.__aenter__.return_value = mock_session

            await data_collector._save_update_log(log_data)

    @pytest.mark.asyncio
    async def test_get_latest_update_status(self, data_collector):
        """测试获取最新更新状态"""
        with patch('src.services.data_updater.collector.get_session') as mock_session_getter:
            mock_session = AsyncMock()
            mock_session_getter.return_value.__aenter__.return_value = mock_session

            mock_log = MagicMock()
            mock_log.success = True
            mock_log.sectors_updated = 10
            mock_log.stocks_updated = 100
            mock_log.started_at = datetime.now()
            mock_log.completed_at = datetime.now()
            mock_session.scalar.return_value = mock_log

            status = await data_collector.get_latest_update_status()

            assert status is not None
            assert status['success'] is True

    @pytest.mark.asyncio
    async def test_get_latest_update_status_no_logs(self, data_collector):
        """测试获取最新更新状态 - 无记录"""
        with patch('src.services.data_updater.collector.get_session') as mock_session_getter:
            mock_session = AsyncMock()
            mock_session_getter.return_value.__aenter__.return_value = mock_session
            mock_session.scalar.return_value = None

            status = await data_collector.get_latest_update_status()

            assert status is None

    @pytest.mark.asyncio
    async def test_get_update_history(self, data_collector):
        """测试获取更新历史"""
        with patch('src.services.data_updater.collector.get_session') as mock_session_getter:
            mock_session = AsyncMock()
            mock_session_getter.return_value.__aenter__.return_value = mock_session

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = []
            mock_session.execute.return_value = mock_result

            history = await data_collector.get_update_history(1, 20)

            assert history is not None
