---
feat_id: "plan-04"
title: "异步任务与fencing"
dimension: backend
phase: 2
status: done
depends_on: ["plan-03"]
---

# plan-04: 异步任务与fencing

## 功能概要

- **目标**: 新增保留任务类型 `sync_market_margin`（`TaskType.SYNC_MARKET_MARGIN`）并注册范围同步 handler（逐日串行调 `MarginService.sync_date`，camelCase result 含成功/跳过/失败计数与逐日明细）；把 16 期 plan-04 交付的 fencing 基础设施**扩展**为支持第二个任务类型：锁 key 常量、`create_exclusive_task` 按 task_type 解析锁、stale 恢复参数化、`TaskFenceContext` 类型集合化、TaskExecutor 并列 margin owner lock、`RESERVED_TASK_TYPES` 加成员并封堵通用入口。
- **完成后可观察结果**: 触发一个小范围（2-3 个真实交易日）`sync_market_margin` 任务后等待终态：任务 status=completed，`market_margin_daily` 出现范围内每个交易日恰一行且六指标正确，`result` 携带 successCount/skippedCount/failedCount 与逐日 dateResults（camelCase）。同类型已有 pending/running 时再次创建返回 None（互斥）。通过通用 `POST /api/v1/admin/tasks` 创建 `sync_market_margin` 被拒绝并提示专用端点。`sync_market_metrics` 与其余约 30 类任务的行为逐项不变（16 期任务系统全量回归通过）。
- **依赖**: plan-03（handler 调 `MarginService.sync_date`）
- **关联验收标准**: [AC-3]（同步任务互斥）、[AC-8]（通用入口封堵）
- **涉及架构模块**: 异步任务与 fencing（spec REQ-4，对应 16 期 plan-04 基础设施 + plan-05 handler 的合并——17 期无 collector/自动日更，spec T4 将 handler 划入本功能）
- **前置条件**: plan-01~03 已合并；本地 PostgreSQL（advisory lock 需真 PG）；`TUSHARE_TOKEN`（执行验证需要）。
- **不在范围**: admin 专用触发端点（plan-05）；查询 API（plan-06）；collector 自动日更（spec 无此需求，两融不在 REQ 内自动更新）。

## 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| modify | `server/src/services/task_handlers.py` | TaskType 加 `SYNC_MARKET_MARGIN`（L92 旁）+ margin handler + 私有 helper |
| modify | `server/src/services/task_manager.py` | MARGIN_LOCK_KEY/MARGIN_OWNER_LOCK_KEY、锁 key 映射、create_exclusive_task 扩展、stale 恢复参数化、RESERVED_TASK_TYPES |
| modify | `server/src/services/task_fence.py` | FENCED_TASK_TYPE 单值 → FENCED_TASK_TYPES 集合 |
| modify | `server/src/services/task_executor.py` | 并列 margin owner lock 状态族 + 类型分派扩展 |
| modify | `server/src/api/admin/tasks.py` | RESERVED 拒绝消息按类型提示对应专用端点 |
| modify | `server/tests/services/test_task_manager.py` | margin 互斥/恢复用例增量 |
| modify | `server/tests/services/test_task_executor.py` | margin owner lock/派发用例增量 |
| create | `server/tests/services/test_sync_market_margin_handler.py` | handler 单测（dateResults/进度/停止分支） |

## 实现规格

### 后端部分

#### 1. TaskType 与 handler（spec REQ-4 / T4）

`task_handlers.py`：

- `TaskType` 枚举（L27 起）新增 `SYNC_MARKET_MARGIN = "sync_market_margin"`（L92 `SYNC_MARKET_METRICS` 旁）
- `@TaskRegistry.register(TaskType.SYNC_MARKET_MARGIN)` `async def sync_market_margin_task(task_id, params, manager)`，签名三参不变，逐段仿 `sync_market_metrics_task`（L1876-2073）：
  1. `ctx = TaskFenceRegistry.get(task_id)`；None → `RuntimeError`（自动路径不走 handler）
  2. 解析 `params["start_date"]/["end_date"]`（ISO）；`TradingCalendarRepository(manager.db).get_trading_days(start, end)` 取交易日升序；`skipped_count = 自然日数 − 交易日数`；`total = len(trading_days)`
  3. `update_progress(task_id, 0, total)` + INFO 起始日志（范围/交易日数/自然日数/skipped）——**无 16 期生命周期 preflight**（两融无该环节）
  4. 逐交易日串行：`MarginService(manager.db).sync_date(day, task_context=ctx)`（升序，无跨日缓存参数）：
     - `except FenceValidationError` → `_build_margin_result(..., unprocessed=trading_days[idx:])` → `_finalize_margin_stop(...)` → return（当日未提交计入 unprocessedDates）
     - `except asyncio.CancelledError` → 同上保存 partial result 后 `raise`（recovery 兜底）
     - `except Exception as e` → `failed_count += 1`；dateResults append `{"tradeDate": ..., "status": "failed", "reason": f"{type(e).__name__}: {e}"}`；WARNING 日志；继续下一日
     - 成功（else 分支）→ `success_count += 1`；dateResults append `{"tradeDate": ..., "status": "success"}`（两融无四类计数，明细只含 tradeDate/status/reason?）
     - 每日 `processed += 1` → `update_progress(task_id, processed, total)` + INFO 进度日志
  5. 全部结束：`result = _build_margin_result(success, skipped, failed, date_results, [])` → `_persist_margin_result(manager, task_id, result)`；`failed_count > 0` → 抛一次摘要（max_retries=0 由执行器落 failed，成功日不回滚）
- 私有 helper 并列新增（不动 16 期 `_build/_persist/_finalize_market_metrics_*` 签名）：
  - `_build_margin_result(...) -> {"successCount", "skippedCount", "failedCount", "dateResults", "unprocessedDates"}`（camelCase 键，`AsyncTask.to_dict()` 原样透传不经 `_dict_to_camel`，plan-08 前端直消费）
  - `_persist_margin_result(manager, task_id, result)`：`update(AsyncTask).where(task_id==...).values(result=result)` + commit（范式同 `_persist_market_metrics_result` L1779）
  - `_finalize_margin_stop(manager, task_id, token, result)`：重读停止首因（cancel/timeout 双字段按较早数据库时间、同刻 cancel 优先；双标记 critical 告警）→ 对应 `finalize_*_with_result`；未落终态则持久化 partial result 交 recovery 兜底（范式同 `_finalize_market_metrics_stop` L1824）

#### 2. task_manager.py 扩展（spec T4 / 16 期 plan-04 双锁设计）

- 常量（L38-39 旁）：`MARGIN_LOCK_KEY = 9001003`（创建互斥，事务级 xact lock）、`MARGIN_OWNER_LOCK_KEY = 9001004`（执行器单 owner，会话级 try lock）——**不与 9001001/9001002 冲突**，沿用 16 期"创建互斥锁与 owner 锁分 key"裁定
- 新增映射 `_EXCLUSIVE_TASK_LOCK_KEYS: Dict[str, int] = {"sync_market_metrics": MARKET_METRICS_LOCK_KEY, "sync_market_margin": MARGIN_LOCK_KEY}`
- `create_exclusive_task`（L508）：`pg_advisory_xact_lock` 的 key 由 `self._exclusive_lock_key(task_type)` 解析（映射查表，缺省回落 `MARKET_METRICS_LOCK_KEY` 保持既有行为不变）；其余逻辑（同类型 pending/running 互斥、`max_retries=0`、commit 释放锁）不动
- stale 恢复参数化：`recover_stale_market_metrics_tasks(current_token)`（L724）重构为通用 `recover_stale_fenced_tasks(task_type: str, current_token: str)`（候选查询、`_recover_one_stale` 复核、`_rebuild_recovery_result` 计数重建全部以 `task_type` 参数化——margin 的 dateResults 重建口径同 16 期：`unprocessedDates = 范围交易日 − 已处理日`，未处理日不计入 failedCount）；旧方法改为薄包装 `return await self.recover_stale_fenced_tasks("sync_market_metrics", current_token)`（既有调用方/测试零改动）
- `RESERVED_TASK_TYPES = {"sync_market_metrics", "sync_market_margin"}`（L28）

#### 3. task_fence.py 扩展

- `FENCED_TASK_TYPE = "sync_market_metrics"`（L36）改为 `FENCED_TASK_TYPES = {"sync_market_metrics", "sync_market_margin"}`；`lock_and_validate` 的类型校验（L144）改 `task.task_type not in FENCED_TASK_TYPES` → 拒绝
- 全文件 grep `FENCED_TASK_TYPE` 引用（含 task_executor 可能的导入）同步更新；其余校验（status/token/停止字段/guard 双检）不动

#### 4. task_executor.py 扩展（并列 margin owner lock，16 期 `_mm_*` 状态族照搬）

- `__init__`（L101-108 旁）并列新增 margin 状态族：`_margin_lock_conn/_margin_lock_engine/_margin_lock_held/_margin_owner_token/_margin_guard/_margin_task_coroutines/_margin_standby_logged`（初值与 `_mm_*` 同款）
- 方法族并列新增（逐个照搬 L468-640 `_ensure_mm_lock_connection/_close_mm_lock_connection/_maintain_mm_owner_lock/_on_mm_owner_acquired/_lose_mm_owner_lock/_consume_mm_stop_requests`，替换锁 key 为 `MARGIN_OWNER_LOCK_KEY`、recovery 调 `recover_stale_fenced_tasks("sync_market_margin", token)`、日志前缀 margin）
- 共享分支的类型判定**语义保持**扩展：
  - poll loop：`_maintain_mm_owner_lock()` 旁并列调 `_maintain_margin_owner_lock()`；停止消费两把锁各自判断
  - 拉取/派发过滤（L211/221/261/277）：`task.task_type == _MARKET_METRICS_TYPE` 的各分支改为按类型集合判断（`_FENCED_TYPES = {"sync_market_metrics", "sync_market_margin"}`，模块级常量与 task_fence 对齐），未持**对应**锁不拉取该类型 pending；`start_task` 的 `acquisition_token` 按类型取对应 owner token（margin 取 `_margin_owner_token`）
  - 协程映射：margin 任务写 `_margin_task_coroutines`（done_callback 清理同款）
  - 超时扫描（L321）：margin 超时同样走 `manager.request_timeout` 条件更新（不再直接置 failed）
- **硬约束**：`sync_market_metrics` 路径行为逐项不变——所有共享行改动必须跑 `tests/services/test_task_executor.py` + `tests/test_task_system.py` 既有用例全绿后才算完成

#### 5. admin/tasks.py RESERVED 封堵（spec REQ-4 / AC-8）

- 通用 `POST ""` 的保留类型拒绝（L140）消息按类型提示专用端点：映射 `_RESERVED_ENDPOINT_HINTS = {"sync_market_metrics": "POST /api/v1/admin/init/market-metrics", "sync_market_margin": "POST /api/v1/admin/init/margin"}`；`sync_market_margin` 请求返回 `ApiResponse(success=False, message="sync_market_margin 为保留任务类型，请使用 POST /api/v1/admin/init/margin")`（HTTP 200，与 16 期锚点一致）

**安全要求（16 期 §8.3 惯例继承）**: 全部端点维持 `require_admin`；SQL 一律参数化；handler 不透传 max_retries。

**可观测性**: owner lock 获取/丢失、recovery 统计、fencing 拒绝、standby 状态均记日志（margin 前缀），测试断言关键日志行。

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | TaskType.SYNC_MARKET_MARGIN + handler 主流程 | backend | done | 逐日串行 + dateResults camelCase |
| 2 | margin 私有 helper（build/persist/finalize_stop） | backend | done | 不动 16 期 helper 签名 |
| 3 | task_manager：锁 key 常量 + 映射 + create_exclusive_task 扩展 | backend | done | 缺省回落保旧行为 |
| 4 | task_manager：recover_stale_fenced_tasks 参数化 + 旧方法薄包装 | backend | done | 既有测试零改动 |
| 5 | task_fence：FENCED_TASK_TYPES 集合化 | backend | done | grep 全部引用同步 |
| 6 | task_executor：margin owner lock 状态族 + 派发/停止/超时扩展 | backend | done | 16 期回归全绿为完成门槛 |
| 7 | admin/tasks.py：RESERVED 消息映射 + 新成员 | backend | done | AC-8 |
| 8 | 测试：handler 单测 + manager/executor 增量 | backend | done | 含执行验证 |
| 9 | 执行验证：小范围真实任务触发→等待→查库 | backend | done | task handler 不豁免项 |

## 验收标准

### 后端验收

- [x] AC-3（互斥底座）并发两次 `create_exclusive_task(task_type='sync_market_margin', ...)` 仅一个成功（真 PG advisory lock 事务级测试；第二个返回 None）
- [x] AC-8 通用 `POST /api/v1/admin/tasks` 创建 `sync_market_margin` 被拒，消息含 `POST /api/v1/admin/init/margin` 提示；其他非保留类型创建不受影响；`sync_market_metrics` 封堵行为与消息不变
- [x] **执行验证（task handler 不豁免）**：`create_exclusive_task(task_type='sync_market_margin', params={'start_date': <近2-3个交易日>, 'end_date': <...>})` → 启动执行器等待终态 → 任务 `status='completed'` → 查 `market_margin_daily` 确认范围内每个交易日恰一行、六指标非空且 rzrqye == rzye + rqye（真实 Tushare + 本地 PG）
- [x] 执行验证（续）：任务 `result` 含 `successCount/skippedCount/failedCount/dateResults/unprocessedDates`（camelCase 键）；范围含非交易日时 `skippedCount = 自然日数 − 交易日数`
- [x] 含失败日场景（mock 或构造失败日）：任务落 failed、`failedCount ≥ 1`、成功日数据保留在库；dateResults 失败项含截断 reason
- [x] 停止分支：running 中请求 cancel → fence 拒绝 → handler 保存 partial result + unprocessedDates → 落 cancelled（单测 mock 链路）
- [x] recovery：margin 旧 token（含 NULL）running 被 `recover_stale_fenced_tasks("sync_market_margin", token)` 按停止首因回收为 cancelled / failed(task_timeout) / failed(executor_restarted)；计数只来自已提交 dateResults
- [x] executor：未持 margin owner lock 的实例不拉取 sync_market_margin pending；持有后派发写 `_margin_owner_token` 为 acquisition_token；断线重连生成新 token
- [x] **16 期回归（硬门槛）**：`pytest tests/services/test_task_manager.py tests/services/test_task_executor.py tests/services/test_sync_market_metrics_handler.py tests/test_task_system.py -q --no-cov` 全绿——sync_market_metrics 与其他任务类型行为逐项不变
- [x] E2E 不适用：后端任务功能无浏览器界面；以执行验证（上第 3-4 条）为质量门，前端可见性由 plan-08 覆盖

## 验证命令

```bash
cd server && source .venv/bin/activate

# 1. 本功能单测
pytest tests/services/test_sync_market_margin_handler.py -v --no-cov
pytest tests/services/test_task_manager.py tests/services/test_task_executor.py -v --no-cov

# 2. 16 期任务系统回归（共享文件扩展的硬门槛）
pytest tests/services/test_sync_market_metrics_handler.py tests/test_task_system.py tests/test_admin_api.py -q --no-cov

# 3. 执行验证（需 TUSHARE_TOKEN + 本地 PG；先 alembic upgrade head）
python -c "
import asyncio
from src.db.database import AsyncSessionLocal
from src.services.task_manager import TaskManager
async def main():
    async with AsyncSessionLocal() as s:
        m = TaskManager(s)
        t = await m.create_exclusive_task(task_type='sync_market_margin',
            params={'start_date':'2026-08-11','end_date':'2026-08-13'}, created_by=None)
        print('created:', t.task_id if t else 'BLOCKED')
asyncio.run(main())
"
# 启动执行器（现有服务入口）等待终态后查库：
python -c "
import asyncio
from sqlalchemy import select
from src.db.database import AsyncSessionLocal
from src.models.market_margin_daily import MarketMarginDaily
async def main():
    async with AsyncSessionLocal() as s:
        rows = (await s.execute(select(MarketMarginDaily).order_by(MarketMarginDaily.trade_date))).scalars().all()
        for r in rows:
            print(r.trade_date, 'rzye=', r.rzye, 'rqye=', r.rqye, 'rzrqye=', r.rzrqye,
                  '重算一致=', r.rzrqye == (r.rzye or 0) + (r.rqye or 0))
asyncio.run(main())
"

# 4. 全量回归
pytest tests/ -q --no-cov
```

## 交接上下文

- **spec 章节**: REQ-4（异步任务）、边界（必须：专属锁+fencing+互斥+恢复照搬 16 期范式；禁止：改动 market-metrics 现有代码逻辑）、任务清单 T4
- **相关代码**: `server/src/services/task_handlers.py`（TaskType L27/L92、handler 范式 L1876-2073、helper L1758-1873）、`server/src/services/task_manager.py`（RESERVED L28、锁 key L38-39、`create_exclusive_task` L508、`recover_stale_market_metrics_tasks` L724、`_recover_one_stale` L781、finalize 族 L626-678）、`server/src/services/task_fence.py`（FENCED_TASK_TYPE L36、类型校验 L144）、`server/src/services/task_executor.py`（`_mm_*` 状态族 L101-108、owner lock 方法族 L468-640、类型分派 L211/221/261/277/321）、`server/src/api/admin/tasks.py`（RESERVED 拒绝 L140）
- **契约 / 数据对象**: `MarginTaskResult`（result JSON：`{successCount, skippedCount, failedCount, dateResults: [{tradeDate, status, reason?}], unprocessedDates}`，camelCase 直消费）；params `{start_date, end_date}`（ISO 字符串，user_input）
- **下游消费方**: plan-05（`create_exclusive_task(task_type='sync_market_margin')`）、plan-08（读任务 result 与日志）
- **实现级补充项**: executor 类型分派集合化与 `recover_stale_fenced_tasks` 参数化是"扩展不改逻辑"的落地方式，服务于 AC-3/AC-8，非新造 AC

## 风险与边界

- **执行顺序**: 按 Task 列表顺序执行；Task 3-5 是 Task 6 的前置；每个共享文件改完立即跑 16 期回归
- **验证失败排查方向**: 任务一直 pending → 检查执行器是否持 margin owner lock（日志 margin owner lock acquired）；互斥测试不过 → 查锁 key 是否误与 9001001/9001002 撞号
- **允许修改的额外文件**: 仅 `server/tests/` 下 16 期任务测试文件的**增量**（新用例追加，不改既有用例断言）
- **暂停条件**: 若 executor 共享分支扩展导致 16 期 `test_task_executor.py` 既有用例失败且无法在不改变 sync_market_metrics 语义的前提下修复，暂停并请求确认分派结构方案
- **风险备注**: 本功能是 17 期最大风险面（并发状态机）；测试必须覆盖验收标准列出的全部分支，不允许"先跑通再补测"

### 后端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| 范围全为非交易日 | total=0：直接持久化 result（success=0）并正常完成，不进循环 | done |
| 单日失败 | 回滚该日、dateResults 记 failed+reason、继续下一日 | done |
| 任务运行中被取消 | 保存 partial result + unprocessedDates 后 finalize cancelled | done |
| margin 与 market_metrics 任务同时运行 | 两把 owner lock 独立 key，互不阻塞；并发 gate 共用 max_concurrent_tasks | done |
| 未持 margin owner lock 的实例 | 不拉取 sync_market_margin pending，其他类型正常 | done |
| recovery 遇 margin NULL token 遗留 running | IS DISTINCT FROM 命中，按无停止字段分支落 failed(executor_restarted) | done |
