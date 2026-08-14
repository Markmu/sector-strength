---
feat_id: "plan-04"
title: "异步任务 fencing 基础设施"
dimension: backend
phase: 2
status: done
depends_on: ["plan-01"]
---

# plan-04: 异步任务 fencing 基础设施

## 功能概要

- **目标**: 为 `sync_market_metrics` 建立单 owner 任务执行基础设施：AsyncTask 表扩展（`result/cancel_requested_at/timeout_requested_at/executor_acquisition_token`）、`TaskFenceContext`/`OwnerGenerationGuard`（新建 `task_fence.py`）、TaskManager 互斥创建与原子停止终态方法、TaskExecutor 专属 session advisory lock + token fencing + orphan recovery、通用任务端点的 reserved 封堵与 result 字段扩展。
- **完成后可观察结果**: 管理员无法再通过通用 `POST /api/v1/admin/tasks` 创建 `sync_market_metrics`（明确提示用专用端点）；任务详情/列表响应携带 nullable `result`；同一时刻同类型最多一个 pending/running（含"停止中/待 recovery"）；执行器重启后遗留 running 被新 owner 按停止首因原子回收为 `cancelled` / `failed(task_timeout)` / `failed(executor_restarted)` 三分支之一；旧 token 的事务写被 fencing 拒绝；其他约 28 类任务走原路径、新字段保持 NULL、行为不变。
- **依赖**: plan-01（迁移链顺序；本功能迁移 down_revision 指向 plan-01 迁移）
- **关联验收标准**: [AC-02]（任务状态机底座）、[AC-07]（失败恢复底座）、[AC-11]（任务互斥与权限的服务端底座）
- **涉及架构模块**: 任务入口与编排（架构 §4.2 模块 3）
- **前置条件**: plan-01 已合并；本地 PostgreSQL（advisory lock 需真 PG）。
- **不在范围**: `sync_market_metrics` handler 本体与专用创建路由（plan-05）；collector 自动日更（plan-05）。

## 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| modify | `server/src/models/async_task.py` | 4 个 nullable 新列 + to_dict 扩展 result |
| create | `server/alembic/versions/2026_08_15_0001-<rev12>_add_async_task_result.py` | 4 列迁移，down_revision=plan-01 迁移 revision |
| create | `server/src/services/task_fence.py` | TaskFenceContext / OwnerGenerationGuard / fence 注册表 |
| modify | `server/src/services/task_manager.py` | create_exclusive_task、条件停止写入、原子 finalize、recovery |
| modify | `server/src/services/task_executor.py` | 专属 lock、token/guard、recovery、停止消费、coroutine 映射 |
| modify | `server/src/api/admin/tasks.py` | RESERVED 封堵 + result 字段 + logs true total |
| create | `server/tests/services/test_task_manager.py` | 互斥/条件停止/原子终态/recovery |
| create | `server/tests/services/test_task_executor.py` | token 轮换、fencing、接管竞态 |

## 实现规格

### 后端部分

#### 1. AsyncTask 模型扩展（架构 §7.2 末段）

`async_tasks` 新列（全部 nullable，仅 sync_market_metrics 路径读写）：`result` JSON、`cancel_requested_at` DateTime(timezone=True)、`timeout_requested_at` DateTime(timezone=True)、`executor_acquisition_token` String(36)。`to_dict()` 增加 `result` 键（原样透传 dict | None）。

#### 2. task_fence.py（架构 §6.2.3/6/§7.4）

- `OwnerGenerationGuard`：`token: str`、`active: bool`（持锁且 recovery 完成才 True）、`invalidate()`（置 False 并 cancel 注册到本 guard 的全部 `asyncio.Task`）、`register_coroutine(task)` / `unregister(task_id)`
- `TaskFenceContext(task_id, acquisition_token, guard)`：
  - `async lock_and_validate(session)`：对 AsyncTask 行 `SELECT ... FOR UPDATE`，校验 `task_type=='sync_market_metrics'`、`status=='running'`、`executor_acquisition_token == context.token`、`cancel_requested_at IS NULL AND timeout_requested_at IS NULL`、`guard.active`（**事务前轻检 + 行锁后双检**，§6.2.6）；任一不符抛 `FenceValidationError` → 调用方整体 rollback
- 进程级注册表 `TaskFenceRegistry`：`set(task_id, ctx)` / `get(task_id)` / `pop(task_id)`——handler（plan-05）由此取 executor 构造好的 fence context，不改变现有 handler 三参签名

#### 3. TaskManager 扩展（架构 §6.2.2/5、§7.4）

- 常量 `MARKET_METRICS_LOCK_KEY = <int>`、`RESERVED_TASK_TYPES = {"sync_market_metrics"}`（放 task_manager.py，tasks.py 导入）
- `create_exclusive_task(task_type, params, created_by, timeout_seconds)`：单数据库事务内先 `SELECT pg_advisory_xact_lock(MARKET_METRICS_LOCK_KEY)`，再查同类型 `status IN ('pending','running')`（**running 含停止中/待 recovery**，命中则返回 None 或抛互斥错误），创建任务固定 `max_retries=0`；锁随 commit 释放，等待者随后看到已提交任务被拒
- 条件停止写入（首因胜出）：
  - `request_cancel(task_id)`：`UPDATE ... SET cancel_requested_at=now() WHERE task_id=? AND status='running' AND cancel_requested_at IS NULL AND timeout_requested_at IS NULL`；pending 任务仍走现有 `cancel_task` 立即置 cancelled
  - `request_timeout(task_id)`：对称条件更新 `timeout_requested_at`
- 原子终态（行锁 + 双检 token/guard + partial result 同事务）：
  - `finalize_cancel_with_result(task_id, token, result)` → `cancelled`
  - `finalize_timeout_with_result(task_id, token, result)` → `failed`（error_message='task_timeout'）
  - `finalize_restarted_with_result(task_id, result)` → `failed`（error_message='executor_restarted'）
- `recover_stale_market_metrics_tasks(current_token)`（§6.2.3，由持锁 executor 调用）：查 `task_type='sync_market_metrics' AND status='running' AND executor_acquisition_token IS DISTINCT FROM current_token`（含 NULL）；逐行独立事务 `SELECT ... FOR UPDATE` 后复核类型/running/旧 token；以任务参数、本地日历与**已提交 result.dateResults** 重建计数（`unprocessedDates` = 范围交易日 − 已处理日；**未处理日不计入 failedCount**）；按已持久化停止首因执行唯一终态：仅 cancel → `finalize_cancel_with_result`；仅 timeout → `finalize_timeout_with_result`；均空 → `finalize_restarted_with_result`；**双字段同非空 = 不变量破坏**：critical 告警日志，按较早数据库时间选首因（同刻 cancel 优先）。提交前复验当前 acquisition 未失效

#### 4. TaskExecutor 扩展（架构 §6.2.3/5、§3.3、§8.2）

现有结构（`_poll_and_execute` L140-188 并发 gate、进程内 `_running_tasks` set L82、`_get_executable_tasks` L190）上叠加：

- **专属 owner lock**：后台 loop 起一个独立长连接（复用 `get_task_executor_engine`），循环尝试 `pg_try_advisory_lock(MARKET_METRICS_LOCK_KEY)`；未持锁不拉取本类型 pending（其他任务不受影响）
- **每次成功 acquisition**：生成全新 UUID token（同进程断线重连也必须更换）+ 新 guard；先 `recover_stale_market_metrics_tasks(token)`，完成后 `guard.active=True`
- **锁丢失**（advisory lock 会话断开/检测失效）：立即 `旧guard.invalidate()`（cancel 旧 token 全部 coroutine），重连后走新 acquisition
- **派发**：本类型 pending→running 时（`start_task` 同事务）写 `executor_acquisition_token=token` 到任务行，构造 `TaskFenceContext` 存入 `TaskFenceRegistry`；维护 `task_id → asyncio.Task` 映射（本类型）
- **并发 gate 前消费停止**：每轮扫描当前 owner 的本类型 running，读 `cancel_requested_at/timeout_requested_at` 胜出者 → cancel 对应 coroutine（handler 感知后走 finalize_with_result）；**本类型失败不自动重试**（max_retries=0，现有重试分支自然短路）
- **超时扫描**：本类型超时改走 `request_timeout` 条件更新（不再直接置 failed）；其他类型保持 `check_task_timeout` 原语义（task_manager.py L450）
- 可观测性（§8.5）：owner lock 获取/丢失、recovery 数量、fencing 拒绝、standby 状态均记日志

#### 5. admin/tasks.py 扩展（架构 §7.3）

- 通用 `POST ""`：类型校验后、创建前，若 `request.task_type in RESERVED_TASK_TYPES` → `ApiResponse(success=False, message="sync_market_metrics 为保留任务类型，请使用 POST /api/v1/admin/init/market-metrics")`（HTTP 200，与锚点 init_index_basic.py:60-72 一致）
- `TaskResponse`/`TaskDetailResponse` 增加 `result: Optional[dict]`；list/get 从 `task.to_dict()` 透传
- `GET /{task_id}/logs`：`total` 由 `len(logs)` 改为真实 count 查询（TaskManager 补 `count_task_logs`）

**安全要求（架构 §8.3）**：全部端点维持 `require_admin`；新增字段无额外入参；SQL 一律 SQLAlchemy 参数化。

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | AsyncTask 4 列扩展 + 迁移 + to_dict result | backend | done | 仅本类型读写 |
| 2 | task_fence.py：Guard / FenceContext / Registry | backend | done | 双检 + 行锁 |
| 3 | TaskManager：create_exclusive_task（xact advisory lock） | backend | done | max_retries=0 |
| 4 | TaskManager：条件停止写入 + 三个 finalize_with_result | backend | done | 首因胜出、原子终态 |
| 5 | TaskManager：recover_stale_market_metrics_tasks 三分支 | backend | done | 双标记 critical 告警 |
| 6 | TaskExecutor：专属 lock 循环 + token/guard + recovery 接线 | backend | done | 未持锁不拉本类型 pending |
| 7 | TaskExecutor：停止消费 + coroutine 映射 + 超时条件更新 | backend | done | gate 前消费 |
| 8 | admin/tasks.py：RESERVED 封堵 + result 字段 + logs total | backend | done | 通用入口拒绝 |
| 9 | 编写 test_task_manager.py / test_task_executor.py | backend | done | 覆盖下述全部分支 |

## 验收标准

### 后端验收

- [ ] AC-11（互斥底座）并发两次 `create_exclusive_task` 仅一个成功（真 PG advisory lock 事务级测试）
- [ ] AC-02 状态机：pending→running→completed/failed/cancelled；取消 pending 立即 cancelled；running 取消只写 `cancel_requested_at`，任务仍占互斥直至 finalize
- [ ] 同一 TaskExecutor 断线重连生成**新** token（断言 token 变化）；旧 token running 被 `IS DISTINCT FROM` 命中回收
- [ ] recovery 三分支各自原子落终态并保存 partial result：cancel 标记→cancelled；timeout 标记→failed(task_timeout)；无标记→failed(executor_restarted)；三分支均释放互斥允许新任务
- [ ] 双停止字段同非空 → critical 日志 + 按较早时间（同刻 cancel 优先）落对应终态
- [ ] recovery 计数只来自已提交 `dateResults`；`unprocessedDates` 准确且未处理日不计入 failedCount
- [ ] lock loss 后旧 token 协程不能再开新 fence 事务（FenceValidationError）；接管竞态下行锁二选一（旧先提交被纳入 / recovery 先提交旧回滚）
- [ ] 通用 POST 创建 sync_market_metrics 被拒并提示专用端点；其他类型创建不受影响
- [ ] 非 sync_market_metrics 任务：新列保持 NULL、取消/超时/重试语义与扩展前一致（回归 `tests/test_task_system.py`）
- [ ] list/get 响应携带 nullable result；logs total 为真实 count
- [ ] E2E 不适用：纯任务基础设施，无直接用户入口；其执行验证（触发→等待→查库）由 plan-05 handler 落地后覆盖，本功能以任务系统测试为质量门

### 可观测性注入（架构 §8.5）

- [ ] owner lock 获取/丢失、orphan recovery 数量、fencing 拒绝、standby 状态均有日志输出（测试断言关键日志行）

## 验证命令

```bash
cd server && source .venv/bin/activate

# 1. 迁移
alembic upgrade head

# 2. 任务系统单测
pytest tests/services/test_task_manager.py tests/services/test_task_executor.py -v --no-cov

# 3. 全量回归（其他任务类型不受影响是硬门槛）
pytest tests/test_task_system.py tests/test_admin_api.py -q --no-cov
pytest tests/ -q --no-cov
```

## 交接上下文

- **架构章节**: §3.3、§4.2 模块 3、§6.2.2-6.2.6、§7.2 末段、§7.4、§8.2、§8.5、§8.6（取消/超时/重启三行）
- **相关代码**: `server/src/services/task_executor.py`（`_poll_and_execute` L140、`_running_tasks` L82、`_get_executable_tasks` L190、超时 L324-350）、`server/src/services/task_manager.py`（`create_task` L23、`cancel_task` L124、`check_task_timeout` L450）、`server/src/api/admin/tasks.py`（通用 POST L118、logs L346）
- **契约 / 数据对象**: `MarketMetricsTaskResult`（架构 §7.2，plan-05 写入、本功能透传为不透明 JSON）；`TaskFenceRegistry`（plan-05 handler 消费）
- **下游消费方**: plan-05（handler + 专用路由 + collector）；plan-08（前端读 result 字段）
- **实现级补充项**: `TaskFenceRegistry` 为 handler 不改签名的落地方式，服务于 AC-02/07

## 风险与边界

- **执行顺序**: 按 Task 列表顺序执行；Task 2 是 3-7 的前置
- **验证失败排查方向**: advisory lock 测试需两个独立 session/engine；死锁排查先看 Task 行锁顺序（recovery 与旧事务共用行锁）
- **允许修改的额外文件**: `server/src/services/task_handlers.py` 仅当 import 触发需要（本功能不注册 handler）
- **暂停条件**: 若现有 TaskExecutor 结构与架构假设冲突（如无独立 task engine），暂停并请求确认连接管理方案
- **风险备注**: 这是全项目最复杂的状态机——测试必须覆盖 §9 Phase B.5 列出的全部分支，不允许"先跑通再补测"

### 后端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| 停止请求与锁丢失竞态 | 行锁串行化，首因按持久化字段胜出 | done |
| 旧事务在 recovery 后尝试提交 | token 谓词失败回滚（禁止 recovery 后旧提交） | done |
| 未持专属 lock 的实例 | 不拉取本类型 pending，其他类型正常 | done |
| token 为 NULL 的遗留 running | recovery 命中（IS DISTINCT FROM 含 NULL） | done |
| 双停止字段同非空 | critical 告警 + 较早时间首因（同刻 cancel 优先） | done |
| finalize 时 guard 已失效 | FenceValidationError，留给新 owner recovery | done |
