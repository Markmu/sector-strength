#!/usr/bin/env python3
"""
测试 Tushare ETF 相关接口可用性与字段口径（供第 14 期 ETF 监控功能架构设计验证）。
用法: python scripts/test_etf_apis.py
"""
import json, os, sys, requests


def load_env():
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    token, api_url = None, "https://ts.gyzcloud.top/api"
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("TUSHARE_TOKEN="):
                    token = line.split("=", 1)[1].strip()
                elif line.startswith("TUSHARE_API_URL="):
                    api_url = line.split("=", 1)[1].strip()
    return token, api_url


def call(api_url, token, api_name, params, fields=""):
    payload = {"api_name": api_name, "token": token, "params": params, "fields": fields}
    resp = requests.post(api_url, json=payload, timeout=30)
    return resp.json()


def show(label, data, max_rows=3):
    print(f"\n{'='*70}\n>>> {label}\n{'='*70}")
    code = data.get("code")
    msg = data.get("msg")
    fields = data.get("fields", [])
    items = data.get("data", {}).get("items", []) if isinstance(data.get("data"), dict) else []
    print(f"code={code}  msg={msg}  fields({len(fields)})={fields}")
    print(f"items total={len(items)}，展示前 {max_rows} 条：")
    for row in items[:max_rows]:
        # 与 fields 对齐成 dict
        print("  " + json.dumps(dict(zip(fields, row)), ensure_ascii=False))


def main():
    token, api_url = load_env()
    if not token:
        print("ERROR: .env 未找到 TUSHARE_TOKEN"); sys.exit(1)
    print(f"API URL : {api_url}\nToken   : {token[:8]}...{token[-4:]}")

    # 1) fund_basic —— 拉场内基金（market=E），看 ETF 分类与"跟踪指数"字段
    show("fund_basic market=E（场内基金，看 fund_type 与跟踪指数字段）",
         call(api_url, token, "fund_basic", {"market": "E"}))

    # 2) fund_share —— ETF 份额（试点：510300 沪深300ETF）
    show("fund_share ts_code=510300.SH（ETF 份额）",
         call(api_url, token, "fund_share", {"ts_code": "510300.SH"}))

    # 3) fund_nav —— 基金净值
    show("fund_nav ts_code=510300.SH（基金净值）",
         call(api_url, token, "fund_nav", {"ts_code": "510300.SH"}))

    # 4) fund_daily —— 场内基金日线（二级市场价格/涨跌幅）
    show("fund_daily ts_code=510300.SH（场内基金日线行情）",
         call(api_url, token, "fund_daily", {"ts_code": "510300.SH", "start_date": "20260701", "end_date": "20260729"}))

    # 5) fund_share 不带 ts_code、按 trade_date 全量（看能否批量按日拉全 ETF 份额）
    show("fund_share trade_date=20260728（按日全量 ETF 份额）",
         call(api_url, token, "fund_share", {"trade_date": "20260728"}))


if __name__ == "__main__":
    main()
