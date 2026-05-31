#!/usr/bin/env python3
"""
测试 Tushare 同花顺接口权限
用法: python scripts/test_tushare_apis.py
"""

import json
import os
import sys

import requests


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


def call(api_url, token, api_name, params):
    payload = {"api_name": api_name, "token": token, "params": params, "fields": ""}
    print(f"  POST {api_url}")
    print(f"  Body: {json.dumps(payload, ensure_ascii=False)}")
    resp = requests.post(api_url, json=payload, timeout=30)
    return resp.json()


def main():
    token, api_url = load_env()
    if not token:
        print("ERROR: .env 中未找到 TUSHARE_TOKEN")
        sys.exit(1)

    print(f"API URL : {api_url}")
    print(f"Token   : {token[:8]}...{token[-4:]}")

    apis = [
        ("ths_index",  {"exchange": "A", "type": "I"},           "行业板块列表"),
        ("ths_index",  {"exchange": "A", "type": "N"},           "概念板块列表"),
        ("ths_daily",  {"ts_code": "885835.TI", "start_date": "20250501", "end_date": "20250530"}, "板块日线行情"),
        ("ths_daily",  {"ts_code": "885835.TI", "start_date": "20250501", "end_date": "20250530"}, "概念板块日线"),
        ("ths_member", {"ts_code": "885835.TI"},                    "板块成分股"),
    ]

    for api_name, params, desc in apis:
        print(f"\n{'='*60}")
        print(f">>> {api_name} — {desc}")
        print(f"{'='*60}")
        data = call(api_url, token, api_name, params)
        print(f"  Response:")
        print(f"  {json.dumps(data, ensure_ascii=False, indent=2)}")


if __name__ == "__main__":
    main()
