"""
板块资金流（同花顺即时）采集链路验证脚本

跑通 fetcher → 落库 → 查询 的全链路，并打印采集板块数。
盘中/非交易时段均可运行（取同花顺即时接口当前返回值）。

用法：
    cd server
    .venv/bin/python scripts/test_fund_flow.py
"""

import asyncio
import json
import os
import sys
from datetime import date

# 将 server/ 加入 sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import select, func

from src.db.database import AsyncSessionLocal
from src.models.sector_fund_flow import SectorFundFlow
from src.services.data_acquisition.akshare_fund_flow import AkshareFundFlowFetcher


def test_fetcher():
    """测试 fetcher 单独采集（不落库）"""
    print(f"\n{'='*60}")
    print(">>> 1. 测试 AkshareFundFlowFetcher 单独采集")
    print(f"{'='*60}")

    fetcher = AkshareFundFlowFetcher()
    summary = {}
    for sector_type in ("industry", "concept"):
        try:
            items = fetcher.fetch(sector_type)
            summary[sector_type] = len(items)
            print(f"  [{sector_type}] 采集到 {len(items)} 个板块")
            for it in items[:3]:
                print(
                    f"      {it.sector_name}: 净额={it.net_inflow} "
                    f"流入={it.inflow} 流出={it.outflow} 领涨股={it.leading_stock}"
                )
            # 行业/概念之间强制 sleep，避免风控（fetch_all 内部已处理，
            # 这里手动连续调用也加一次）
            if sector_type == "industry":
                import time
                time.sleep(1.0)
        except Exception as e:
            summary[sector_type] = 0
            print(f"  [{sector_type}] 采集失败: {e}")

    print(f"\n  采集汇总: {json.dumps(summary, ensure_ascii=False)}")
    print(f"  期望: industry≈90, concept≈386")
    return summary


async def test_collect_and_persist():
    """测试 collector 落库 + 查询"""
    print(f"\n{'='*60}")
    print(">>> 2. 测试 collector._update_sector_fund_flow 落库")
    print(f"{'='*60}")

    from src.services.data_updater.collector import DataCollector

    collector = DataCollector()

    # 第一次落库
    count1 = await collector._update_sector_fund_flow()
    print(f"  首次落库写入/更新: {count1} 条")

    # 查询当日记录
    today = date.today()
    async with AsyncSessionLocal() as session:
        # 按 sector_type 分组统计
        stmt = (
            select(SectorFundFlow.sector_type, func.count(SectorFundFlow.id))
            .where(SectorFundFlow.trade_date == today)
            .group_by(SectorFundFlow.sector_type)
        )
        result = await session.execute(stmt)
        grouped = {row[0]: row[1] for row in result}

        total_stmt = (
            select(func.count(SectorFundFlow.id))
            .where(SectorFundFlow.trade_date == today)
        )
        total = (await session.execute(total_stmt)).scalar_one()

    print(f"  当日({today}) sector_fund_flow 记录: 共 {total} 条")
    print(f"    分组: {json.dumps(grouped, ensure_ascii=False)}")

    # 抽样打印一条完整记录
    async with AsyncSessionLocal() as session:
        sample_stmt = (
            select(SectorFundFlow)
            .where(SectorFundFlow.trade_date == today)
            .limit(1)
        )
        sample = (await session.execute(sample_stmt)).scalar_one_or_none()
        if sample:
            print(f"\n  抽样记录:")
            print(f"    trade_date   = {sample.trade_date}")
            print(f"    sample_time  = {sample.sample_time}")
            print(f"    sector_type  = {sample.sector_type}")
            print(f"    sector_name  = {sample.sector_name}")
            print(f"    net_inflow   = {sample.net_inflow}")
            print(f"    inflow       = {sample.inflow}")
            print(f"    outflow      = {sample.outflow}")
            print(f"    leading_stock= {sample.leading_stock}")

    # 同分钟重复触发：验证 on_conflict 覆盖（记录数不应翻倍）
    print(f"\n  验证同分钟重复触发不产生重复行...")
    count2 = await collector._update_sector_fund_flow()
    async with AsyncSessionLocal() as session:
        total2 = (
            await session.execute(
                select(func.count(SectorFundFlow.id)).where(
                    SectorFundFlow.trade_date == today
                )
            )
        ).scalar_one()
    print(f"  二次落库写入/更新: {count2} 条，当日总记录仍为: {total2} 条")
    if total2 == total:
        print(f"  ✅ on_conflict_do_update 覆盖生效（未产生重复行）")
    else:
        print(f"  ❌ 警告：总记录数变化（{total} → {total2}），请检查唯一约束")

    return total, grouped


def main():
    print("=" * 60)
    print("板块资金流（同花顺即时）采集链路验证")
    print("=" * 60)

    # 1. fetcher 单独采集
    summary = test_fetcher()

    # 2. 落库 + 查询
    total, grouped = asyncio.run(test_collect_and_persist())

    print(f"\n{'='*60}")
    print("验证完成")
    print(f"  fetcher 采集: industry={summary.get('industry', 0)}, "
          f"concept={summary.get('concept', 0)}")
    print(f"  落库查询: 当日共 {total} 条，分组 {grouped}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
