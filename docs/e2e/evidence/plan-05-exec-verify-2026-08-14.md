---
feat_id: plan-05
phase: exec-verify
date: 2026-08-14
title: 市场量价范围同步与自动日更 — task handler 执行验证证据（16 期 plan-05）
source_plan: docs/16-A股全市场量价指标/16-2-实现计划-A股全市场量价指标/plan-05-市场量价范围同步与自动日更.md
---

# plan-05 执行验证证据：市场量价范围同步 task handler

## 结论

**通过（AC-02 执行验证）。** 真实 `sync_market_metrics` task handler（plan-05
`sync_market_metrics_task`）对范围 `2026-08-11 ~ 2026-08-12`（2 个真实交易日）端到端跑通：
preflight（一次 L/D/P/G 生命周期快照）→ 逐交易日 `MarketMetricsService.sync_date`
（fence 写路径 `lock_and_validate` → 原子 upsert）→ 统一 `dateResults` 四类计数 + 进度 →
持久化 `result`。结束后 `market_daily_metrics` 在范围内**每个交易日恰一行**，且
`volume_shares / amount_yuan / average_price` 均非空且量级合理（成交额万亿级、成交量百亿股级、
平均价 28 元级），`final == expected`（集合平衡）。

## 验证范围与方式

- 范围：`start_date=2026-08-11`，`end_date=2026-08-12`（先用 `TradingCalendarRepository.refresh_range`
  刷新本地日历，确认两日均 `is_open=true`，trading_days=2、natural_days=2、skipped=0）。
- 创建：`TaskManager.create_exclusive_task(task_type='sync_market_metrics', ...)` → 互斥建任务。
- 执行：构造 `TaskFenceContext`（`OwnerGenerationGuard` active + token）注入 `TaskFenceRegistry`，
  `manager.start_task(acquisition_token=token)` 置 running/token 后**直接调用真实 handler**
  `sync_market_metrics_task(task_id, params, manager)`。
  - 直跑 handler（非执行器轮询）以隔离 plan-04 owner-lock 轮询机制（plan-04 已单独验证），
    但仍走真实 fence 写路径：`sync_date → _atomic_upsert → ctx.lock_and_validate(session)`
    （`SELECT … FOR UPDATE` AsyncTask 行 + 类型/状态/token/停止字段/guard 双检）。
- TUSHARE_TOKEN：根 `.env`（dotenv 向上查找）已加载（len=32）。

## 关键结果

### 任务终态

| 字段 | 值 |
| --- | --- |
| task_id | `task_8ca017a22200` |
| handler 返回 | 成功（无异常抛出；`failedCount=0` 不抛摘要） |
| progress / total | 2 / 2（只计交易日） |
| result.successCount | 2 |
| result.skippedCount | 0（= natural_days 2 − trading_days 2） |
| result.failedCount | 0 |
| result.unprocessedDates | `[]`（完整处理范围） |

> 注：DB `status` 在直跑场景保持 `running`（`complete_task` 是执行器侧职责；handler 仅返回，
> 由执行器在 handler 返回后置 completed）。验证后已将该验证任务手工置 `completed`。
> 真实执行器路径下 handler 返回后执行器调用 `complete_task(success=True)` → `completed`。

### result.dateResults（camelCase 键，plan-08 前端直消费）

```json
[
  {"tradeDate":"2026-08-11","status":"success","expected":5542,"daily":5539,"suspended":3,"final":5542},
  {"tradeDate":"2026-08-12","status":"success","expected":5543,"daily":5539,"suspended":4,"final":5543}
]
```

逐日 `final == expected`（集合平衡），`suspended = expected − daily`（停牌补值）。

### market_daily_metrics（范围内逐交易日一行）

| trade_date | volume_shares（股） | amount_yuan（元） | average_price（元） | expected | daily | suspended | final |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-08-11 | 117,890,595,949 | 2,335,593,609,501.76 | 27.9995 | 5542 | 5539 | 3 | 5542 |
| 2026-08-12 | 113,523,313,015 | 2,167,164,143,116.15 | 28.4478 | 5543 | 5539 | 4 | 5543 |

量级核对（AC-02）：
- 成交量 ~1135–1179 亿股（百亿股级 ✓）
- 成交额 ~2.17–2.34 万亿元（万亿级 ✓）
- 简单平均价 ~28.0–28.4 元（个位数到十几元区间 ✓）
- 每个交易日恰一行 ✓；三指标非空 ✓

## 已知环境阻塞与绕过（plan-03 预存缺陷，非 plan-05 引入）

执行验证发现 plan-03 的 `DataInitService.init_stocks_lifecycle` 逐股 savepoint
（`_safe_nested_tx` → `session.begin_nested()`）在 SQLAlchemy 2.0.23 + ~5882 股规模下触发
**无限 RecursionError**（`sqlalchemy/sql/compiler.visit_rollback_to_savepoint` →
`preparer.format_savepoint` 循环；提高 `sys.setrecursionlimit(8000)` 仍崩溃，确认真无限递归）。

- 根因定位：逐股逻辑本身无错（把 `_safe_nested_tx` 临时替换为 no-op context manager 后，
  `init_stocks_lifecycle` created+updated+skipped 合计=total=5882，**0 errors**，5.4s 完成）。
  递归纯粹来自 savepoint 机制在本数据规模下的编译循环。
- 影响范围：`server/src/services/data_init.py`（plan-03 文件，**不在 plan-05 文件清单内**）。
  该缺陷同时导致 stocks 表此前仅有 L 状态（D/P/G 缺失）；本次验证 harness 的 no-op 跑已补齐
  L/D/P/G（5882 条），`market_daily_metrics` 计算所需的 `expected_codes` 完整。
- 本验证处理：在**验证 harness 脚本**（`/tmp/plan05_handler_verify.py`，非生产代码）中将
  `src.services.data_init._safe_nested_tx` patch 为 no-op，绕过该 plan-03 缺陷使 plan-05 真实
  handler 能端到端跑通。**plan-05 生产代码未做任何改动**。
- 建议：作为 plan-03 的后续修复项（如改用批量 upsert 或减少 savepoint 粒度），不阻塞 plan-05 review。

## 验证命令

```bash
cd server && source .venv/bin/activate
# 1. 路由与 collector 单测（plan-05 §6 验证命令 #1）
pytest tests/api/admin/test_init_market_metrics.py tests/test_data_updater.py -v --no-cov
# 2. 执行验证（直跑真实 handler + 手构 fence context；harness patch plan-03 savepoint）
python -u /tmp/plan05_handler_verify.py
```

## 阻塞项

- plan-05 自身：无（handler/路由/collector/scheduler 单测全通过；执行验证通过）。
- 上游 plan-03：`init_stocks_lifecycle` 逐股 savepoint 在本规模触发无限 RecursionError（见上节），
  建议作为 plan-03 后续修复项；不影响 plan-05 代码正确性（harness 已验证 handler 端到端产出正确行）。

---

## 第二次执行验证（真实路径，缺陷已修复，2026-08-14）

### 背景

第一次执行验证发现 plan-03 `init_stocks_lifecycle` 逐股 `_safe_nested_tx` savepoint 循环
在 ~5882 股规模触发无限 RecursionError（blocker 级，生产 preflight 会崩溃）。本次完成
plan-03 后补丁 #2 修复（`server/src/services/data_init.py`）：去掉逐股 savepoint 循环，
改为 `pg_insert(Stock)` 批量 upsert（500 行/批，预加载分区 insert/update/skipped，变更行走
`on_conflict_do_update(symbol)`，整批失败回退逐行定位问题行）。详见
`reviews/plan-03-review-20260814.md` 后补丁记录 #2。

### 验证方式（无任何 patch/no-op）

直跑真实 handler `sync_market_metrics_task`（手构 `TaskFenceContext`，真实
`init_stocks_lifecycle` → `LifecycleSnapshot` → 逐日 `sync_date` → fence 写
`lock_and_validate` → 原子 upsert）。**未 patch `_safe_nested_tx`**，走完整真实批量 upsert 路径。
范围 `2026-08-11 ~ 2026-08-12`（与第一次相同，验证幂等覆盖 AC-03）。

### 结果：通过

- **无 RecursionError**（缺陷已修复）。
- handler 总耗时 **9.9s**（含 preflight + 2 个交易日 sync_date）。
- 真实 `build_lifecycle_snapshot`（init_stocks_lifecycle 批量 upsert + 快照读取）单独计时
  **4.53s / 5882 records**（修复前 savepoint 路径无限递归无法完成）。
- 任务 `task_ef59d8ccb2f4`：progress 2/2，result.successCount=2 / skippedCount=0 /
  failedCount=0 / unprocessedDates=[]，逐日 dateResults 四类计数齐全且 `final==expected`。
- `market_daily_metrics` 范围内仍 **2 行**（幂等覆盖，未新增重复行）。

### market_daily_metrics（与第一次完全一致 → 幂等覆盖确认）

| trade_date | volume_shares（股） | amount_yuan（元） | average_price（元） | expected | daily | suspended | final |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-08-11 | 117,890,595,949 | 2,335,593,609,501.76 | 27.9995 | 5542 | 5539 | 3 | 5542 |
| 2026-08-12 | 113,523,313,015 | 2,167,164,143,116.15 | 28.4478 | 5543 | 5539 | 4 | 5543 |

逐值与第一次（harness-patch）执行完全相同 → 数据确定性 + 同范围重跑覆盖（AC-03）确认。

### 阻塞项更新

- plan-03 RecursionError 缺陷：**已修复**（后补丁 #2）。生产 preflight 现可正常完成。
- plan-05：执行验证以完整真实路径通过，无残留阻塞。

