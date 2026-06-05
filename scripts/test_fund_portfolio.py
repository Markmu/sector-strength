#!/usr/bin/env python
"""
查看 Tushare fund_portfolio 接口的完整返回。

读取 .env 中的 TUSHARE_TOKEN 与 TUSHARE_API_URL，
通过 tushare pro 客户端调用 fund_portfolio 并完整打印结果。

Tushare 文档：基金持仓（fund_portfolio）
- 必填：ts_code（基金代码，支持多只基金逗号分隔）或 ann_date / period（任选一）
- 可选：symbol（股票代码）、ann_date、period、start_date、end_date
- 返回字段（按 Tushare 官方文档）：ts_code, ann_date, end_date, symbol, mkv, amount, stk_mkv_ratio, stk_float_ratio
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# 读取项目根 .env
ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
if ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())

TUSHARE_TOKEN = os.environ.get("TUSHARE_TOKEN", "")
TUSHARE_API_URL = os.environ.get("TUSHARE_API_URL", "http://api.waditu.com/dataapi")
if not TUSHARE_TOKEN:
    print("未找到 TUSHARE_TOKEN，请检查 .env", file=sys.stderr)
    sys.exit(1)

# 让 tushare pro 客户端使用项目配置的网关
os.environ.setdefault("TUSHARE_PRO_API_URL", TUSHARE_API_URL)

import pandas as pd  # noqa: E402
import requests  # noqa: E402

# 直接走 HTTP 拿到原始 JSON，避免 pandas 截断打印
http_url = TUSHARE_API_URL.rstrip("/")


def call_fund_portfolio(params: dict, fields: str = "") -> dict:
    """直接调 Tushare HTTP 接口，返回完整 JSON。"""
    req_params = {
        "api_name": "fund_portfolio",
        "token": TUSHARE_TOKEN,
        "params": params,
        "fields": fields,
    }
    url = f"{http_url}/fund_portfolio"
    resp = requests.post(url, json=req_params, timeout=30)
    resp.raise_for_status()
    return resp.json()


# 多只基金样本：覆盖场内 ETF、LOF、QDII、股票型 / 混合型开放式基金
SAMPLES: list[tuple[str, str, dict]] = [
    (
        "场内 ETF（沪深）",
        "510300.SH",
        {"ts_code": "510300.SH", "period": "20241231"},
    ),
    (
        "场内 ETF（深市）",
        "159915.SZ",
        {"ts_code": "159915.SZ", "period": "20241231"},
    ),
    (
        "LOF 基金",
        "163406.OF",
        {"ts_code": "163406.OF", "period": "20241231"},
    ),
    (
        "主动股票型（参考样本）",
        "005827.OF",
        {"ts_code": "005827.OF", "period": "20241231"},
    ),
]


def render_result(label: str, ts_code: str, params: dict) -> None:
    print("=" * 80)
    print(f"类型: {label}    ts_code: {ts_code}")
    print(f"请求: {json.dumps(params, ensure_ascii=False)}")
    print("=" * 80)
    try:
        result = call_fund_portfolio(params)
    except Exception as exc:  # noqa: BLE001
        print(f"  ❌ 调用失败: {exc!r}")
        return

    code = result.get("code")
    msg = result.get("msg")
    data = result.get("data") or {}
    fields = data.get("fields") or []
    items = data.get("items") or []
    has_more = data.get("has_more")

    if code != 0 or not fields:
        print(f"  ⚠️ code={code} msg={msg!r}  data={data}")
        return

    print(f"  code={code}  has_more={has_more}  records={len(items)}")
    print(f"  fields: {fields}")
    if items:
        df = pd.DataFrame(items, columns=fields)
        print(df.head(5).to_string(index=False))
    else:
        # 空结果时尝试不同参数再确认一次
        print("  (空结果，尝试仅用 ts_code 再次查询确认)")
        try:
            r2 = call_fund_portfolio({"ts_code": ts_code})
            d2 = r2.get("data") or {}
            print(f"     重试 records={len(d2.get('items') or [])}  has_more={d2.get('has_more')}")
            if d2.get("items"):
                df = pd.DataFrame(d2["items"], columns=d2.get("fields") or fields)
                print(df.head(3).to_string(index=False))
        except Exception as exc:  # noqa: BLE001
            print(f"     重试失败: {exc!r}")


def main() -> None:
    print(f"Tushare 网关: {http_url}")
    print(f"Token 前 6 位: {TUSHARE_TOKEN[:6]}***\n")
    for label, ts_code, params in SAMPLES:
        render_result(label, ts_code, params)
        print()


if __name__ == "__main__":
    main()
