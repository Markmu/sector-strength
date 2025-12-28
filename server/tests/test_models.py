"""
数据库模型单元测试

测试所有数据模型的基本功能。
"""

import pytest
from datetime import date, datetime
import sys
from pathlib import Path

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from models.base import Base
from models.sector import Sector
from models.stock import Stock
from models.sector_stock import SectorStock
from models.period_config import PeriodConfig
from models.daily_market_data import DailyMarketData
from models.moving_average_data import MovingAverageData
from models.cache import CacheEntry
from models.update_log import DataUpdateLog


class TestSectorModel:
    """板块模型测试"""

    def test_create_sector(self):
        """测试创建板块"""
        sector = Sector(
            name="银行",
            code="BK0001",
            type="industry",
            description="银行业板块",
        )
        assert sector.name == "银行"
        assert sector.code == "BK0001"
        assert sector.type == "industry"
        assert sector.description == "银行业板块"
        # Note: default=0 only applies at database level, not Python object creation
        # sector.strength_score will be None until persisted to database

    def test_sector_repr(self):
        """测试板块字符串表示"""
        sector = Sector(id=1, name="银行", code="BK0001", type="industry")
        assert "Sector" in repr(sector)
        assert "银行" in repr(sector)


class TestStockModel:
    """股票模型测试"""

    def test_create_stock(self):
        """测试创建股票"""
        stock = Stock(
            symbol="000001",
            name="平安银行",
            current_price=10.5,
            market_cap=1000000000,
        )
        assert stock.symbol == "000001"
        assert stock.name == "平安银行"
        assert stock.current_price == 10.5
        assert stock.market_cap == 1000000000

    def test_stock_repr(self):
        """测试股票字符串表示"""
        stock = Stock(id=1, symbol="000001", name="平安银行")
        assert "Stock" in repr(stock)
        assert "000001" in repr(stock)


class TestSectorStockModel:
    """板块-股票关联模型测试"""

    def test_create_sector_stock(self):
        """测试创建关联"""
        sector_stock = SectorStock(
            sector_id=1,
            stock_id=1,
        )
        assert sector_stock.sector_id == 1
        assert sector_stock.stock_id == 1

    def test_sector_stock_repr(self):
        """测试关联字符串表示"""
        sector_stock = SectorStock(sector_id=1, stock_id=1)
        assert "SectorStock" in repr(sector_stock)


class TestPeriodConfigModel:
    """周期配置模型测试"""

    def test_create_period_config(self):
        """测试创建周期配置"""
        config = PeriodConfig(
            period="5d",
            name="5日均线",
            days=5,
            weight=0.15,
            is_active=True,
        )
        assert config.period == "5d"
        assert config.name == "5日均线"
        assert config.days == 5
        assert config.weight == 0.15
        assert config.is_active is True

    def test_period_config_repr(self):
        """测试周期配置字符串表示"""
        config = PeriodConfig(
            id=1, period="5d", name="5日均线", days=5, weight=0.15
        )
        assert "PeriodConfig" in repr(config)
        assert "5d" in repr(config)


class TestDailyMarketDataModel:
    """日线行情数据模型测试"""

    def test_create_daily_market_data(self):
        """测试创建日线行情数据"""
        data = DailyMarketData(
            entity_type="stock",
            entity_id=1,
            date=date(2024, 1, 1),
            open=10.0,
            high=10.5,
            low=9.8,
            close=10.3,
            volume=1000000,
            turnover=15.5,
            change=0.3,
            change_percent=3.0,
        )
        assert data.entity_type == "stock"
        assert data.entity_id == 1
        assert data.date == date(2024, 1, 1)
        assert data.open == 10.0
        assert data.high == 10.5
        assert data.low == 9.8
        assert data.close == 10.3
        assert data.volume == 1000000
        assert data.turnover == 15.5
        assert data.change == 0.3
        assert data.change_percent == 3.0

    def test_daily_market_data_repr(self):
        """测试日线数据字符串表示"""
        data = DailyMarketData(
            entity_type="stock",
            entity_id=1,
            date=date(2024, 1, 1),
        )
        assert "DailyMarketData" in repr(data)


class TestMovingAverageDataModel:
    """均线数据模型测试"""

    def test_create_moving_average_data(self):
        """测试创建均线数据"""
        ma_data = MovingAverageData(
            entity_type="stock",
            entity_id=1,
            date=date(2024, 1, 1),
            period="5d",
            ma_value=10.2,
            price_ratio=1.02,
            trend=1,
        )
        assert ma_data.entity_type == "stock"
        assert ma_data.entity_id == 1
        assert ma_data.period == "5d"
        assert ma_data.ma_value == 10.2
        assert ma_data.price_ratio == 1.02
        assert ma_data.trend == 1

    def test_moving_average_data_repr(self):
        """测试均线数据字符串表示"""
        ma_data = MovingAverageData(
            entity_type="stock",
            entity_id=1,
            date=date(2024, 1, 1),
            period="5d",
        )
        assert "MovingAverageData" in repr(ma_data)


class TestCacheEntryModel:
    """缓存条目模型测试"""

    def test_create_cache_entry(self):
        """测试创建缓存条目"""
        cache_entry = CacheEntry(
            key="test_key",
            value=b"test_value",
            expires_at=datetime(2024, 12, 31, 23, 59, 59),
        )
        assert cache_entry.key == "test_key"
        assert cache_entry.value == b"test_value"
        assert cache_entry.expires_at == datetime(2024, 12, 31, 23, 59, 59)

    def test_cache_entry_repr(self):
        """测试缓存条目字符串表示"""
        cache_entry = CacheEntry(
            key="test_key",
            value=b"test_value",
            expires_at=datetime(2024, 12, 31, 23, 59, 59),
        )
        assert "CacheEntry" in repr(cache_entry)


class TestDataUpdateLogModel:
    """数据更新日志模型测试"""

    def test_create_data_update_log(self):
        """测试创建更新日志"""
        log = DataUpdateLog(
            start_time=datetime(2024, 1, 1, 0, 0, 0),
            status="running",
            sectors_updated=10,
            stocks_updated=100,
            market_data_updated=500,
            calculations_performed=1000,
        )
        assert log.status == "running"
        assert log.sectors_updated == 10
        assert log.stocks_updated == 100
        assert log.market_data_updated == 500
        assert log.calculations_performed == 1000

    def test_data_update_log_completed(self):
        """测试完成状态的更新日志"""
        log = DataUpdateLog(
            start_time=datetime(2024, 1, 1, 0, 0, 0),
            end_time=datetime(2024, 1, 1, 0, 5, 0),
            status="completed",
            sectors_updated=10,
        )
        assert log.status == "completed"
        assert log.end_time == datetime(2024, 1, 1, 0, 5, 0)

    def test_data_update_log_repr(self):
        """测试更新日志字符串表示"""
        log = DataUpdateLog(
            start_time=datetime(2024, 1, 1, 0, 0, 0),
            status="running",
        )
        assert "DataUpdateLog" in repr(log)


class TestModelRelationships:
    """模型关系测试"""

    def test_sector_stocks_relationship(self):
        """测试板块-股票关联关系"""
        sector = Sector(id=1, name="银行", code="BK0001", type="industry")
        stock = Stock(id=1, symbol="000001", name="平安银行")

        # 模拟 ORM 加载的关系（实际需要数据库会话）
        assert hasattr(sector, "stocks")
        assert hasattr(stock, "sectors")
