"""
测试同花顺板块接口输出

调用 TushareDataSource 的板块相关方法，查看原始返回数据。

用法：
    cd server
    python scripts/test_ths_sectors.py                          # 全部测试
    python scripts/test_ths_sectors.py --only list              # 只测板块列表
    python scripts/test_ths_sectors.py --only member            # 只测成分股
    python scripts/test_ths_sectors.py --only daily             # 只测板块日线
    python scripts/test_ths_sectors.py --sector-code 885835.TI  # 指定板块代码
"""

import argparse
import json
import os
import sys

# 将 server/ 加入 sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

from src.services.data_acquisition.tushare_client import TushareDataSource


def test_sector_list(ds: TushareDataSource, sector_type: str | None = None):
    """测试获取板块列表"""
    print(f"\n{'='*60}")
    label = f"{sector_type}板块" if sector_type else "全部板块"
    print(f">>> 获取{label}列表 (ths_index)")
    print(f"{'='*60}")

    try:
        sectors = ds.get_sector_list(sector_type=sector_type)
        print(f"✅ 获取到 {len(sectors)} 个板块")

        # 按类型分组统计
        by_type = {}
        for s in sectors:
            by_type.setdefault(s.type, []).append(s)

        for stype, items in by_type.items():
            print(f"\n  [{stype}] 共 {len(items)} 个，展示前 5 个:")
            for s in items[:5]:
                print(f"    {s.code}  {s.name}")

        # 打印前 3 个的完整数据
        print(f"\n  前 3 个板块完整数据:")
        for s in sectors[:3]:
            print(f"    {json.dumps(s.model_dump(mode='json'), ensure_ascii=False)}")

        return sectors
    except Exception as e:
        print(f"❌ 获取板块列表失败: {e}")
        return []


def test_sector_members(ds: TushareDataSource, ts_code: str):
    """测试获取板块成分股"""
    print(f"\n{'='*60}")
    print(f">>> 获取板块成分股 (ths_member) — {ts_code}")
    print(f"{'='*60}")

    try:
        result = ds.get_sector_members(ts_code=ts_code)
        print(f"✅ 板块 {result.sector_code} 获取到 {len(result.stock_codes)} 只成分股")
        print(f"  前 20 只: {result.stock_codes[:20]}")
        print(f"\n  完整数据:")
        print(f"    {json.dumps(result.model_dump(mode='json'), ensure_ascii=False)[:500]}...")
        return result
    except Exception as e:
        print(f"❌ 获取成分股失败: {e}")
        return None


def test_sector_daily(
    ds: TushareDataSource, ts_code: str, start_date: str, end_date: str
):
    """测试获取板块日线行情"""
    print(f"\n{'='*60}")
    print(f">>> 获取板块日线行情 (ths_daily) — {ts_code}")
    print(f"    日期范围: {start_date} ~ {end_date}")
    print(f"{'='*60}")

    from datetime import date as date_type

    start = date_type.fromisoformat(start_date)
    end = date_type.fromisoformat(end_date)

    # 先查找板块名称
    try:
        sectors = ds.get_sector_list()
        sector_name = None
        sector_type = None
        for s in sectors:
            if s.code == ts_code:
                sector_name = s.name
                sector_type = s.type
                break

        if not sector_name:
            print(f"⚠️ 未在板块列表中找到 {ts_code}，尝试直接调用 ths_daily...")
            # 直接用 pro_api 调用
            pro = ds._get_pro_api()
            df = pro.ths_daily(
                ts_code=ts_code,
                start_date=start_date.replace("-", ""),
                end_date=end_date.replace("-", ""),
            )
            print(f"✅ 获取到 {len(df)} 条数据")
            print(f"  列名: {list(df.columns)}")
            print(f"  前 5 条:")
            print(df.head().to_string(index=False))
            return
    except Exception as e:
        print(f"⚠️ 查找板块名称失败: {e}")

    try:
        quotes = ds.get_sector_daily_data(
            sector_name=sector_name or ts_code,
            sector_type=sector_type or "industry",
            start_date=start,
            end_date=end,
        )
        print(f"✅ 获取到 {len(quotes)} 条日线数据")
        for q in quotes[:5]:
            print(
                f"    {q.trade_date}  O={q.open:.2f}  H={q.high:.2f}  "
                f"L={q.low:.2f}  C={q.close:.2f}  V={q.volume:.0f}"
            )
        if quotes:
            print(f"\n  第一条完整数据:")
            print(f"    {json.dumps(quotes[0].model_dump(mode='json'), ensure_ascii=False)}")
    except Exception as e:
        print(f"❌ 获取板块日线失败: {e}")


def test_raw_api_call(ds: TushareDataSource):
    """直接调用底层 pro_api，查看原始返回"""
    print(f"\n{'='*60}")
    print(f">>> 直接调用 pro_api 查看原始返回 (ths_index)")
    print(f"{'='*60}")

    try:
        pro = ds._get_pro_api()

        # 行业板块
        print("\n  [行业板块 ths_index(exchange='A', type='I')]")
        df = pro.ths_index(exchange="A", type="I")
        print(f"  返回行数: {len(df)}, 列: {list(df.columns)}")
        print(f"  dtypes:\n{df.dtypes.to_string()}")
        print(f"  前 3 行:")
        print(df.head(3).to_string(index=False))

        # 概念板块
        print("\n  [概念板块 ths_index(exchange='A', type='N')]")
        df2 = pro.ths_index(exchange="A", type="N")
        print(f"  返回行数: {len(df2)}, 列: {list(df2.columns)}")
        print(f"  前 3 行:")
        print(df2.head(3).to_string(index=False))

    except Exception as e:
        print(f"❌ 原始调用失败: {e}")


def main():
    parser = argparse.ArgumentParser(description="测试同花顺板块接口")
    parser.add_argument(
        "--only",
        choices=["list", "member", "daily", "raw"],
        default=None,
        help="只运行指定测试",
    )
    parser.add_argument(
        "--sector-code",
        default="885835.TI",
        help="板块代码 (默认 885835.TI)",
    )
    parser.add_argument(
        "--start-date",
        default="2025-05-01",
        help="日线开始日期 (默认 2025-05-01)",
    )
    parser.add_argument(
        "--end-date",
        default="2025-05-30",
        help="日线结束日期 (默认 2025-05-30)",
    )
    args = parser.parse_args()

    token = os.getenv("TUSHARE_TOKEN", "")
    if not token:
        print("❌ TUSHARE_TOKEN 未配置，请在 .env 文件中设置")
        sys.exit(1)

    api_url = os.getenv("TUSHARE_API_URL", "https://ts.gyzcloud.top/api")
    print(f"API URL : {api_url}")
    print(f"Token   : {token[:8]}...{token[-4:]}")
    print(f"板块代码: {args.sector_code}")

    ds = TushareDataSource()

    if args.only is None or args.only == "raw":
        test_raw_api_call(ds)

    if args.only is None or args.only == "list":
        test_sector_list(ds, sector_type="industry")
        test_sector_list(ds, sector_type="concept")

    if args.only is None or args.only == "member":
        test_sector_members(ds, ts_code=args.sector_code)

    if args.only is None or args.only == "daily":
        test_sector_daily(
            ds, ts_code=args.sector_code, start_date=args.start_date, end_date=args.end_date
        )

    print(f"\n{'='*60}")
    print("测试完成")


if __name__ == "__main__":
    main()
