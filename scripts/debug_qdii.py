#!/usr/bin/env python
"""
排查 QDII 基金 fund_portfolio 返回 0 条的原因。

对 513050.SH（中概互联网 50ETF）做多组实验：
1. fund_basic 查基金类型
2. fund_portfolio 用多种 ts_code / period / symbol 组合
3. 不带 ts_code 改用 ann_date 拉所有 QDII 持仓
4. fund_company / fund_div / fund_share 旁路接口验证
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

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
    print("未找到 TUSHARE_TOKEN", file=sys.stderr)
    sys.exit(1)

import requests  # noqa: E402

http_url = TUSHARE_API_URL.rstrip("/")


def call(api_name: str, params: dict, fields: str = "") -> dict:
    body = {
        "api_name": api_name,
        "token": TUSHARE_TOKEN,
        "params": params,
        "fields": fields,
    }
    url = f"{http_url}/{api_name}"
    r = requests.post(url, json=body, timeout=30)
    r.raise_for_status()
    return r.json()


def show(api_name: str, params: dict, label: str = "", fields: str = "") -> None:
    print("=" * 80)
    print(f"[{api_name}]  {label}")
    print(f"params = {json.dumps(params, ensure_ascii=False)}")
    if fields:
        print(f"fields = {fields}")
    print("=" * 80)
    try:
        result = call(api_name, params, fields=fields)
    except Exception as exc:  # noqa: BLE001
        print(f"  ❌ 异常: {exc!r}")
        return
    code = result.get("code")
    msg = result.get("msg")
    data = result.get("data") or {}
    items = data.get("items") or []
    fs = data.get("fields") or []
    print(f"  code={code}  msg={msg!r}  records={len(items)}  has_more={data.get('has_more')}")
    print(f"  fields={fs}")
    if items:
        # 只打印前 5 条
        for row in items[:5]:
            print("  ", row)
    print()


def main() -> None:
    TS = "513050.SH"

    # 1. 查基金基础信息，确认类型 / 名称
    show("fund_basic", {"ts_code": TS}, label="fund_basic(QDII 基金元数据)")
    show("fund_basic", {"ts_code": "513050"}, label="fund_basic(无后缀)")
    show("fund_basic", {"ts_code": "513050.OF"}, label="fund_basic(.OF 后缀)")

    # 2. 不同参数组合
    show("fund_portfolio", {"ts_code": TS}, label="仅 ts_code")
    show("fund_portfolio", {"ts_code": TS, "period": "20240930"}, label="2024Q3 报告期")
    show("fund_portfolio", {"ts_code": TS, "period": "20240630"}, label="2024Q2 报告期")
    show("fund_portfolio", {"ts_code": TS, "period": "20240331"}, label="2024Q1 报告期")
    show("fund_portfolio", {"ts_code": TS, "period": "20231231"}, label="2023 年报")
    show("fund_portfolio", {"ts_code": TS, "period": "20221231"}, label="2022 年报")
    show("fund_portfolio", {"ts_code": TS, "ann_date": "20250121"}, label="按公告日 20250121")
    show("fund_portfolio", {"ts_code": TS, "start_date": "20240101", "end_date": "20251231"}, label="start/end_date 大窗口")
    # 用 .OF 后缀再试
    show("fund_portfolio", {"ts_code": "513050.OF"}, label=".OF 后缀 ts_code")

    # 3. 按港股 symbol 反查
    show("fund_portfolio", {"symbol": "0700.HK"}, label="symbol=0700.HK 反查")
    show("fund_portfolio", {"symbol": "9988.HK"}, label="symbol=9988.HK 反查")
    show("fund_portfolio", {"symbol": "BABA"}, label="symbol=BABA 反查")

    # 4. 拉一段时间所有基金的持仓，看 513050 到底有没有数据
    show("fund_portfolio", {"ann_date": "20250121"}, label="20250121 当天全部公告")
    show("fund_portfolio", {"ann_date": "20250331"}, label="20250331 当天全部公告")
    show("fund_portfolio", {"period": "20241231"}, label="20241231 所有基金持仓")

    # 5. 旁路接口验证
    show("fund_div", {"ts_code": TS}, label="fund_div(分红) - 旁路")
    show("fund_share", {"ts_code": TS}, label="fund_share(份额) - 旁路")


if __name__ == "__main__":
    main()
