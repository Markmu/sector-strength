"""
数据获取服务单元测试

测试 AkShare 数据源的各种功能，包括：
- 数据获取功能
- 重试机制
- 数据验证
- 错误处理
"""

from datetime import date, datetime
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest

# 假设测试在服务器根目录运行
import sys
from pathlib import Path

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.data_acquisition.akshare_client import AkShareDataSource
from services.data_acquisition.exceptions import (
    DataFetchError,
    DataValidationError,
    DataSourceTimeoutError,
    RetryExhaustedError,
)
from services.data_acquisition.models import (
    DailyQuote,
    SectorConstituent,
    SectorInfo,
    StockInfo,
)


class TestAkShareDataSource:
    """AkShare 数据源测试类"""

    @pytest.fixture
    def data_source(self):
        """创建数据源实例"""
        return AkShareDataSource(
            max_retries=2,
            retry_delay=0.01,  # 缩短测试延迟
            backoff_factor=2,
        )

    @pytest.fixture
    def mock_ak_functions(self, data_source):
        """模拟 akshare 函数"""
        mock_ak = MagicMock()
        # 直接设置 _ak 属性，绕过延迟加载
        data_source._ak = mock_ak
        return mock_ak

    @pytest.fixture
    def sample_stock_df(self):
        """创建示例股票数据 DataFrame"""
        return pd.DataFrame({
            "代码": ["000001", "000002", "600000"],
            "名称": ["平安银行", "万科A", "浦发银行"],
            "行业": ["银行", "房地产", "银行"],
        })

    @pytest.fixture
    def sample_sector_df(self):
        """创建示例板块数据 DataFrame"""
        return pd.DataFrame({
            "板块代码": ["BK0001", "BK0002"],
            "板块名称": ["银行", "房地产"],
        })

    @pytest.fixture
    def sample_daily_df(self):
        """创建示例日线数据 DataFrame"""
        return pd.DataFrame({
            "日期": ["2024-01-02", "2024-01-03", "2024-01-04"],
            "开盘": [10.0, 10.5, 11.0],
            "最高": [10.5, 11.0, 11.5],
            "最低": [9.8, 10.2, 10.8],
            "收盘": [10.3, 10.8, 11.2],
            "成交量": [1000000, 1200000, 900000],
            "成交额": [10300000, 12960000, 10080000],
            "换手率": [0.5, 0.6, 0.45],
        })

    @pytest.fixture
    def sample_constituent_df(self):
        """创建示例成分股数据 DataFrame"""
        return pd.DataFrame({
            "代码": ["000001", "600000"],
            "名称": ["平安银行", "浦发银行"],
        })

    # ==================== get_stock_list 测试 ====================

    def test_get_stock_list_success(self, data_source, mock_ak_functions, sample_stock_df):
        """测试成功获取股票列表"""
        mock_ak_functions.stock_zh_a_spot_em.return_value = sample_stock_df

        stocks = data_source.get_stock_list()

        assert len(stocks) == 3
        assert stocks[0].symbol == "000001"
        assert stocks[0].name == "平安银行"
        assert stocks[0].market == "SZ"
        assert stocks[0].industry == "银行"

        assert stocks[2].symbol == "600000"
        assert stocks[2].market == "SH"

    def test_get_stock_list_retry_on_failure(self, data_source, mock_ak_functions, sample_stock_df):
        """测试失败重试机制"""
        # 修改为 3 次重试，前两次失败，第三次成功
        data_source.max_retries = 3
        mock_ak_functions.stock_zh_a_spot_em.side_effect = [
            Exception("Network error"),
            Exception("Network error"),
            sample_stock_df,
        ]

        stocks = data_source.get_stock_list()

        assert len(stocks) == 3
        assert mock_ak_functions.stock_zh_a_spot_em.call_count == 3

    def test_get_stock_list_retry_exhausted(self, data_source, mock_ak_functions):
        """测试重试耗尽"""
        mock_ak_functions.stock_zh_a_spot_em.side_effect = Exception("Network error")

        with pytest.raises(RetryExhaustedError) as exc_info:
            data_source.get_stock_list()

        assert exc_info.value.attempts == 2  # max_retries = 2
        assert "重试" in str(exc_info.value)

    # ==================== get_sector_list 测试 ====================

    def test_get_sector_list_industry_only(self, data_source, mock_ak_functions, sample_sector_df):
        """测试获取行业板块"""
        mock_ak_functions.stock_board_industry_name_em.return_value = sample_sector_df

        sectors = data_source.get_sector_list(sector_type="industry")

        assert len(sectors) == 2
        assert sectors[0].code == "BK0001"
        assert sectors[0].name == "银行"
        assert sectors[0].type == "industry"

        # 确保没有调用概念板块接口
        mock_ak_functions.stock_board_concept_name_em.assert_not_called()

    def test_get_sector_list_all(self, data_source, mock_ak_functions, sample_sector_df):
        """测试获取所有板块"""
        mock_ak_functions.stock_board_industry_name_em.return_value = sample_sector_df
        mock_ak_functions.stock_board_concept_name_em.return_value = sample_sector_df

        sectors = data_source.get_sector_list()

        # 应该有 4 个板块（2 个行业 + 2 个概念）
        assert len(sectors) == 4
        assert mock_ak_functions.stock_board_industry_name_em.called
        assert mock_ak_functions.stock_board_concept_name_em.called

    # ==================== get_daily_data 测试 ====================

    def test_get_daily_data_success(self, data_source, mock_ak_functions, sample_daily_df):
        """测试成功获取日线数据"""
        mock_ak_functions.stock_zh_a_hist.return_value = sample_daily_df

        quotes = data_source.get_daily_data(
            symbol="000001",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        assert len(quotes) == 3
        assert quotes[0].symbol == "000001"
        assert quotes[0].trade_date == date(2024, 1, 2)
        assert quotes[0].open == 10.0
        assert quotes[0].high == 10.5
        assert quotes[0].low == 9.8
        assert quotes[0].close == 10.3
        assert quotes[0].volume == 1000000

    def test_get_daily_data_empty_result(self, data_source, mock_ak_functions):
        """测试日线数据为空"""
        mock_ak_functions.stock_zh_a_hist.return_value = pd.DataFrame()

        quotes = data_source.get_daily_data(
            symbol="000001",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        assert len(quotes) == 0

    def test_get_daily_data_invalid_date_range(self, data_source):
        """测试无效日期范围"""
        with pytest.raises(ValueError, match="开始日期不能晚于结束日期"):
            data_source.get_daily_data(
                symbol="000001",
                start_date=date(2024, 1, 31),
                end_date=date(2024, 1, 1),
            )

    def test_get_daily_data_invalid_symbol(self, data_source):
        """测试无效股票代码"""
        with pytest.raises(ValueError, match="股票代码不能为空"):
            data_source.get_daily_data(
                symbol="",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
            )

    # ==================== get_sector_stocks 测试 ====================

    def test_get_sector_stocks_success(self, data_source, mock_ak_functions, sample_constituent_df):
        """测试成功获取板块成分股"""
        mock_ak_functions.stock_board_concept_cons_em.return_value = sample_constituent_df

        constituents = data_source.get_sector_stocks("BK0001")

        assert len(constituents) == 2
        assert constituents[0].sector_code == "BK0001"
        assert constituents[0].symbol == "000001"
        assert constituents[0].name == "平安银行"

    def test_get_sector_stocks_empty_result(self, data_source, mock_ak_functions):
        """测试板块成分股为空"""
        mock_ak_functions.stock_board_concept_cons_em.return_value = pd.DataFrame()

        constituents = data_source.get_sector_stocks("BK0001")

        assert len(constituents) == 0

    def test_get_sector_stocks_invalid_code(self, data_source):
        """测试无效板块代码"""
        with pytest.raises(ValueError, match="板块代码不能为空"):
            data_source.get_sector_stocks("")

    # ==================== health_check 测试 ====================

    def test_health_check_success(self, data_source, mock_ak_functions, sample_stock_df):
        """测试健康检查成功"""
        mock_ak_functions.stock_zh_a_spot_em.return_value = sample_stock_df

        assert data_source.health_check() is True

    def test_health_check_failure(self, data_source, mock_ak_functions):
        """测试健康检查失败"""
        mock_ak_functions.stock_zh_a_spot_em.side_effect = Exception("Network error")

        assert data_source.health_check() is False


class TestDataModels:
    """数据模型验证测试"""

    def test_stock_info_valid(self):
        """测试有效股票信息"""
        stock = StockInfo(
            symbol="000001",
            name="平安银行",
            market="SZ",
            industry="银行",
        )
        assert stock.symbol == "000001"
        assert stock.market == "SZ"

    def test_stock_info_invalid_symbol(self):
        """测试无效股票代码"""
        with pytest.raises(ValueError, match="股票代码不能为空"):
            StockInfo(symbol="", name="测试")

    def test_stock_info_invalid_market(self):
        """测试无效市场类型"""
        with pytest.raises(ValueError, match="无效的市场类型"):
            StockInfo(symbol="000001", name="测试", market="INVALID")

    def test_daily_quote_price_validation(self):
        """测试日线价格关系验证"""
        # high < max(open, close) 应该失败
        with pytest.raises(ValueError, match="最高价不能低于"):
            DailyQuote(
                symbol="000001",
                trade_date=date(2024, 1, 1),
                open=10.0,
                high=9.5,  # 低于 open
                low=9.0,
                close=10.0,
                volume=1000000,
            )

        # low > min(open, close) 应该失败
        with pytest.raises(ValueError, match="最低价不能高于"):
            DailyQuote(
                symbol="000001",
                trade_date=date(2024, 1, 1),
                open=10.0,
                high=11.0,
                low=10.5,  # 高于 open
                close=10.0,
                volume=1000000,
            )

    def test_sector_info_valid(self):
        """测试有效板块信息"""
        sector = SectorInfo(
            code="BK0001",
            name="银行",
            type="industry",
        )
        assert sector.code == "BK0001"
        assert sector.type == "industry"

    def test_sector_info_invalid_type(self):
        """测试无效板块类型"""
        with pytest.raises(ValueError, match="无效的板块类型"):
            SectorInfo(
                code="BK0001",
                name="银行",
                type="invalid",
            )
