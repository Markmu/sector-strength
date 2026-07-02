---
feat_id: plan-01
phase: red
date: 2026-06-29
title: 后端趋势聚合与趋势 API — pytest API 集成测试 red 阶段证据（10 期）
---

# plan-01 E2E Red 证据（10 需求）

## 结论

**预期失败，测试有效。**

- 后端 FEAT plan-01（10 期券商荐股推荐趋势聚合与趋势 API）为纯后端 API（3 个 repository 跨月聚合方法 + 1 个 service `get_trend_ranking` + 1 个新 GET 端点 + 4 个 Pydantic model），E2E 形态为 **pytest API 集成测试**（参照 08 期先例 `plan-01-08-pytest-red-2026-06-24.md` + 09 期既有 `server/tests/test_broker_recommend_analysis_api.py` fixture/断言范式 + MEMORY「后端 FEAT E2E 适配 pytest」），非 Playwright。
- 新增 **30 个测试用例全部失败**，失败原因均为「功能尚未实现」：
  - 28 个 API 用例 → **404 Not Found**（`/api/v1/broker-recommend-analysis/trend-ranking` 路由未注册）
  - 1 个认证用例 → **404 == 401**（路由未注册，FastAPI 优先返回 404 而非触发认证依赖；实现后应为 401）
  - 2 个 import/方法存在性用例 → **AssertionError**（`BrokerRecommendRepository` 缺 `get_trend_aggregations/get_trend_cumulative_counts/get_trend_brokers`、`BrokerRecommendAnalysisService` 缺 `get_trend_ranking`）
- 测试文件可被 pytest 正常收集（**30 tests collected in 0.03s**），无 ImportError、无语法错误——失败完全来自功能缺失，符合 red 关键原则。
- 现有 09 期 `test_broker_recommend_analysis_api.py` + `test_broker_recommend_sync.py` **79 个用例全部通过**（无回归破坏），证明本期测试改动未破坏既有功能。

## 关联文档

- 功能文件：`docs/10-券商荐股趋势/10-2-实现计划-券商荐股趋势/plan-01-后端趋势聚合与API.md`（§3 实现规格 #1/#2/#3、§5 验收标准 AC-02/03/04/07/08/09/11/12、§后端边界场景）
- 架构文档：`docs/10-券商荐股趋势/10-1-架构文档-券商荐股趋势.md`（§4.2 / §6.1 趋势榜加载链路 / §7.2 最小 Schema / §7.3 API 边界 / §9 Phase A）
- 测试文件：`server/tests/test_broker_recommend_trend.py`
- 先例参照：`docs/e2e/evidence/plan-01-08-pytest-red-2026-06-24.md`（08 期后端 pytest red 证据格式）、`server/tests/test_broker_recommend_analysis_api.py`（09 期 fixture/auth_client/INSERT 范式）、`server/tests/conftest.py`（test_session/client fixture）

## 失败原因

后端 GET `/api/v1/broker-recommend-analysis/trend-ranking` 端点尚未在 `server/src/api/v1/broker_recommend_analysis.py` 注册，FastAPI 对所有 `/api/v1/broker-recommend-analysis/trend-ranking` 的 GET 请求统一返回 **`404 Not Found`**。配套的 repository 3 方法与 service `get_trend_ranking` 均未实现。

待实现模块（plan-01 §3 实现规格 #1 #2 #3）：

| 模块 | 文件 | 待实现 |
| --- | --- | --- |
| Repository 扩展 | `server/src/repositories/broker_recommend_repository.py` | `get_trend_aggregations` / `get_trend_cumulative_counts` / `get_trend_brokers`（3 跨月聚合方法） |
| Service 扩展 | `server/src/services/broker_recommend_analysis_service.py` | `get_trend_ranking`（连续性计数 ADR-3 + 多级排序 AC-03 + 分页 AC-08 + 行业 JOIN + 展开券商预加载） |
| API 端点 | `server/src/api/v1/broker_recommend_analysis.py` | `GET /trend-ranking` + 4 个 Pydantic model（TrendMonthPoint/TrendMonthBroker/TrendRankingItem/TrendRankingData） |

## 测试用例清单（30 个新增，覆盖 plan-01 §5 全部 AC）

### 新增 fixtures

| 名称 | 说明 |
| --- | --- |
| `sample_trend_data` | 主测试数据：3 个已同步月份 [2026-05,04,03] + 7 只股票 + 23 条 broker_recommend；刻意构造覆盖 AC-02 跨月聚合 + AC-03 多级排序全部 4 级 tiebreak + AC-04 口径一致 + AC-07 断档 + AC-08 分页。预期排序 `[600519,600036,000001,600000,000888,600001,600002]` total=7 |
| `sample_trend_data_with_industry` | 在 sample_trend_data 基础上加 sector_stocks（600519→食品饮料，000001 无映射），验证 AC-02 industries 字段 |
| `sample_trend_data_single_month` | 仅 1 个已同步月份（验证 AC-11：consecutiveMonths 均为 1、monthlySeries 单点、latest==cumulative） |

### TestTrendRankingAggregation（7 个）— AC-02/04/端点契约

| # | 用例 | 对应 AC | red 断言 | 结果 |
| --- | --- | --- | --- | --- |
| 1 | test_endpoint_exists_and_wrapper | 端点契约 | 200 + {success,data} 包裹 + hasData + total=7 + 默认 page_size=20 | FAIL 404 |
| 2 | test_no_month_param_full_window | 无 month 参数 | monthlySeries 跨全 3 月份（趋势固定全窗口，架构 §7.3） | FAIL 404 |
| 3 | test_fields_complete_camel_case | AC-02 | 四指标字段齐全 + camelCase（无 snake_case 泄漏）；600519 consec=3/cum=3/latest=3 | FAIL 404 |
| 4 | test_continuous_months_desc_top | AC-02 | 榜首 600519 consecutiveMonths=3 | FAIL 404 |
| 5 | test_latest_month_count_matches_stock_ranking | AC-04 | 每股 latestMonthBrokerCount == 09 stock-ranking 同月 brokerCount | FAIL 404 |
| 6 | test_monthly_series_values | AC-02 | 600519 monthlySeries=[03:1,04:2,05:3]（旧→新升序） | FAIL 404 |
| 7 | test_monthly_brokers_desc_with_top3 | AC-06 | monthlyBrokers 新→旧降序 + 每点 topBrokers≤3 + 05 月 3 家券商 | FAIL 404 |

### TestTrendRankingMultiLevelSort（4 个）— AC-03

| # | 用例 | 对应 AC | red 断言 | 结果 |
| --- | --- | --- | --- | --- |
| 8 | test_full_multi_level_order | AC-03 全链 | 完整 4 级排序 = [600519,600036,000001,600000,000888,600001,600002] | FAIL 404 |
| 9 | test_cumulative_tiebreak | AC-03 level-2 | 600036(cum3) 排在 000001(cum2) 之前 | FAIL 404 |
| 10 | test_latest_month_count_tiebreak | AC-03 level-3 | 000001(latest2) 排在 600000(latest1) 之前 | FAIL 404 |
| 11 | test_symbol_tiebreak_asc | AC-03 level-4 | 600001 排在 600002 之前（三指标全同） | FAIL 404 |

### TestTrendRankingGap（3 个）— AC-07 断档

| # | 用例 | 对应 AC | red 断言 | 结果 |
| --- | --- | --- | --- | --- |
| 12 | test_gap_stock_consecutive_stops_at_gap | AC-07 | 000888 consec=1（05 有/04 断档即停，非 2） | FAIL 404 |
| 13 | test_gap_stock_cumulative_includes_pre_gap_months | AC-07 | 000888 cum=2（含 03 月招商+中信，断档前仍计入） | FAIL 404 |
| 14 | test_gap_stock_monthly_series_includes_gap_month_zero | AC-07 | 000888 monthlySeries=[03:2,04:0,05:1]（断档月 0 值仍出现） | FAIL 404 |

### TestTrendRankingPagination（3 个）— AC-08

| # | 用例 | 对应 AC | red 断言 | 结果 |
| --- | --- | --- | --- | --- |
| 15 | test_pagination_total_is_full_window | AC-08 | page_size=2 → 当前页 2 条但 total=7 | FAIL 404 |
| 16 | test_pagination_second_page | AC-08 | page=2 → 2 条 total=7 | FAIL 404 |
| 17 | test_pagination_last_page_partial | AC-08 | page=4 → 末页 1 条（7=2*3+1）total=7 | FAIL 404 |

### TestTrendRankingSearch（5 个）— AC-09

| # | 用例 | 对应 AC | red 断言 | 结果 |
| --- | --- | --- | --- | --- |
| 18 | test_search_by_symbol_prefix | AC-09 | search=600 → total=5（600 系列） | FAIL 404 |
| 19 | test_search_by_name_contains | AC-09 | search=茅台 → total=1（贵州茅台） | FAIL 404 |
| 20 | test_search_no_match_returns_empty | AC-09 | 无匹配 → items=[] + total=0（服务端全量重查） | FAIL 404 |
| 21 | test_search_escapes_like_wildcards | 安全 §8.3 | search=% → total=0（LIKE 转义） | FAIL 404 |
| 22 | test_search_keeps_multi_level_order | AC-09+03 | search=600 命中 5 只仍按多级排序 | FAIL 404 |

### TestTrendRankingSingleMonth（3 个）— AC-11

| # | 用例 | 对应 AC | red 断言 | 结果 |
| --- | --- | --- | --- | --- |
| 23 | test_single_month_consecutive_all_one | AC-11 | 单月 → 所有 consec=1 | FAIL 404 |
| 24 | test_single_month_series_single_point | AC-11 | 单月 → monthlySeries 单点（600519 latest=2） | FAIL 404 |
| 25 | test_single_month_latest_equals_cumulative | AC-11 | 单月 → latestMonthBrokerCount == cumulativeBrokerCount | FAIL 404 |

### TestTrendRankingEmptyState（1 个）— AC-12

| # | 用例 | 对应 AC | red 断言 | 结果 |
| --- | --- | --- | --- | --- |
| 26 | test_empty_table_has_data_false | AC-12 | 表无数据 → hasData=false + items=[] + total=0 | FAIL 404 |

### TestTrendRankingIndustry（1 个）— AC-02 industries

| # | 用例 | 对应 AC | red 断言 | 结果 |
| --- | --- | --- | --- | --- |
| 27 | test_industries_joined | AC-02 | 600519→['食品饮料']，000001→[]（行业 JOIN） | FAIL 404 |

### TestTrendImportable（2 个）— 构建校验

| # | 用例 | 对应 | red 断言 | 结果 |
| --- | --- | --- | --- | --- |
| 28 | test_repository_trend_methods_exist | §3 #1 | repo 含 3 个趋势方法 | FAIL（缺 get_trend_aggregations） |
| 29 | test_service_trend_method_exists | §3 #2 | service 含 get_trend_ranking | FAIL（缺方法） |

### TestTrendRankingAuth（1 个）— 安全

| # | 用例 | 对应 | red 断言 | 结果 |
| --- | --- | --- | --- | --- |
| 30 | test_trend_ranking_requires_auth | 安全 §8.3 | 未认证 → 401（实现后）；red 阶段 404（路由未注册） | FAIL 404 |

## 断言保护强度（不放宽）

每个用例都严格断言：

- **响应字段**：camelCase 字段（`consecutiveMonths`/`cumulativeBrokerCount`/`latestMonthBrokerCount`/`monthlySeries`/`monthlyBrokers`/`hasData`/`pageSize`）必须存在；通过 `_find_item` helper 按 `symbol` 字段查找（不放宽为「任意 key」）；并显式断言无 snake_case 泄漏。
- **数据正确性**：
  - AC-02：600519 `consecutiveMonths=3`（不是 2）、`cumulativeBrokerCount=3`、`latestMonthBrokerCount=3`；monthlySeries 精确 `[{03:1},{04:2},{05:3}]`。
  - AC-03：完整 7 股排序必须精确 `[600519,600036,000001,600000,000888,600001,600002]`（不允许错位），且 4 级 tiebreak 各有独立用例。
  - AC-04：对窗口内每只股票，趋势 `latestMonthBrokerCount` 必须逐只 == 09 `stock-ranking` 同月 `brokerCount`（不是抽查）。
  - AC-07：000888 断档股 `consecutiveMonths=1`（不是 2）、`cumulativeBrokerCount=2`（含断档前 03 月）、monthlySeries 含 `04:0`（断档月 0 值）。
  - AC-08：total=7 必须跨 page=1/2/4 三次请求一致（非当前页条数）。
  - AC-09：`search=%` 必须 total=0（LIKE 转义）；无匹配 items=[] + total=0。
  - AC-11：单月所有股 consec=1（逐只断言）、latest==cumulative（逐只）。
- **边界**：空表 must hasData=false（不是 null）、items=[]、total=0。

## 执行命令

```bash
cd /Users/muchao/code/sector-strength/server && source .venv/bin/activate

# 新增测试文件（plan-01 范围）
pytest tests/test_broker_recommend_trend.py --no-cov -v

# 现有 09 broker 测试回归（不应破坏）
pytest tests/test_broker_recommend_analysis_api.py tests/test_broker_recommend_sync.py --no-cov -q

# 仅验证收集阶段
pytest tests/test_broker_recommend_trend.py --no-cov --collect-only -q
```

> **MEMORY 提醒**：后端跑单/子集测试文件必须加 `--no-cov`，否则 `cov-fail-under=80` 致退出码非 0 误判失败。

## 执行结果摘要

### 范围 A：新增测试文件（30 个用例）

```
=========================== short test summary info ============================
FAILED tests/test_broker_recommend_trend.py::TestTrendRankingAggregation::test_endpoint_exists_and_wrapper - assert 404 == 200
FAILED tests/test_broker_recommend_trend.py::TestTrendRankingAggregation::test_no_month_param_full_window - assert 404 == 200
FAILED tests/test_broker_recommend_trend.py::TestTrendRankingAggregation::test_fields_complete_camel_case - assert 404 == 200
FAILED tests/test_broker_recommend_trend.py::TestTrendRankingAggregation::test_continuous_months_desc_top - assert 404 == 200
FAILED tests/test_broker_recommend_trend.py::TestTrendRankingAggregation::test_latest_month_count_matches_stock_ranking - assert 404 == 200
FAILED tests/test_broker_recommend_trend.py::TestTrendRankingAggregation::test_monthly_series_values - assert 404 == 200
FAILED tests/test_broker_recommend_trend.py::TestTrendRankingAggregation::test_monthly_brokers_desc_with_top3 - assert 404 == 200
FAILED tests/test_broker_recommend_trend.py::TestTrendRankingMultiLevelSort::test_full_multi_level_order - assert 404 == 200
FAILED tests/test_broker_recommend_trend.py::TestTrendRankingMultiLevelSort::test_cumulative_tiebreak - assert 404 == 200
FAILED tests/test_broker_recommend_trend.py::TestTrendRankingMultiLevelSort::test_latest_month_count_tiebreak - assert 404 == 200
FAILED tests/test_broker_recommend_trend.py::TestTrendRankingMultiLevelSort::test_symbol_tiebreak_asc - assert 404 == 200
FAILED tests/test_broker_recommend_trend.py::TestTrendRankingGap::test_gap_stock_consecutive_stops_at_gap - assert 404 == 200
FAILED tests/test_broker_recommend_trend.py::TestTrendRankingGap::test_gap_stock_cumulative_includes_pre_gap_months - assert 404 == 200
FAILED tests/test_broker_recommend_trend.py::TestTrendRankingGap::test_gap_stock_monthly_series_includes_gap_month_zero - assert 404 == 200
FAILED tests/test_broker_recommend_trend.py::TestTrendRankingPagination::test_pagination_total_is_full_window - assert 404 == 200
FAILED tests/test_broker_recommend_trend.py::TestTrendRankingPagination::test_pagination_second_page - assert 404 == 200
FAILED tests/test_broker_recommend_trend.py::TestTrendRankingPagination::test_pagination_last_page_partial - assert 404 == 200
FAILED tests/test_broker_recommend_trend.py::TestTrendRankingSearch::test_search_by_symbol_prefix - assert 404 == 200
FAILED tests/test_broker_recommend_trend.py::TestTrendRankingSearch::test_search_by_name_contains - assert 404 == 200
FAILED tests/test_broker_recommend_trend.py::TestTrendRankingSearch::test_search_no_match_returns_empty - assert 404 == 200
FAILED tests/test_broker_recommend_trend.py::TestTrendRankingSearch::test_search_escapes_like_wildcards - assert 404 == 200
FAILED tests/test_broker_recommend_trend.py::TestTrendRankingSearch::test_search_keeps_multi_level_order - assert 404 == 200
FAILED tests/test_broker_recommend_trend.py::TestTrendRankingSingleMonth::test_single_month_consecutive_all_one - assert 404 == 200
FAILED tests/test_broker_recommend_trend.py::TestTrendRankingSingleMonth::test_single_month_series_single_point - assert 404 == 200
FAILED tests/test_broker_recommend_trend.py::TestTrendRankingSingleMonth::test_single_month_latest_equals_cumulative - assert 404 == 200
FAILED tests/test_broker_recommend_trend.py::TestTrendRankingEmptyState::test_empty_table_has_data_false - assert 404 == 200
FAILED tests/test_broker_recommend_trend.py::TestTrendRankingIndustry::test_industries_joined - assert 404 == 200
FAILED tests/test_broker_recommend_trend.py::TestTrendImportable::test_repository_trend_methods_exist - AssertionError: BrokerRecommendRepository 缺趋势方法: get_trend_aggregations
FAILED tests/test_broker_recommend_trend.py::TestTrendImportable::test_service_trend_method_exists - AssertionError: BrokerRecommendAnalysisService 缺方法 get_trend_ranking
FAILED tests/test_broker_recommend_trend.py::TestTrendRankingAuth::test_trend_ranking_requires_auth - assert 404 == 401
======================= 30 failed, 10 warnings in 10.76s ========================
```

### 范围 B：现有 09 broker 测试回归（不应破坏）

```
collected 79 items
tests/test_broker_recommend_analysis_api.py ............................................  [ 35%]
............................                                             [ 70%]
tests/test_broker_recommend_sync.py .......................              [100%]
======================= 79 passed, 10 warnings in 20.74s =======================
```

### 收集阶段证据

```
collected 30 items
<Dir server>
  <Dir tests>
    <Module test_broker_recommend_trend.py>
      <Class TestTrendRankingAggregation> ... (7 coroutines)
      <Class TestTrendRankingMultiLevelSort> ... (4 coroutines)
      <Class TestTrendRankingGap> ... (3 coroutines)
      <Class TestTrendRankingPagination> ... (3 coroutines)
      <Class TestTrendRankingSearch> ... (5 coroutines)
      <Class TestTrendRankingSingleMonth> ... (3 coroutines)
      <Class TestTrendRankingEmptyState> ... (1 coroutine)
      <Class TestTrendRankingIndustry> ... (1 coroutine)
      <Class TestTrendImportable> ... (2 functions)
      <Class TestTrendRankingAuth> ... (1 coroutine)
========================= 30 tests collected in 0.03s ==========================
```

无 ImportError，无 collection error，测试代码语法正确、import 正确。失败完全来自被测端点/方法尚未实现，符合 red 阶段关键原则。

## 后续步骤

- 进入 `implement` 阶段（plan-01 §3 Task 列表 #1→#2→#3 repo 三方法 → #4 service `get_trend_ranking` → #5 API 端点 + 4 Pydantic model）：实现 `BrokerRecommendRepository` 3 跨月聚合方法 + `BrokerRecommendAnalysisService.get_trend_ranking`（连续性计数 ADR-3 + 多级排序 AC-03 + 分页 + 行业 JOIN + 展开券商预加载）+ GET /trend-ranking 端点 + 4 Pydantic model。
- 实现完成后跑同一组 pytest 用例，验证 30 个用例全部通过，证据写入 `docs/e2e/evidence/plan-01-10-pytest-green-2026-06-29.md`。
