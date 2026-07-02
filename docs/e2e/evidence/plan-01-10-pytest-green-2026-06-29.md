---
feat_id: plan-01
phase: green
date: 2026-06-29
title: 后端趋势聚合与趋势 API — pytest API 集成测试 green 阶段证据（10 期）
---

# plan-01 E2E Green 证据（10 需求）

## 结论

**通过。**

- 后端 FEAT plan-01（10 期券商荐股推荐趋势聚合与趋势 API）为纯后端 API（3 个 repository 跨月聚合方法 + 1 个 service `get_trend_ranking` + 1 个新 GET 端点 + 4 个 Pydantic model），E2E 形态为 **pytest API 集成测试**（参照 08 期 green 先例 `plan-01-08-pytest-green-2026-06-24.md` + MEMORY「后端 FEAT E2E 适配 pytest」），非 Playwright。
- 新增 **30 个 pytest 用例全部通过**（30 passed, 0 failed，10.80s）；plan-01 §3 Task 列表 #1/#2/#3 的实现（`BrokerRecommendRepository` 3 跨月聚合方法 + `BrokerRecommendAnalysisService.get_trend_ranking` + GET `/trend-ranking` 端点 + 4 个 Pydantic model）端到端契约稳定。
- 现有 09 期 broker 测试**无回归破坏**：`pytest tests/ -k "broker"` 共 **109 个用例全部通过**（109 passed, 0 failed，30.90s），含新增 30 个 trend 用例 + 79 个既有 09 期 `test_broker_recommend_analysis_api.py`（71）+ `test_broker_recommend_sync.py`（23）+ trend（30）+ 其余 broker 命中用例。
- 测试断言全部保持 red 阶段强度（**未放宽**）—— 见下方「关键护栏验证点」。

## 关联文档

- 功能文件：`docs/10-券商荐股趋势/10-2-实现计划-券商荐股趋势/plan-01-后端趋势聚合与API.md`（§3 实现规格 #1/#2/#3、§5 验收标准 AC-02/03/04/06/07/08/09/11/12、§后端边界场景）
- 架构文档：`docs/10-券商荐股趋势/10-1-架构文档-券商荐股趋势.md`（§4.2 / §6.1 趋势榜加载链路 / §7.2 最小 Schema / §7.3 API 边界 / §9 Phase A）
- 实现计划 README：`docs/10-券商荐股趋势/10-2-实现计划-券商荐股趋势/README.md`（§7.2 开发状态机：plan-01 当前步骤 `green-e2e`，由主 agent 推进 task-review）
- 测试文件：`server/tests/test_broker_recommend_trend.py`（30 用例）
- Red 证据：`docs/e2e/evidence/plan-01-10-pytest-red-2026-06-29.md`（30 用例曾全 404 / AssertionError）

## 已实现交付物（green 前置）

| 文件 | 模块 | 状态 |
| --- | --- | --- |
| `server/src/repositories/broker_recommend_repository.py` | `BrokerRecommendRepository` 扩展：`get_trend_aggregations` / `get_trend_cumulative_counts` / `get_trend_brokers`（3 跨月聚合方法） | done |
| `server/src/services/broker_recommend_analysis_service.py` | `BrokerRecommendAnalysisService.get_trend_ranking`（连续性计数 ADR-3 + 多级排序 AC-03 + 分页 AC-08 + 行业 JOIN + 展开券商预加载） | done |
| `server/src/api/v1/broker_recommend_analysis.py` | `GET /trend-ranking` 端点 + 4 个 Pydantic model（TrendMonthPoint / TrendMonthBroker / TrendRankingItem / TrendRankingData） | done |

## 覆盖的 AC

| AC-ID | AC 简述 | green 验证用例 |
| --- | --- | --- |
| AC-02 | 跨月聚合 + 连续性口径 | `test_continuous_months_desc_top`（600519 consec=3）/ `test_monthly_series_values`（[03:1,04:2,05:3]）/ `test_fields_complete_camel_case` |
| AC-03 | 多级排序（4 级 tiebreak） | `test_full_multi_level_order`（完整 7 股序）/ `test_cumulative_tiebreak` / `test_latest_month_count_tiebreak` / `test_symbol_tiebreak_asc` |
| AC-04 | 趋势口径与单月榜一致 | `test_latest_month_count_matches_stock_ranking`（每股 latest == 09 stock-ranking 同月 brokerCount） |
| AC-06 | 展开券商 topBrokers≤3 | `test_monthly_brokers_desc_with_top3`（新→旧降序 + 每点 top3 + 05 月 3 家券商） |
| AC-07 | 断档降级 | `test_gap_stock_consecutive_stops_at_gap`（000888 consec=1）/ `test_gap_stock_cumulative_includes_pre_gap_months`（cum=2）/ `test_gap_stock_monthly_series_includes_gap_month_zero`（[03:2,04:0,05:1]） |
| AC-08 | 分页 total 全窗口 | `test_pagination_total_is_full_window` / `test_pagination_second_page` / `test_pagination_last_page_partial`（total=7 跨 page=1/2/4 一致） |
| AC-09 | 排行榜内搜索 | `test_search_by_symbol_prefix` / `test_search_by_name_contains` / `test_search_no_match_returns_empty` / `test_search_escapes_like_wildcards`（% → total=0）/ `test_search_keeps_multi_level_order` |
| AC-11 | 单月兜底 | `test_single_month_consecutive_all_one` / `test_single_month_series_single_point` / `test_single_month_latest_equals_cumulative` |
| AC-12 | 空表降级 | `test_empty_table_has_data_false`（hasData=false + items=[] + total=0） |

## 关键护栏验证点（断言强度未放宽）

### 1. 端点契约（AC-02）

- `test_endpoint_exists_and_wrapper`：200 + `{success, data}` 包裹 + `hasData` + total=7 + 默认 `pageSize=20`。
- `test_no_month_param_full_window`：无 `month` 参数时 monthlySeries 跨全 3 个月（趋势固定全窗口，架构 §7.3）。
- `test_fields_complete_camel_case`：四指标字段（`consecutiveMonths` / `cumulativeBrokerCount` / `latestMonthBrokerCount` / `monthlySeries` / `monthlyBrokers`）齐全且 camelCase，**无 snake_case 泄漏**。

### 2. 连续性计数（ADR-3）+ 跨月聚合（AC-02）

- `test_continuous_months_desc_top`：榜首 600519 `consecutiveMonths=3`。
- `test_monthly_series_values`：600519 `monthlySeries=[03:1, 04:2, 05:3]`（旧→新升序精确值）。

### 3. 多级排序（AC-03 全链 + 4 级独立 tiebreak）

- `test_full_multi_level_order`：完整 7 股序必须精确 `[600519, 600036, 000001, 600000, 000888, 600001, 600002]`（不允许错位）。
- `test_cumulative_tiebreak`（level-2）：600036(cum3) 排在 000001(cum2) 之前。
- `test_latest_month_count_tiebreak`（level-3）：000001(latest2) 排在 600000(latest1) 之前。
- `test_symbol_tiebreak_asc`（level-4）：600001 排在 600002 之前（三指标全同）。

### 4. 口径一致（AC-04）

- `test_latest_month_count_matches_stock_ranking`：对窗口内每只股票，趋势 `latestMonthBrokerCount` 必须 **逐只** == 09 `stock-ranking` 同月 `brokerCount`（非抽查）。

### 5. 断档降级（AC-07）

- `test_gap_stock_consecutive_stops_at_gap`：000888 `consecutiveMonths=1`（05 有/04 断档即停，**不是 2**）。
- `test_gap_stock_cumulative_includes_pre_gap_months`：`cumulativeBrokerCount=2`（含断档前 03 月招商+中信）。
- `test_gap_stock_monthly_series_includes_gap_month_zero`：`monthlySeries=[03:2, 04:0, 05:1]`（断档月 0 值仍出现）。

### 6. 分页（AC-08）+ 搜索（AC-09 + 安全 §8.3）

- `test_pagination_*`：total=7 跨 page=1/2/4 三次请求一致（非当前页条数）。
- `test_search_escapes_like_wildcards`：search=`%` → total=0（LIKE 转义生效，不匹配全表）。
- `test_search_no_match_returns_empty`：无匹配 → items=[] + total=0（服务端全量重查）。

### 7. 单月兜底（AC-11）+ 空表降级（AC-12）

- `test_single_month_consecutive_all_one`：单月所有股 `consecutiveMonths=1`（逐只断言）。
- `test_single_month_latest_equals_cumulative`：单月逐只 `latestMonthBrokerCount == cumulativeBrokerCount`。
- `test_empty_table_has_data_false`：表无数据 → `hasData=false`（非 null）+ items=[] + total=0。

### 8. 行业 JOIN + 展开券商（AC-02 industries + AC-06）

- `test_industries_joined`：600519→`['食品饮料']`，000001→`[]`（无 sector_stocks 映射）。
- `test_monthly_brokers_desc_with_top3`：monthlyBrokers 新→旧降序 + 每点 `topBrokers≤3` + 05 月 3 家券商。

### 9. 认证守卫 + 构建校验

- `test_trend_ranking_requires_auth`：未认证 → **401**（实现后；red 阶段为 404）。
- `test_repository_trend_methods_exist`：repo 含 3 个趋势方法。
- `test_service_trend_method_exists`：service 含 `get_trend_ranking`。

## 执行命令

```bash
cd /Users/muchao/code/sector-strength/server && source .venv/bin/activate

# 范围 A：plan-01 新增测试（核心 green 验证）
python -m pytest tests/test_broker_recommend_trend.py -v --no-cov

# 范围 B：09 期 broker 回归（不应破坏）
python -m pytest tests/ -k "broker" --no-cov
```

> **MEMORY 提醒**：后端跑单/子集测试文件必须加 `--no-cov`，否则 `cov-fail-under=80` 致退出码非 0 误判失败。

## 执行结果摘要

### 范围 A：plan-01 新增测试文件（30 个用例）

```
============================= test session starts ==============================
platform darwin -- Python 3.12.13, pytest-9.0.3, pluggy-1.6.0 -- /Users/muchao/code/sector-strength/server/.venv/bin/python
cachedir: .pytest_cache
rootdir: /Users/muchao/code/sector-strength/server
configfile: pytest.ini
plugins: cov-7.1.0, asyncio-1.3.0, anyio-4.13.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=session, asyncio_default_test_loop_scope=function
collecting ... collected 30 items

tests/test_broker_recommend_trend.py::TestTrendRankingAggregation::test_endpoint_exists_and_wrapper PASSED [  3%]
tests/test_broker_recommend_trend.py::TestTrendRankingAggregation::test_no_month_param_full_window PASSED [  6%]
tests/test_broker_recommend_trend.py::TestTrendRankingAggregation::test_fields_complete_camel_case PASSED [ 10%]
tests/test_broker_recommend_trend.py::TestTrendRankingAggregation::test_continuous_months_desc_top PASSED [ 13%]
tests/test_broker_recommend_trend.py::TestTrendRankingAggregation::test_latest_month_count_matches_stock_ranking PASSED [ 16%]
tests/test_broker_recommend_trend.py::TestTrendRankingAggregation::test_monthly_series_values PASSED [ 20%]
tests/test_broker_recommend_trend.py::TestTrendRankingAggregation::test_monthly_brokers_desc_with_top3 PASSED [ 23%]
tests/test_broker_recommend_trend.py::TestTrendRankingMultiLevelSort::test_full_multi_level_order PASSED [ 26%]
tests/test_broker_recommend_trend.py::TestTrendRankingMultiLevelSort::test_cumulative_tiebreak PASSED [ 30%]
tests/test_broker_recommend_trend.py::TestTrendRankingMultiLevelSort::test_latest_month_count_tiebreak PASSED [ 33%]
tests/test_broker_recommend_trend.py::TestTrendRankingMultiLevelSort::test_symbol_tiebreak_asc PASSED [ 36%]
tests/test_broker_recommend_trend.py::TestTrendRankingGap::test_gap_stock_consecutive_stops_at_gap PASSED [ 40%]
tests/test_broker_recommend_trend.py::TestTrendRankingGap::test_gap_stock_cumulative_includes_pre_gap_months PASSED [ 43%]
tests/test_broker_recommend_trend.py::TestTrendRankingGap::test_gap_stock_monthly_series_includes_gap_month_zero PASSED [ 46%]
tests/test_broker_recommend_trend.py::TestTrendRankingPagination::test_pagination_total_is_full_window PASSED [ 50%]
tests/test_broker_recommend_trend.py::TestTrendRankingPagination::test_pagination_second_page PASSED [ 53%]
tests/test_broker_recommend_trend.py::TestTrendRankingPagination::test_pagination_last_page_partial PASSED [ 56%]
tests/test_broker_recommend_trend.py::TestTrendRankingSearch::test_search_by_symbol_prefix PASSED [ 60%]
tests/test_broker_recommend_trend.py::TestTrendRankingSearch::test_search_by_name_contains PASSED [ 63%]
tests/test_broker_recommend_trend.py::TestTrendRankingSearch::test_search_no_match_returns_empty PASSED [ 66%]
tests/test_broker_recommend_trend.py::TestTrendRankingSearch::test_search_escapes_like_wildcards PASSED [ 70%]
tests/test_broker_recommend_trend.py::TestTrendRankingSearch::test_search_keeps_multi_level_order PASSED [ 73%]
tests/test_broker_recommend_trend.py::TestTrendRankingSingleMonth::test_single_month_consecutive_all_one PASSED [ 76%]
tests/test_broker_recommend_trend.py::TestTrendRankingSingleMonth::test_single_month_series_single_point PASSED [ 80%]
tests/test_broker_recommend_trend.py::TestTrendRankingSingleMonth::test_single_month_latest_equals_cumulative PASSED [ 83%]
tests/test_broker_recommend_trend.py::TestTrendRankingEmptyState::test_empty_table_has_data_false PASSED [ 86%]
tests/test_broker_recommend_trend.py::TestTrendRankingIndustry::test_industries_joined PASSED [ 90%]
tests/test_broker_recommend_trend.py::TestTrendImportable::test_repository_trend_methods_exist PASSED [ 93%]
tests/test_broker_recommend_trend.py::TestTrendImportable::test_service_trend_method_exists PASSED [ 96%]
tests/test_broker_recommend_trend.py::TestTrendRankingAuth::test_trend_ranking_requires_auth PASSED [100%]

======================= 30 passed, 10 warnings in 10.80s =======================
```

### 范围 B：09 期 broker 回归（不应破坏）

```
============================= test session starts ==============================
platform darwin -- Python 3.12.13, pytest-9.0.3, pluggy-1.6.0 -- /Users/muchao/code/sector-strength/server/.venv/bin/python
cachedir: .pytest_cache
rootdir: /Users/muchao/code/sector-strength/server
configfile: pytest.ini
plugins: cov-7.1.0, asyncio-1.3.0, anyio-4.13.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=session, asyncio_default_test_loop_scope=function
collecting ... collected 1050 items / 941 deselected / 109 selected

tests/test_broker_recommend_analysis_api.py ...（71 个）
tests/test_broker_recommend_sync.py ...............（23 个）
tests/test_broker_recommend_trend.py ..............................（30 个，本 FEAT 新增）
... 其余 broker 命中用例 PASSED

============== 109 passed, 941 deselected, 13 warnings in 30.90s ===============
```

- **109 passed, 0 failed**：含新增 30 个 trend 用例 + 79 个既有 09 期 broker 用例（`test_broker_recommend_analysis_api.py` 71 + `test_broker_recommend_sync.py` 23）+ 其余 broker 命中用例，全部通过，**无回归破坏**。

## 后续步骤

- plan-01 进入 `task-review`（由主 agent 触发 task-review skill），通过后状态 `review → done` 并更新 README §7.2 开发状态机表 + plan-01 frontmatter `status: done`。
- plan-02（前端趋势榜展示）等待 plan-01 done 后由 auto-dev 串行启动；其 green 证据将含 Playwright 前端 E2E。
