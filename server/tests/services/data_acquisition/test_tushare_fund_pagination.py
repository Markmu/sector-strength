"""fund_basic / fund_portfolio offset 分页守卫单元测试（评审报告 B4）

实测故障模式：代理忽略 offset 参数，每页返回相同内容且始终满页，
while True 循环会无限追加重复数据直至 OOM。守卫要求：
1. 页签名重复（首行 ts_code + 行数在不同 offset 重现）→ DataFetchError
2. 页数超过安全上限 → DataFetchError
正常分页（满页 + 尾页短页）行为不变。
"""

import os
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.services.data_acquisition.exceptions import DataFetchError
from src.services.data_acquisition.tushare_client import TushareDataSource


def make_ds():
    mock_pro = MagicMock()
    with patch.dict(os.environ, {"TUSHARE_TOKEN": "fake"}):
        ds = TushareDataSource()
    ds._pro_api = mock_pro
    ds._api_interval = 0.0
    ds._retry_delay = 0.001
    return ds, mock_pro


def fund_df(start_idx: int, count: int) -> pd.DataFrame:
    """构造 count 行的 fund 页，ts_code 随 start_idx 递增保证每页唯一"""
    return pd.DataFrame(
        {
            "ts_code": [f"{i:06d}.OF" for i in range(start_idx, start_idx + count)],
            "name": [f"基金{i}" for i in range(start_idx, start_idx + count)],
        }
    )


class TestGetFundListPagination:
    def test_normal_pagination_multi_page(self):
        """满页 + 尾页短页：正常终止，返回全部记录"""
        ds, mock_pro = make_ds()
        full = fund_df(0, 15000)
        tail = fund_df(15000, 30)
        mock_pro.fund_basic = MagicMock(side_effect=[full, tail])

        records = ds.get_fund_list("E")

        assert len(records) == 15030
        assert mock_pro.fund_basic.call_count == 2

    def test_offset_ignored_repeated_page_raises(self):
        """代理忽略 offset 重复回同一满页 → 页签名重复守卫必须抛错"""
        ds, mock_pro = make_ds()
        identical = fund_df(0, 15000)
        mock_pro.fund_basic = MagicMock(return_value=identical)

        with pytest.raises(DataFetchError, match="页签名重复"):
            ds.get_fund_list("E")

        # 守卫应在第 2 页就触发，而不是无限循环
        assert mock_pro.fund_basic.call_count == 2

    def test_page_cap_raises(self):
        """每页唯一但页数超上限 → 硬上限守卫抛错"""
        ds, mock_pro = make_ds()
        ds.FUND_BASIC_MAX_PAGES = 3
        page_no = [0]

        def always_new_full_page(*args, **kwargs):
            page_no[0] += 1
            return fund_df((page_no[0] - 1) * 15000, 15000)

        mock_pro.fund_basic = MagicMock(side_effect=always_new_full_page)

        with pytest.raises(DataFetchError, match="安全上限"):
            ds.get_fund_list("E")

        assert mock_pro.fund_basic.call_count == 3  # 上限 3 页，第 4 页前触发


class TestGetFundPortfolioPagination:
    def test_normal_single_short_page(self):
        ds, mock_pro = make_ds()
        mock_pro.fund_portfolio = MagicMock(
            return_value=fund_df(0, 120)
        )

        records = ds.get_fund_portfolio("20241231")

        assert len(records) == 120
        mock_pro.fund_portfolio.assert_called_once()

    def test_offset_ignored_repeated_page_raises(self):
        ds, mock_pro = make_ds()
        # 构造与 batch_size 等长的满页（5000 行）重复返回
        identical = fund_df(0, 5000)
        mock_pro.fund_portfolio = MagicMock(return_value=identical)

        with pytest.raises(DataFetchError, match="页签名重复"):
            ds.get_fund_portfolio("20241231")

        assert mock_pro.fund_portfolio.call_count == 2

    def test_page_cap_raises(self, monkeypatch):
        """每页内容唯一但总页数超上限 → 硬上限守卫抛错（不再无限循环）"""
        ds, mock_pro = make_ds()
        # 5000/页的 batch_size 是局部常量；用唯一满页 + 低上限触发
        ds.FUND_PORTFOLIO_MAX_PAGES = 3
        page_no = [0]

        def always_new_full_page(*args, **kwargs):
            page_no[0] += 1
            return fund_df((page_no[0] - 1) * 5000, 5000)

        mock_pro.fund_portfolio = MagicMock(side_effect=always_new_full_page)

        with pytest.raises(DataFetchError, match="安全上限"):
            ds.get_fund_portfolio("20241231")

        assert mock_pro.fund_portfolio.call_count == 3  # 上限 3 页，第 4 页前触发
