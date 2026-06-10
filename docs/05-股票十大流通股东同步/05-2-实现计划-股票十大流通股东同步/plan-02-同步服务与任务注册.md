---
feat_id: "plan-02"
title: "同步服务与任务注册"
dimension: backend
phase: 2
status: done
depends_on: ["plan-01"]
---

# plan-02: 同步服务与任务注册

## 功能概要

- **目标**: 创建十大流通股东同步服务（逐股票遍历 + 先删后写 + 进度上报），并在现有任务体系中注册新的任务类型和处理器。
- **完成后可观察结果**: 通过 Admin Tasks API 创建 `sync_top10_holders` 类型任务后，TaskExecutor 能正确拾取并执行。同步过程中 AsyncTask 的 progress/total 字段实时更新。同步完成后 `top10_float_holders` 表中包含指定报告期全市场股票的十大流通股东数据。单只股票失败不中断整体同步，失败股票记录在任务日志中。同一报告期重复同步不产生重复数据。
- **依赖**: plan-01（Top10FloatHolder Model + `get_top10_float_holders()` 方法）
- **关联验收标准**: [AC-02, AC-04, AC-06, AC-07]
- **涉及架构模块**: Top10HolderDataInitService, TaskType.SYNC_TOP10_HOLDERS, sync_top10_holders_task handler
- **前置条件**: plan-01 已完成（数据表存在、Tushare 方法可用），TaskExecutor 正常运行
- **不在范围**: Admin API 端点（plan-03）、前端 UI（plan-03）、定时调度

## 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| create | `server/src/services/data_init_top10_holder.py` | 十大流通股东同步服务 |
| modify | `server/src/services/task_handlers.py` | 新增 TaskType 枚举值 + 注册任务处理器 |

## 实现规格

### 后端部分

#### 1. 创建 Top10HolderDataInitService

文件：`server/src/services/data_init_top10_holder.py`

参考 `server/src/services/data_init_fund.py` 中的 `FundDataInitService`，创建 `Top10HolderDataInitService`。

**构造函数**：
```python
class Top10HolderDataInitService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.tushare = DataSourceFactory.create()
        self._progress_callback = None
        self._cancel_check = None
```

**核心方法 `sync_top10_holders(period: str) -> dict`**：

实现逻辑（参考 `FundDataInitService.sync_fund_portfolio`）：

1. **查询在市股票列表**：
   - `SELECT symbol, ts_code FROM stocks WHERE list_status IN ('L', 'M')`
   - 对 ts_code 为空的股票，通过 `TushareDataSource._symbol_to_ts_code(symbol)` 转换
   - 无法转换的跳过并记录

2. **初始化计数器**：`added=0, skipped=0, failed=0, failed_stocks=[]`

3. **遍历股票列表**，每 50 只检查一次 `_cancel_check()`：
   - 调用 `tushare.get_top10_float_holders(ts_code, period)`
   - 空数据：`skipped += 1`，continue（ADR-5）
   - DELETE：`DELETE FROM top10_float_holders WHERE symbol=:symbol AND report_period=:period_date`（ADR-1 先删后写）
   - 解析返回数据，逐条创建 `Top10FloatHolder` 实例
   - `session.add_all(instances)` + `session.flush()` + `session.commit()`（ADR-2 逐股票 commit）
   - `added += 实际写入条数`
   - 异常捕获：`failed += 1`，`failed_stocks.append({"symbol": symbol, "reason": str(e)})`，`session.rollback()`，continue

4. **每处理 100 只股票或到达末尾**，调用 `_progress_callback(processed, total)`

5. **返回结果**：`{"added": added, "skipped": skipped, "failed": failed, "failed_stocks": failed_stocks}`

**工具方法**（参考 FundDataInitService）：
- `_parse_date(value)` — `YYYYMMDD` 字符串 → `date` 对象
- `_parse_float(value)` — 安全 float 转换（None/NaN → None）
- `_parse_period_to_date(period: str) -> date` — `"20241231"` → `date(2024, 12, 31)`

**安全要求（架构 §8.3）**: period 参数由任务处理器传入（system_generated），无需额外校验。

**可观测性（架构 §8.5）**: 使用 `TaskManager.log_message()` 记录关键节点（开始同步、每 500 只股票进度、完成统计、失败详情）。Service 层通过 `logging.getLogger(__name__)` 记录 warning/error 级别日志。输出结构化日志 `{ action, symbol, period, count, error }`。

#### 2. 注册任务类型和处理器

文件：`server/src/services/task_handlers.py`

**2a. 在 `TaskType` 枚举中新增**：
```python
SYNC_TOP10_HOLDERS = "sync_top10_holders"
```
（参考现有的 `SYNC_FUND_BASIC` 和 `SYNC_FUND_PORTFOLIO`）

**2b. 新增任务处理器函数**：
```python
@TaskRegistry.register(TaskType.SYNC_TOP10_HOLDERS)
async def sync_top10_holders_task(task_id: str, params: dict, manager: TaskManager):
    """十大流通股东同步任务处理器"""
```

实现逻辑（参考 `sync_fund_portfolio_task`）：
1. 从 params 获取 `period`，校验非空
2. 创建 `AsyncSessionLocal()` session
3. 创建 `Top10HolderDataInitService(session)`
4. 设置进度回调：`callback = await _make_progress_callback(manager, task_id)` + `service.set_progress_callback(callback)`（await 异步工厂函数）
5. 设置取消检查：`async def _check_cancelled(): task = await manager.get_task(task_id); return task is not None and task.status == "cancelled"` + `service.set_cancel_check(_check_cancelled)`（async 闭包查询 DB 状态）
6. 执行：`result = await service.sync_top10_holders(period)`
7. 记录结果到任务日志：`manager.log_message(task_id, "info", f"同步完成: 新增 {result['added']} 条, 跳过 {result['skipped']} 只, 失败 {result['failed']} 只")`
8. 若有失败股票，记录详情：`manager.log_message(task_id, "warning", f"失败股票: {result['failed_stocks'][:20]}")`
9. 更新 `__all__` 列表

### 性能验收（架构 §8.1 目标）

- 全量同步耗时目标 ≤ 35 分钟（~5000 只股票 × 0.3s 间隔 ≈ 25 分钟，含重试余量）

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | 创建 Top10HolderDataInitService 文件，实现 `sync_top10_holders()` 核心方法 | backend | done | 参考 FundDataInitService.sync_fund_portfolio |
| 2 | 在 TaskType 枚举中新增 `SYNC_TOP10_HOLDERS` | backend | done | 在 task_handlers.py 的 TaskType 类中添加 |
| 3 | 创建 `sync_top10_holders_task` 处理器并注册 | backend | done | `@TaskRegistry.register` + 进度回调 + 取消检查 |

## 验收标准

### 执行验证（AC-02, AC-04, AC-06, AC-07）

- [ ] AC-02 执行验证：通过 Admin Tasks API 创建 `sync_top10_holders` 任务（`POST /admin/tasks`，body `{"task_type": "sync_top10_holders", "params": {"period": "20241231"}, "timeout_seconds": 3600}`），任务状态最终变为 `completed`，`top10_float_holders` 表有新增记录且字段值正确（symbol、holder_name、hold_amount 等非空）
- [ ] AC-04 部分失败容错：同步过程中单只股票异常不中断整体任务，任务最终 status=completed，结果包含 failed 计数
- [ ] AC-06 幂等性：同一报告期触发两次同步，`SELECT COUNT(*) FROM top10_float_holders WHERE report_period='2024-12-31'` 两次结果一致
- [ ] AC-07 任务级失败：Tushare Token 无效时，任务 status=failed，error_message 包含具体原因
- [ ] 进度字段实时更新：同步过程中 `GET /admin/tasks/{task_id}` 返回的 `progress` 和 `total` 字段持续递增

### 后端验收

- [ ] TaskType 枚举包含 `SYNC_TOP10_HOLDERS = "sync_top10_holders"`
- [ ] `TaskRegistry.list_registered_tasks()` 返回列表中包含 `"sync_top10_holders"`
- [ ] 同步空报告期（如未来季度）时，任务正常完成，统计中 skipped 数量接近总股票数
- [ ] 取消机制生效：同步过程中调用 `POST /admin/tasks/{task_id}/cancel`，任务停止

### 性能验收（架构 §8.1 目标）

- [ ] 全量同步（~5000 只股票）耗时 ≤ 35 分钟（日志中记录的 started_at → completed_at 时间差）

## 验证命令

```bash
# 验证任务注册
cd server && python -c "
from server.src.services.task_handlers import TaskRegistry, TaskType
print('TaskType.SYNC_TOP10_HOLDERS:', TaskType.SYNC_TOP10_HOLDERS.value)
print('Registered:', 'sync_top10_holders' in TaskRegistry.list_registered_tasks())
"

# 执行验证：创建并运行同步任务
# 前提：后端服务运行中（uvicorn server.main:app --port 8000）
# 1. 创建任务
curl -X POST http://localhost:8000/api/admin/tasks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {admin_token}" \
  -d '{"task_type": "sync_top10_holders", "params": {"period": "20241231"}, "timeout_seconds": 3600}'

# 2. 记录返回的 task_id，轮询任务状态
curl http://localhost:8000/api/admin/tasks/{task_id} \
  -H "Authorization: Bearer {admin_token}"

# 3. 任务完成后，查询数据库验证数据
cd server && python -c "
import asyncio
from sqlalchemy import text, func
from server.src.db.database import AsyncSessionLocal

async def check():
    async with AsyncSessionLocal() as session:
        # 总记录数
        result = await session.execute(text(\"SELECT COUNT(*) FROM top10_float_holders WHERE report_period='2024-12-31'\"))
        count = result.scalar()
        print(f'Total records: {count}')
        assert count > 0, 'No data found'
        # 样本数据
        result = await session.execute(text(\"SELECT symbol, holder_name, hold_amount FROM top10_float_holders WHERE report_period='2024-12-31' LIMIT 5\"))
        for row in result.fetchall():
            print(f'  {row[0]}: {row[1]} ({row[2]})')

asyncio.run(check())
"
```

## 交接上下文

- **架构章节**: §4.2 模块职责、§6.2 执行同步、§7.1 核心对象、§9 Phase B、ADR-1/ADR-2/ADR-5
- **相关代码**:
  - `server/src/services/data_init_fund.py` — `FundDataInitService.sync_fund_portfolio()` 逐基金同步模式参考
  - `server/src/services/task_handlers.py` — `sync_fund_portfolio_task` 处理器注册模式参考（约第 1091 行）
  - `server/src/services/task_handlers.py` — `_make_progress_callback()` 进度回调辅助函数参考（约第 63 行）
  - `server/src/services/task_manager.py` — `TaskManager.update_progress()`、`TaskManager.log_message()` 方法
- **契约 / 数据对象**:
  - 输入：`period: str`（YYYYMMDD 格式，如 "20241231"）
  - 输出：`{"added": int, "skipped": int, "failed": int, "failed_stocks": [{"symbol": str, "reason": str}]}`
- **下游消费方**: plan-03（Admin API 端点将创建此类型任务，前端将轮询任务状态）

## 风险与边界

- **执行顺序**: 先实现 Service（Task 1），再注册任务类型（Task 2），最后注册处理器（Task 3）
- **验证失败排查方向**:
  - 任务不被 TaskExecutor 拾取：检查 `TaskRegistry.register` 是否被正确调用（import 时执行）
  - 同步过程中 Tushare 报错：检查 Token 有效性、积分余额、速率限制
  - 数据未写入：检查先删后写的 DELETE 条件是否匹配、commit 是否成功
  - 进度不更新：检查 `_progress_callback` 是否正确设置、调用频率（每 100 只）
- **允许修改的额外文件**: 无
- **暂停条件**: Tushare Token 认证失败或积分不足时，暂停并提示用户
- **E2E 不适用说明**: 本功能为纯后端任务处理器，无可观察 UI；执行验证通过 API 触发 + 数据库查询完成。验证项已覆盖任务创建、执行、数据写入全链路。
- **风险备注**:
  - 全量同步预计 25-30 分钟，测试时可用少量股票验证（手动限制查询结果），完整验证需全量执行
  - `_symbol_to_ts_code` 对北交所股票（8/4 开头）的转换需验证

### 后端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| 单只股票 Tushare 超时/限流 | `_execute_with_retry` 指数退避重试 3 次，仍失败则 catch 记录为 failed，continue | todo |
| 单只股票 commit 失败 | rollback 该股票，记入 failed_stocks，continue 下一只 | todo |
| 股票 ts_code 为空 | 通过 `_symbol_to_ts_code` 转换，无法转换的 skip 并记录 | todo |
| Tushare 返回空数据 | skipped += 1，不视为失败（ADR-5） | todo |
| 同步中用户取消任务 | `_cancel_check()` 每 50 只检查一次，检测到取消则抛异常终止 | todo |
| 任务超时 | TaskExecutor 超时机制（timeout=3600s）自动标记 failed | todo |
| 重复触发同一报告期 | 先删后写保证幂等（ADR-1），不产生重复数据 | todo |
| stocks 表无在市股票 | 同步正常完成，added=0，无报错 | todo |
