"""
查询股票基本信息测试脚本

调用 Tushare stock_basic 接口获取 A 股列表，直接打印返回的完整参数。

用法：
    cd server
    python scripts/query_stock_basic.py              # 默认展示前 10 条
    python scripts/query_stock_basic.py --limit 5       # 展示前 5 条
    python scripts/query_stock_basic.py --symbol 000001  # 查询指定股票
    python scripts/query_stock_basic.py --industry 银行  # 按行业筛选
"""

import argparse
import json
import os
import sys

# 将 server/ 加入 sys.path，使得 from src import ... 正常工作
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

from src.services.data_acquisition.tushare_client import TushareDataSource


def main():
    parser = argparse.ArgumentParser(description="查询 Tushare 股票基本信息")
    parser.add_argument(
        "--limit", type=int, default=10, help="展示前 N 条记录（默认 10）"
    )
    parser.add_argument("--symbol", type=str, default=None, help="查询指定股票代码")
    parser.add_argument("--industry", type=str, default=None, help="按行业筛选")
    args = parser.parse_args()

    token = os.getenv("TUSHARE_TOKEN", "")
    if not token:
        print("❌ TUSHARE_TOKEN 未配置，请在 .env 文件中设置")
        sys.exit(1)

    ds = TushareDataSource()

    # 获取股票列表
    try:
        stocks = ds.get_stock_list()
    except Exception as e:
        print(f"❌ 获取失败: {e}")
        sys.exit(1)

    if not stocks:
        print("⚠️ 股票列表为空")
        sys.exit(0)

    # 筛选
    filtered = stocks
    if args.symbol:
        filtered = [s for s in filtered if s.symbol == args.symbol]
        if not filtered:
            print(f"❌ 未找到股票代码: {args.symbol}")
            sys.exit(1)
    if args.industry:
        filtered = [s for s in filtered if s.industry == args.industry]
        if not filtered:
            print(f"❌ 未找到行业: {args.industry}")
            sys.exit(1)

    # 直接打印完整参数
    display = filtered[: args.limit]
    print(json.dumps([s.model_dump(mode="json") for s in display], indent=2, ensure_ascii=False))

    if len(filtered) > args.limit:
        print(f"\n... 还有 {len(filtered) - args.limit} 条记录未展示（共 {len(filtered)} 条）", file=sys.stderr)


if __name__ == "__main__":
    main()
