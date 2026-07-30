#!/usr/bin/env python3
"""ETF 采集链路手动验证脚本（plan-01，第 14 期）

跑通 sync_etf_basic + sync_etf_daily 全链路，验证采集 → 归类 → 计算 → 落库。

用法:
    cd server
    python scripts/test_etf_pipeline.py                 # 当日
    python scripts/test_etf_pipeline.py 20260728        # 指定交易日

前置条件:
    - PostgreSQL 运行中，alembic upgrade head 已执行（etf_basic/etf_daily 表已建）
    - .env 配置 TUSHARE_TOKEN / TUSHARE_API_URL 可用（token 恢复后用真实数据验证；
      token 过期时不影响 pytest 用例——pytest 用 mock 数据源，不依赖真实 Tushare）

输出:
    - sync_etf_basic 结果（入库数 / 归类分布）
    - sync_etf_daily 结果（处理数 / 跳过 / 净值缺失）
    - 抽样核对 share_change / net_inflow 计算正确性
"""
import asyncio
import sys
import os
from datetime import datetime
from decimal import Decimal
from collections import Counter

# 确保可 import src.*
SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SERVER_DIR)

from sqlalchemy import select, func

from src.db.database import AsyncSessionLocal
from src.models.etf import EtfBasic, EtfDaily
from src.services.data_init_etf import EtfDataInitService


def _trade_date_arg() -> str:
    """从命令行取 trade_date，默认当日 YYYYMMDD"""
    if len(sys.argv) >= 2:
        return sys.argv[1]
    return datetime.now().strftime("%Y%m%d")


async def main():
    trade_date = _trade_date_arg()
    print(f"=== ETF 采集链路验证 (trade_date={trade_date}) ===\n")

    async with AsyncSessionLocal() as session:
        svc = EtfDataInitService(session)

        # 1. sync_etf_basic
        print("[1/2] sync_etf_basic ...")
        basic_result = await svc.sync_etf_basic()
        print(f"  结果: {basic_result}")

        # 归类分布核对（架构 §8.5 自检）
        cat_result = await session.execute(
            select(EtfBasic.category, func.count(EtfBasic.id))
            .group_by(EtfBasic.category)
        )
        cat_dist = Counter()
        for cat, cnt in cat_result:
            cat_dist[cat or "(null)"] = cnt
        print(f"  归类分布: {dict(cat_dist)}")

        # 宽基命中率自检（沪深300/中证500/中证1000 等应 100% 命中 broad）
        broad_sample = await session.execute(
            select(EtfBasic.ts_code, EtfBasic.name, EtfBasic.index_name)
            .where(EtfBasic.category == "broad")
            .limit(10)
        )
        print("  宽基样本:")
        for ts_code, name, index_name in broad_sample:
            print(f"    {ts_code}  {name}  ->  {index_name}")

        # 2. sync_etf_daily
        print(f"\n[2/2] sync_etf_daily(trade_date={trade_date}) ...")
        daily_result = await svc.sync_etf_daily(trade_date)
        print(f"  结果: {daily_result}")

        # 当日记录数核对
        cnt_result = await session.execute(
            select(func.count()).select_from(EtfDaily)
        )
        total_daily = cnt_result.scalar()
        print(f"  etf_daily 总记录数: {total_daily}")

        # 抽样核对 share_change / net_inflow 计算正确性（前 5 条有计算值的）
        sample_result = await session.execute(
            select(EtfDaily.ts_code, EtfDaily.share, EtfDaily.unit_nav,
                   EtfDaily.share_change, EtfDaily.net_inflow)
            .where(EtfDaily.share_change.isnot(None))
            .limit(5)
        )
        print("  share_change / net_inflow 抽样核对:")
        for ts_code, share, unit_nav, share_change, net_inflow in sample_result:
            # 手算 net_inflow = share_change × unit_nav / 10000
            if unit_nav and share_change is not None:
                expected = (Decimal(str(share_change)) * Decimal(str(unit_nav))
                            / Decimal("10000"))
            else:
                expected = None
            ok = (
                net_inflow is not None
                and abs(Decimal(str(net_inflow)) - expected.quantize(Decimal("0.0001"))) <= Decimal("0.01")
            ) if expected is not None else net_inflow is None
            flag = "OK " if ok else "FAIL"
            print(
                f"    {flag} {ts_code}  share={share} unit_nav={unit_nav} "
                f"share_change={share_change} net_inflow={net_inflow} "
                f"(期望={expected})"
            )

    print("\n=== 验证完成 ===")


if __name__ == "__main__":
    asyncio.run(main())
