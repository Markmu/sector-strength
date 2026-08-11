"""快速验证科创/创业指数代码归属 + index_dailybasic 覆盖范围

发现的问题：
1. index_basic(name=...) 在代理上不过滤，返回 11610 条全量 → 本地精确过滤找真实代码
2. 科创50/100 的 index_dailybasic 返回空 → 确认是数据源不覆盖还是代码问题

验证思路：
- 拉一次 index_basic 全量，本地精确匹配 name 含"科创"/"创业"的代码
- 对真实代码重测 index_dailybasic，确认覆盖范围
"""
from __future__ import annotations

import os
import sys
import time

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

from dotenv import load_dotenv

load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))

from tushare.pro.client import DataApi

TOKEN = os.getenv("TUSHARE_TOKEN", "").strip()
API_URL = os.getenv("TUSHARE_API_URL", "https://ts.gyzcloud.top/api").strip()

api = DataApi(token=TOKEN, timeout=60)
api._DataApi__http_url = API_URL

print("=== 1. 拉取全量 index_basic，本地精确过滤 ===")
t0 = time.time()
df_all = api.index_basic()
print(f"全量 {len(df_all)} 条 (耗时 {time.time()-t0:.1f}s)\n")

for kw in ("科创", "创业"):
    sub = df_all[df_all["name"].str.contains(kw, na=False)]
    print(f"--- name 含 '{kw}': {len(sub)} 条 ---")
    if len(sub) > 0:
        # 只展示常见规模/核心指数（过滤掉策略/主题类）
        core = sub[sub["category"].isin(["规模指数", "综合指数", "成份指数"]) | sub["ts_code"].isin(["000688.SH","000698.SH","000833.SH","399006.SZ","399102.SZ","399673.SZ"])]
        show = core if len(core) > 0 else sub.head(20)
        print(show[["ts_code","name","market","category","base_date","list_date"]].head(25).to_string(index=False))
    print()

print("\n=== 2. 确认候选代码是否存在于 index_basic ===")
candidates = ["000688.SH","000698.SH","000833.SH","399006.SZ","399102.SZ","399673.SZ"]
for code in candidates:
    hit = df_all[df_all["ts_code"] == code]
    if len(hit) > 0:
        r = hit.iloc[0]
        print(f"  {code}: {r['name']}  market={r['market']}  category={r['category']}")
    else:
        print(f"  {code}: ❌ index_basic 中不存在")

print("\n=== 3. 验证 index_dailybasic 对科创/创业的覆盖 ===")
# 官方文档说 index_dailybasic "仅支持上证综指、深证成指等核心指数"
# 测试更广范围确认边界
test_codes = [
    ("000001.SH","上证指数"),
    ("000016.SH","上证50"),
    ("000300.SH","沪深300"),
    ("000905.SH","中证500"),
    ("000852.SH","中证1000"),
    ("000688.SH","科创50"),
    ("000698.SH","科创100"),
    ("399001.SZ","深证成指"),
    ("399006.SZ","创业板指"),
    ("399102.SZ","创业板综"),
    ("399673.SZ","创业板50"),
]
print(f"{'代码':<12}{'名称':<10}{'index_dailybasic'}")
print("-" * 40)
for code, name in test_codes:
    try:
        d = api.index_dailybasic(ts_code=code, start_date="20260801", end_date="20260810")
        if d is not None and not d.empty:
            print(f"{code:<12}{name:<10}✅ {len(d)} 行  (PE_TTM={d.iloc[0].get('pe_ttm','-')})")
        else:
            print(f"{code:<12}{name:<10}⚠️  空（数据源未覆盖）")
    except Exception as e:
        print(f"{code:<12}{name:<10}❌ {str(e)[:60]}")
