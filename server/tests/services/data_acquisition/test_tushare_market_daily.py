"""plan-02：全市场量价采集适配器单元测试（mock DataApi，不依赖网络）

覆盖 TushareDataSource 新增能力（ADR-1/2/3，架构 §6.1.3-6）：
- 单日模式 get_market_daily_quotes：exact-3000/6000 + 空尾页、单页短页、
  首空页语义、expected_count 硬页数、Decimal 数值与原始单位
- 共享分页守卫四类完整性错误：页签名重复 / 满页无新增 key /
  页数超硬上限 / 跨页重复行 key
- 行级校验：日期谓词、close>0 / vol>=0 / amount>=0、NaN/Infinity
- 历史窗口模式 get_close_quotes_in_window：谓词、首空页=窗口无命中、
  批次内分块（>100 只）、越界行抛错
- get_suspensions（suspend_d 全量不过滤）与 get_lifecycle_stocks
  （L/D/P/G 分页合并）
- 性能验收：单日常态 2 页请求（offset 只出现 0 与 3000）、每页 0.3s 节流
"""

import os
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from src.services.data_acquisition.models import (
    LifecycleStock,
    MarketDataIntegrityError,
    MarketDailyQuote,
    SuspensionRecord,
)
from src.services.data_acquisition.tushare_client import TushareDataSource

TRADE_DATE = date(2026, 8, 12)
TRADE_DATE_STR = "20260812"
PAGE_SIZE = 3000
DAILY_FIELDS = "ts_code,trade_date,close,pre_close,vol,amount"


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


def gen_codes(n, start=0):
    """生成 n 个唯一 ts_code"""
    return [f"{start + i:06d}.SZ" for i in range(n)]


def daily_df(ts_codes, trade_date=TRADE_DATE_STR, close=10.85, vol=12345.0, amount=2000.25):
    """构造一页 daily 响应 DataFrame"""
    n = len(ts_codes)
    return pd.DataFrame(
        {
            "ts_code": list(ts_codes),
            "trade_date": [trade_date] * n,
            "close": [close] * n,
            "pre_close": [close] * n,
            "vol": [vol] * n,
            "amount": [amount] * n,
        }
    )


def empty_daily_df():
    return pd.DataFrame(columns=["ts_code", "trade_date", "close", "pre_close", "vol", "amount"])


class DailyApiStub:
    """按 (ts_code 参数, offset) 路由 pro.daily 返回页，并记录请求参数

    单日模式不带 ts_code 参数（key 中为 None），历史窗口模式按分块的
    ts_code 逗号串区分，两模式可共用。
    """

    def __init__(self):
        self.pages = {}
        self.calls = []

    def add(self, ts_code, offset, df):
        self.pages[(ts_code, offset)] = df
        return self

    def daily(self, **kwargs):
        self.calls.append(kwargs)
        key = (kwargs.get("ts_code"), kwargs.get("offset", 0))
        return self.pages.get(key, empty_daily_df())


def install_daily(ds, stub):
    ds._pro_api = MagicMock()
    ds._pro_api.daily.side_effect = stub.daily
    return ds._pro_api


# ═══════════════════════════════════════════════════════════════
# 单日模式：get_market_daily_quotes
# ═══════════════════════════════════════════════════════════════


class TestGetMarketDailyQuotes:
    """单日模式分页、首空页语义、Decimal 数值与单位（AC-01 原料）"""

    def test_single_short_page_returns_quotes_and_request_params(self):
        """单页 <3000 直接终止，请求参数（fields/limit/offset/trade_date）精确"""
        stub = DailyApiStub()
        stub.add(None, 0, daily_df(gen_codes(100)))
        ds = make_ds(None)
        install_daily(ds, stub)

        quotes = ds.get_market_daily_quotes(TRADE_DATE, expected_count=5400)

        assert len(quotes) == 100
        assert all(isinstance(q, MarketDailyQuote) for q in quotes)
        assert len(stub.calls) == 1
        call = stub.calls[0]
        assert call["trade_date"] == TRADE_DATE_STR
        assert call["limit"] == PAGE_SIZE
        assert call["offset"] == 0
        assert call["fields"] == DAILY_FIELDS

    def test_exact_3000_page_plus_empty_probe_terminates(self):
        """exact-3000 页 + 空尾页正常终止（尾部探测页）"""
        stub = DailyApiStub()
        stub.add(None, 0, daily_df(gen_codes(3000)))
        stub.add(None, 3000, empty_daily_df())
        ds = make_ds(None)
        install_daily(ds, stub)

        quotes = ds.get_market_daily_quotes(TRADE_DATE, expected_count=3000)

        assert len(quotes) == 3000
        assert [c["offset"] for c in stub.calls] == [0, 3000]

    def test_exact_6000_two_full_pages_plus_empty_probe_terminates(self):
        """exact-6000 两满页 + 空尾页正常终止，共 3 次请求"""
        stub = DailyApiStub()
        stub.add(None, 0, daily_df(gen_codes(3000, start=0)))
        stub.add(None, 3000, daily_df(gen_codes(3000, start=3000)))
        stub.add(None, 6000, empty_daily_df())
        ds = make_ds(None)
        install_daily(ds, stub)

        quotes = ds.get_market_daily_quotes(TRADE_DATE, expected_count=6000)

        assert len(quotes) == 6000
        assert [c["offset"] for c in stub.calls] == [0, 3000, 6000]
        # 两页代码不重叠
        codes = {q.ts_code for q in quotes}
        assert len(codes) == 6000

    def test_normal_market_day_requests_only_two_pages(self):
        """性能验收：约 5400 行的常态交易日仅 2 页请求（offset 只出现 0 与 3000）"""
        stub = DailyApiStub()
        stub.add(None, 0, daily_df(gen_codes(3000, start=0)))
        stub.add(None, 3000, daily_df(gen_codes(2400, start=3000)))
        ds = make_ds(None)
        install_daily(ds, stub)

        quotes = ds.get_market_daily_quotes(TRADE_DATE, expected_count=5400)

        assert len(quotes) == 5400
        assert [c["offset"] for c in stub.calls] == [0, 3000]

    def test_decimal_values_and_original_units(self):
        """数值为 Decimal(str(...)) 精度保持；vol 保持手、amount 保持千元（不转换）"""
        stub = DailyApiStub()
        page = pd.DataFrame(
            {
                "ts_code": ["000001.SZ", "600000.SH"],
                "trade_date": [TRADE_DATE_STR, TRADE_DATE_STR],
                "close": [10.85, 3.14159],
                "pre_close": [10.5, 3.10],
                "vol": [12345.5, 88.0],
                # 第二行 amount 以字符串形态进入（Decimal(str) 路径同样适用）
                "amount": [2000.25, "3000.5"],
            }
        )
        stub.add(None, 0, page)
        ds = make_ds(None)
        install_daily(ds, stub)

        quotes = ds.get_market_daily_quotes(TRADE_DATE, expected_count=5400)

        q = quotes[0]
        assert type(q.close) is Decimal
        assert type(q.vol) is Decimal
        assert type(q.amount) is Decimal
        assert q.close == Decimal("10.85")
        assert q.pre_close == Decimal("10.5")
        assert q.vol == Decimal("12345.5")  # 手，未 ×100
        assert q.amount == Decimal("2000.25")  # 千元，未 ×1000
        assert quotes[1].amount == Decimal("3000.5")
        assert q.trade_date == TRADE_DATE

    def test_first_page_empty_returns_empty_list(self):
        """单日首张空页：返回空列表（由调用方判为全市场空），不抛错"""
        stub = DailyApiStub()
        stub.add(None, 0, empty_daily_df())
        ds = make_ds(None)
        install_daily(ds, stub)

        quotes = ds.get_market_daily_quotes(TRADE_DATE, expected_count=5400)

        assert quotes == []
        assert len(stub.calls) == 1

    def test_expected_count_zero_probes_single_empty_page(self):
        """边界：expected_count=0 → 硬页数=1，仅探测一页"""
        stub = DailyApiStub()
        stub.add(None, 0, empty_daily_df())
        ds = make_ds(None)
        install_daily(ds, stub)

        quotes = ds.get_market_daily_quotes(TRADE_DATE, expected_count=0)

        assert quotes == []
        assert len(stub.calls) == 1

    def test_expected_count_zero_full_page_hits_hard_cap(self):
        """边界：expected_count=0 且返回满页 → 请求第 2 页超硬上限即失败"""
        stub = DailyApiStub()
        stub.add(None, 0, daily_df(gen_codes(3000)))
        ds = make_ds(None)
        install_daily(ds, stub)

        with pytest.raises(MarketDataIntegrityError, match="硬上限"):
            ds.get_market_daily_quotes(TRADE_DATE, expected_count=0)
        assert len(stub.calls) == 1

    def test_negative_expected_count_raises_value_error(self):
        ds = make_ds(None)
        with pytest.raises(ValueError, match="expected_count"):
            ds.get_market_daily_quotes(TRADE_DATE, expected_count=-1)


# ═══════════════════════════════════════════════════════════════
# 共享分页守卫：四类完整性错误（AC-07 原料）
# ═══════════════════════════════════════════════════════════════


class TestMarketDailyPaginationGuards:
    """页签名重复 / 满页无新增 key / 页数超限 / 跨页重复（均抛完整性错误）"""

    def test_page_signature_repeat_raises(self):
        """页签名重复：代理忽略 offset 重复回页（首行 key + 行数重复出现）"""
        same_page = daily_df(gen_codes(3000))
        stub = DailyApiStub()
        stub.add(None, 0, same_page)
        stub.add(None, 3000, same_page)
        ds = make_ds(None)
        install_daily(ds, stub)

        with pytest.raises(MarketDataIntegrityError, match="页签名重复") as exc_info:
            ds.get_market_daily_quotes(TRADE_DATE, expected_count=6000)
        # 错误信息含页数与计数
        msg = str(exc_info.value)
        assert "第 2 页" in msg
        assert "3000" in msg

    def test_full_page_with_no_new_keys_raises(self):
        """满页但新增 key 数为 0：同批代码换序重排整页"""
        codes = gen_codes(3000)
        rotated = codes[1:] + codes[:1]  # 首行不同，避免先触发页签名守卫
        stub = DailyApiStub()
        stub.add(None, 0, daily_df(codes))
        stub.add(None, 3000, daily_df(rotated))
        ds = make_ds(None)
        install_daily(ds, stub)

        with pytest.raises(MarketDataIntegrityError, match="新增 key 数为 0") as exc_info:
            ds.get_market_daily_quotes(TRADE_DATE, expected_count=6000)
        msg = str(exc_info.value)
        assert "第 2 页" in msg
        assert "offset=3000" in msg

    def test_page_count_exceeds_hard_cap_raises(self):
        """页数超过 ceil(expected/3000)+1：expected=6000 → 上限 3 页"""
        call_state = {"n": 0}

        def endless_pages(**kwargs):
            call_state["n"] += 1
            # 每次请求都返回全新手代码的满页（offset 失效的病态 Provider）
            return daily_df(gen_codes(3000, start=call_state["n"] * 100000))

        ds = make_ds(None)
        mock_pro = MagicMock()
        mock_pro.daily.side_effect = endless_pages
        ds._pro_api = mock_pro

        with pytest.raises(MarketDataIntegrityError, match="超过硬上限") as exc_info:
            ds.get_market_daily_quotes(TRADE_DATE, expected_count=6000)
        msg = str(exc_info.value)
        assert "4" in msg and "3" in msg  # 请求页数 4 超过上限 3
        assert mock_pro.daily.call_count == 3  # 第 4 页在请求前被硬上限拦截

    def test_cross_page_duplicate_ts_code_raises(self):
        """跨页重复 ts_code：第二页短页中出现第一页已有代码"""
        first_codes = gen_codes(3000)
        dup_page = daily_df([f"999999.SZ", first_codes[5]])
        stub = DailyApiStub()
        stub.add(None, 0, daily_df(first_codes))
        stub.add(None, 3000, dup_page)
        ds = make_ds(None)
        install_daily(ds, stub)

        with pytest.raises(MarketDataIntegrityError, match="重复行 key") as exc_info:
            ds.get_market_daily_quotes(TRADE_DATE, expected_count=5400)
        msg = str(exc_info.value)
        assert first_codes[5] in msg
        assert "第 2 页" in msg

    def test_duplicate_within_same_page_raises(self):
        """页内重复 ts_code 同样视为完整性错误（禁止 drop_duplicates 静默修复）"""
        codes = gen_codes(10)
        codes_with_dup = codes + [codes[3]]
        stub = DailyApiStub()
        stub.add(None, 0, daily_df(codes_with_dup))
        ds = make_ds(None)
        install_daily(ds, stub)

        with pytest.raises(MarketDataIntegrityError, match="重复行 key"):
            ds.get_market_daily_quotes(TRADE_DATE, expected_count=5400)


# ═══════════════════════════════════════════════════════════════
# 行级校验：日期谓词与数值（架构 §6.1.4）
# ═══════════════════════════════════════════════════════════════


class TestMarketDailyRowValidation:
    """单日模式行级校验：日期谓词与 close/vol/amount 数值合法性"""

    def _single_page_ds(self, page):
        stub = DailyApiStub()
        stub.add(None, 0, page)
        ds = make_ds(None)
        install_daily(ds, stub)
        return ds

    def test_row_with_wrong_trade_date_raises(self):
        """出现非目标日期行 → 完整性错误（含 ts_code）"""
        codes = gen_codes(5)
        page = daily_df(codes)
        page.loc[2, "trade_date"] = "20260811"
        ds = self._single_page_ds(page)

        with pytest.raises(MarketDataIntegrityError, match="非目标日期") as exc_info:
            ds.get_market_daily_quotes(TRADE_DATE, expected_count=5400)
        assert codes[2] in str(exc_info.value)

    def test_close_zero_raises(self):
        codes = gen_codes(3)
        page = daily_df(codes)
        page.loc[1, "close"] = 0.0
        ds = self._single_page_ds(page)

        with pytest.raises(MarketDataIntegrityError, match="close 非法") as exc_info:
            ds.get_market_daily_quotes(TRADE_DATE, expected_count=5400)
        assert codes[1] in str(exc_info.value)

    def test_close_negative_raises(self):
        page = daily_df(gen_codes(3))
        page.loc[0, "close"] = -1.5
        ds = self._single_page_ds(page)

        with pytest.raises(MarketDataIntegrityError, match="close 非法"):
            ds.get_market_daily_quotes(TRADE_DATE, expected_count=5400)

    def test_vol_negative_raises(self):
        codes = gen_codes(3)
        page = daily_df(codes)
        page.loc[0, "vol"] = -100.0
        ds = self._single_page_ds(page)

        with pytest.raises(MarketDataIntegrityError, match="vol 非法") as exc_info:
            ds.get_market_daily_quotes(TRADE_DATE, expected_count=5400)
        assert codes[0] in str(exc_info.value)

    def test_amount_negative_raises(self):
        page = daily_df(gen_codes(3))
        page.loc[0, "amount"] = -5.0
        ds = self._single_page_ds(page)

        with pytest.raises(MarketDataIntegrityError, match="amount 非法"):
            ds.get_market_daily_quotes(TRADE_DATE, expected_count=5400)

    def test_nan_close_raises(self):
        """close=NaN → 完整性错误"""
        page = daily_df(gen_codes(3))
        page.loc[0, "close"] = np.nan
        ds = self._single_page_ds(page)

        with pytest.raises(MarketDataIntegrityError, match="close"):
            ds.get_market_daily_quotes(TRADE_DATE, expected_count=5400)

    def test_infinity_close_raises(self):
        """close=Infinity → 非有限数完整性错误"""
        page = daily_df(gen_codes(3))
        page.loc[0, "close"] = float("inf")
        ds = self._single_page_ds(page)

        with pytest.raises(MarketDataIntegrityError, match="非有限数"):
            ds.get_market_daily_quotes(TRADE_DATE, expected_count=5400)

    def test_zero_vol_and_amount_allowed(self):
        """vol=0 / amount=0 合法（>=0 谓词，停牌补值口径由 plan-03 处理）"""
        page = daily_df(gen_codes(2), vol=0.0, amount=0.0)
        ds = self._single_page_ds(page)

        quotes = ds.get_market_daily_quotes(TRADE_DATE, expected_count=5400)
        assert quotes[0].vol == Decimal("0.0")
        assert quotes[0].amount == Decimal("0.0")

    def test_pre_close_none_allowed(self):
        """pre_close 可为空（Optional）"""
        page = daily_df(gen_codes(2))
        page.loc[0, "pre_close"] = np.nan
        ds = self._single_page_ds(page)

        quotes = ds.get_market_daily_quotes(TRADE_DATE, expected_count=5400)
        assert quotes[0].pre_close is None
        assert quotes[1].pre_close == Decimal("10.85")

    def test_missing_ts_code_raises(self):
        """缺 ts_code 列 → 行 key 全为 None，分页守卫以重复行 key 拦截"""
        page = daily_df(gen_codes(3)).drop(columns=["ts_code"])
        ds = self._single_page_ds(page)

        with pytest.raises(MarketDataIntegrityError, match="重复行 key=None"):
            ds.get_market_daily_quotes(TRADE_DATE, expected_count=5400)


# ═══════════════════════════════════════════════════════════════
# 历史窗口模式：get_close_quotes_in_window
# ═══════════════════════════════════════════════════════════════


class TestGetCloseQuotesInWindow:
    """历史窗口模式谓词、首空页语义、批次内分块（AC-13 原料）"""

    WINDOW_START = date(2026, 7, 13)
    WINDOW_END = date(2026, 8, 11)

    def test_window_query_params_and_membership(self):
        """请求参数（ts_code 逗号拼接/start/end/limit/offset/fields）与批次归属"""
        codes = ["000001.SZ", "600000.SH", "830001.BJ"]
        dates = ["20260713", "20260720", "20260811"]
        rows = {"ts_code": [], "trade_date": [], "close": [], "pre_close": [], "vol": [], "amount": []}
        for c in codes:
            for d in dates:
                rows["ts_code"].append(c)
                rows["trade_date"].append(d)
                rows["close"].append(10.0)
                rows["pre_close"].append(9.9)
                rows["vol"].append(1000.0)
                rows["amount"].append(500.0)
        stub = DailyApiStub()
        stub.add(",".join(codes), 0, pd.DataFrame(rows))
        ds = make_ds(None)
        install_daily(ds, stub)

        quotes = ds.get_close_quotes_in_window(codes, self.WINDOW_START, self.WINDOW_END)

        assert len(quotes) == 9
        assert {q.ts_code for q in quotes} == set(codes)
        for q in quotes:
            assert self.WINDOW_START <= q.trade_date <= self.WINDOW_END
        call = stub.calls[0]
        assert call["ts_code"] == ",".join(codes)
        assert call["start_date"] == "20260713"
        assert call["end_date"] == "20260811"
        assert call["limit"] == PAGE_SIZE
        assert call["offset"] == 0
        assert call["fields"] == DAILY_FIELDS
        # 升序排列（plan-03 按升序缓存消费）
        assert quotes == sorted(quotes, key=lambda q: (q.trade_date, q.ts_code))

    def test_window_two_full_pages_plus_probe(self):
        """100 只 × 60 自然日 = 6000 候选行：两满页 + 空尾页正常终止"""
        window_start = date(2026, 6, 13)  # [6-13, 8-11] 共 60 个自然日
        codes = gen_codes(100, start=100000)
        dates = [(window_start + timedelta(days=i)) for i in range(60)]
        all_rows = {"ts_code": [], "trade_date": [], "close": [], "pre_close": [], "vol": [], "amount": []}
        for c in codes:
            for d in dates:
                all_rows["ts_code"].append(c)
                all_rows["trade_date"].append(d.strftime("%Y%m%d"))
                all_rows["close"].append(5.0)
                all_rows["pre_close"].append(5.0)
                all_rows["vol"].append(10.0)
                all_rows["amount"].append(20.0)
        full = pd.DataFrame(all_rows)
        ts_param = ",".join(codes)
        stub = DailyApiStub()
        stub.add(ts_param, 0, full.iloc[:3000])
        stub.add(ts_param, 3000, full.iloc[3000:6000])
        stub.add(ts_param, 6000, empty_daily_df())
        ds = make_ds(None)
        install_daily(ds, stub)

        quotes = ds.get_close_quotes_in_window(codes, window_start, self.WINDOW_END)

        assert len(quotes) == 6000
        assert [c["offset"] for c in stub.calls] == [0, 3000, 6000]

    def test_window_first_empty_page_returns_empty_list(self):
        """历史窗口首张空页 = 窗口无命中：返回空列表不抛错"""
        stub = DailyApiStub()
        stub.add("000001.SZ", 0, empty_daily_df())
        ds = make_ds(None)
        install_daily(ds, stub)

        quotes = ds.get_close_quotes_in_window(["000001.SZ"], self.WINDOW_START, self.WINDOW_END)

        assert quotes == []
        assert len(stub.calls) == 1

    def test_window_out_of_range_date_raises(self):
        """窗口外日期行（早于 window_start）→ 完整性错误"""
        codes = ["000001.SZ"]
        page = daily_df(codes, trade_date="20260712")  # 早一天
        stub = DailyApiStub()
        stub.add(",".join(codes), 0, page)
        ds = make_ds(None)
        install_daily(ds, stub)

        with pytest.raises(MarketDataIntegrityError, match="窗口外日期"):
            ds.get_close_quotes_in_window(codes, self.WINDOW_START, self.WINDOW_END)

    def test_window_later_than_end_date_raises(self):
        """窗口外日期行（晚于 window_end）→ 完整性错误"""
        codes = ["000001.SZ"]
        page = daily_df(codes, trade_date="20260812")
        stub = DailyApiStub()
        stub.add(",".join(codes), 0, page)
        ds = make_ds(None)
        install_daily(ds, stub)

        with pytest.raises(MarketDataIntegrityError, match="窗口外日期"):
            ds.get_close_quotes_in_window(codes, self.WINDOW_START, self.WINDOW_END)

    def test_window_foreign_code_raises(self):
        """批次外代码行 → 完整性错误"""
        codes = ["000001.SZ"]
        page = daily_df(["999999.SZ"], trade_date="20260720")
        stub = DailyApiStub()
        stub.add(",".join(codes), 0, page)
        ds = make_ds(None)
        install_daily(ds, stub)

        with pytest.raises(MarketDataIntegrityError, match="批次外代码"):
            ds.get_close_quotes_in_window(codes, self.WINDOW_START, self.WINDOW_END)

    def test_window_duplicate_row_key_across_pages_raises(self):
        """复合 key (ts_code, trade_date) 跨页重复 → 完整性错误"""
        codes = gen_codes(60, start=200000)
        dates = [(self.WINDOW_START + timedelta(days=i)).strftime("%Y%m%d") for i in range(60)]
        rows = {"ts_code": [], "trade_date": [], "close": [], "pre_close": [], "vol": [], "amount": []}
        for c in codes:
            for d in dates:
                rows["ts_code"].append(c)
                rows["trade_date"].append(d)
                rows["close"].append(5.0)
                rows["pre_close"].append(5.0)
                rows["vol"].append(10.0)
                rows["amount"].append(20.0)
        full = pd.DataFrame(rows)  # 3600 行
        ts_param = ",".join(codes)
        dup_row = full.iloc[[0, 1, 2]]  # 首行与第一页首行同 (code, date)
        stub = DailyApiStub()
        stub.add(ts_param, 0, full.iloc[:3000])
        stub.add(ts_param, 3000, dup_row)
        ds = make_ds(None)
        install_daily(ds, stub)

        with pytest.raises(MarketDataIntegrityError, match="重复行 key"):
            ds.get_close_quotes_in_window(codes, self.WINDOW_START, self.WINDOW_END)

    def test_window_chunked_when_over_100_codes(self):
        """>100 只代码按 100/批内部分块：两块各自独立分页"""
        codes = gen_codes(150, start=300000)
        chunk1, chunk2 = codes[:100], codes[100:]
        stub = DailyApiStub()
        stub.add(",".join(chunk1), 0, daily_df(chunk1[:3], trade_date="20260720"))
        stub.add(",".join(chunk2), 0, daily_df(chunk2[:3], trade_date="20260721"))
        ds = make_ds(None)
        install_daily(ds, stub)

        quotes = ds.get_close_quotes_in_window(codes, self.WINDOW_START, self.WINDOW_END)

        assert len(quotes) == 6
        assert len(stub.calls) == 2
        ts_params = [c["ts_code"] for c in stub.calls]
        assert ",".join(chunk1) in ts_params
        assert ",".join(chunk2) in ts_params
        for param in ts_params:
            assert len(param.split(",")) <= 100
        # 两块参数并集等于批次全集
        merged = set(",".join(ts_params).split(","))
        assert merged == set(codes)

    def test_window_page_count_exceeds_candidates_cap_raises(self):
        """历史模式硬页数 = ceil(候选行/3000)+1：3 只 × 10 日 → 上限 2 页"""
        codes = ["000001.SZ", "000002.SZ", "000003.SZ"]
        call_state = {"n": 0}

        def endless_pages(**kwargs):
            call_state["n"] += 1
            # 与批次无关的满页新 key（行级校验在合并后才会执行）
            return daily_df(gen_codes(3000, start=call_state["n"] * 100000), trade_date="20260720")

        ds = make_ds(None)
        mock_pro = MagicMock()
        mock_pro.daily.side_effect = endless_pages
        ds._pro_api = mock_pro

        with pytest.raises(MarketDataIntegrityError, match="超过硬上限"):
            ds.get_close_quotes_in_window(
                codes, self.WINDOW_START, self.WINDOW_START + timedelta(days=9)
            )
        assert mock_pro.daily.call_count == 2

    def test_window_empty_codes_returns_empty_without_request(self):
        ds = make_ds(None)
        mock_pro = MagicMock()
        ds._pro_api = mock_pro

        quotes = ds.get_close_quotes_in_window([], self.WINDOW_START, self.WINDOW_END)

        assert quotes == []
        mock_pro.daily.assert_not_called()

    def test_window_invalid_range_raises_value_error(self):
        ds = make_ds(None)
        with pytest.raises(ValueError, match="开始日期不能晚于结束日期"):
            ds.get_close_quotes_in_window(
                ["000001.SZ"], self.WINDOW_END, self.WINDOW_START
            )


# ═══════════════════════════════════════════════════════════════
# suspend_d 停牌查询（AC-13 原料）
# ═══════════════════════════════════════════════════════════════


class TestGetSuspensions:
    """get_suspensions：原始行保真（日期归一化），不做日期/类型过滤（ADR-3）

    上游实测：代理忽略 suspend_date 查询过滤、且把日期列命名为 trade_date
    （官方 schema 为 suspend_date），适配器双键兼容并归一化为 suspend_date。
    """

    def test_proxy_schema_trade_date_parsed_unfiltered(self):
        """代理 schema（trade_date 列）：多日期行全部保留且逐行解析，不做过滤"""
        mock_pro = MagicMock()
        mock_pro.suspend_d.return_value = pd.DataFrame(
            {
                "ts_code": ["000001.SZ", "600000.SH", "830001.BJ", "000002.SZ"],
                "trade_date": ["20260812", "20260811", "20260812", "20260801"],
                "suspend_type": ["S", "S", "M", "R"],
                "suspend_timing": [None, "开盘", None, None],
            }
        )
        ds = make_ds(mock_pro)

        records = ds.get_suspensions(TRADE_DATE)

        # 忠实返回全部 4 行（含非目标日期行），不做客户端过滤
        assert len(records) == 4
        assert all(isinstance(r, SuspensionRecord) for r in records)
        # trade_date 列归一化为 suspend_date，逐行 YYYYMMDD 解析
        assert records[0].suspend_date == TRADE_DATE
        assert records[1].suspend_date == date(2026, 8, 11)
        assert records[2].suspend_date == TRADE_DATE
        assert records[3].suspend_date == date(2026, 8, 1)
        # 不过滤类型：S / M / R 都返回，判定交 plan-03
        assert {r.suspend_type for r in records} == {"S", "M", "R"}
        assert records[0].suspend_timing is None
        assert records[1].suspend_timing == "开盘"
        # 请求不传 fields（取原生 schema），仍传 suspend_date 查询参数
        mock_pro.suspend_d.assert_called_once_with(suspend_date=TRADE_DATE_STR)

    def test_official_schema_suspend_date_parsed(self):
        """官方 schema（suspend_date 列）同样兼容：双键归一化"""
        mock_pro = MagicMock()
        mock_pro.suspend_d.return_value = pd.DataFrame(
            {
                "ts_code": ["000001.SZ"],
                "suspend_date": ["20260812"],
                "suspend_type": ["S"],
                "suspend_timing": [None],
            }
        )
        ds = make_ds(mock_pro)

        records = ds.get_suspensions(TRADE_DATE)

        assert len(records) == 1
        assert records[0].suspend_date == TRADE_DATE

    def test_invalid_date_raises_integrity_error(self):
        """日期解析失败 → 完整性错误（含字段名与 ts_code）"""
        mock_pro = MagicMock()
        mock_pro.suspend_d.return_value = pd.DataFrame(
            {
                "ts_code": ["000001.SZ"],
                "trade_date": ["2026/08/12"],  # 非 YYYYMMDD
                "suspend_type": ["S"],
                "suspend_timing": [None],
            }
        )
        ds = make_ds(mock_pro)

        with pytest.raises(MarketDataIntegrityError, match="无法解析") as exc_info:
            ds.get_suspensions(TRADE_DATE)
        msg = str(exc_info.value)
        assert "trade_date" in msg
        assert "000001.SZ" in msg

    def test_missing_date_columns_raises(self):
        """suspend_date/trade_date 均缺失 → 完整性错误"""
        mock_pro = MagicMock()
        mock_pro.suspend_d.return_value = pd.DataFrame(
            {
                "ts_code": ["000001.SZ"],
                "suspend_type": ["S"],
                "suspend_timing": [None],
            }
        )
        ds = make_ds(mock_pro)

        with pytest.raises(MarketDataIntegrityError, match="缺少日期字段"):
            ds.get_suspensions(TRADE_DATE)

    def test_empty_result_returns_empty_list(self):
        """边界：suspend_d 无记录 → 空列表"""
        mock_pro = MagicMock()
        mock_pro.suspend_d.return_value = pd.DataFrame(
            columns=["ts_code", "trade_date", "suspend_type", "suspend_timing"]
        )
        ds = make_ds(mock_pro)

        assert ds.get_suspensions(TRADE_DATE) == []
        mock_pro.suspend_d.assert_called_once()


# ═══════════════════════════════════════════════════════════════
# L/D/P/G 生命周期拉取（ADR-2）
# ═══════════════════════════════════════════════════════════════


LIFECYCLE_FIELDS = (
    "ts_code,symbol,name,area,industry,market,exchange,"
    "list_status,list_date,delist_date"
)


def lifecycle_df(ts_codes, list_status, exchange="SZSE", list_date="20200101", delist_date=None):
    n = len(ts_codes)
    return pd.DataFrame(
        {
            "ts_code": list(ts_codes),
            "symbol": [c.split(".")[0] for c in ts_codes],
            "name": [f"股票{i}" for i in range(n)],
            "area": ["深圳"] * n,
            "industry": ["银行"] * n,
            "market": ["主板"] * n,
            "exchange": [exchange] * n,
            "list_status": [list_status] * n,
            "list_date": [list_date] * n,
            "delist_date": [delist_date] * n,
        }
    )


class TestGetLifecycleStocks:
    """get_lifecycle_stocks：四状态分页合并，不写库（AC-13 原料）"""

    def _install(self, pages):
        """pages: {(list_status, offset): DataFrame}"""
        calls = []

        def stock_basic_side_effect(**kwargs):
            calls.append(kwargs)
            key = (kwargs.get("list_status"), kwargs.get("offset", 0))
            return pages.get(
                key,
                pd.DataFrame(
                    columns=["ts_code", "symbol", "name", "area", "industry", "market",
                             "exchange", "list_status", "list_date", "delist_date"]
                ),
            )

        mock_pro = MagicMock()
        mock_pro.stock_basic.side_effect = stock_basic_side_effect
        return mock_pro, calls

    def test_four_statuses_merged_with_l_pagination(self):
        """L 状态跨页分页 + D 带 delist_date + G 空日期合法，四状态合并返回"""
        l_codes_page1 = gen_codes(3000, start=0)
        l_codes_page2 = gen_codes(500, start=3000)
        mock_pro, calls = self._install(
            {
                ("L", 0): lifecycle_df(l_codes_page1, "L"),
                ("L", 3000): lifecycle_df(l_codes_page2, "L"),
                ("D", 0): lifecycle_df(gen_codes(10, start=10000), "D",
                                      exchange="SH", list_date="19990101", delist_date="20250601"),
                ("P", 0): lifecycle_df(gen_codes(5, start=20000), "P"),
                ("G", 0): lifecycle_df(gen_codes(3, start=30000), "G", list_date=None),
            }
        )
        ds = make_ds(mock_pro)

        stocks = ds.get_lifecycle_stocks()

        assert len(stocks) == 3000 + 500 + 10 + 5 + 3
        assert all(isinstance(s, LifecycleStock) for s in stocks)
        by_status = {}
        for s in stocks:
            by_status.setdefault(s.list_status, []).append(s)
        assert set(by_status) == {"L", "D", "P", "G"}
        # L 分页：offset 0 与 3000 各请求一次
        l_offsets = [c["offset"] for c in calls if c["list_status"] == "L"]
        assert l_offsets == [0, 3000]
        # 四状态按 L/D/P/G 顺序请求（L 有两页），exchange="" 全量
        status_order = []
        for c in calls:
            if not status_order or status_order[-1] != c["list_status"]:
                status_order.append(c["list_status"])
        assert status_order == ["L", "D", "P", "G"]
        for c in calls:
            assert c["exchange"] == ""
            assert c["fields"] == LIFECYCLE_FIELDS
            assert c["limit"] == 3000
        # D 状态含 delist_date（date 对象）
        assert all(s.delist_date == date(2025, 6, 1) for s in by_status["D"])
        # G 状态日期为空合法（固定排除在 plan-03）
        assert all(s.list_date is None and s.delist_date is None for s in by_status["G"])
        # 常规字段映射
        assert by_status["L"][0].exchange == "SZSE"
        assert by_status["L"][0].list_date == date(2020, 1, 1)
        assert by_status["L"][0].name is not None

    def test_status_with_zero_rows_returns_empty_for_that_status(self):
        """边界：某状态 0 行 → 该状态空集，合并继续"""
        mock_pro, calls = self._install(
            {
                ("L", 0): lifecycle_df(gen_codes(4), "L"),
                ("D", 0): lifecycle_df(gen_codes(2, start=10000), "D",
                                      list_date="19990101", delist_date="20250101"),
                ("P", 0): lifecycle_df(gen_codes(1, start=20000), "P"),
                # G 无页 → 空响应
            }
        )
        ds = make_ds(mock_pro)

        stocks = ds.get_lifecycle_stocks()

        assert len(stocks) == 7
        assert {s.list_status for s in stocks} == {"L", "D", "P"}
        # G 仍被请求了一次（空集）
        assert any(c["list_status"] == "G" for c in calls)


# ═══════════════════════════════════════════════════════════════
# 节流与重试集成（性能验收 §8.1）
# ═══════════════════════════════════════════════════════════════


class TestRateLimitAndRetryIntegration:
    """每页请求走 0.3s 节流 + 3 次退避重试（_execute_with_retry 集成）"""

    def test_rate_limit_enforced_per_page_request(self):
        """2 页请求 → _enforce_rate_limit 恰好触发 2 次"""
        stub = DailyApiStub()
        stub.add(None, 0, daily_df(gen_codes(3000)))
        stub.add(None, 3000, daily_df(gen_codes(2400, start=3000)))
        ds = make_ds(None)
        install_daily(ds, stub)

        throttle_calls = []
        original = ds._enforce_rate_limit

        def spy():
            throttle_calls.append(1)
            original()

        ds._enforce_rate_limit = spy

        ds.get_market_daily_quotes(TRADE_DATE, expected_count=5400)

        assert len(stub.calls) == 2
        assert len(throttle_calls) == 2

    def test_daily_page_retried_on_transient_failure(self):
        """瞬时异常经 _execute_with_retry 退避重试后成功"""
        good_page = daily_df(gen_codes(10))
        mock_pro = MagicMock()
        mock_pro.daily.side_effect = [Exception("网络抖动"), Exception("网络抖动"), good_page]
        ds = make_ds(mock_pro)

        quotes = ds.get_market_daily_quotes(TRADE_DATE, expected_count=5400)

        assert len(quotes) == 10
        assert mock_pro.daily.call_count == 3

    def test_daily_non_retryable_error_fails_immediately(self):
        """非可重试关键字（权限不足）立即失败，不重试"""
        mock_pro = MagicMock()
        mock_pro.daily.side_effect = Exception("抱歉，您没有权限不足访问该接口")
        ds = make_ds(mock_pro)

        from src.services.data_acquisition.exceptions import DataFetchError

        with pytest.raises(DataFetchError, match="不可恢复"):
            ds.get_market_daily_quotes(TRADE_DATE, expected_count=5400)
        assert mock_pro.daily.call_count == 1
