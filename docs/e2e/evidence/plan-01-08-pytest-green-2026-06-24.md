---
feat_id: plan-01
phase: green
date: 2026-06-24
title: 后端基金扎堆度聚合查询 API — pytest API 集成测试 green 阶段证据（08 期）
---

# plan-01 E2E Green 证据（08 需求）

## 结论

**通过。**

- 后端 FEAT plan-01（08 期基金扎堆度聚合查询 API）为纯后端 API，E2E 形态为 **pytest API 集成测试**（参照 `server/tests/test_fund_api.py` 既有风格，非 Playwright；参照 MEMORY「后端 FEAT E2E 适配 pytest」）。
- 新增 **20 个 pytest 用例全部通过**（20 passed, 0 failed，7.32s）；plan-01 §4 Task 列表 Task 2-7 的实现（`FundCrowdRepository` 4 方法 + `FundCrowdAnalysisService` 3 方法 + 4 个 Pydantic 响应模型 + `_dict_to_camel` helper + 2 个端点 + v1 路由注册）端到端契约稳定。
- 现有 `server/tests/test_fund_api.py` **34 个用例全部通过**（34 passed, 0 failed，12.63s），无回归破坏。
- 测试断言全部保持 red 阶段强度（**未放宽**）—— 见下方「关键护栏验证点」。

## 关联文档

- 功能文件：`docs/08-基金扎堆股票分析/08-2-实现计划-基金扎堆股票分析/plan-01-后端基金扎堆度聚合查询API.md`（§3 #1-#10 实现规格、§4 Task 列表、§5 验收标准）
- 架构文档：`docs/08-基金扎堆股票分析/08-1-架构文档-基金扎堆股票分析.md`
- 实现计划 README：`docs/08-基金扎堆股票分析/08-2-实现计划-基金扎堆股票分析/README.md`（§7.2 开发状态机：plan-01 当前步骤 `green-e2e`，由主 agent 推进 task-review）
- 测试文件：`server/tests/test_fund_crowd_api.py`（20 用例）
- Red 证据：`docs/e2e/evidence/plan-01-08-pytest-red-2026-06-24.md`（20 用例曾全 404）

## 已实现交付物（green 前置）

| 文件 | 模块 | 状态 |
| --- | --- | --- |
| `server/src/repositories/fund_crowd_repository.py` | `FundCrowdRepository`（`get_report_periods` / `get_crowd_aggregation`（含 NULL + scope 过滤 + search SQL 层 + `_escape_like_keyword`）/ `get_industry_for_stocks` / `get_stock_names`） | done |
| `server/src/services/fund_crowd_analysis_service.py` | `FundCrowdAnalysisService`（`get_rankings` / `get_industry_distribution` / `_compute_changes`）+ 常量 `PASSIVE_INVEST_TYPES` | done |
| `server/src/api/v1/fund_crowd_analysis.py` | 路由 `prefix="/fund-crowd-analysis"` + 2 端点（`GET /rankings` + `GET /industry-distribution`）+ 4 个 Pydantic 模型（`RankingItem` / `RankingsData` / `IndustryItem` / `IndustryDistributionData`）+ `_dict_to_camel` helper | done |
| `server/src/api/v1/__init__.py` | 注册 `fund_crowd_analysis_router`（紧邻 funds_router 之后） | done |
| `server/alembic/versions/4b8668ae3d1d_add_fund_portfolio_period_symbol_index.py` | 非阻塞索引优化 `ix_fund_portfolio_period_symbol (report_period, stock_symbol)`（Task 9） | done |

## 覆盖的 AC

| AC-ID | AC 简述 | green 验证用例 |
| --- | --- | --- |
| AC-01 | 扎堆度排行榜展示（按基金数降序、辅以占流通比） | `test_rankings_returns_active_scope_only` / `test_rankings_all_scope_includes_passive` / `test_rankings_order_by_fund_count_desc` / `test_rankings_total_float_ratio_sum` |
| AC-02 | 主动/被动口径切换 | `test_rankings_all_scope_includes_passive`（scope=all 纳入被动型，fundCount=4 > scope=active 的 2） |
| AC-03 | 环比变化展示（含新进） | `test_rankings_change_computation`（fundCountChange / totalFloatRatioChange / isNew 三态） |
| AC-04 | 行业分布展示 | `test_industry_distribution_active_scope` / `test_industry_distribution_multi_industries_per_stock` / `test_industry_distribution_empty_when_no_industry_mapping` |
| AC-06 | 上期数据缺失降级呈现 | `test_rankings_no_prev_period_returns_null_changes`（hasPrevPeriod=false → change 字段全 null） |
| AC-07 | 持仓数据未同步空状态 | `test_rankings_empty_portfolio_returns_has_data_false` / `test_industry_distribution_empty_portfolio` |
| AC-08 | 排行榜内搜索 | `test_rankings_search_by_code_prefix` / `test_rankings_search_by_name_contains` / `test_rankings_search_no_match` / `test_rankings_search_escapes_like_wildcards` |

> AC-05（下钻反查）由 plan-03 独立承接，不在 plan-01 范围。

## 关键护栏验证点（断言强度未放宽）

### 1. 无阈值聚合（ADR-2）

- `test_rankings_total_float_ratio_sum`：scope=all 时 600519 `totalFloatRatio≈4.8`（2.5 + 1.5 + 0.8 + 0，NULL 忽略）；持仓计入 = 存在即重仓，**未引入 stk_mkv_ratio ≥ 1% 阈值**。

### 2. NULL 处理（ADR-1 + L2/L3 降级）

- **`invest_type` NULL → 显式归主动型**：`test_rankings_returns_active_scope_only` 断言 scope=active 时 600519 `fundCount=2`（含 001004.OF invest_type=None，通过 `Fund.invest_type.is_(None)` 显式包含），**不是 NOT IN 漏 NULL 的 1**。
- **`stk_float_ratio` NULL → SUM 自动忽略**：`test_rankings_total_float_ratio_null_when_all_null`（L3 降级）所有 stk_float_ratio=None 时 `totalFloatRatio=null`，但 `fundCount` 仍正常（不是 None）。
- **`stocks` 表缺失 → stockName=null**：`test_rankings_stock_name_null_when_stocks_table_missing`（L2 降级）999999 不在 stocks 表时 `stockName=null`，`fundCount` 仍正常。

### 3. scope 过滤（AC-02）

- `test_rankings_all_scope_includes_passive`：scope=all 时 600519 `fundCount=4`（全部 4 只基金，含 2 只被动 + 1 只 NULL）。
- `test_rankings_returns_active_scope_only`：scope=active 时 `fundCount=2`（仅主动）。
- 两个 scope 的 fundCount 差异验证了 `PASSIVE_INVEST_TYPES` 过滤生效。

### 4. camelCase 输出（API 契约）

- 测试通过 `_find_item` helper 按 `stockSymbol`、`fundCount`、`totalFloatRatio`、`fundCountChange`、`totalFloatRatioChange`、`isNew`、`currentPeriod`、`prevPeriod`、`hasPrevPeriod`、`hasData`、`pageSize`、`stockCount`、`percentage` 等 camelCase 字段直接访问响应；`_dict_to_camel` 递归转换生效，snake_case 字段经 Pydantic `to_camel` alias 输出。

### 5. 环比 + 新进（AC-03 + ADR-3）

- `test_rankings_change_computation`：
  - 600519 `fundCountChange=0`（本期 2 主动 − 上期 2 主动）、`totalFloatRatioChange≈0.5`（2.5 − 2.0）。
  - 000001 `isNew=true`、`fundCountChange=null`（上期无记录 → 新进，变化数值为 null）。
- `test_rankings_no_prev_period_returns_null_changes`（AC-06）：单期数据 → `hasPrevPeriod=false`、所有 item 的 `fundCountChange/totalFloatRatioChange/isNew` 统一 null（含 is_new=null 三态）。

### 6. 其他护栏

- **search SQL 层过滤**（AC-08）：`test_rankings_search_by_code_prefix`（search=600 → 仅命中 600519，total=1）、`test_rankings_search_by_name_contains`（search=茅台 → 命中贵州茅台）、`test_rankings_search_no_match`（无匹配 total=0）、`test_rankings_search_escapes_like_wildcards`（search=% → 不匹配全表，total=0；`_escape_like_keyword` 转义生效）。
- **分页 total 正确**：`test_rankings_pagination` page=1 page_size=1 → 1 条 total=2；page=2 → 1 条。
- **认证守卫**：`test_rankings_requires_auth` / `test_industry_distribution_requires_auth` 未注入认证 → 401。
- **空表降级**（AC-07）：`test_rankings_empty_portfolio_returns_has_data_false`（`hasData=false` 非 null、`items=[]` 非 None）、`test_industry_distribution_empty_portfolio`（`hasData=false`、`distribution=[]`）。
- **一股多行业**（ADR-5）：`test_industry_distribution_multi_industries_per_stock` 600519 关联 2 行业时两桶均计数（独立计数，不取首个）；`test_industry_distribution_empty_when_no_industry_mapping` 无 sector_stocks 关联 → 归「未分类」桶。

## 执行命令

```bash
cd /Users/muchao/code/sector-strength/server && source .venv/bin/activate

# 范围 A：plan-01 新增测试（核心 green 验证）
pytest tests/test_fund_crowd_api.py --no-cov -v

# 范围 B：现有 funds 测试回归（不应破坏）
pytest tests/test_fund_api.py --no-cov -q
```

> **MEMORY 提醒**：后端跑单/子集测试文件必须加 `--no-cov`，否则 `cov-fail-under=80` 致退出码非 0 误判失败。

## 执行结果摘要

### 范围 A：plan-01 新增测试文件（20 个用例）

```
============================= test session starts ==============================
platform darwin -- Python 3.12.13, pytest-9.0.3, pluggy-1.6.0 -- /Users/muchao/code/sector-strength/server/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /Users/muchao/code/sector-strength/server
configfile: pytest.ini
plugins: cov-7.1.0, asyncio-1.3.0, anyio-4.13.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=session, asyncio_default_test_loop_scope=function
collecting ... collected 20 items

tests/test_fund_crowd_api.py::TestRankings::test_rankings_returns_active_scope_only PASSED [  5%]
tests/test_fund_crowd_api.py::TestRankings::test_rankings_all_scope_includes_passive PASSED [ 10%]
tests/test_fund_crowd_api.py::TestRankings::test_rankings_order_by_fund_count_desc PASSED [ 15%]
tests/test_fund_crowd_api.py::TestRankings::test_rankings_total_float_ratio_sum PASSED [ 20%]
tests/test_fund_crowd_api.py::TestRankings::test_rankings_change_computation PASSED [ 25%]
tests/test_fund_crowd_api.py::TestRankings::test_rankings_no_prev_period_returns_null_changes PASSED [ 30%]
tests/test_fund_crowd_api.py::TestRankings::test_rankings_empty_portfolio_returns_has_data_false PASSED [ 35%]
tests/test_fund_crowd_api.py::TestRankings::test_rankings_search_by_code_prefix PASSED [ 40%]
tests/test_fund_crowd_api.py::TestRankings::test_rankings_search_by_name_contains PASSED [ 45%]
tests/test_fund_crowd_api.py::TestRankings::test_rankings_search_no_match PASSED [ 50%]
tests/test_fund_crowd_api.py::TestRankings::test_rankings_pagination PASSED [ 55%]
tests/test_fund_crowd_api.py::TestRankings::test_rankings_requires_auth PASSED [ 60%]
tests/test_fund_crowd_api.py::TestRankings::test_rankings_stock_name_null_when_stocks_table_missing PASSED [ 65%]
tests/test_fund_crowd_api.py::TestRankings::test_rankings_total_float_ratio_null_when_all_null PASSED [ 70%]
tests/test_fund_crowd_api.py::TestRankings::test_rankings_search_escapes_like_wildcards PASSED [ 75%]
tests/test_fund_crowd_api.py::TestIndustryDistribution::test_industry_distribution_active_scope PASSED [ 80%]
tests/test_fund_crowd_api.py::TestIndustryDistribution::test_industry_distribution_multi_industries_per_stock PASSED [ 85%]
tests/test_fund_crowd_api.py::TestIndustryDistribution::test_industry_distribution_empty_when_no_industry_mapping PASSED [ 90%]
tests/test_fund_crowd_api.py::TestIndustryDistribution::test_industry_distribution_empty_portfolio PASSED [ 95%]
tests/test_fund_crowd_api.py::TestIndustryDistribution::test_industry_distribution_requires_auth PASSED [100%]

======================= 20 passed, 10 warnings in 7.32s ========================
```

### 范围 B：现有 funds 测试回归（不应破坏）

```
collected 34 items

tests/test_fund_api.py ..................................                [100%]

======================= 34 passed, 10 warnings in 12.63s =======================
```

## 后续步骤

- plan-01 进入 `task-review`（由主 agent 触发 task-review skill），通过后状态 `review → done` 并更新 README §7.2 开发状态机表 + plan-01 frontmatter `status: done`。
- plan-02 / plan-03 等待 plan-01 done 后由 auto-dev 串行启动。
