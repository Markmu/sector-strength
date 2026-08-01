#!/usr/bin/env python3
"""etf_share_size 接口手动验证脚本

直连 Tushare `pro.etf_share_size`，查询指定交易日的全市场 ETF 份额/规模/净值，
核对返回字段与条数，抽样打印，不做落库。

用法:
    cd server
    python scripts/test_etf_share_size.py              # 默认 20260731
    python scripts/test_etf_share_size.py 20260731     # 指定交易日

前置条件:
    - .env 配置 TUSHARE_TOKEN / TUSHARE_API_URL 可用
"""
import asyncio
import os
import sys
from collections import Counter

# 确保可 import src.*
SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SERVER_DIR)

# 从项目根目录加载 .env（根目录在 server/ 的上一级）
from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(SERVER_DIR)
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from src.services.data_acquisition.tushare_client import TushareDataSource


def _trade_date_arg() -> str:
    """从命令行取 trade_date，默认 20260731"""
    if len(sys.argv) >= 2:
        return sys.argv[1]
    return "20260731"


async def main():
    trade_date = _trade_date_arg()
    print(f"=== etf_share_size 接口验证 (trade_date={trade_date}) ===\n")

    client = TushareDataSource()
    records = client.get_etf_share_size(trade_date)

    if not records:
        print("!! 接口返回空数据，请检查 trade_date 是否为交易日或 token 是否可用。")
        return

    print(f"返回总条数: {len(records)}\n")

    # 字段完整性核对
    sample = records[0]
    print(f"字段列表: {list(sample.keys())}\n")

    # 交易所分布
    exchange_dist = Counter(r.get("exchange") for r in records)
    print(f"交易所分布: {dict(exchange_dist)}\n")

    # 缺失率核对（nav / close 常有缺失）
    for field in ("total_share", "total_size", "nav", "close"):
        missing = sum(1 for r in records if r.get(field) is None)
        print(f"  {field} 缺失: {missing}/{len(records)}")
    print()

    # 抽样打印（前 10 条）
    print("抽样（前 10 条）:")
    for r in records[:10]:
        print(
            f"  {r.get('ts_code') or '-':<12} {(r.get('etf_name') or '-'):<16} "
            f"share={r.get('total_share')} size={r.get('total_size')} "
            f"nav={r.get('nav')} close={r.get('close')} exch={r.get('exchange')}"
        )
    print()

    # 规模 Top 5（亿元，total_size 为万元）
    def _size_bn(r):
        v = r.get("total_size")
        return (v or 0) / 10000.0

    top = sorted(records, key=_size_bn, reverse=True)[:5]
    print("规模 Top 5（亿元）:")
    for r in top:
        print(
            f"  {r.get('ts_code') or '-':<12} {(r.get('etf_name') or '-'):<16} "
            f"size={_size_bn(r):.2f}亿 share={r.get('total_share')}"
        )

    print("\n=== 验证完成 ===")


if __name__ == "__main__":
    asyncio.run(main())
