---
feat_id: "plan-01"
title: "基金数据模型与同步基础设施"
dimension: backend
phase: 1
status: review
depends_on: []
---

# plan-01: 基金数据模型与同步基础设施

## 功能概要

- **目标**: 在后端建立 `funds` / `fund_portfolio` 两张表 + 数据模型、扩展 Tushare 客户端方法、注册两个异步任务类型（`SYNC_FUND_BASIC`、`SYNC_FUND_PORTFOLIO`），使管理员能通过现有 `AsyncTask` 框架触发基金信息与持仓明细的同步。
- **完成后可观察结果**: 运行 `alembic upgrade head` 后数据库新增 `funds` 与 `fund_portfolio` 两张表（含三处索引）；管理员在管理后台点击同步后，`TaskExecutor` 能在轮询中获取任务并调用注册的 handler，handler 调用 `TushareDataSource` 拉取数据并写入对应表。同步成功时 `AsyncTask.status='completed'` 且 `result` 字段含 `{added, updated, failed}` 统计；同步失败时 `status='failed'` 且 `error_message` 含错误原因，旧数据不受影响。
- **依赖**: 无（首期基础）
- **关联验收标准**: [AC-06, AC-07]
- **涉及架构模块**: FundDataService、FundTaskHandler、Fund 模型、FundPortfolio 模型（架构 §4.2）
- **前置条件**:
  - PostgreSQL 已运行且 `DATABASE_URL_ASYNC` 已配置
  - `TushareDataSource` 与 `BaseRepository` 已在仓库中存在
  - `TushareDataSource._enforce_rate_limit()` / `_execute_with_retry()` 经验证可被新方法直接复用
- **不在范围**:
  - 业务 API 端点（由 plan-02 负责）
  - 管理员 UI 面板（由 plan-03 负责）
  - 前端页面（由 plan-04、plan-05 负责）

## 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| create | `server/src/models/fund.py` | Fund 模型（`__tablename__ = "funds"`），字段见架构 §7.2 |
| create | `server/src/models/fund_portfolio.py` | FundPortfolio 模型（`__tablename__ = "fund_portfolio"`），字段见架构 §7.2 |
| modify | `server/src/models/__init__.py` | 导出新模型以便 Alembic autogenerate 与其它模块引用 |
| modify | `server/src/services/task_handlers.py` | 在 `TaskType` 枚举新增 `SYNC_FUND_BASIC` / `SYNC_FUND_PORTFOLIO`，注册两个 handler 函数 |
| modify | `server/src/services/data_acquisition/tushare_client.py` | `TushareDataSource` 新增 `get_fund_list(market: str)` 与 `get_fund_portfolio(period: str)` 方法 |
| create | `server/src/services/data_acquisition/models.py`（已存在则 modify） | 新增 `FundInfo` Pydantic 模型（fund_basic 响应字段映射） |
| create | `server/src/services/data_init_fund.py` | `FundDataInitService`（含 `sync_fund_basic()` 与 `sync_fund_portfolio(period)`），内部组合 Tushare 拉取 + 入库 + 统计 |
| create | `server/alembic/versions/xxx_add_fund_tables.py` | 迁移脚本，创建 funds / fund_portfolio 表与索引 |

### 前端维度

无。

## 实现规格

### 后端部分

#### 1. 模型定义（`server/src/models/fund.py`）

- 继承 `server/src/models/base.py` 的 `Base`
- 字段定义严格对齐架构 §7.2 `Fund` interface（13 个字段，含 id 自增主键）：`id`（自增主键）、`ts_code`（唯一索引）、`name`、`management`、`custodian`、`fund_type`、`invest_type`、`benchmark`、`market`、`found_date`、`list_date`、`delist_date`、`status`
- `ts_code` 上加 `unique=True` 约束；并按需加 `name` 普通索引（用于 LIKE 搜索）

#### 2. 模型定义（`server/src/models/fund_portfolio.py`）

- 字段定义严格对齐架构 §7.2 `FundPortfolio` interface：`id`、`fund_ts_code`、`report_period`、`ann_date`、`stock_symbol`、`market_value`、`amount`、`stk_mkv_ratio`、`stk_float_ratio`
- 联合索引 `(fund_ts_code, report_period)`（架构 §5 ADR-2 要求）
- 联合索引 `(stock_symbol, report_period)`（架构 §5 ADR-2 要求）
- 注意：`stock_name` 不入库（架构 §7.2 注释明确，运行时 LEFT JOIN stocks 表获取）

#### 3. Alembic 迁移

- 新建 `server/alembic/versions/xxx_add_fund_tables.py`（xxx 替换为实际生成的时间戳 ID）
- `upgrade()`：`op.create_table` 两张表 + `op.create_index` 三处索引（`funds.ts_code` 唯一、`fund_portfolio(fund_ts_code, report_period)`、`fund_portfolio(stock_symbol, report_period)`）
- `downgrade()`：按相反顺序删除索引 → 表
- 参照 `server/alembic/versions/2025_01_20_0001.py` 的 `revision` / `down_revision` / `op.create_table` 写法保持一致

#### 4. Tushare 客户端扩展（`server/src/services/data_acquisition/tushare_client.py`）

- 新增 `async def get_fund_list(self, market: str) -> list[dict]`
  - 调用 `self._execute_with_retry('fund_basic', market=market)`
  - 复用 `self._enforce_rate_limit()` 做速率控制
  - Tushare fund_basic 单次最大 15000 条，需要 offset 循环直到返回为空（架构 §6.4 step 5）
- 新增 `async def get_fund_portfolio(self, period: str) -> list[dict]`
  - 调用 `self._execute_with_retry('fund_portfolio', period=period)`
  - 同样 offset 循环，每次取 5000 条（架构 §6.4 step 6）

#### 5. Pydantic 模型（`server/src/services/data_acquisition/models.py`）

- 新增 `FundInfo` 模型，字段名严格按 Tushare fund_basic 返回的 camelCase 原始键（如 `ts_code`、`name`、`management`、`fund_type`、`market` 等）
- 不在模型层做语义转换（保留 Tushare 原始字段），转换在 `FundDataInitService` 中完成

#### 6. 任务处理器（`server/src/services/task_handlers.py`）

- 在 `TaskType` 枚举追加：
  - `SYNC_FUND_BASIC = "sync_fund_basic"`
  - `SYNC_FUND_PORTFOLIO = "sync_fund_portfolio"`
- 新增两个 handler：
  - `@TaskRegistry.register(TaskType.SYNC_FUND_BASIC)` → `async def sync_fund_basic_task(task_id, params, db)`：内部实例化 `FundDataInitService` 并调用 `sync_fund_basic()`，使用 `_make_progress_callback` 上报进度
  - `@TaskRegistry.register(TaskType.SYNC_FUND_PORTFOLIO)` → `async def sync_fund_portfolio_task(task_id, params, db)`：从 `params['period']` 读取报告期，调用 `sync_fund_portfolio(period)`
- 两个 handler 在异常时调用 `manager.update_task_status(task_id, 'failed', error_message=...)`，并保留旧数据（架构 §6.4 step 8）

#### 7. 同步服务（`server/src/services/data_init_fund.py`）

- `class FundDataInitService`：
  - `async def sync_fund_basic(self) -> dict`：先调 `tushare.get_fund_list('E')` 再调 `tushare.get_fund_list('O')`，合并后逐条 `upsert` 到 `funds` 表（ON CONFLICT ts_code DO UPDATE），返回 `{added, updated, failed}`
  - `async def sync_fund_portfolio(self, period: str) -> dict`：调 `tushare.get_fund_portfolio(period)` 拉取全量；按架构 §6.4 step 6 描述采用"先 INSERT 新数据 → 再 DELETE 旧数据"策略（实现方式：插入临时 batch → `DELETE WHERE report_period = period AND id NOT IN (新数据 id)` 或使用临时表）
- 失败重试：依赖 `TushareDataSource._execute_with_retry()`，单条入库失败计入 failed 计数不中断整体流程（架构 §8.2）

#### 8. 安全与可观测性（NFR 传播）

- **安全要求（架构 §8.3）**：
  - 所有 DB 操作走 SQLAlchemy 参数化（`session.merge()` / `session.execute(update(...))`），禁止字符串拼接
  - Tushare Token 仅服务端持有，handler 不接受外部传入
- **可观测性（架构 §8.5）**：
  - 通过 `_make_progress_callback` 输出 `[current/total] message` 到 `AsyncTaskLog`
  - 任务完成后将 `{added, updated, failed}` 写入 `AsyncTask.result`
  - 失败时将 `error_message` 写入 `AsyncTask.error_message`

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | 创建 `Fund` 模型 | backend | done | `server/src/models/fund.py`，含 13 个字段（含 id）+ ts_code 唯一索引 + name 普通索引 |
| 2 | 创建 `FundPortfolio` 模型 | backend | done | `server/src/models/fund_portfolio.py`，含 9 字段 + 2 联合索引 |
| 3 | 导出新模型 | backend | done | 修改 `server/src/models/__init__.py` |
| 4 | 扩展 Tushare 客户端 | backend | done | `tushare_client.py` 新增 `get_fund_list(market)` 与 `get_fund_portfolio(period)` |
| 5 | 新增 `FundInfo` Pydantic 模型 | backend | done | `data_acquisition/models.py` |
| 6 | 创建 `FundDataInitService` | backend | done | `server/src/services/data_init_fund.py`，实现两个 sync 方法 + 统计返回 |
| 7 | 任务枚举与 handler 注册 | backend | done | `task_handlers.py` 追加 `SYNC_FUND_BASIC` / `SYNC_FUND_PORTFOLIO` 枚举 + handler |
| 8 | 生成并应用 Alembic 迁移 | backend | done | `alembic revision --autogenerate -m "add fund tables"` 后人工核对索引 + `alembic upgrade head` |

## 验收标准

### 后端验收

- [ ] AC-06（执行验证）触发 `SYNC_FUND_BASIC` 任务：调用 TaskExecutor / admin API 启动任务 → 等待 `status='completed'` → 查询 `funds` 表确认新增/更新数量与 `AsyncTask.result.added/updated` 一致
- [ ] AC-06（执行验证）触发 `SYNC_FUND_PORTFOLIO` 任务（指定 report_period）：同上，确认 `fund_portfolio` 表中有目标报告期数据
- [ ] AC-07（执行验证）同步失败时：`status='failed'` 且 `error_message` 有内容；查询 `fund_portfolio` / `funds` 表数据未被清空（旧数据保留）
- [ ] `alembic upgrade head` 在干净库上成功；`alembic downgrade -1` 成功
- [ ] 数据库索引 `funds.ts_code`（唯一）、`fund_portfolio(fund_ts_code, report_period)`、`fund_portfolio(stock_symbol, report_period)` 均存在（`\\d funds`、`\\d fund_portfolio` 验证）
- [ ] `pytest tests/` 通过（已有测试不被破坏）
- [ ] NFR-性能（架构 §8.1）：基本信息同步 < 10 分钟（约 2 万条），持仓明细同步 < 30 分钟（约 30-50 万条/期）
- [ ] **E2E 不适用说明**：本功能为内部 task handler，不存在 UI 触达点；按 skill 规则，task handler 必须包含"执行验证"验收项（已覆盖）

### 性能验收（架构 §8.1）

- [ ] `SYNC_FUND_BASIC` 任务在 < 10 分钟内完成
- [ ] `SYNC_FUND_PORTFOLIO` 任务（单期）在 < 30 分钟内完成

## 验证命令

```bash
# 迁移
cd server
alembic upgrade head

# 触发同步（需在管理 API 就绪后由 plan-03 提供；plan-01 阶段可使用 task_manager 直接注册任务）
python -c "
import asyncio
from src.services.task_manager import TaskManager
from src.services.task_handlers import TaskType
from src.db.database import AsyncSessionLocal

async def run():
    async with AsyncSessionLocal() as session:
        manager = TaskManager(session)
        # 基本信息
        tid = await manager.create_task(TaskType.SYNC_FUND_BASIC, params={})
        print('SYNC_FUND_BASIC task_id:', tid)
        # 持仓（指定报告期）
        tid2 = await manager.create_task(TaskType.SYNC_FUND_PORTFOLIO, params={'period': '20241231'})
        print('SYNC_FUND_PORTFOLIO task_id:', tid2)

asyncio.run(run())
"

# 任务执行验证（TaskExecutor 轮询）
uvicorn server.main:app --port 8000

# 验证表数据
psql $DATABASE_URL -c "SELECT COUNT(*) FROM funds;"
psql $DATABASE_URL -c "SELECT COUNT(*) FROM fund_portfolio WHERE report_period = '2024-12-31';"

# 验证索引
psql $DATABASE_URL -c "\\d funds"
psql $DATABASE_URL -c "\\d fund_portfolio"
```

## 交接上下文

- **架构章节**: §4.2 模块职责、§5 ADR-1~4、§6.4 管理员同步流程、§7.1 核心对象、§7.2 Schema、§7.6 命名映射
- **相关代码**:
  - `server/src/services/task_handlers.py`（追加枚举与 handler）
  - `server/src/services/task_executor.py`（轮询逻辑，无需修改）
  - `server/src/services/task_manager.py`（`create_task` / `update_progress` / `log_message` / `update_task_status`）
  - `server/src/services/data_acquisition/tushare_client.py`（基类 `_execute_with_retry` / `_enforce_rate_limit`）
  - `server/src/repositories/base.py`（可被新 `FundRepository` 继承，本 plan 不创建 Repository）
- **契约 / 数据对象**:
  - `Fund` ORM 模型 → 对应架构 §7.2 `interface Fund`
  - `FundPortfolio` ORM 模型 → 对应架构 §7.2 `interface FundPortfolio`
  - `SyncResult { added, updated, failed }` → 写入 `AsyncTask.result`
- **下游消费方**:
  - plan-02（业务 API）依赖 `Fund` / `FundPortfolio` 模型与 `FundDataInitService` 暴露的同步入口
  - plan-03（管理端面板）依赖 `TaskType.SYNC_FUND_BASIC` / `SYNC_FUND_PORTFOLIO` 与任务统计字段

## 风险与边界

- **执行顺序**: 按 Task 列表 1→8 顺序执行；迁移（Task 8）必须在模型定义（Task 1-3）完成后才能生成
- **验证失败排查方向**:
  - 任务 `failed`：检查 `AsyncTask.error_message` → 若是 Tushare 401/权限错误，确认 `TUSHARE_TOKEN` 有效且积分 ≥ 2000/5000
  - 表数据未写入：检查 `funds` / `fund_portfolio` 表是否被成功创建（Alembic 状态）→ 检查 `TushareDataSource` 是否成功返回 → 检查 `FundDataInitService` 中 upsert / insert 是否报错
  - 索引缺失：检查迁移脚本中 `op.create_index` 是否被显式列出（autogenerate 不会为联合索引自动生成）
- **允许修改的额外文件**: 无
- **暂停条件**:
  - Tushare 实际返回字段与架构 §7.2 不一致时（需人工核对字段映射）
  - 同步任务超时（4 小时）仍未完成，需检查 Tushare 网络与积分状态
- **风险备注**:
  - 持仓同步采用"先 INSERT 新数据 → 再 DELETE 旧数据"策略时，若同步中途失败，可能出现"新数据未写完但旧数据已删"——需确保 DELETE 在 INSERT 全部成功后执行（架构 §6.4 实现原则已约束）
  - Tushare fund_basic 单次最大 15000 条，offset 循环必须正确终止（空列表时退出）
- **E2E 不适用说明**: 本功能为内部基础设施，无 UI 入口；按 skill 规则已包含执行验证验收项

### 后端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| Tushare 返回 401（积分不足） | handler 捕获异常，task 置 `failed`，`error_message` 写"Tushare 权限不足" | todo |
| Tushare 返回空列表（无新数据） | upsert / insert 正常完成，`added=0, updated=0, failed=0`，task 仍 `completed` | todo |
| 单条数据入库异常（主键冲突或字段超长） | 计入 `failed` 计数，不中断整体同步 | todo |
| 同步任务超时（4 小时） | 沿用 `AsyncTask.timeout_seconds`；超时后 task 置 `failed` | todo |
| 持仓同步先 INSERT 后 DELETE 中途中断 | 中断时 `fund_portfolio` 表中可能同时存在新旧两期；下次同报告期同步会覆盖修复；任务标 `failed` 等待重试 | todo |
