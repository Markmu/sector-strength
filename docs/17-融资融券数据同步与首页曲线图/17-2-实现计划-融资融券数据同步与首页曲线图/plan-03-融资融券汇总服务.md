---
feat_id: "plan-03"
title: "融资融券汇总服务"
dimension: backend
phase: 2
status: done
depends_on: ["plan-01", "plan-02"]
---

# plan-03: 融资融券汇总服务

## 功能概要

- **目标**: 新建 `MarginService(session)`，实现单交易日完整闭环：日历守卫 → `get_margin` 拉取全部交易所行（实测 SSE/SZSE/BSE 三行，行数以接口实际返回为准）→ 五字段求和 + `rzrqye` 重算（全 Decimal）→ 原子 upsert（`on_conflict_do_update(trade_date)`，成功立即 commit、失败回滚当日）。不建仓储层（market-metrics 无仓储层先例，service 内直查，spec 代码地图条件分支裁定为不需要 `margin_repository.py`）。
- **完成后可观察结果**: 对一个交易日 T 调用 `sync_date(T)` 后，`market_margin_daily` 恰好新增/覆盖一行：rzye/rqye/rzmre/rzche/rqmcl 为全部交易所行求和、rzrqye 为 `Σrzye + Σrqye` 重算值（AC-1 数值用例：SSE {rzye:1.0e12, rqye:5.0e10, rzmre:7.0e10} + SZSE {rzye:8.0e11, rqye:3.0e10, rzmre:4.0e10} + BSE {rzye:2.0e10, rqye:1.0e10, rzmre:1.0e10} → rzye=1.82e12、rqye=9.0e10、rzmre=1.2e11、rzrqye=1.91e12）。同日重复 sync 为覆盖而非新增、updated_at 刷新（AC-2）。休市日返回 skipped 且不调 Provider；任何失败当日不留半成品。
- **依赖**: plan-01（MarketMarginDaily 表）、plan-02（get_margin 与完整性异常）
- **关联验收标准**: [AC-1]（聚合正确）、[AC-2]（幂等 upsert）
- **涉及架构模块**: 融资融券汇总服务（spec REQ-3，对应 16 期 plan-03 的 MarketMetricsService）
- **前置条件**: plan-01/02 已合并；本地 PostgreSQL 可用（日历守卫需真表）。
- **不在范围**: AsyncTask 编排与 fence context 的实现（plan-04；本功能仅消费 `task_context` 协议）；admin 触发端点（plan-05）；查询 API（plan-06）。

## 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| create | `server/src/services/margin_service.py` | MarginService.sync_date + 聚合 + _atomic_upsert + MarginSyncError |
| create | `server/tests/services/test_margin_service.py` | 单日闭环全套测试（AC-1/AC-2 数值用例） |

## 实现规格

### 后端部分

#### 1. MarginService.sync_date()（spec REQ-3）

```python
class MarginService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.data_source = DataSourceFactory.create()

    async def sync_date(
        self,
        trade_date: date,
        task_context: Optional["TaskFenceContext"] = None,  # TYPE_CHECKING 前向引用（16 期 plan-03 同款协议）
    ) -> str:  # "success" | "skipped"；抛异常 = failed
```

步骤（仿 `market_metrics_service.py:328` sync_date 结构，去掉生命周期/停牌/补价环节）：

1. **日历守卫**：`TradingCalendarRepository(self.session).get_record(T)`——本地记录休市 → `return "skipped"`（不调 Provider）；无覆盖记录 → 抛 `MarginSyncError`（拒绝按自然日/工作日猜测，16 期同款）
2. **拉取**：`rows = self.data_source.get_margin(T)`；`not rows` → 抛 `MarginSyncError("融资融券数据为空 trade_date=...")`（当日无两融数据，整日失败）
3. **聚合**（全 Decimal，禁止 float）：
   - `rzye = Σ row['rzye']`、`rqye = Σ row['rqye']`、`rzmre = Σ row['rzmre']`、`rzche = Σ row['rzche']`、`rqmcl = Σ row['rqmcl']`（五字段对全部行求和，spec 冻结 D2）
   - `rzrqye = Σ row['rzye'] + Σ row['rqye']`（**服务层重算；禁止直接 Σ row['rzrqye']**）
   - 各结果 `quantize(Decimal('0.01'))` 对齐 Numeric(20,2)
4. **原子 upsert**：`await self._atomic_upsert(...)`（见下）
5. **可观测性**：结构化日志 `trade_date/exchange_count/row_count/rzrqye/duration_ms/status`；交易所集合缺少 SSE 或 SZSE 时记 WARNING（含交易所集合）后继续（BSE 缺席不告警——口径对全部返回行求和，2026-08-14 用户裁定）

#### 2. _atomic_upsert()（仿 market_metrics_service.py:805）

```python
async def _atomic_upsert(
    self,
    trade_date: date,
    rzye: Decimal, rqye: Decimal, rzmre: Decimal,
    rzche: Decimal, rqmcl: Decimal, rzrqye: Decimal,
    task_context: Optional["TaskFenceContext"],
) -> None:
```

- `task_context` 非 None 时先 `await task_context.lock_and_validate(self.session)`（同事务 `SELECT ... FOR UPDATE` AsyncTask 行；协议方法实现于 16 期 plan-04 已交付的 `task_fence.py`，本期直接复用）
- `pg_insert(MarketMarginDaily).values(...)` + `on_conflict_do_update(index_elements=['trade_date'], set_={六指标列 + 'updated_at': func.now()})`
- **显式刷新 updated_at**（16 期 S1 教训，market_metrics_service.py:839-843 同款）：`on_conflict_do_update` 不触发 ORM onupdate，必须在 `set_` 显式写 `func.now()`，否则 AC-2 的 updated_at 刷新断言必挂
- 成功 `await self.session.commit()`；任何异常 `await self.session.rollback()` 后 raise（当日不留半成品）

#### 3. MarginSyncError

简单异常类（message 携带 trade_date 与原因）；无需 16 期的四类计数结构（两融无参与集合概念），`dateResults` 的逐日明细为 `{tradeDate, status, reason?}`（plan-04 handler 构造）。

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | MarginService 骨架与 sync_date 日历守卫 | backend | done | skipped/无记录抛错分支 |
| 2 | 多行聚合 + rzrqye 重算（Decimal） | backend | done | 五字段求和 + 重算 + quantize |
| 3 | _atomic_upsert（on_conflict + 显式 updated_at） | backend | done | task_context 协议调用 + commit/rollback |
| 4 | 编写 test_margin_service.py | backend | done | AC-1/AC-2 数值用例 + 守卫 + 回滚 |

## 验收标准

### 后端验收

- [x] AC-1 聚合复算：mock get_margin 返回 spec 数值三行（SSE {rzye:1.0e12, rqye:5.0e10, rzmre:7.0e10}、SZSE {rzye:8.0e11, rqye:3.0e10, rzmre:4.0e10}、BSE {rzye:2.0e10, rqye:1.0e10, rzmre:1.0e10}，rzche/rqmcl 任填），`sync_date` 后查库断言 `rzye == Decimal('1.82E12')`、`rqye == Decimal('9.0E10')`、`rzmre == Decimal('1.2E11')`、`rzrqye == Decimal('1.91E12')`
- [x] AC-1 rzrqye 重算：构造行内 tushare rzrqye 与 Σrzye+Σrqye 不一致的脏数据，断言落库值为**重算值**而非行值之和或行原值（mock 断言不读行 rzrqye 参与聚合）
- [x] AC-2 幂等：同日两次 `sync_date` → 表中恰一行；第二次值覆盖且 `updated_at` 刷新（断言 updated_at 变化）
- [x] 日历守卫：休市日返回 `"skipped"` 且 get_margin 零调用（mock 断言）；本地日历无记录 → 抛 MarginSyncError
- [x] 空数据：get_margin 返回空列表 → 抛 MarginSyncError，表无新行
- [x] 失败回滚：聚合或 upsert 阶段抛错（mock 注入）→ 表无新行、无半成品
- [x] Decimal 全程：构造 float 精度陷阱用例（如 0.1 累加）断言无累计误差
- [x] task_context 协议：非 None 时先 lock_and_validate 再 upsert（mock 验证调用顺序）；lock_and_validate 抛 FenceValidationError → 当日整体回滚
- [x] E2E 不适用：纯服务层功能；其数据正确性通过 plan-04 任务执行验证与 plan-07 面板展示间接验收

## 验证命令

```bash
cd server && source .venv/bin/activate

# 1. 服务单测（mock DataSourceFactory.create 的 get_margin；日历守卫用例先经
#    TradingCalendarRepository 种子本地日历，参照 test_market_metrics_service.py 惯例）
pytest tests/services/test_margin_service.py -v --no-cov

# 2. 全量回归（确认未触碰 market_metrics_service 行为）
pytest tests/services/ -q --no-cov
```

## 交接上下文

- **spec 章节**: REQ-3（汇总服务）、边界（必须：rzrqye 重算 / 原子 upsert 三范式复用）、任务清单 T3
- **相关代码**: `server/src/services/market_metrics_service.py`（sync_date L328 结构范式、`_atomic_upsert` L805 逐行对照、显式 updated_at L839-843）、`server/src/services/trading_calendar_repository.py`（get_record，16 期交付直接复用）、`server/src/services/task_fence.py`（TaskFenceContext 协议，16 期交付直接复用）
- **契约 / 数据对象**: `MarketMarginDaily`（plan-01）；`TaskFenceContext`（`lock_and_validate(session)`，TYPE_CHECKING 前向引用 + `from __future__ import annotations`，运行时不导入）
- **下游消费方**: plan-04（handler 逐日调 `sync_date(day, task_context=ctx)`；无 16 期 close_cache/lifecycle_snapshot 参数——两融无跨日状态）
- **实现级补充项**: 全部行参与求和已由 2026-08-14 用户裁定升级为 spec 级口径（D2：行数以接口实际返回为准，实测 SSE/SZSE/BSE 三行）；缺 SSE/SZSE 记 WARNING 继续是实现级护栏
- **不建仓储层说明**: spec 代码地图写"margin_repository.py — NEW（若 market-metrics 有仓储层；否则 service 内直查）"——实测 market-metrics 无仓储层（MarketMetricsService 直查直写），故本期同样 service 内直查，不创建该文件

## 风险与边界

- **执行顺序**: 按 Task 列表顺序执行
- **验证失败排查方向**: 测试先 mock `DataSourceFactory.create`（参照 `tests/services/test_market_metrics_service.py` patch 惯例）；AC-2 的 updated_at 断言失败先查 `set_` 是否显式写 func.now()
- **允许修改的额外文件**: 无
- **暂停条件**: 若 16 期 `TaskFenceContext.lock_and_validate` 的类型校验（FENCED_TASK_TYPE）在 margin 任务上行不通（plan-04 扩展前），单测阶段以 mock task_context 规避，不提前改 16 期文件——真类型扩展在 plan-04
- **风险备注**: 休市日 tushare margin 也可能返回空——先日历守卫再拉取的顺序保证休市日不浪费积分配额

### 后端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| 本地日历无该日记录 | 抛 MarginSyncError（拒绝猜测），不落库 | done |
| 休市日 | 返回 skipped，零 Provider 调用 | done |
| get_margin 返回空列表 | 抛 MarginSyncError，当日失败 | done |
| 返回行数异常（缺 SSE/SZSE 或仅 1 行） | 全部行参与求和（口径兼容），记 WARNING 日志 | done |
| upsert 前夕 fence 校验失败 | 业务写与任务写一起 rollback | done |
| 同日重复同步 | upsert 覆盖，updated_at 显式刷新 | done |
