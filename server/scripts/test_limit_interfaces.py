#!/usr/bin/env python3
"""涨跌停专题三接口可用性探测脚本

检测 limit_list_d / limit_step / limit_cpt_list 在「最新交易日」的数据是否存在且正常。
直接调用 Tushare pro 接口，不依赖项目封装、不落库。

用法:
    cd server
    python scripts/test_limit_interfaces.py                # 自动取最新交易日
    python scripts/test_limit_interfaces.py 20260731       # 指定交易日

前置条件:
    - .env 配置 TUSHARE_TOKEN / TUSHARE_API_URL 可用
    - 账户具备涨跌停专题接口权限（通常需较高积分）

接口文档:
    limit_list_d   每日涨跌停/炸板  https://tushare.pro/document/2?doc_id=298
    limit_step     涨停连板天梯    https://tushare.pro/document/2?doc_id=356
    limit_cpt_list 涨停最强板块    https://tushare.pro/document/2?doc_id=357
"""
import asyncio
import os
import sys
from datetime import datetime

# 确保可 import src.*
SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SERVER_DIR)

# 从项目根目录加载 .env
from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(SERVER_DIR)
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from src.services.data_acquisition.tushare_client import TushareDataSource
from src.services.data_acquisition.exceptions import DataFetchError


def _resolve_trade_date(client: TushareDataSource) -> str:
    """通过 trade_cal 获取最近的交易日（YYYYMMDD）"""
    pro = client._get_pro_api()
    # 取 SSE 日历最近 10 天，倒序找第一个 is_open==1
    end = datetime.now().strftime("%Y%m%d")
    df = pro.trade_cal(exchange="SSE", end_date=end, limit=15)
    if df is None or df.empty:
        raise RuntimeError("trade_cal 返回为空，无法确定交易日")
    # 倒序：按 cal_date 降序找最近的开盘日
    df = df.sort_values("cal_date", ascending=False)
    open_dates = df[df["is_open"] == 1]["cal_date"].tolist()
    if not open_dates:
        raise RuntimeError("未找到最近的开放交易日")
    return str(open_dates[0])


def _check(name: str, fetcher, expected_key: str = "trade_date"):
    """调用单个接口并打印检测结果。返回 (ok: bool, rows: int)"""
    print(f"\n--- [{name}] ---")
    try:
        df = fetcher()
    except DataFetchError as e:
        print(f"  ✗ 不可恢复错误: {e}")
        return False, 0
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        if any(kw in msg for kw in ("权限", "积分", "forbidden", "无权", "访问")):
            print(f"  ✗ 权限不足: {e}")
        else:
            print(f"  ✗ 调用异常: {type(e).__name__}: {e}")
        return False, 0

    if df is None or (hasattr(df, "empty") and df.empty):
        print("  ✗ 返回空数据（该交易日可能无数据或未生成）")
        return False, 0

    rows = len(df)
    cols = list(df.columns)
    print(f"  ✓ 行数: {rows}    字段({len(cols)}): {cols}")

    # 交易日字段一致性核对
    if expected_key in cols:
        dates = df[expected_key].astype(str).unique().tolist()
        print(f"  {expected_key} 取值: {dates[:5]}{' ...' if len(dates) > 5 else ''}")

    # 抽样前 5 行（转成可读字符串，NaN 显示为空）
    import pandas as pd
    with pd.option_context("display.max_columns", None, "display.width", 200):
        print("  抽样:")
        for _, row in df.head(5).iterrows():
            cells = "  ".join(f"{c}={row[c]}" for c in cols[:8])
            print(f"    {cells}")
    return True, rows


async def main():
    client = TushareDataSource()

    if len(sys.argv) >= 2:
        trade_date = sys.argv[1]
    else:
        trade_date = _resolve_trade_date(client)
    print(f"=== 涨跌停专题三接口检测 (trade_date={trade_date}) ===")

    pro = client._get_pro_api()

    results = {}

    # 1. limit_list_d — 每日涨跌停/炸板（单次最大 2500）
    def _limit_list_d():
        return client._execute_with_retry(
            lambda: pro.limit_list_d(trade_date=trade_date)
        )

    results["limit_list_d"] = _check("limit_list_d 涨跌停/炸板", _limit_list_d)

    # 2. limit_step — 涨停连板天梯
    def _limit_step():
        return client._execute_with_retry(
            lambda: pro.limit_step(trade_date=trade_date)
        )

    results["limit_step"] = _check("limit_step 连板天梯", _limit_step)

    # 3. limit_cpt_list — 涨停最强板块
    def _limit_cpt_list():
        return client._execute_with_retry(
            lambda: pro.limit_cpt_list(trade_date=trade_date)
        )

    results["limit_cpt_list"] = _check(
        "limit_cpt_list 最强板块", _limit_cpt_list, expected_key="trade_date"
    )

    # 汇总
    print("\n=== 检测汇总 ===")
    all_ok = True
    for name, (ok, rows) in results.items():
        status = "✓ 正常" if ok else "✗ 异常"
        print(f"  {name:<18} {status}  ({rows} 行)")
        if not ok:
            all_ok = False
    print("\n结论: " + ("全部接口数据正常 ✅" if all_ok else "存在异常，请见上文 ⚠️"))


if __name__ == "__main__":
    asyncio.run(main())
