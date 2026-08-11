"""Tushare 宽基指数接口探测脚本

目的：验证当前代理 https://ts.gyzcloud.top/api 下，各指数接口是否可用、数据是否正常。
覆盖接口：
  - index_basic      指数基础信息
  - index_daily      指数日线行情
  - index_dailybasic 大盘指数每日指标(PE/PB/换手率等)
  - index_weight     指数成分权重
  - index_member     指数成分股(当前在册)
  - index_classify   申万行业分类(已有，对照)
  - sw_daily         申万行业指数日线(已有，对照)

运行: python scripts/probe_index_apis.py
"""
from __future__ import annotations

import os
import sys
import time
import traceback
from datetime import date, timedelta

# 确保能读到项目根目录的 .env
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

from dotenv import load_dotenv

load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))

import tushare as ts
from tushare.pro.client import DataApi

TOKEN = os.getenv("TUSHARE_TOKEN", "").strip()
API_URL = os.getenv("TUSHARE_API_URL", "https://ts.gyzcloud.top/api").strip()

# 主要宽基 / 风格指数（覆盖沪深京三市 + 风格）
MAJOR_INDICES = {
    "000001.SH": "上证指数",
    "000300.SH": "沪深300",
    "000016.SH": "上证50",
    "000905.SH": "中证500",
    "000852.SH": "中证1000",
    "399001.SZ": "深证成指",
    "399006.SZ": "创业板指",
    "899050.BJ": "北证50",
}

# 探测用的日期区间：最近 5 个交易日近似
_TODAY = date.today()
END_DATE = _TODAY.strftime("%Y%m%d")
START_DATE = (_TODAY - timedelta(days=10)).strftime("%Y%m%d")


def make_api() -> DataApi:
    if not TOKEN:
        print("[FATAL] TUSHARE_TOKEN 未配置")
        sys.exit(1)
    api = DataApi(token=TOKEN, timeout=60)
    api._DataApi__http_url = API_URL  # 与项目一致的代理注入方式
    print(f"[INFO] 代理地址: {API_URL}")
    print(f"[INFO] Token: {TOKEN[:8]}...{TOKEN[-4:]}")
    print("=" * 72)
    return api


def probe(title: str, fn):
    """统一执行 + 计时 + 异常归类。返回 (df_or_None, ok_bool)。"""
    print(f"\n>>> {title}")
    t0 = time.time()
    try:
        df = fn()
        elapsed = time.time() - t0
        if df is None:
            print(f"   返回 None  (耗时 {elapsed:.2f}s)")
            return df, False
        if hasattr(df, "empty") and df.empty:
            print(f"   返回空 DataFrame  (耗时 {elapsed:.2f}s)")
            return df, False
        rows, cols = df.shape
        print(f"   ✅ {rows} 行 × {cols} 列  (耗时 {elapsed:.2f}s)")
        print(f"   字段: {list(df.columns)}")
        print(f"   前 3 行预览:")
        print(df.head(3).to_string(index=False))
        return df, True
    except Exception as e:
        elapsed = time.time() - t0
        msg = str(e)
        print(f"   ❌ 失败 (耗时 {elapsed:.2f}s): {type(e).__name__}: {msg[:300]}")
        return None, False


def main():
    api = make_api()
    results: dict[str, str] = {}

    # 1) index_basic —— 全量指数基础信息（按 market 过滤）
    _, ok = probe("1) index_basic  上交所指数列表", lambda: api.index_basic(market="SSE"))
    results["index_basic(SSE)"] = "OK" if ok else "FAIL"

    _, ok = probe("1b) index_basic  按 ts_code 查沪深300", lambda: api.index_basic(ts_code="000300.SH"))
    results["index_basic(ts_code)"] = "OK" if ok else "FAIL"

    # 2) index_daily —— 各宽基指数日线
    daily_ok: list[str] = []
    for code, name in MAJOR_INDICES.items():
        _, ok = probe(
            f"2) index_daily  {name} {code}  ({START_DATE}~{END_DATE})",
            lambda c=code: api.index_daily(ts_code=c, start_date=START_DATE, end_date=END_DATE),
        )
        if ok:
            daily_ok.append(code)
    results[f"index_daily({len(MAJOR_INDICES)}个指数)"] = f"{len(daily_ok)}/{len(MAJOR_INDICES)} OK"

    # 3) index_dailybasic —— 大盘指标 PE/PB/换手率
    db_ok: list[str] = []
    for code in ["000001.SH", "000300.SH", "399001.SZ", "399006.SZ"]:
        name = MAJOR_INDICES.get(code, code)
        _, ok = probe(
            f"3) index_dailybasic  {name} {code}  ({START_DATE}~{END_DATE})",
            lambda c=code: api.index_dailybasic(ts_code=c, start_date=START_DATE, end_date=END_DATE),
        )
        if ok:
            db_ok.append(code)
    results["index_dailybasic"] = f"{len(db_ok)}/4 OK"

    # 4) index_weight —— 成分权重（沪深300）
    _, ok = probe(
        "4) index_weight  沪深300 成分权重 (本月)",
        lambda: api.index_weight(index_code="000300.SH", start_date=START_DATE, end_date=END_DATE),
    )
    results["index_weight"] = "OK" if ok else "FAIL"

    # 5) index_member —— 当前成分股快照（沪深300/中证500）
    for code in ["000300.SH", "000905.SH"]:
        name = MAJOR_INDICES.get(code, code)
        _, ok = probe(
            f"5) index_member  {name} {code} (is_new=Y)",
            lambda c=code: api.index_member(index_code=c, is_new="Y"),
        )
        results[f"index_member({code})"] = "OK" if ok else "FAIL"

    # 6) 对照组：index_classify / sw_daily（项目已用，验证代理整体健康）
    _, ok = probe("6) [对照] index_classify 申万L1 (项目已用)", lambda: api.index_classify(level="L1", src="SW2021"))
    results["index_classify(L1)"] = "OK" if ok else "FAIL"

    _, ok = probe(
        "6b) [对照] sw_daily 申万银行 801010.SI",
        lambda: api.sw_daily(ts_code="801010.SI", start_date=START_DATE, end_date=END_DATE),
    )
    results["sw_daily"] = "OK" if ok else "FAIL"

    # ---------------------------------------------------------------
    # 科创板 / 创业板 主要指数（额外验证）
    # ---------------------------------------------------------------
    print("\n" + "─" * 72)
    print("【科创板 / 创业板相关指数】")
    print("─" * 72)

    # 先发现真实代码：index_basic 按 name 模糊查
    for kw in ("科创", "创业"):
        df, ok = probe(
            f"SI-0) index_basic  按 name 查 '{kw}'",
            lambda k=kw: api.index_basic(name=k),
        )
        if ok:
            results[f"index_basic(name={kw})"] = f"{len(df)} 条"

    # 候选主要指数实测（含行情 + 估值指标）
    # 注意：000833.SH 是错误代码；真正的"科创创业50"是 931643.CSI（中证指数）
    sci_inno_indices = {
        "000688.SH": "科创50",
        "000698.SH": "科创100",
        "000699.SH": "科创200",
        "931643.CSI": "科创创业50",
        "399006.SZ": "创业板指",
        "399102.SZ": "创业板综",
        "399673.SZ": "创业板50",
    }

    si_daily_ok: list[str] = []
    si_basic_ok: list[str] = []
    for code, name in sci_inno_indices.items():
        _, ok = probe(
            f"SI-1) index_daily  {name} {code}  ({START_DATE}~{END_DATE})",
            lambda c=code: api.index_daily(ts_code=c, start_date=START_DATE, end_date=END_DATE),
        )
        if ok:
            si_daily_ok.append(code)

        _, ok = probe(
            f"SI-2) index_dailybasic  {name} {code}  ({START_DATE}~{END_DATE})",
            lambda c=code: api.index_dailybasic(ts_code=c, start_date=START_DATE, end_date=END_DATE),
        )
        if ok:
            si_basic_ok.append(code)

    results["科创创业 index_daily"] = f"{len(si_daily_ok)}/{len(sci_inno_indices)} OK"
    results["科创创业 index_dailybasic"] = f"{len(si_basic_ok)}/{len(sci_inno_indices)} OK"

    # 7) index_global（全球指数，非必需，看代理是否转发）
    _, ok = probe("7) [可选] index_global 美股道琼斯", lambda: api.index_global())
    results["index_global"] = "OK" if ok else "FAIL/不支持"

    print("\n" + "=" * 72)
    print("汇总结果：")
    for k, v in results.items():
        print(f"  {k:40s} → {v}")
    print("=" * 72)


if __name__ == "__main__":
    main()
