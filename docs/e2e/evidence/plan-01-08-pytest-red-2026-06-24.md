---
feat_id: plan-01
phase: red
date: 2026-06-24
title: 后端基金扎堆度聚合查询 API — pytest API 集成测试 red 阶段证据（08 期）
---

# plan-01 E2E Red 证据（08 需求）

## 结论

**预期失败，测试有效。**

- 后端 FEAT plan-01（08 期基金扎堆度聚合查询 API）为纯后端 API（2 个新 GET 端点 + 7 个 Pydantic 模型 + 1 个 service + 1 个 repository），E2E 形态为 **pytest API 集成测试**（参照 `server/tests/test_fund_api.py` 既有 33 用例 + fixtures 风格），非 Playwright（参照 MEMORY「后端 FEAT E2E 适配 pytest」）。
- 新增 **20 个测试用例全部失败**，失败原因均为「端点尚未实现 → **404 Not Found**」（FastAPI 对未注册的路由前缀 `/api/v1/fund-crowd-analysis/*` 返回 404），正是 red 阶段的预期信号。
- 测试文件可被 pytest 正常收集（**20 tests collected in 0.01s**），无 ImportError、无语法错误——失败完全来自端点缺失，符合 red 关键原则。
- 现有 `server/tests/test_fund_api.py` **34 个用例全部通过**（无回归破坏），证明本期测试改动未破坏既有功能。

## 关联文档

- 功能文件：`docs/08-基金扎堆股票分析/08-2-实现计划-基金扎堆股票分析/plan-01-后端基金扎堆度聚合查询API.md`（§3 #7 pytest 测试用例 / §5 验收标准 / §8 边界场景）
- 架构文档：`docs/08-基金扎堆股票分析/08-1-架构文档-基金扎堆股票分析.md`
- 实现计划 README：`docs/08-基金扎堆股票分析/08-2-实现计划-基金扎堆股票分析/README.md`（§7.2 开发状态机：plan-01 当前步骤 `red-e2e`）
- 测试文件：`server/tests/test_fund_crowd_api.py`
- 先例参照：`server/tests/test_fund_api.py`（既有 34 用例 + fixtures）、`server/tests/test_shareholder_group_admin_api.py`、`server/tests/conftest.py`

## 失败原因

后端 2 个新端点尚未实现（路由未在 `server/src/api/v1/__init__.py` 注册），FastAPI 对所有 `/api/v1/fund-crowd-analysis/rankings` 与 `/api/v1/fund-crowd-analysis/industry-distribution` 的 GET 请求统一返回 **`404 Not Found`**。

待实现端点（plan-01 §3 #4 #5 实现规格）：

| 方法 | 路径 | 用途 | 对应 AC |
| --- | --- | --- | --- |
| GET | /api/v1/fund-crowd-analysis/rankings | 扎堆度排行榜（含 scope/search/page 参数） | AC-01/02/03/06/07/08 |
| GET | /api/v1/fund-crowd-analysis/industry-distribution | 行业分布 | AC-04 |

待实现模块（plan-01 §3 #1 #2 #3 #6 实现规格）：

- `server/src/repositories/fund_crowd_repository.py` — `FundCrowdRepository`（4 个方法）
- `server/src/services/fund_crowd_analysis_service.py` — `FundCrowdAnalysisService`（3 个方法 + 常量 `PASSIVE_INVEST_TYPES`）
- `server/src/api/v1/fund_crowd_analysis.py` — 路由 + 7 个 Pydantic 响应模型 + `_dict_to_camel` helper
- `server/src/api/v1/__init__.py` — 注册 `fund_crowd_analysis_router`

## 测试用例清单（20 个新增，覆盖 plan-01 §5 的 18 个设计 + 2 个空表/认证补充）

### 新增 fixtures

| 名称 | 说明 |
| --- | --- |
| `sample_crowd_data` | 主测试数据：4 只基金（主动 001001 / 被动 001002 / 被动 001003 / NULL 主动 001004）+ 7 条持仓（最新期 600519×4 + 000001×2，上一期 600519×2）+ 2 只 stocks；覆盖 AC-01/02/03/08 主路径 |
| `sample_crowd_data_single_period` | 仅 1 个报告期数据（验证 AC-06 hasPrevPeriod=false、change 字段全 null） |
| `sample_industry_data` | 在 `sample_crowd_data` 基础上加 sector_stocks（600519 → 食品饮料 + 消费龙头，000001 无映射），验证 AC-04 + 一股多行业 |
| `sample_null_stocks_table` | 持仓股票 999999 不在 stocks 表（验证 L2 降级 stockName=null） |
| `sample_all_null_ratio` | 所有 stk_float_ratio=None（验证 L3 降级 totalFloatRatio=null） |

### TestRankings（15 个）

| # | 用例 | 类型 | 对应 AC | red 断言 | 结果 |
| --- | --- | --- | --- | --- | --- |
| 1 | test_rankings_returns_active_scope_only | Happy | AC-01 | scope=active → 600519 fundCount=2（排除 2 只被动 + 含 1 只 NULL 主动） | FAIL 404 |
| 2 | test_rankings_all_scope_includes_passive | Happy | AC-02 | scope=all → 600519 fundCount=4 | FAIL 404 |
| 3 | test_rankings_order_by_fund_count_desc | Happy | AC-01 排序 | 600519(4) 排在 000001(2) 之前 | FAIL 404 |
| 4 | test_rankings_total_float_ratio_sum | Happy | AC-01 辅指标 | scope=all → 600519 totalFloatRatio≈4.8（NULL 忽略） | FAIL 404 |
| 5 | test_rankings_change_computation | Happy | AC-03 | 600519 fundCountChange=0、totalFloatRatioChange≈0.5；000001 isNew=true | FAIL 404 |
| 6 | test_rankings_no_prev_period_returns_null_changes | Edge | AC-06 | 单期 → hasPrevPeriod=false、所有 change 字段 null | FAIL 404 |
| 7 | test_rankings_empty_portfolio_returns_has_data_false | Edge | AC-07 | 空表 → hasData=false、items=[] | FAIL 404 |
| 8 | test_rankings_search_by_code_prefix | Happy | AC-08 | search=600 → total=1，仅命中 600519 | FAIL 404 |
| 9 | test_rankings_search_by_name_contains | Happy | AC-08 | search=茅台 → total=1，命中贵州茅台 | FAIL 404 |
| 10 | test_rankings_search_no_match | Edge | AC-08 边界 | search=不存在的股票 → total=0 | FAIL 404 |
| 11 | test_rankings_pagination | Edge | 隐含约束 | page=1&page_size=1 → 1 条 total=2；page=2 → 1 条 | FAIL 404 |
| 12 | test_rankings_requires_auth | 权限 | 安全 §8.3 | 未认证 → 401 | FAIL 404 |
| 13 | test_rankings_stock_name_null_when_stocks_table_missing | 降级 | L2 | stocks 表无 symbol → stockName=null、fundCount 正常 | FAIL 404 |
| 14 | test_rankings_total_float_ratio_null_when_all_null | 降级 | L3 | 所有 stk_float_ratio=None → totalFloatRatio=null | FAIL 404 |
| 15 | test_rankings_search_escapes_like_wildcards | 安全 | 安全 §8.3 | search=% → total=0（LIKE 通配符转义） | FAIL 404 |

### TestIndustryDistribution（5 个）

| # | 用例 | 类型 | 对应 AC | red 断言 | 结果 |
| --- | --- | --- | --- | --- | --- |
| 16 | test_industry_distribution_active_scope | Happy | AC-04 | 食品饮料/消费龙头/未分类 三桶 + percentage≈50% | FAIL 404 |
| 17 | test_industry_distribution_multi_industries_per_stock | Happy | AC-04 一股多行业 | 600519 同时出现在 2 个行业桶 | FAIL 404 |
| 18 | test_industry_distribution_empty_when_no_industry_mapping | Edge | AC-04 边界 | 无 sector_stocks → 全归未分类 | FAIL 404 |
| 19 | test_industry_distribution_empty_portfolio | Edge | AC-07 | 空表 → hasData=false、distribution=[] | FAIL 404 |
| 20 | test_industry_distribution_requires_auth | 权限 | 安全 §8.3 | 未认证 → 401 | FAIL 404 |

## 与 plan-01 §5 设计的差异说明

plan-01 §5 列出 18 个用例设计，本测试文件实际落地 20 个（+2 个补充）：

- **第 19 个新增** `test_industry_distribution_empty_portfolio`（AC-07 行业分布侧）：plan-01 §5 #7 的 industry-distribution 列表中未显式列空表测试，但 AC-07 与 rankings 一致要求 `fund_portfolio` 表无数据时返回 `hasData=false`、`distribution=[]`，作为对称覆盖补充。
- **第 20 个新增** `test_industry_distribution_requires_auth`：plan-01 §5 #7 在 rankings 侧有 `test_rankings_requires_auth`，但 industry-distribution 同样受 `Depends(get_current_user)` 保护，对称补充一条权限测试。

其余 18 个用例与 plan-01 §5 设计一一对应（test 名称、AC 映射、断言点完全一致）。这是测试侧的合理对称扩展，不构成对 plan-01 §5 设计的偏离。

## 断言保护强度（不放宽）

每个用例都严格断言：

- **响应字段**：camelCase 字段（`stockSymbol` / `stockName` / `fundCount` / `totalFloatRatio` / `fundCountChange` / `totalFloatRatioChange` / `isNew` / `currentPeriod` / `prevPeriod` / `hasPrevPeriod` / `hasData` / `pageSize` / `stockCount` / `percentage`）必须存在；通过 `_find_item` helper 按 `stockSymbol` 字段查找（不放宽为「任意 key」）。
- **数据正确性**：
  - AC-01：`scope=active` 时 600519 `fundCount=2`（不是 4、不是 1），明确排除被动型且包含 NULL 主动。
  - AC-02：`scope=all` 时 600519 `fundCount=4`（不是 2）。
  - AC-03：600519 `fundCountChange=0`（本期 2 主动 - 上期 2 主动），`totalFloatRatioChange≈0.5`（2.5-2.0）；000001 `isNew=true`、`fundCountChange=null`。
  - AC-04：`percentage≈50.0`（1 扎堆股 / 2 总扎堆股 × 100）。
- **排序**：600519 必须严格排在 000001 之前（不允许相等）。
- **分页**：page=1 page_size=1 必须返回恰好 1 行、total=2；page=2 必须返回恰好 1 行。
- **降级**：L2 stockName=null 时 fundCount 必须仍正常（不是 None）；L3 totalFloatRatio=null 时 fundCount 必须仍正常。
- **安全**：`search=%` 必须 total=0（不允许 total > 0 的全表匹配）；未认证必须 401。
- **边界**：空表必须 hasData=false（不是 null）、items=[]（不是 None）。

## 执行命令

```bash
cd /Users/muchao/code/sector-strength/server && source .venv/bin/activate

# 新增测试文件（plan-01 范围）
pytest tests/test_fund_crowd_api.py --no-cov -v

# 现有 funds 测试回归（不应破坏）
pytest tests/test_fund_api.py --no-cov -q

# 仅验证收集阶段
pytest tests/test_fund_crowd_api.py --no-cov --collect-only -q
```

> **MEMORY 提醒**：后端跑单/子集测试文件必须加 `--no-cov`，否则 `cov-fail-under=80` 致退出码非 0 误判失败。

## 执行结果摘要

### 范围 A：新增测试文件（20 个用例）

```
=========================== short test summary info ============================
FAILED tests/test_fund_crowd_api.py::TestRankings::test_rankings_returns_active_scope_only - assert 404 == 200
FAILED tests/test_fund_crowd_api.py::TestRankings::test_rankings_all_scope_includes_passive - assert 404 == 200
FAILED tests/test_fund_crowd_api.py::TestRankings::test_rankings_order_by_fund_count_desc - assert 404 == 200
FAILED tests/test_fund_crowd_api.py::TestRankings::test_rankings_total_float_ratio_sum - assert 404 == 200
FAILED tests/test_fund_crowd_api.py::TestRankings::test_rankings_change_computation - assert 404 == 200
FAILED tests/test_fund_crowd_api.py::TestRankings::test_rankings_no_prev_period_returns_null_changes - assert 404 == 200
FAILED tests/test_fund_crowd_api.py::TestRankings::test_rankings_empty_portfolio_returns_has_data_false - assert 404 == 200
FAILED tests/test_fund_crowd_api.py::TestRankings::test_rankings_search_by_code_prefix - assert 404 == 200
FAILED tests/test_fund_crowd_api.py::TestRankings::test_rankings_search_by_name_contains - assert 404 == 200
FAILED tests/test_fund_crowd_api.py::TestRankings::test_rankings_search_no_match - assert 404 == 200
FAILED tests/test_fund_crowd_api.py::TestRankings::test_rankings_pagination - assert 404 == 200
FAILED tests/test_fund_crowd_api.py::TestRankings::test_rankings_requires_auth - assert 404 == 401
FAILED tests/test_fund_crowd_api.py::TestRankings::test_rankings_stock_name_null_when_stocks_table_missing - assert 404 == 200
FAILED tests/test_fund_crowd_api.py::TestRankings::test_rankings_total_float_ratio_null_when_all_null - assert 404 == 200
FAILED tests/test_fund_crowd_api.py::TestRankings::test_rankings_search_escapes_like_wildcards - assert 404 == 200
FAILED tests/test_fund_crowd_api.py::TestIndustryDistribution::test_industry_distribution_active_scope - assert 404 == 200
FAILED tests/test_fund_crowd_api.py::TestIndustryDistribution::test_industry_distribution_multi_industries_per_stock - assert 404 == 200
FAILED tests/test_fund_crowd_api.py::TestIndustryDistribution::test_industry_distribution_empty_when_no_industry_mapping - assert 404 == 200
FAILED tests/test_fund_crowd_api.py::TestIndustryDistribution::test_industry_distribution_empty_portfolio - assert 404 == 200
FAILED tests/test_fund_crowd_api.py::TestIndustryDistribution::test_industry_distribution_requires_auth - assert 404 == 401
======================= 20 failed, 10 warnings in 6.95s ========================
```

### 范围 B：现有 funds 测试回归（不应破坏）

```
collected 34 items
tests/test_fund_api.py ..................................                [100%]
======================= 34 passed, 10 warnings in 12.24s =======================
```

### 收集阶段证据

```
collected 20 items
<Dir server>
  <Dir tests>
    <Module test_fund_crowd_api.py>
      <Class TestRankings> ... (15 coroutines)
      <Class TestIndustryDistribution> ... (5 coroutines)
========================= 20 tests collected in 0.01s ==========================
```

无 ImportError，无 collection error，测试代码语法正确、import 正确。失败完全来自被测端点尚未实现，符合 red 阶段关键原则。

## 后续步骤

- 进入 `implement` 阶段（plan-01 §4 Task 列表 Task 2-8）：实现 `FundCrowdRepository` + `FundCrowdAnalysisService` + 路由 + 7 个 Pydantic 模型 + v1 路由注册
- 实现完成后跑同一组 pytest 用例，验证 20 个用例全部通过，证据写入 `docs/e2e/evidence/plan-01-08-pytest-green-2026-06-24.md`
