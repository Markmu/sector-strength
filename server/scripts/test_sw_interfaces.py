#!/usr/bin/env python3
"""申万行业分类接口可用性探测脚本

检测 index_classify（申万行业分类）与 index_member_all（申万行业成分分级）
的数据是否存在且正常，重点核对两个接口的 code 字段格式是否一致（成分股关联前提）。
直接调用 Tushare pro 接口，不依赖项目封装、不落库。

用法:
    cd server
    python scripts/test_sw_interfaces.py

前置条件:
    - .env 配置 TUSHARE_TOKEN / TUSHARE_API_URL 可用
    - 账户具备申万行业分类接口权限（index_classify 需 2000 积分）

接口文档:
    index_classify     申万行业分类      https://tushare.pro/document/2?doc_id=181
    index_member_all   申万行业成分分级  https://tushare.pro/document/2?doc_id=335
"""
import asyncio
import os
import sys

# 确保可 import src.*
SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SERVER_DIR)

# 从项目根目录加载 .env
from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(SERVER_DIR)
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from src.services.data_acquisition.tushare_client import TushareDataSource
from src.services.data_acquisition.exceptions import DataFetchError


def _check(name: str, fetcher):
    """调用单个接口并打印检测结果。返回 (ok: bool, df)"""
    print(f"\n--- [{name}] ---")
    try:
        df = fetcher()
    except DataFetchError as e:
        print(f"  ✗ 不可恢复错误: {e}")
        return False, None
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        if any(kw in msg for kw in ("权限", "积分", "forbidden", "无权", "访问")):
            print(f"  ✗ 权限不足: {e}")
        else:
            print(f"  ✗ 调用异常: {type(e).__name__}: {e}")
        return False, None

    if df is None or (hasattr(df, "empty") and df.empty):
        print("  ✗ 返回空数据")
        return False, None

    rows = len(df)
    cols = list(df.columns)
    print(f"  ✓ 行数: {rows}    字段({len(cols)}): {cols}")

    import pandas as pd
    with pd.option_context("display.max_columns", None, "display.width", 200):
        print("  抽样（前 5 行）:")
        for _, row in df.head(5).iterrows():
            cells = "  ".join(f"{c}={row[c]}" for c in cols[:10])
            print(f"    {cells}")
    return True, df


async def main():
    client = TushareDataSource()
    print("=== 申万行业分类接口检测 ===")

    pro = client._get_pro_api()

    # 1. index_classify — 申万一级行业列表
    def _classify_l1():
        return client._execute_with_retry(
            lambda: pro.index_classify(level="L1", src="SW2021")
        )

    ok_l1, df_l1 = _check("index_classify L1 申万一级行业", _classify_l1)

    # 2. index_classify — 申万二级行业列表
    def _classify_l2():
        return client._execute_with_retry(
            lambda: pro.index_classify(level="L2", src="SW2021")
        )

    ok_l2, df_l2 = _check("index_classify L2 申万二级行业", _classify_l2)

    # 3. index_classify — 申万三级行业列表
    def _classify_l3():
        return client._execute_with_retry(
            lambda: pro.index_classify(level="L3", src="SW2021")
        )

    ok_l3, df_l3 = _check("index_classify L3 申万三级行业", _classify_l3)

    # 4. index_member_all — 申万行业成分（当前快照）
    def _member_all():
        return client._execute_with_retry(
            lambda: pro.index_member_all(is_new="Y")
        )

    ok_member, df_member = _check("index_member_all 申万成分股（当前快照）", _member_all)

    # ----- code 格式一致性核对（成分股关联前提）-----
    print("\n=== code 字段格式一致性核对 ===")
    if ok_l1 and ok_member:
        classify_codes = set(df_l1["index_code"].astype(str).tolist())
        member_l1_codes = set(df_member["l1_code"].astype(str).dropna().tolist())
        print(f"  index_classify L1 index_code 样例: {list(classify_codes)[:3]}")
        print(f"  index_member_all  l1_code     样例: {list(member_l1_codes)[:3]}")
        # 双向交集比例
        common_l1 = classify_codes & member_l1_codes
        only_classify = classify_codes - member_l1_codes
        only_member = member_l1_codes - classify_codes
        print(
            f"  L1 交集 {len(common_l1)} 条；"
            f"仅 classify 有 {len(only_classify)}；仅 member 有 {len(only_member)}"
        )
        if only_classify:
            print(f"    仅 classify 样例: {list(only_classify)[:3]}")
        if only_member:
            print(f"    仅 member 样例: {list(only_member)[:3]}")
        if classify_codes == member_l1_codes:
            print("  ✓ L1 code 完全一致，可直接关联")
        else:
            print("  ⚠ L1 code 不完全一致，需在 fetch 层做归一化")
    else:
        print("  ✗ 无法核对（接口未全部成功）")

    # 汇总
    print("\n=== 检测汇总 ===")
    results = {
        "index_classify L1": ok_l1,
        "index_classify L2": ok_l2,
        "index_classify L3": ok_l3,
        "index_member_all": ok_member,
    }
    all_ok = all(results.values())
    for name, ok in results.items():
        status = "✓ 正常" if ok else "✗ 异常"
        print(f"  {name:<22} {status}")
    print("\n结论: " + ("全部接口数据正常 ✅" if all_ok else "存在异常，请见上文 ⚠️"))


if __name__ == "__main__":
    asyncio.run(main())
