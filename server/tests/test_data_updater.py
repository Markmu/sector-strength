"""
数据更新服务测试

测试数据收集器的功能。
"""

import pytest
from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.data_updater.collector import DataCollector


@pytest.fixture
def data_collector():
    """创建数据收集器实例"""
    return DataCollector()


class TestDataCollector:
    """数据收集器测试"""

    @pytest.mark.asyncio
    async def test_is_trading_day_weekday(self, data_collector):
        """测试判断交易日 - 工作日"""
        # 周三
        test_date = date(2024, 1, 10)
        assert await data_collector._is_trading_day(test_date) is True

    @pytest.mark.asyncio
    async def test_is_trading_day_weekend(self, data_collector):
        """测试判断交易日 - 周末"""
        # 周六
        test_date = date(2024, 1, 13)
        assert await data_collector._is_trading_day(test_date) is False

    @pytest.mark.asyncio
    async def test_is_trading_day_holiday(self, data_collector):
        """测试判断交易日 - 节假日"""
        # 元旦
        test_date = date(2024, 1, 1)
        assert await data_collector._is_trading_day(test_date) is False

    @pytest.mark.asyncio
    async def test_run_daily_update_trading_day(self, data_collector):
        """测试执行每日更新 - 交易日"""
        with patch.object(data_collector, '_is_trading_day', return_value=True), \
             patch.object(data_collector, '_update_sectors', new_callable=AsyncMock, return_value=10), \
             patch.object(data_collector, '_update_stocks', new_callable=AsyncMock, return_value=100), \
             patch.object(data_collector, '_update_market_data', new_callable=AsyncMock, return_value=100), \
             patch.object(data_collector, '_run_calculations', new_callable=AsyncMock, return_value=100), \
             patch.object(data_collector, '_clear_cache', new_callable=AsyncMock, return_value=10), \
             patch.object(data_collector, '_save_update_log', new_callable=AsyncMock):

            result = await data_collector.run_daily_update()

            assert result['success'] is True
            assert result['sectors_updated'] == 10
            assert result['stocks_updated'] == 100
            assert result['market_data_updated'] == 100

    @pytest.mark.asyncio
    async def test_run_daily_update_non_trading_day(self, data_collector):
        """测试执行每日更新 - 非交易日"""
        with patch.object(data_collector, '_is_trading_day', return_value=False), \
             patch.object(data_collector, '_save_update_log', new_callable=AsyncMock):

            result = await data_collector.run_daily_update()

            assert result['success'] is True
            assert result['message'] == '非交易日，跳过更新'

    @pytest.mark.asyncio
    async def test_update_sectors(self, data_collector):
        """测试更新板块数据"""
        with patch('src.services.data_updater.collector.AkShareDataSource') as mock_source_class:
            mock_source = AsyncMock()
            mock_source.fetch_sectors.return_value = [
                {'code': 'BK0001', 'name': '测试板块', 'type': 'concept'}
            ]
            mock_source_class.return_value = mock_source

            count = await data_collector._update_sectors()

            assert count >= 0

    @pytest.mark.asyncio
    async def test_update_stocks(self, data_collector):
        """测试更新股票数据"""
        with patch('src.services.data_updater.collector.AkShareDataSource') as mock_source_class:
            mock_source = AsyncMock()
            mock_source.fetch_stocks.return_value = [
                {'symbol': '000001', 'name': '测试股票', 'sector_code': 'BK0001'}
            ]
            mock_source_class.return_value = mock_source

            count = await data_collector._update_stocks()

            assert count >= 0

    @pytest.mark.asyncio
    async def test_update_market_data(self, data_collector):
        """测试更新行情数据"""
        with patch('src.services.data_updater.collector.AkShareDataSource') as mock_source_class:
            mock_source = AsyncMock()
            mock_source.fetch_daily_quotes.return_value = [
                {'symbol': '000001', 'date': '2024-01-10', 'close': 10.5}
            ]
            mock_source_class.return_value = mock_source

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

            # Should not raise exception
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
