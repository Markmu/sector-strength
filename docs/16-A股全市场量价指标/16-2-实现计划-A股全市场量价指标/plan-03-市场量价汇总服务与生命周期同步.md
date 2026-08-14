---
feat_id: "plan-03"
title: "市场量价汇总服务与生命周期同步"
dimension: backend
phase: 2
status: done
depends_on: ["plan-01", "plan-02"]
---

# plan-03: 市场量价汇总服务与生命周期同步

## 功能概要

- **目标**: 新建 `MarketMetricsService(session)`，实现单交易日完整闭环：生命周期快照校验 → 全市场行情拉取与过滤 → 停牌确认与前收盘补值 → 完整性核验 → Decimal 计算 → 日级原子 upsert；同时扩展 `DataInitService` 提供 L/D/P/G 联合生命周期同步（upsert + 四状态全集 set-diff 清理），产出不可变 `LifecycleSnapshot`。
- **完成后可观察结果**: 对一个完整交易日调用 `sync_date` 后，`market_daily_metrics` 恰好新增/覆盖一行，量、额、平均价可由原始行复算（vol×100、amount×1000、Σclose/最终参与数）；全天停牌股票量额为 0 且沿用最近有效收盘价；任何不完整场景（缺行、重复、集合不平衡、补价失败）整日不落库并抛出含四类计数与问题代码样本的错误；重复同步同日为覆盖而非新增。自动日更路径传 `task_context=None` 即可工作。
- **依赖**: plan-01（TradingCalendarRepository 日历守卫）、plan-02（四个采集方法与完整性异常）
- **关联验收标准**: [AC-01]（单日正确性）、[AC-03]（重复同步安全覆盖）、[AC-09]（sync_date 非交易日守卫）、[AC-13]（全天停牌参与计算）
- **涉及架构模块**: 市场量价汇总服务（架构 §4.2 模块 2）
- **前置条件**: plan-01/02 已合并；本地 PostgreSQL 可用。
- **不在范围**: AsyncTask 编排与 TaskFenceContext 的 guard 实现（plan-04；本功能仅定义 `task_context` 参数协议）；范围任务与自动日更接线（plan-05）；查询 API（plan-06）。

## 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| create | `server/src/services/market_metrics_service.py` | MarketMetricsService + LifecycleSnapshot |
| modify | `server/src/services/data_init.py` | 新增 `init_stocks_lifecycle()`（L/D/P/G 联合同步 + 四状态全集清理） |
| create | `server/tests/services/test_market_metrics_service.py` | 单日闭环全套测试 |
| modify | `server/tests/test_data_init.py` | 生命周期联合同步测试（现有文件，架构路径偏差见交接上下文） |

## 实现规格

### 后端部分

#### 1. DataInitService.init_stocks_lifecycle()（ADR-2 / §6.2.4 / §8.6 首行）

```python
async def init_stocks_lifecycle(self) -> dict:  # 返回统计；不返回 snapshot
```

- 调 `get_lifecycle_stocks()`（四状态全集）
- **记录级校验**：所有记录 `ts_code/exchange` 必填；L/D/P 必须有 `list_date`；D 还必须有 `delist_date`；G 允许两日期为空。任一违反 → 抛错（含代码样本），不降级用当前 L 集合
- 逐股 savepoint upsert 到 `stocks`（复用 `_safe_nested_tx` 与现有字段映射，data_init.py L30/L464-614 范式），A 股以 **L/D/P/G 四状态联合全集** 做 set-diff 清理（替换现 `init_stocks` 仅以 L 清理的行为——旧 `init_stocks()` 保持不动，供其他调用方使用）
- 港股清理逻辑不受影响（沿用现有 `_cleanup_disappeared_stocks` 入口，仅 A 股全集口径变化）
- 结构化日志：四状态行数、created/updated/deleted 计数（架构 §8.5）

#### 2. LifecycleSnapshot（架构 §6.1.2）

`market_metrics_service.py` 内 frozen dataclass：

- `records: tuple[LifecycleStock, ...]` + `status_flags: dict[str, bool]`（L/D/P/G 四类成功标记）
- `expected_codes(trade_date: date) -> set[str]`：交易所 ∈ {SSE, SZSE, BSE}（由 ts_code 后缀 .SH/.SZ/.BJ 判定，exchange 字段缺失时以后缀兜底）且：
  - L/P：`list_date <= T`
  - D：`list_date <= T` 且 `T < delist_date`
  - G：**无论日期字段是否为空固定排除**
- 构造入口 `build_lifecycle_snapshot()`：调 `init_stocks_lifecycle()` 后从库里读回（或直接用拉取结果）构建；快照不可变，范围任务与日更各只构建一次

#### 3. MarketMetricsService.sync_date()（架构 §6.1 全链）

```python
async def sync_date(
    self, trade_date: date,
    lifecycle_snapshot: LifecycleSnapshot,
    task_context: Optional["TaskFenceContext"] = None,  # TYPE_CHECKING 前向引用，plan-04 落地
    close_cache: Optional[MutableMapping[str, tuple[date, Decimal]]] = None,  # 范围任务跨日缓存
) -> Literal["success", "skipped", "failed"]  # 抛异常=failed
```

步骤（§6.1.1-9）：

1. **日历守卫**：`TradingCalendarRepository.get_record(T)`——本地记录休市 → 返回 `skipped`；无覆盖记录 → 抛错（AC-09）
2. **快照校验**：`status_flags` 四类全真、逐记录字段校验（同 init_stocks_lifecycle 规则）
3. **拉取**：`get_market_daily_quotes(T, expected_count=len(snapshot.expected_codes(T)))`；空列表 → 抛"全市场空"
4. **过滤与数值复验**：仅保留 `.SH/.SZ/.BJ` 且 ∈ 预期集合的行；越界代码/日期不符 → 抛错（复验 finite/close>0/vol≥0/amount≥0）
5. **停牌确认**：对预期集合中无 daily 的代码查 `get_suspensions(T)`：daily 已存在者（含盘中临停）直接用；仅 `suspend_type=='S'` 且 `suspend_timing` 为空或被明确规则识别为全天 → 进补价集合；无法判定 → 整日失败（AC-13 / §8.6）
6. **有界补价**（ADR-3 / §6.1.6）：补价集合按 ≤100 代码分块；从 `[T-60日, T-1日]`（自然日窗口）起向前调 `get_close_quotes_in_window`；逐代码取 `<T` 的最大有效 `trade_date/close`；扫描下界 = 各股 `list_date`；每批最多 250 个窗口；总请求预算常量 `MAX_CLOSE_LOOKBACK_REQUESTS`（写入模块常量，§8.4）；先查 `close_cache` 命中则免请求；扫描到底未命中 → 整日失败（**禁止 qfq 后备/逐股无界 N+1**）
7. **补值与平衡**：停牌行补 `{close:last_close, vol:0, amount:0}`；校验 `daily_count + full_day_suspended_count == expected_count == final_count`；仅当某交易所预期非空、补齐后最终参与为 0 时判该交易所整体缺失 → 失败
8. **计算**（全 Decimal）：`volume_shares = Σ(vol×100)`；`amount_yuan = Σ(amount×1000)`；`average_price = Σclose / final_count`（quantize 4 位）
9. **原子 upsert**：`task_context` 非 None 时先 `await task_context.lock_and_validate(session)`（同事务 `SELECT ... FOR UPDATE` AsyncTask 行，见 §6.1.9——本功能只调协议方法，实现于 plan-04）；随后 `pg_insert(MarketDailyMetric).on_conflict_do_update(trade_date)` 单事务提交。任何异常整体 rollback，不保留部分日结果（AC-01/03）
10. 结构化日志：`trade_date/page_count/expected/daily/suspended/final/duplicate_count/duration_ms/status`（§8.5）

#### 4. 失败错误结构

自定义异常 `MarketMetricsSyncError`：`expected/daily/suspended/final` 四类计数 + 最多 50 个问题代码样本（§6.2 实现原则），message 截断展示（AC-07）。

**可观测性（架构 §8.5）**：每日结果日志使用标准 `logging` 结构化字段（与现有服务一致，无 structured logger 则 key=value 拼接），失败日志只记录 endpoint、错误类别和问题代码样本。

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | DataInitService.init_stocks_lifecycle 联合同步与四状态清理 | backend | done | 记录级校验 + savepoint upsert + set-diff |
| 2 | LifecycleSnapshot 与 expected_codes | backend | done | G 固定排除、D 需 delist_date |
| 3 | sync_date 日历守卫与快照校验 | backend | done | skipped/failed 分支 |
| 4 | 行情拉取过滤与停牌确认 | backend | done | suspend_type=S 全天判定 |
| 5 | 分块有界前收盘补价与缓存 | backend | done | 100/批、60 日窗、250 窗、预算常量 |
| 6 | 集合平衡 + Decimal 计算 + 原子 upsert | backend | done | task_context 协议调用 |
| 7 | MarketMetricsSyncError 四类计数与样本 | backend | done | ≤50 代码截断 |
| 8 | 编写 test_market_metrics_service.py 与 test_data_init.py 增量 | backend | done | 覆盖 AC-01/03/09/13 与边界 |

## 验收标准

### 后端验收

- [ ] AC-01 完整数据日：`sync_date` 落库一行，`volume_shares/amount_yuan/average_price` 可由 mock 原始行手工复算（手×100、千元×1000、Σclose/数）
- [ ] AC-01 任一关键值非法、集合不平衡、预期外代码、重复 → 整日不落库且表无新增行
- [ ] AC-03 同日重复 `sync_date` → 恰一行，值覆盖更新（`updated_at` 变化），不新增重复行
- [ ] AC-09 本地日历休市日 → 返回 `skipped` 且不调 Provider（mock 断言零调用）；无日历记录 → 抛错
- [ ] AC-13 全天停牌股：量额为 0、close=最近有效收盘；`suspended_stock_count` 计入 final；suspend 信息或前收盘缺失 → 整日失败
- [ ] 盘中临停（daily 有行）优先用 daily 行，不进补价集合
- [ ] 补价窗口扫描遵守 100/批、≤250 窗、总预算常量；预算耗尽仍有未决代码 → 整日失败
- [ ] G 状态股不出现在任何 T 的参与集合；L/D/P 缺 list_date、D 缺 delist_date → 抛错
- [ ] init_stocks_lifecycle 清理仅以四状态联合全集为口径（构造 D-only 场景验证不误删）
- [ ] Decimal 全程：构造 float 精度陷阱用例断言无累计误差
- [ ] E2E 不适用：纯服务层功能；其数据正确性通过 plan-05 任务执行验证与 plan-07 面板展示间接验收

## 验证命令

```bash
cd server && source .venv/bin/activate

# 1. 服务单测（mock DataSourceFactory.create）
pytest tests/services/test_market_metrics_service.py -v --no-cov

# 2. 生命周期同步测试
pytest tests/test_data_init.py -v --no-cov

# 3. 全量回归（确认 init_stocks 旧路径未破坏）
pytest tests/ -q --no-cov
```

## 交接上下文

- **架构章节**: §4.2 模块 2、§5 ADR-2/3/4、§6.1、§7.1、§8.2/8.5/8.6
- **相关代码**: `server/src/services/data_init.py`（`_safe_nested_tx` L30、`init_stocks` L464-614、`_cleanup_disappeared_stocks` 调用 L578-581 / 定义 L616）；模型 `MarketDailyMetric`（plan-01）
- **契约 / 数据对象**: `LifecycleSnapshot`、`TaskFenceContext` 协议（`lock_and_validate(session)`，实现在 plan-04 `task_fence.py`；本功能用 `from __future__ import annotations` + TYPE_CHECKING 引用，运行时不导入）
- **下游消费方**: plan-05（handler 与 collector 调 `sync_date`；`close_cache` 由范围任务按升序传入）
- **路径偏差标注**: 架构 §9 Phase A 写 `server/tests/services/test_data_init.py`，实际现有文件为 `server/tests/test_data_init.py`（flat）——以代码约定为准，修改现有文件
- **实现级补充项**: `close_cache` 参数与预算常量服务于 AC-13/AC-02（跨日缓存命中），非新造 AC

## 风险与边界

- **执行顺序**: 按 Task 列表顺序执行；Task 1-2 是 3-6 的前置
- **验证失败排查方向**: 测试先 mock `DataSourceFactory.create`（参照 tests 内既有 patch 惯例）；日历守卫用例需先经 Repository 写入本地日历
- **允许修改的额外文件**: 无（`stocks` 表不加列——已核实 `Stock` 具备 `exchange/list_status/list_date/delist_date`，见 server/src/models/stock.py:27-31）
- **暂停条件**: 若现有 `init_stocks()` 的调用方（其他任务 handler）依赖"仅 L 清理"语义且测试无法兼容四状态口径，暂停并请求确认清理入口拆分方式
- **风险备注**: suspend_timing 全天判定规则保留适配器侧"明确识别"口径——无法判定一律失败，宁失败不猜测（§8.6）

### 后端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| 快照四类标记不全 | 抛错，不用当前 L 集合降级 | done |
| 单交易所补齐后参与为 0 | 该交易所整体缺失 → 整日失败 | done |
| 补价命中 close_cache | 免 Provider 请求直接复用 | done |
| upsert 前夕 task_context 校验失败 | 业务写与任务写一起 rollback | done |
| 平均价除零（final_count=0） | 不可能到达（平衡校验先失败），防御性抛错 | done |
