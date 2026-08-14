"""plan-02：融资融券采集适配器单元测试（mock DataApi，不依赖网络）

覆盖 TushareDataSource.get_margin（spec D1，margin 汇总接口，无分页）：
- 正常三行（SSE/SZSE/BSE，2026-08-14 实测并经人工裁定全量求和口径）：
  单次调用取全，七数值字段全为 Decimal(str()) 构造，键名与 tushare
  原生 schema 一致（蛇形），trade_date 与入参一致；本层不强制行数，
  两行/单行照常返回（行集合口径归 plan-03）
- 空结果（None/空 DataFrame）：返回空列表不抛错（当日失败判定归 plan-03）
- 六类非法场景抛 MarketDataIntegrityError（含 exchange_id 与字段值）：
  字段缺失 / NaN / Infinity / 负值 / 日期不符 / exchange_id 为空
- Decimal(str(...)) 精度保持：科学计数法值无 float 精度损失
- 瞬时异常经 _execute_with_retry 退避重试后成功
"""

import os
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from src.services.data_acquisition.models import MarketDataIntegrityError
from src.services.data_acquisition.tushare_client import TushareDataSource

TRADE_DATE = date(2026, 8, 13)
TRADE_DATE_STR = "20260813"

MARGIN_COLUMNS = [
    "trade_date",
    "exchange_id",
    "rzye",
    "rzmre",
    "rzche",
    "rqye",
    "rqmcl",
    "rqyl",
    "rzrqye",
]

DECIMAL_FIELDS = ["rzye", "rzmre", "rzche", "rqye", "rqmcl", "rqyl", "rzrqye"]


# ═══════════════════════════════════════════════════════════════
# 测试工具
# ═══════════════════════════════════════════════════════════════


def make_ds(mock_pro):
    """构造注入 mock DataApi 的 TushareDataSource（不限流、快重试）"""
    with patch.dict(os.environ, {"TUSHARE_TOKEN": "fake"}):
        ds = TushareDataSource()
    ds._pro_api = mock_pro
    ds._api_interval = 0.0
    ds._retry_delay = 0.001
    return ds


def margin_df(
    exchange_ids=("SSE", "SZSE", "BSE"),
    trade_date=TRADE_DATE_STR,
    rzye=9_512_345_678_901.23,
    rzmre=65_432_100_000.50,
    rzche=64_000_000_000.00,
    rqye=1_234_567_890.12,
    rqmcl=345_678_900.0,
    rqyl=1_234_567_890.0,
    rzrqye=10_746_913_467_791.35,
):
    """构造 margin 响应 DataFrame（默认 SSE/SZSE/BSE 三行，元/股原始口径量级）"""
    n = len(exchange_ids)
    return pd.DataFrame(
        {
            "trade_date": [trade_date] * n,
            "exchange_id": list(exchange_ids),
            "rzye": [rzye] * n,
            "rzmre": [rzmre] * n,
            "rzche": [rzche] * n,
            "rqye": [rqye] * n,
            "rqmcl": [rqmcl] * n,
            "rqyl": [rqyl] * n,
            "rzrqye": [rzrqye] * n,
        }
    )


def empty_margin_df():
    return pd.DataFrame(columns=MARGIN_COLUMNS)


def make_margin_ds(df):
    """构造 pro.margin 返回指定 DataFrame 的数据源"""
    mock_pro = MagicMock()
    mock_pro.margin.return_value = df
    return make_ds(mock_pro), mock_pro


# ═══════════════════════════════════════════════════════════════
# 主流程：get_margin
# ═══════════════════════════════════════════════════════════════


class TestGetMargin:
    """正常三行、请求参数、单次调用、Decimal 数值与蛇形键（plan-03 原料）"""

    def test_normal_three_rows_sse_szse_bse(self):
        """正常三行（SSE/SZSE/BSE）：七数值字段全为 Decimal，trade_date 与入参一致"""
        ds, mock_pro = make_margin_ds(margin_df())

        rows = ds.get_margin(TRADE_DATE)

        assert len(rows) == 3
        assert {r["exchange_id"] for r in rows} == {"SSE", "SZSE", "BSE"}
        for row in rows:
            # 七数值字段全为 Decimal 实例（非 float 构造）
            for field in DECIMAL_FIELDS:
                assert type(row[field]) is Decimal, field
            assert row["trade_date"] == TRADE_DATE
            assert type(row["trade_date"]) is date
            # 键名与 tushare 原生 schema 一致（蛇形），无多余键
            assert set(row.keys()) == set(MARGIN_COLUMNS)
        # 原始值透传（Decimal(str()) 路径，元/股口径不换算）
        sse = next(r for r in rows if r["exchange_id"] == "SSE")
        assert sse["rzye"] == Decimal("9512345678901.23")
        assert sse["rzmre"] == Decimal("65432100000.50")
        assert sse["rqmcl"] == Decimal("345678900.0")
        assert sse["rzrqye"] == Decimal("10746913467791.35")

    def test_two_rows_returned_as_is(self):
        """返回 2 行（某交易所缺失）：本层照常返回，不强制行数（口径归 plan-03）"""
        ds, _ = make_margin_ds(margin_df(exchange_ids=("SSE", "SZSE")))

        rows = ds.get_margin(TRADE_DATE)

        assert len(rows) == 2
        assert {r["exchange_id"] for r in rows} == {"SSE", "SZSE"}

    def test_single_call_no_pagination(self):
        """单日仅发起 1 次 margin 调用（无 offset/limit 分页循环）"""
        ds, mock_pro = make_margin_ds(margin_df())

        ds.get_margin(TRADE_DATE)

        assert mock_pro.margin.call_count == 1

    def test_request_params_exact(self):
        """请求参数精确：仅 trade_date=YYYYMMDD，不传 fields（取原生 schema）"""
        ds, mock_pro = make_margin_ds(margin_df())

        ds.get_margin(TRADE_DATE)

        mock_pro.margin.assert_called_once_with(trade_date=TRADE_DATE_STR)

    def test_string_numeric_values_accepted(self):
        """数值以字符串形态进入（Decimal(str) 路径同样适用）"""
        df = pd.DataFrame(
            {
                "trade_date": [TRADE_DATE_STR],
                "exchange_id": ["SSE"],
                "rzye": ["9512345678901.23"],
                "rzmre": ["65432100000.5"],
                "rzche": ["64000000000"],
                "rqye": ["1234567890.12"],
                "rqmcl": ["345678900"],
                "rqyl": ["1234567890"],
                "rzrqye": ["10746913467791.35"],
            }
        )
        ds, _ = make_margin_ds(df)

        rows = ds.get_margin(TRADE_DATE)

        assert rows[0]["rzye"] == Decimal("9512345678901.23")
        assert rows[0]["rzche"] == Decimal("64000000000")
        assert rows[0]["rqyl"] == Decimal("1234567890")

    def test_scientific_notation_no_float_precision_loss(self):
        """科学计数法值经 Decimal(str()) 无 float 精度损失（禁 binary float 路径）"""
        df = margin_df(exchange_ids=("SSE",))
        # 1.0e12 量级：float 列 str() 后无损；字符串科学计数法原样保真
        df.loc[0, "rzye"] = 1.0e12
        df["rqye"] = df["rqye"].astype(object)  # 模拟 Provider 返回字符串列
        df.loc[0, "rqye"] = "9.87654321e+11"
        ds, _ = make_margin_ds(df)

        rows = ds.get_margin(TRADE_DATE)

        # Decimal(str(1.0e12)) == 1000000000000.0，非 1e12 的二进制近似
        assert rows[0]["rzye"] == Decimal("1000000000000.0")
        # 字符串 "9.87654321e+11" 各位数字完整保留，无精度损失
        assert rows[0]["rqye"] == Decimal("9.87654321e+11")
        assert rows[0]["rqye"] == Decimal("987654321000")

    def test_empty_dataframe_returns_empty_list(self):
        """Provider 返回空 DataFrame：返回空列表不抛错（失败判定归 plan-03）"""
        ds, mock_pro = make_margin_ds(empty_margin_df())

        rows = ds.get_margin(TRADE_DATE)

        assert rows == []
        assert mock_pro.margin.call_count == 1

    def test_none_response_returns_empty_list(self):
        """Provider 返回 None：同样返回空列表不抛错"""
        ds, _ = make_margin_ds(None)

        assert ds.get_margin(TRADE_DATE) == []

    def test_single_row_returned_as_is(self):
        """返回仅 1 行（如上游截断）：本层照常返回，不强制行数（口径归 plan-03）"""
        ds, _ = make_margin_ds(margin_df(exchange_ids=("SSE",)))

        rows = ds.get_margin(TRADE_DATE)

        assert len(rows) == 1
        assert rows[0]["exchange_id"] == "SSE"

    def test_transient_failure_retried_then_success(self):
        """瞬时异常经 _execute_with_retry 退避重试后成功"""
        mock_pro = MagicMock()
        mock_pro.margin.side_effect = [
            Exception("网络抖动"),
            Exception("网络抖动"),
            margin_df(),
        ]
        ds = make_ds(mock_pro)

        rows = ds.get_margin(TRADE_DATE)

        assert len(rows) == 3
        assert mock_pro.margin.call_count == 3

    def test_non_retryable_error_fails_immediately(self):
        """非可重试关键字（积分/权限）立即失败，不重试不吞错"""
        from src.services.data_acquisition.exceptions import DataFetchError

        mock_pro = MagicMock()
        mock_pro.margin.side_effect = Exception("抱歉，您没有足够积分访问该接口")
        ds = make_ds(mock_pro)

        with pytest.raises(DataFetchError, match="不可恢复"):
            ds.get_margin(TRADE_DATE)
        assert mock_pro.margin.call_count == 1


# ═══════════════════════════════════════════════════════════════
# 行级校验：六类完整性错误（AC-1 聚合输入质量）
# ═══════════════════════════════════════════════════════════════


class TestMarginRowValidation:
    """字段缺失 / NaN / Infinity / 负值 / 日期不符 / exchange_id 为空"""

    def test_missing_field_raises(self):
        """某数值字段缺失（列不存在）→ 完整性错误（含 exchange_id）"""
        df = margin_df().drop(columns=["rzye"])
        ds, _ = make_margin_ds(df)

        with pytest.raises(MarketDataIntegrityError, match="rzye") as exc_info:
            ds.get_margin(TRADE_DATE)
        assert "SSE" in str(exc_info.value)

    def test_nan_field_raises(self):
        """某数值字段为 NaN（_df_to_rows 归一为 None）→ 完整性错误"""
        df = margin_df(exchange_ids=("SZSE",))
        df.loc[0, "rqmcl"] = np.nan
        ds, _ = make_margin_ds(df)

        with pytest.raises(MarketDataIntegrityError, match="rqmcl") as exc_info:
            ds.get_margin(TRADE_DATE)
        assert "SZSE" in str(exc_info.value)

    def test_infinity_field_raises(self):
        """某数值字段为 Infinity → 非有限数完整性错误（含字段值）"""
        df = margin_df(exchange_ids=("SSE",))
        df.loc[0, "rzrqye"] = float("inf")
        ds, _ = make_margin_ds(df)

        with pytest.raises(MarketDataIntegrityError, match="非有限数"):
            ds.get_margin(TRADE_DATE)

    def test_negative_field_raises(self):
        """负值 → 完整性错误，错误信息含 exchange_id 与字段值"""
        df = margin_df(exchange_ids=("SSE",))
        df.loc[0, "rzmre"] = -123.45
        ds, _ = make_margin_ds(df)

        with pytest.raises(MarketDataIntegrityError, match="非法") as exc_info:
            ds.get_margin(TRADE_DATE)
        msg = str(exc_info.value)
        assert "rzmre" in msg
        assert "-123.45" in msg
        assert "SSE" in msg

    def test_each_negative_decimal_field_raises(self):
        """七字段逐一为负均拒绝（余额/买入额/偿还额/卖出量/余量不可能为负）"""
        for field in DECIMAL_FIELDS:
            df = margin_df(exchange_ids=("SZSE",))
            df.loc[0, field] = -1.0
            ds, _ = make_margin_ds(df)

            with pytest.raises(MarketDataIntegrityError, match=field):
                ds.get_margin(TRADE_DATE)

    def test_zero_values_allowed(self):
        """七字段全 0 合法（>=0 谓词；两融开闸前/极端日口径由 plan-03 解释）"""
        ds, _ = make_margin_ds(margin_df(exchange_ids=("SSE",), **{f: 0.0 for f in DECIMAL_FIELDS}))

        rows = ds.get_margin(TRADE_DATE)

        for field in DECIMAL_FIELDS:
            assert rows[0][field] == Decimal("0.0")

    def test_wrong_trade_date_raises(self):
        """行 trade_date 与入参不符 → 完整性错误（防串日，含 exchange_id）"""
        df = margin_df(exchange_ids=("SSE",), trade_date="20260812")
        ds, _ = make_margin_ds(df)

        with pytest.raises(MarketDataIntegrityError, match="非目标日期") as exc_info:
            ds.get_margin(TRADE_DATE)
        msg = str(exc_info.value)
        assert "2026-08-12" in msg
        assert "SSE" in msg

    def test_unparsable_trade_date_raises(self):
        """行 trade_date 非 YYYYMMDD → 解析失败完整性错误（含 exchange_id）"""
        df = margin_df(exchange_ids=("SSE",), trade_date="2026/08/13")
        ds, _ = make_margin_ds(df)

        with pytest.raises(MarketDataIntegrityError, match="无法解析") as exc_info:
            ds.get_margin(TRADE_DATE)
        assert "SSE" in str(exc_info.value)

    def test_empty_exchange_id_raises(self):
        """exchange_id 为空串 → 完整性错误"""
        df = margin_df(exchange_ids=("  ",))
        ds, _ = make_margin_ds(df)

        with pytest.raises(MarketDataIntegrityError, match="exchange_id"):
            ds.get_margin(TRADE_DATE)

    def test_missing_exchange_id_raises(self):
        """exchange_id 列缺失（None）→ 完整性错误"""
        df = margin_df().drop(columns=["exchange_id"])
        ds, _ = make_margin_ds(df)

        with pytest.raises(MarketDataIntegrityError, match="exchange_id"):
            ds.get_margin(TRADE_DATE)

    def test_exchange_id_whitespace_stripped(self):
        """exchange_id 前后空白被 strip 归一化"""
        df = margin_df(exchange_ids=("  SSE  ",))
        ds, _ = make_margin_ds(df)

        rows = ds.get_margin(TRADE_DATE)

        assert rows[0]["exchange_id"] == "SSE"
