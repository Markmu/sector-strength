"""
数据源工厂与抽象层测试

覆盖 plan-01：BaseDataSource 新增 get_trading_calendar 抽象方法，
DataSourceFactory 基于 DATA_SOURCE_TYPE 环境变量创建数据源实例。
覆盖 plan-02：TushareDataSource 字段映射、重试机制、参数校验。
覆盖 plan-03：服务层解耦，确认无残留 AkShareDataSource 直接导入。
"""

import os
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import date
from typing import List

import pandas as pd


# ═══════════════════════════════════════════════════════════════
# Plan-01: 抽象层与工厂
# ═══════════════════════════════════════════════════════════════


class TestBaseDataSourceAbstractMethods:
    """验证 BaseDataSource 的抽象方法定义完整"""

    def test_get_trading_calendar_is_abstract(self):
        """未实现 get_trading_calendar 的子类不能实例化"""
        from src.services.data_acquisition.base import BaseDataSource

        with pytest.raises(TypeError):
            class IncompleteSource(BaseDataSource):
                def get_stock_list(self): return []
                def get_sector_list(self, sector_type=None): return []
                def get_daily_data(self, symbol, start_date, end_date): return []
                def get_sector_daily_data(self, sector_name, sector_type, start_date, end_date): return []

            IncompleteSource("test")

    def test_complete_subclass_can_instantiate(self):
        """实现了所有抽象方法（含 get_trading_calendar）的子类可以实例化"""
        from src.services.data_acquisition.base import BaseDataSource

        class CompleteSource(BaseDataSource):
            def get_stock_list(self): return []
            def get_sector_list(self, sector_type=None): return []
            def get_daily_data(self, symbol, start_date, end_date): return []
            def get_sector_daily_data(self, sector_name, sector_type, start_date, end_date): return []
            def get_trading_calendar(self): return []

        instance = CompleteSource("Test")
        assert instance.source_name == "Test"


class TestDataSourceFactory:
    """验证 DataSourceFactory 根据环境变量创建正确的数据源实例"""

    def test_default_is_akshare(self):
        """DATA_SOURCE_TYPE 未设置时默认使用 AkShare"""
        from src.services.data_acquisition import DataSourceFactory, AkShareDataSource

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("DATA_SOURCE_TYPE", None)
            ds = DataSourceFactory.create()
            assert isinstance(ds, AkShareDataSource)
            assert ds.source_name == "AkShare"

    def test_akshare_explicit(self):
        """DATA_SOURCE_TYPE=akshare 时返回 AkShareDataSource"""
        from src.services.data_acquisition import DataSourceFactory, AkShareDataSource

        with patch.dict(os.environ, {"DATA_SOURCE_TYPE": "akshare"}):
            ds = DataSourceFactory.create()
            assert isinstance(ds, AkShareDataSource)

    def test_tushare_returns_tushare_data_source(self):
        """DATA_SOURCE_TYPE=tushare 时返回 TushareDataSource"""
        from src.services.data_acquisition import DataSourceFactory, TushareDataSource

        with patch.dict(os.environ, {"DATA_SOURCE_TYPE": "tushare"}):
            # Mock _get_pro_api 避免真正连接 Tushare
            with patch.object(TushareDataSource, "_get_pro_api", return_value=None):
                ds = DataSourceFactory.create()
                assert isinstance(ds, TushareDataSource)
                assert ds.source_name == "Tushare"

    def test_invalid_type_raises_value_error(self):
        """非法 DATA_SOURCE_TYPE 抛出 ValueError"""
        from src.services.data_acquisition import DataSourceFactory

        for invalid_val in ["invalid", "UNKNOWN", "foo", ""]:
            with patch.dict(os.environ, {"DATA_SOURCE_TYPE": invalid_val}):
                with pytest.raises(ValueError, match="无效的数据源类型"):
                    DataSourceFactory.create()

    def test_case_insensitive(self):
        """DATA_SOURCE_TYPE 大小写不敏感"""
        from src.services.data_acquisition import DataSourceFactory, AkShareDataSource

        with patch.dict(os.environ, {"DATA_SOURCE_TYPE": "AKSHARE"}):
            ds = DataSourceFactory.create()
            assert isinstance(ds, AkShareDataSource)

        with patch.dict(os.environ, {"DATA_SOURCE_TYPE": "  AkShare  "}):
            ds = DataSourceFactory.create()
            assert isinstance(ds, AkShareDataSource)

    def test_valid_types_constant(self):
        """VALID_TYPES 应包含 tushare 和 akshare"""
        from src.services.data_acquisition import DataSourceFactory

        assert "tushare" in DataSourceFactory.VALID_TYPES
        assert "akshare" in DataSourceFactory.VALID_TYPES
        assert len(DataSourceFactory.VALID_TYPES) == 2


class TestAkShareCompatibility:
    """验证新增抽象方法后 AkShareDataSource 不受影响"""

    def test_akshare_has_get_trading_calendar(self):
        """AkShareDataSource 应已实现 get_trading_calendar"""
        from src.services.data_acquisition import AkShareDataSource

        ds = AkShareDataSource()
        assert hasattr(ds, "get_trading_calendar")
        assert callable(ds.get_trading_calendar)

    def test_akshare_is_base_data_source(self):
        """AkShareDataSource 应是 BaseDataSource 的子类"""
        from src.services.data_acquisition import AkShareDataSource, BaseDataSource

        assert issubclass(AkShareDataSource, BaseDataSource)


# ═══════════════════════════════════════════════════════════════
# Plan-02: TushareDataSource 单元测试
# ═══════════════════════════════════════════════════════════════


class TestTushareDataSourceInit:
    """验证 TushareDataSource 初始化"""

    def test_source_name(self):
        from src.services.data_acquisition.tushare_client import TushareDataSource

        with patch.dict(os.environ, {"TUSHARE_TOKEN": "test_token"}):
            ds = TushareDataSource()
            assert ds.source_name == "Tushare"

    def test_missing_token_raises(self):
        """未配置 TUSHARE_TOKEN 时 _get_pro_api 抛出 DataFetchError"""
        from src.services.data_acquisition.tushare_client import TushareDataSource
        from src.services.data_acquisition.exceptions import DataFetchError

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("TUSHARE_TOKEN", None)
            ds = TushareDataSource()
            with pytest.raises(DataFetchError, match="TUSHARE_TOKEN 未配置"):
                ds._get_pro_api()


class TestTushareSymbolMapping:
    """验证 _symbol_to_ts_code 字段映射"""

    def test_sh_prefix(self):
        from src.services.data_acquisition.tushare_client import TushareDataSource
        assert TushareDataSource._symbol_to_ts_code("600000") == "600000.SH"

    def test_sz_0_prefix(self):
        from src.services.data_acquisition.tushare_client import TushareDataSource
        assert TushareDataSource._symbol_to_ts_code("000001") == "000001.SZ"

    def test_sz_3_prefix(self):
        from src.services.data_acquisition.tushare_client import TushareDataSource
        assert TushareDataSource._symbol_to_ts_code("300001") == "300001.SZ"

    def test_bj_8_prefix(self):
        from src.services.data_acquisition.tushare_client import TushareDataSource
        assert TushareDataSource._symbol_to_ts_code("830001") == "830001.BJ"

    def test_bj_4_prefix(self):
        from src.services.data_acquisition.tushare_client import TushareDataSource
        assert TushareDataSource._symbol_to_ts_code("430001") == "430001.BJ"

    def test_unknown_prefix_passthrough(self):
        from src.services.data_acquisition.tushare_client import TushareDataSource
        assert TushareDataSource._symbol_to_ts_code("999999") == "999999"


class TestTushareRetryMechanism:
    """验证重试机制"""

    def test_retry_exhausted(self):
        """重试耗尽后抛出 RetryExhaustedError"""
        from src.services.data_acquisition.tushare_client import TushareDataSource
        from src.services.data_acquisition.exceptions import RetryExhaustedError

        ds = TushareDataSource()
        ds._max_retries = 2
        ds._retry_delay = 0.01  # 加速测试

        call_count = 0

        def failing_func():
            nonlocal call_count
            call_count += 1
            raise Exception("test error")

        with pytest.raises(RetryExhaustedError):
            ds._execute_with_retry(failing_func)

        assert call_count == 2

    def test_retry_succeeds_on_second_attempt(self):
        """第一次失败，第二次成功"""
        from src.services.data_acquisition.tushare_client import TushareDataSource

        ds = TushareDataSource()
        ds._max_retries = 3
        ds._retry_delay = 0.01

        call_count = 0

        def intermittent_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("first fail")
            return "success"

        result = ds._execute_with_retry(intermittent_func)
        assert result == "success"
        assert call_count == 2


class TestTushareGetTradingCalendar:
    """验证 get_trading_calendar（AC-01）"""

    def _make_ds(self, mock_pro):
        from src.services.data_acquisition.tushare_client import TushareDataSource

        with patch.dict(os.environ, {"TUSHARE_TOKEN": "fake"}):
            ds = TushareDataSource()
            ds._pro_api = mock_pro
            return ds

    def test_returns_sorted_dates(self):
        """返回排序后的交易日列表"""
        mock_pro = MagicMock()
        mock_pro.trade_cal.return_value = pd.DataFrame({
            "cal_date": ["20260105", "20260102", "20260106"],
            "is_open": [1, 1, 1],
        })

        ds = self._make_ds(mock_pro)
        dates = ds.get_trading_calendar()

        assert len(dates) == 3
        assert dates[0] == date(2026, 1, 2)
        assert dates[1] == date(2026, 1, 5)
        assert dates[2] == date(2026, 1, 6)

    def test_empty_data_raises(self):
        """空数据抛出 DataFetchError"""
        from src.services.data_acquisition.exceptions import DataFetchError

        mock_pro = MagicMock()
        mock_pro.trade_cal.return_value = pd.DataFrame({"cal_date": [], "is_open": []})

        ds = self._make_ds(mock_pro)
        with pytest.raises(DataFetchError, match="交易日历返回空数据"):
            ds.get_trading_calendar()


class TestTushareGetStockList:
    """验证 get_stock_list（AC-02）"""

    def _make_ds(self, mock_pro):
        from src.services.data_acquisition.tushare_client import TushareDataSource

        with patch.dict(os.environ, {"TUSHARE_TOKEN": "fake"}):
            ds = TushareDataSource()
            ds._pro_api = mock_pro
            return ds

    def test_field_mapping(self):
        """ts_code → symbol, suffix → market, industry 映射正确"""
        mock_pro = MagicMock()
        mock_pro.stock_basic.return_value = pd.DataFrame({
            "ts_code": ["000001.SZ", "600000.SH", "830001.BJ"],
            "name": ["平安银行", "浦发银行", "测试北交所"],
            "industry": ["银行", None, "其他"],
            "list_date": [pd.NaT, "19991110", "20200101"],
        })

        ds = self._make_ds(mock_pro)
        stocks = ds.get_stock_list()

        assert len(stocks) == 3
        # 验证 SZ
        assert stocks[0].symbol == "000001"
        assert stocks[0].market == "SZ"
        assert stocks[0].industry == "银行"
        # 验证 SH
        assert stocks[1].symbol == "600000"
        assert stocks[1].market == "SH"
        assert stocks[1].list_date == date(1999, 11, 10)
        # 验证 BJ
        assert stocks[2].market == "BJ"


class TestTushareGetSectorList:
    """验证 get_sector_list（AC-03）"""

    def _make_ds(self, mock_pro):
        from src.services.data_acquisition.tushare_client import TushareDataSource

        with patch.dict(os.environ, {"TUSHARE_TOKEN": "fake"}):
            ds = TushareDataSource()
            ds._pro_api = mock_pro
            return ds

    def test_industry_sectors(self):
        """sector_type='industry' 返回行业板块"""
        mock_pro = MagicMock()
        mock_pro.ths_index.return_value = pd.DataFrame({
            "ts_code": ["881101.TI", "881102.TI"],
            "name": ["种植业", "林业"],
        })

        ds = self._make_ds(mock_pro)
        sectors = ds.get_sector_list("industry")

        assert len(sectors) == 2
        assert sectors[0].code == "881101.TI"
        assert sectors[0].type == "industry"

    def test_invalid_sector_type(self):
        """无效板块类型抛出 ValueError"""
        mock_pro = MagicMock()
        ds = self._make_ds(mock_pro)
        with pytest.raises(ValueError, match="无效的板块类型过滤"):
            ds.get_sector_list("invalid")


class TestTushareGetDailyData:
    """验证 get_daily_data（AC-04）"""

    def _make_ds(self, mock_pro):
        from src.services.data_acquisition.tushare_client import TushareDataSource

        with patch.dict(os.environ, {"TUSHARE_TOKEN": "fake"}):
            ds = TushareDataSource()
            ds._pro_api = mock_pro
            return ds

    def test_field_mapping_and_amount_conversion(self):
        """验证字段映射和 amount ×1000 转换"""
        mock_df = pd.DataFrame({
            "ts_code": ["000001.SZ"],
            "trade_date": ["20260105"],
            "open": [10.5],
            "high": [11.0],
            "low": [10.2],
            "close": [10.8],
            "vol": [1000000.0],
            "amount": [5000.0],  # 千元
            "turnover_rate": [2.5],
        })

        mock_ts = MagicMock()
        mock_ts.pro_bar.return_value = mock_df
        with patch.dict("sys.modules", {"tushare": mock_ts}):
            ds = self._make_ds(MagicMock())
            quotes = ds.get_daily_data("000001", date(2026, 1, 5), date(2026, 1, 5))

        assert len(quotes) == 1
        q = quotes[0]
        assert q.symbol == "000001"
        assert q.trade_date == date(2026, 1, 5)
        assert q.open == 10.5
        assert q.close == 10.8
        assert q.volume == 1000000.0
        assert q.amount == 5000000.0  # 5000 × 1000
        assert q.turnover == 2.5

    def test_empty_symbol_raises(self):
        """空股票代码抛出 ValueError"""
        ds = self._make_ds(MagicMock())
        with pytest.raises(ValueError, match="股票代码不能为空"):
            ds.get_daily_data("", date(2026, 1, 1), date(2026, 1, 5))

    def test_invalid_date_range_raises(self):
        """开始日期晚于结束日期抛出 ValueError"""
        ds = self._make_ds(MagicMock())
        with pytest.raises(ValueError, match="开始日期不能晚于结束日期"):
            ds.get_daily_data("000001", date(2026, 1, 10), date(2026, 1, 5))

    def test_empty_result(self):
        """空 DataFrame 返回空列表"""
        mock_ts = MagicMock()
        mock_ts.pro_bar.return_value = pd.DataFrame()
        with patch.dict("sys.modules", {"tushare": mock_ts}):
            ds = self._make_ds(MagicMock())
            quotes = ds.get_daily_data("000001", date(2026, 1, 5), date(2026, 1, 5))
        assert quotes == []


class TestTushareGetSectorDailyData:
    """验证 get_sector_daily_data（AC-05）"""

    def _make_ds(self, mock_pro):
        from src.services.data_acquisition.tushare_client import TushareDataSource

        with patch.dict(os.environ, {"TUSHARE_TOKEN": "fake"}):
            ds = TushareDataSource()
            ds._pro_api = mock_pro
            return ds

    def test_sector_daily_data(self):
        """板块日线字段映射正确"""
        # 先 mock ths_index 用于查找 ts_code
        mock_pro = MagicMock()
        mock_pro.ths_index.return_value = pd.DataFrame({
            "ts_code": ["881101.TI"],
            "name": ["种植业"],
        })
        mock_pro.ths_daily.return_value = pd.DataFrame({
            "ts_code": ["881101.TI"],
            "trade_date": ["20260105"],
            "open": [100.0],
            "high": [110.0],
            "low": [95.0],
            "close": [105.0],
            "vol": [500000.0],
        })

        ds = self._make_ds(mock_pro)
        quotes = ds.get_sector_daily_data("种植业", "industry", date(2026, 1, 5), date(2026, 1, 5))

        assert len(quotes) == 1
        q = quotes[0]
        assert q.symbol == "种植业"
        assert q.open == 100.0
        assert q.close == 105.0

    def test_sector_name_not_found(self):
        """板块名称未找到 ts_code 时返回空列表"""
        mock_pro = MagicMock()
        mock_pro.ths_index.return_value = pd.DataFrame({
            "ts_code": ["881101.TI"],
            "name": ["种植业"],
        })

        ds = self._make_ds(mock_pro)
        quotes = ds.get_sector_daily_data("不存在的板块", "industry", date(2026, 1, 5), date(2026, 1, 5))
        assert quotes == []


class TestTushareHealthCheck:
    """验证 health_check"""

    def test_healthy(self):
        mock_pro = MagicMock()
        mock_pro.trade_cal.return_value = pd.DataFrame({"cal_date": ["20260101"]})

        from src.services.data_acquisition.tushare_client import TushareDataSource

        with patch.dict(os.environ, {"TUSHARE_TOKEN": "fake"}):
            ds = TushareDataSource()
            ds._pro_api = mock_pro
            assert ds.health_check() is True

    def test_unhealthy(self):
        mock_pro = MagicMock()
        mock_pro.trade_cal.side_effect = Exception("connection refused")

        from src.services.data_acquisition.tushare_client import TushareDataSource

        with patch.dict(os.environ, {"TUSHARE_TOKEN": "fake"}):
            ds = TushareDataSource()
            ds._pro_api = mock_pro
            assert ds.health_check() is False


# ═══════════════════════════════════════════════════════════════
# Plan-03: 服务层解耦验证
# ═══════════════════════════════════════════════════════════════


class TestServiceLayerDecoupling:
    """验证 5 个服务文件已移除 AkShareDataSource 直接导入"""

    FILES_TO_CHECK = [
        "src/services/trading_calendar.py",
        "src/services/data_init.py",
        "src/services/data_update.py",
        "src/services/data_updater/collector.py",
        "src/services/monitoring/data_quality.py",
    ]

    def test_no_akshare_import_in_service_files(self):
        """5 个服务文件中不应有 from ...akshare_client import AkShareDataSource"""
        import re

        pattern = re.compile(r"from\s+.*akshare_client\s+import\s+AkShareDataSource")
        for filepath in self.FILES_TO_CHECK:
            with open(filepath) as f:
                content = f.read()
            matches = pattern.findall(content)
            assert matches == [], f"{filepath} 仍包含 AkShareDataSource 直接导入"

    def test_datasource_factory_used(self):
        """5 个服务文件应使用 DataSourceFactory"""
        for filepath in self.FILES_TO_CHECK:
            with open(filepath) as f:
                content = f.read()
            assert "DataSourceFactory" in content, f"{filepath} 未使用 DataSourceFactory"
