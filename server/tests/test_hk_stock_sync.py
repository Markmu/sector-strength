"""
港股基础信息同步测试

覆盖「初始化股票增加港股同步（hk_basic）」的核心与防护改动：
1. StockInfo exchange 校验：接受 HKEX、拒绝非 A 股/港股交易所
2. init_stocks 合并拉取 A 股 + 港股（统计 hk_created）
3. 港股拉取失败不阻断 A 股
4. 实表：init_historical_data / _get_symbols_to_update 仅处理 A 股（防护 B）
5. 实表：rankings/strength 的 exchange 过滤排除港股（防护 C）
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from datetime import date
from sqlalchemy import select

from src.models.stock import Stock
from src.services.data_acquisition.models import A_STOCK_EXCHANGES, StockInfo
from src.services.data_init import DataInitService
from src.services.data_update import DataUpdateService


# ============ 1. exchange 校验（纯单测）============

def test_exchange_validator_accepts_hkex():
    """StockInfo.exchange 接受 HKEX（港股）"""
    s = StockInfo(symbol="00700", name="腾讯控股", ts_code="00700.HK", exchange="HKEX")
    assert s.exchange == "HKEX"


def test_exchange_validator_rejects_foreign_exchange():
    """StockInfo.exchange 拒绝非 A 股/港股交易所（如 NYSE）"""
    with pytest.raises(Exception):
        StockInfo(symbol="99999", name="x", exchange="NYSE")


# ============ fixtures：纯 mock（对齐 test_data_init.py）============

@pytest.fixture
def mock_session():
    """模拟数据库会话"""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def mock_data_source(mock_session):
    """模拟 DataSourceFactory.create() 返回的数据源"""
    mock_source = MagicMock()
    with patch('src.services.data_init.DataSourceFactory') as mock_factory:
        mock_factory.create.return_value = mock_source
        yield mock_source


# ============ 2-3. init_stocks 合并港股（纯 mock）============

@pytest.mark.asyncio
class TestInitStocksWithHK:
    """init_stocks 同时拉取 A 股 + 港股"""

    async def test_init_stocks_includes_hk(self, mock_session, mock_data_source):
        """init_stocks 合并 A 股 + 港股，统计 hk_created / hk_total"""
        mock_data_source.get_stock_list.return_value = [
            StockInfo(symbol="000001", name="平安银行", exchange="SZSE"),
        ]
        mock_data_source.get_hk_stock_list.return_value = [
            StockInfo(symbol="00700", name="腾讯控股", ts_code="00700.HK", exchange="HKEX"),
            StockInfo(symbol="00005", name="汇丰控股", ts_code="00005.HK", exchange="HKEX"),
        ]
        # 全部新增
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        service = DataInitService(mock_session)
        result = await service.init_stocks()

        assert result["success"] is True
        assert result["created"] == 3          # 1 A 股 + 2 港股
        assert result["hk_created"] == 2
        assert result["hk_total"] == 2
        assert result["total"] == 3
        mock_data_source.get_stock_list.assert_called_once()
        mock_data_source.get_hk_stock_list.assert_called_once()
        assert mock_session.add.call_count == 3

    async def test_init_stocks_hk_failure_does_not_block_a(self, mock_session, mock_data_source):
        """港股拉取失败不影响 A 股初始化"""
        mock_data_source.get_stock_list.return_value = [
            StockInfo(symbol="000001", name="平安银行", exchange="SZSE"),
            StockInfo(symbol="600000", name="浦发银行", exchange="SSE"),
        ]
        mock_data_source.get_hk_stock_list.side_effect = RuntimeError("hk_basic 不可用")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        service = DataInitService(mock_session)
        result = await service.init_stocks()

        assert result["success"] is True
        assert result["created"] == 2          # A 股照常入库
        assert result["hk_created"] == 0
        assert result["hk_total"] == 0
        mock_data_source.get_stock_list.assert_called_once()


# ============ 4-5. 实表：下游防护（防护 B + C）============

@pytest.mark.asyncio
class TestDownstreamIsolation:
    """实表验证：港股入库后不污染 A 股下游流程"""

    async def test_get_symbols_to_update_excludes_hk(self, test_session):
        """DataUpdateService._get_symbols_to_update 只返回 A 股（防护 B）"""
        test_session.add(Stock(symbol="000001", name="平安银行", exchange="SZSE", ts_code="000001.SZ"))
        test_session.add(Stock(symbol="00700", name="腾讯控股", exchange="HKEX", ts_code="00700.HK"))
        await test_session.commit()

        svc = DataUpdateService(test_session)
        symbols = await svc._get_symbols_to_update(None, None)

        assert "000001" in symbols
        assert "00700" not in symbols

    async def test_init_historical_excludes_hk(self, test_session, monkeypatch):
        """init_historical_data 仅拉取 A 股行情，不为港股请求 daily（防护 B）"""
        test_session.add(Stock(symbol="000001", name="平安银行", exchange="SZSE", ts_code="000001.SZ"))
        test_session.add(Stock(symbol="00700", name="腾讯控股", exchange="HKEX", ts_code="00700.HK"))
        await test_session.commit()

        called_symbols: list = []

        def fake_get_daily_data(symbol, *args, **kwargs):
            called_symbols.append(symbol)
            return []

        mock_source = MagicMock()
        mock_source.get_daily_data = MagicMock(side_effect=fake_get_daily_data)
        monkeypatch.setattr(
            "src.services.data_init.DataSourceFactory.create", lambda: mock_source
        )

        service = DataInitService(test_session)
        await service.init_historical_data(days=5)

        assert "000001" in called_symbols
        assert "00700" not in called_symbols

    async def test_rankings_strength_filter_excludes_hk(self, test_session):
        """rankings/strength 的 exchange 过滤能排除港股（防护 C）

        港股 strength_score 默认 0（非 NULL），会穿透 isnot(None)；
        必须靠 exchange 过滤排除。
        """
        # A 股有强度，港股默认强度 0
        test_session.add(Stock(symbol="000001", name="平安银行", exchange="SZSE", strength_score=80))
        test_session.add(Stock(symbol="00700", name="腾讯控股", exchange="HKEX", strength_score=0))
        await test_session.commit()

        # 仅 isnot(None)：港股（0）会穿透 —— 说明问题确实存在
        no_filter = await test_session.execute(
            select(Stock.symbol).where(Stock.strength_score.isnot(None))
        )
        no_filter_symbols = {r[0] for r in no_filter.all()}
        assert "000001" in no_filter_symbols
        assert "00700" in no_filter_symbols

        # 叠加 exchange 过滤（rankings/strength 的新条件）：排除港股
        with_filter = await test_session.execute(
            select(Stock.symbol).where(
                Stock.strength_score.isnot(None),
                Stock.exchange.in_(A_STOCK_EXCHANGES),
            )
        )
        with_filter_symbols = {r[0] for r in with_filter.all()}
        assert "000001" in with_filter_symbols
        assert "00700" not in with_filter_symbols


@pytest.mark.asyncio
class TestSetDiffCleanup:
    """init_stocks set-diff 清理：删除数据源已消失的股票 + 级联 + 误删防护"""

    async def test_cleanup_deletes_disappeared_with_cascade(self, test_session, monkeypatch):
        """数据源消失的股票被删除，衍生数据级联清理"""
        from src.models.stock_daily_market_data import StockDailyMarketData
        from src.models.sector_stock import SectorStock

        # 000001 保留、000638 数据源不再返回（退市）
        s_keep = Stock(symbol="000001", name="平安银行", exchange="SZSE")
        s_del = Stock(symbol="000638", name="*ST万方", exchange="SZSE")
        test_session.add_all([s_keep, s_del])
        await test_session.flush()  # 拿 id

        # 衍生数据（应随 000638 级联删除）
        # 股票行情已迁入独立表 StockDailyMarketData（无 entity_type，按 stock_id 软关联）
        test_session.add(StockDailyMarketData(
            stock_id=s_del.id, symbol="000638", date=date(2026, 1, 1)
        ))
        test_session.add(SectorStock(sector_code="BK0001", stock_code="000638"))
        await test_session.commit()

        mock = MagicMock()
        mock.get_stock_list.return_value = [
            StockInfo(symbol="000001", name="平安银行", exchange="SZSE"),
        ]
        mock.get_hk_stock_list.return_value = []
        monkeypatch.setattr("src.services.data_init.DataSourceFactory.create", lambda: mock)

        result = await DataInitService(test_session).init_stocks()

        assert result["success"] is True
        assert "000638" in result["deleted"]
        assert "000001" not in result["deleted"]

        # stocks 表：000001 保留、000638 删除
        syms = {r[0] for r in (await test_session.execute(select(Stock.symbol))).all()}
        assert "000001" in syms
        assert "000638" not in syms
        # 衍生数据级联删（_cascade_delete_stock_data 按 stock_id 清新三表 / 按 stock_code 清 sector_stocks）
        dmd = (await test_session.execute(
            select(StockDailyMarketData).where(StockDailyMarketData.stock_id == s_del.id)
        )).scalars().all()
        assert len(dmd) == 0
        ss = (await test_session.execute(
            select(SectorStock).where(SectorStock.stock_code == "000638")
        )).scalars().all()
        assert len(ss) == 0

    async def test_cleanup_sanity_check_blocks_mass_delete(self, test_session, monkeypatch):
        """待删超过 5% 阈值时拒绝删除（防数据源返回不完整导致误删）"""
        # 插入 110 只 A 股
        test_session.add_all([
            Stock(symbol=f"3000{i:03d}", name=f"s{i}", exchange="SZSE") for i in range(110)
        ])
        await test_session.commit()

        # 数据源只返回前 50 只 → 待删 60 只 > 110*5%=5.5，触发阈值
        mock = MagicMock()
        mock.get_stock_list.return_value = [
            StockInfo(symbol=f"3000{i:03d}", name=f"s{i}", exchange="SZSE") for i in range(50)
        ]
        mock.get_hk_stock_list.return_value = []
        monkeypatch.setattr("src.services.data_init.DataSourceFactory.create", lambda: mock)

        result = await DataInitService(test_session).init_stocks()

        assert result["success"] is True
        assert result["deleted_count"] == 0
        assert len(result["cleanup_errors"]) > 0
        # 库里股票全部保留
        cnt = (await test_session.execute(
            select(Stock.symbol).where(Stock.exchange == "SZSE")
        )).all()
        assert len(cnt) == 110

    async def test_cleanup_skips_hk_when_fetch_fails(self, test_session, monkeypatch):
        """港股拉取失败时不删除港股（避免误删全部港股）"""
        test_session.add(Stock(symbol="00700", name="腾讯控股", exchange="HKEX", ts_code="00700.HK"))
        await test_session.commit()

        mock = MagicMock()
        mock.get_stock_list.return_value = []
        mock.get_hk_stock_list.side_effect = RuntimeError("hk 不可用")
        monkeypatch.setattr("src.services.data_init.DataSourceFactory.create", lambda: mock)

        result = await DataInitService(test_session).init_stocks()

        assert result["success"] is True
        assert "00700" not in result["deleted"]
        hk = (await test_session.execute(
            select(Stock.symbol).where(Stock.exchange == "HKEX")
        )).all()
        assert len(hk) == 1
