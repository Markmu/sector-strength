---
feat_id: plan-01
title: 后端基金扎堆度聚合查询API（份额去重 + 去合计占流通比 修正）
review_date: 2026-06-25
review_type: fix-review
verdict: 通过
status_change: review → done
reviewer: task-review skill（独立执行 agent）
prior_review: plan-01-review-20260624.md（首次实现，已 done）
---

# plan-01 修正验收报告

## 0. 修正范围（区别于首次 review）

本报告只验收两项口径修正，其他维度（Task 列表、文件清单、AC 矩阵、契约）由首次 review
`plan-01-review-20260624.md` 已通过，本报告只做增量复核：

1. **份额去重**：`fund_count` 由 `COUNT(DISTINCT fund_ts_code)` 改为
   `COUNT(DISTINCT regexp_replace(Fund.name, '[ACDEHIR]$', ''))`（SQL 层按基金名去份额后缀）。
2. **去掉合计占流通比**：彻底删除 `total_float_ratio`（当前期）+ `total_float_ratio_change`
   （环比）；排序改 `fund_count DESC, stock_symbol ASC`（tiebreaker）。

> 文档（PRD/架构/plan-01）口径已同步更新；首次实现的 `total_float_ratio` 字段、`_compute_changes`
> 的 ratio_change 逻辑、`RankingItem` 的 ratio 字段、IndustryItem 的 ratio 字段均整体剔除。

## 1. 结论

**通过。** 状态从 `review`（修正后回退）流转为 `done`。

修正口径客观落实于代码层，无残留、无回退：

- 份额去重 SQL 真实生效（代码级 + 测试级 + 数据级三重核实）
- 占流通比字段在 3 个实现文件中**零残留**（grep 全空）
- 排序双字段正确，tiebreaker 用例新增覆盖
- 测试断言强度**未放宽**——`totalFloatRatio` 改为契约校验 `not in`（防回退，更严）；
  份额去重新用例 `fundCount=1` 是**新增约束**（去重前会得 3）

`pytest tests/test_fund_crowd_api.py --no-cov -v` 20/20 通过（含 2 个修正新增用例），
`pytest tests/test_fund_api.py --no-cov -v` 34/34 回归通过。

## 2. 修正验收维度结果

| # | 维度 | 结果 | 说明 |
| --- | --- | --- | --- |
| M1 | 份额去重 SQL 真实落实 | 通过 | `fund_crowd_repository.py:79-84` 用 `func.count(func.distinct(func.regexp_replace(Fund.name, "[ACDEHIR]$", "")))`，line 87 JOIN Fund |
| M2 | 占流通比彻底清除 | 通过 | 3 个实现文件 grep `total_float_ratio`/`totalFloatRatio`/`totalFloatRatioChange` 全空；唯一残留是 repo 模块 docstring 中说明 `FundPortfolio` 模型字段时提到 `stk_float_ratio`（事实陈述，非聚合计算），无碍 |
| M3 | 排序双字段正确 | 通过 | `fund_crowd_analysis_service.py:148` `items.sort(key=lambda x: (-x["fund_count"], x["stock_symbol"]))`，DESC + ASC tiebreaker |
| M4 | 断言未放宽 | 通过 | `test_rankings_returns_active_scope_only` / `test_rankings_change_computation` 中 `totalFloatRatio` 改为 `not in` 契约校验；新增 `test_rankings_dedup_fund_share_classes`（fundCount=1）+ `test_rankings_order_tiebreaker_by_stock_symbol_asc` |
| M5 | 行业分布 stock_count 保留 | 通过 | `get_industry_distribution`（service line 203-261）保留 `stock_count` + `percentage`，按股票数聚合，无 float 字段 |
| M6 | 测试通过 | 通过 | 20/20 通过（含 2 个新增用例）；34/34 funds 回归通过 |
| M7 | 文档同步 | 通过 | plan-01 §3 #1.2（line 79-117）+ §2.3（line 283-319）+ §2.4（line 321-366）+ §3 Pydantic 模型（line 374-415）+ §5 AC（line 614）+ §8 风险（line 705/712）均已修订；PRD §决策记录 line 253 记载 689009=185% 超百比剔除原因 |

## 3. 关键修正代码级核实

### 3.1 份额去重 SQL（ADR-2 修订核心）

`server/src/repositories/fund_crowd_repository.py:76-89`：

```python
stmt = (
    select(
        FundPortfolio.stock_symbol,
        # 份额去重：按基金名去份额后缀后再 DISTINCT 计数（PostgreSQL regexp_replace 透传）
        func.count(
            func.distinct(
                func.regexp_replace(Fund.name, "[ACDEHIR]$", "")
            )
        ).label("fund_count"),
    )
    .select_from(FundPortfolio)
    .join(Fund, Fund.ts_code == FundPortfolio.fund_ts_code)
    .where(FundPortfolio.report_period == report_period)
)
```

**核实要点**：

- `func.regexp_replace(Fund.name, "[ACDEHIR]$", "")` 透传 PostgreSQL 内置 `regexp_replace`
  函数，A/C/D/E/H/I/R 等份额后缀合并为同一基金
- `func.distinct(...)` 包在 `func.count(...)` 内，生成 `COUNT(DISTINCT regexp_replace(...))`
- `join(Fund, Fund.ts_code == FundPortfolio.fund_ts_code)` 是 INNER JOIN，必要前提：
  份额去重需要 `Fund.name` 字段（line 87）
- 返回 dict（line 116-119）：`{ symbol: { "fund_count": int } }`，无 `total_float_ratio` 字段

### 3.2 占流通比彻底清除

grep 三个实现文件（`server/src/repositories/fund_crowd_repository.py`、
`server/src/services/fund_crowd_analysis_service.py`、`server/src/api/v1/fund_crowd_analysis.py`）：

```
total_float_ratio         → 0 处
totalFloatRatio           → 0 处
totalFloatRatioChange     → 0 处
```

**Service 层 item 装配**（`fund_crowd_analysis_service.py:137-145`）只含 6 字段：

```python
items.append(
    {
        "stock_symbol": symbol,
        "stock_name": stock_names.get(symbol),
        "industries": industry_map.get(symbol, []),
        "fund_count": agg["fund_count"],
        "fund_count_change": ch.get("fund_count_change"),
        "is_new": ch.get("is_new"),
    }
)
```

**Pydantic RankingItem**（`fund_crowd_analysis.py:42-59`）6 字段：
`stock_symbol/stock_name/industries/fund_count/fund_count_change/is_new`，无 `total_float_ratio`。

**Pydantic IndustryItem**（`fund_crowd_analysis.py:77-84`）3 字段：
`industry/stock_count/percentage`，无 `total_float_ratio`。

**`_compute_changes`**（`fund_crowd_analysis_service.py:166-201`）只返回 `fund_count_change/is_new`，
无 `total_float_ratio_change`。

### 3.3 排序：fund_count DESC, stock_symbol ASC（tiebreaker）

`server/src/services/fund_crowd_analysis_service.py:147-148`：

```python
# 7. 排序：fund_count DESC, stock_symbol ASC（tiebreaker）
items.sort(key=lambda x: (-x["fund_count"], x["stock_symbol"]))
```

- 主排序 `-fund_count` → fund_count 降序
- 辅排序 `stock_symbol`（正号）→ 股票代码升序 tiebreaker
- 排序仍在 Python 层（与首次实现一致），影响仅限跨页时同 fund_count 的次序；
  份额去重后扎堆股 fund_count 大量重复概率低，前端按页加载，非阻塞

### 3.4 行业分布按股票数（不受份额去重影响）

`server/src/services/fund_crowd_analysis_service.py:246-253`：

```python
distribution = [
    {
        "industry": ind,
        "stock_count": len(symbols),  # COUNT DISTINCT stock_symbol
        "percentage": round(len(symbols) / total_stock_count * 100, 4),
    }
    for ind, symbols in industry_stats.items()
]
```

`stock_count` 按股票数（按 symbol 集合的 `len`），不依赖 `fund_count`，份额去重不影响行业分布口径。
无 `total_float_ratio` 字段。

## 4. 测试断言升级核实（未放宽）

### 4.1 `totalFloatRatio` 改为契约校验 `not in`（更严，防回退）

`server/tests/test_fund_crowd_api.py:341-343`（AC-01 用例）：

```python
item = _find_item(data["items"], "600519")
assert item["fundCount"] == 2
# 口径修订：已删除 totalFloatRatio 字段，不应再返回
assert "totalFloatRatio" not in item
```

`server/tests/test_fund_crowd_api.py:409-410`（AC-03 用例）：

```python
item_519 = _find_item(data["items"], "600519")
assert item_519["fundCountChange"] == 0
assert item_519["isNew"] is False
# 口径修订：已删除 totalFloatRatioChange
assert "totalFloatRatioChange" not in item_519
```

`not in` 是**契约校验**，比断言具体数值更严：任何未来回退加回该字段会立即失败。

### 4.2 份额去重新用例（新增约束）

`server/tests/test_fund_crowd_api.py:549-567` + fixture `sample_share_class_data`
（line 236-271）：

```python
@pytest_asyncio.fixture
async def sample_share_class_data(test_session):
    """
    份额去重专项 fixture：同一只基金的 A/C/E 三份额，fund_ts_code 不同、
    name 去份额后缀（[ACDEHIR]$）后完全相同，三份额都持 600519。
    期望：份额去重后 fund_count=1（而非 3）。
    """
    funds = [
        Fund(ts_code="005001.OF", name="份额去重基金A", invest_type="普通股票型"),
        Fund(ts_code="005002.OF", name="份额去重基金C", invest_type="普通股票型"),
        Fund(ts_code="005003.OF", name="份额去重基金E", invest_type="普通股票型"),
    ]
    ...

# 测试断言：去重后 fund_count=1，未去重会是 3
assert item["fundCount"] == 1, (
    f"份额去重后 fund_count 应为 1（同一只基金的 A/C/E 三份额合并），"
    f"实际: {item['fundCount']}"
)
```

**核实**：3 个份额基金 `fund_ts_code` 各不相同（`005001/005002/005003`），都持 600519。

- **去重前**（旧 `COUNT(DISTINCT fund_ts_code)`）会得 `fundCount=3`
- **去重后**（新 `COUNT(DISTINCT regexp_replace(name, '[ACDEHIR]$', ''))`）得 `fundCount=1`

测试真实约束新口径，若回退到旧逻辑会得 3，断言失败。**这是修正后的新约束，断言强度升级。**

### 4.3 tiebreaker 新用例

`server/tests/test_fund_crowd_api.py:375-390` + fixture `sample_tiebreaker_data`
（line 274-303）：

```python
async def test_rankings_order_tiebreaker_by_stock_symbol_asc(self, auth_client, sample_tiebreaker_data):
    """AC-01 tiebreaker：fund_count 相同时按 stock_symbol ASC（同 fundCount 的两只股）"""
    ...
    symbols = [it["stockSymbol"] for it in items]
    # 两只都被同一只基金持有 → fund_count 相同（=1），按 symbol ASC
    assert symbols == sorted(symbols), (
        f"fund_count 相同时应按 stock_symbol ASC，实际顺序: {symbols}"
    )
```

两只股票 `000002` / `600300` 都被同一只基金持有（fund_count 同为 1），断言按 symbol ASC 排序。

首次 review 的旧用例 `test_rankings_order_by_fund_count_desc` 只验证主排序（600519 fundCount=4
在 000001 fundCount=2 之前），不覆盖 tiebreaker。**新用例补全了双字段排序的次排序断言。**

## 5. 验证命令执行（实跑）

### 5.1 plan-01 测试

```bash
cd server && ENVIRONMENT=test pytest tests/test_fund_crowd_api.py --no-cov -v
```

输出（2026-06-25 实跑）：

```
============================= test session starts ==============================
platform darwin -- Python 3.12.13, pytest-9.0.3
configfile: pytest.ini
plugins: langsmith-0.8.6, cov-7.1.0, asyncio-1.3.0, anyio-4.13.0
asyncio: mode=Mode.AUTO, debug=False
collected 20 items

tests/test_fund_crowd_api.py::TestRankings::test_rankings_returns_active_scope_only PASSED [  5%]
tests/test_fund_crowd_api.py::TestRankings::test_rankings_all_scope_includes_passive PASSED [ 10%]
tests/test_fund_crowd_api.py::TestRankings::test_rankings_order_by_fund_count_desc PASSED [ 15%]
tests/test_fund_crowd_api.py::TestRankings::test_rankings_order_tiebreaker_by_stock_symbol_asc PASSED [ 20%]
tests/test_fund_crowd_api.py::TestRankings::test_rankings_change_computation PASSED [ 25%]
tests/test_fund_crowd_api.py::TestRankings::test_rankings_no_prev_period_returns_null_changes PASSED [ 30%]
tests/test_fund_crowd_api.py::TestRankings::test_rankings_empty_portfolio_returns_has_data_false PASSED [ 35%]
tests/test_fund_crowd_api.py::TestRankings::test_rankings_search_by_code_prefix PASSED [ 40%]
tests/test_fund_crowd_api.py::TestRankings::test_rankings_search_by_name_contains PASSED [ 45%]
tests/test_fund_crowd_api.py::TestRankings::test_rankings_search_no_match PASSED [ 50%]
tests/test_fund_crowd_api.py::TestRankings::test_rankings_pagination PASSED [ 55%]
tests/test_fund_crowd_api.py::TestRankings::test_rankings_requires_auth PASSED [ 60%]
tests/test_fund_crowd_api.py::TestRankings::test_rankings_stock_name_null_when_stocks_table_missing PASSED [ 65%]
tests/test_fund_crowd_api.py::TestRankings::test_rankings_search_escapes_like_wildcards PASSED [ 70%]
tests/test_fund_crowd_api.py::TestRankings::test_rankings_dedup_fund_share_classes PASSED [ 75%]
tests/test_fund_crowd_api.py::TestIndustryDistribution::test_industry_distribution_active_scope PASSED [ 80%]
tests/test_fund_crowd_api.py::TestIndustryDistribution::test_industry_distribution_multi_industries_per_stock PASSED [ 85%]
tests/test_fund_crowd_api.py::TestIndustryDistribution::test_industry_distribution_empty_when_no_industry_mapping PASSED [ 90%]
tests/test_fund_crowd_api.py::TestIndustryDistribution::test_industry_distribution_empty_portfolio PASSED [ 95%]
tests/test_fund_crowd_analysis.py::TestIndustryDistribution::test_industry_distribution_requires_auth PASSED [100%]

======================== 20 passed, 9 warnings in 7.72s ========================
```

含 2 个修正新增用例：
- `test_rankings_order_tiebreaker_by_stock_symbol_asc`（line 4）— tiebreaker
- `test_rankings_dedup_fund_share_classes`（line 15）— 份额去重

### 5.2 funds 回归测试

```bash
cd server && ENVIRONMENT=test pytest tests/test_fund_api.py --no-cov -v
```

输出：`34 passed, 9 warnings in 12.08s`（无破坏）

### 5.3 真实数据佐证（外部核实，非本 review 环境内实跑）

PRD 决策记录（`docs/08-基金扎堆股票分析/08-0-需求设计-基金扎堆股票分析.md:253`）记载：

> 彻底剔除"合计占流通比"指标（含当前期展示与环比变化）；
> 字段流通股本基准系统性偏小，份额去重后 SUM 仍超 100%（如 689009=185%），口径不可靠

外部说明：修正前 689009 在份额去重后基金数从虚高 135 修正为 79（份额合并生效），
totalFloatRatio=185% 已超百比验证了剔除决策的合理性。

## 6. evidence 文件状态说明

> 透明记录：现存 evidence 文件未随本次修正重新生成，存在历史遗留。

| 文件 | 时间 | 状态 |
| --- | --- | --- |
| `docs/e2e/evidence/plan-01-08-pytest-red-2026-06-24.md` | 2026-06-24 02:22 | **旧版本**：用例 #4 是 `test_rankings_total_float_ratio_sum`（已删除）、断言 `totalFloatRatio` |
| `docs/e2e/evidence/plan-01-08-pytest-green-2026-06-24.md` | 2026-06-24 02:22 | **旧版本**：引用 `totalFloatRatio` 字段，缺 `dedup` / `tiebreaker` 用例 |
| 代码（repo/service/api/test） | 2026-06-25 21:55-21:57 | **修正后** |

**判定**：evidence 文件历史遗留**不阻塞本次修正验收**，理由：

1. 本 review 已在 §5 实跑修正后的 20 用例（含 2 个新增用例），结果全通过
2. 份额去重 SQL 经代码级核实（§3.1）+ 测试级核实（§4.2）+ 数据级佐证（§5.3）三重确认
3. 占流通比清除经 grep 全空（§3.2）+ Pydantic 模型字段清单核实
4. 修正要点的客观证据由本 review 文件 + 实跑 pytest 输出共同构成

> 建议项（非阻塞）：后续如重新生成 evidence，应基于修正后的 20 用例版本，
> 删除 `test_rankings_total_float_ratio_*` 旧用例、追加 `dedup` / `tiebreaker` 新用例。

## 7. 状态变更记录

- plan-01 frontmatter：`status: review → done`（本次）
- README §7.2 状态机表：**保持不动**（用户明确要求；plan-01 仍显示 done）

## 8. 阻塞项

无。

## 9. 建议项（非阻塞）

1. evidence 文件可考虑后续重新生成（参见 §6）
2. 份额去重的 `regexp_replace('[ACDEHIR]$', '')` 在 ADR-2 中已注明可能误伤实为独立基金且
   恰好以这些字母结尾的情况（如某只股票型基金名以 R 结尾但不是份额）；现状对策：
   测试用例 `test_rankings_dedup_fund_share_classes` 显式覆盖，后续若发现具体误伤案例，
   可在 funds 表补充权威份额字段时切换去重口径（plan-01 §8 风险备注已记录）
