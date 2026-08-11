---
feat_id: "plan-02"
title: "指数采集服务与同步路由"
dimension: backend
phase: 1
status: done
depends_on: ["plan-01"]
---

# plan-02: 指数采集服务与同步路由

## 功能概要

- **目标**: 新建 IndexDataInitService 采集编排服务（清单同步/历史回填/当日增量），新建 admin 同步路由（3 个 POST 端点返回 task_id），使管理员可通过 API 触发数据采集并入库。
- **完成后可观察结果**: 管理员调用 `POST /api/v1/admin/init/index-basic` 返回 task_id，异步任务完成后 index_basic 表有约 1 万条数据且 14 只预置指数 is_watched=true。调用 `/index-history` 回填后，index_daily/index_dailybasic/index_weight 三张表有近 1 年数据。任务监控页（/admin/tasks）可见指数相关任务的状态和进度。
- **依赖**: plan-01（模型 + 采集方法）
- **关联验收标准**: [AC-08a, AC-08b, AC-09]
- **涉及架构模块**: IndexDataInitService、admin/init_index_basic.py、AsyncTask
- **前置条件**: plan-01 完成（4 张表已建、4 个采集方法可用）
- **不在范围**: 查询 API（plan-03）、前端同步面板 UI（plan-04）

## 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
|------|------|------|
| create | `server/src/services/data_init_index.py` | IndexDataInitService 采集服务 |
| create | `server/src/api/admin/init_index_basic.py` | admin 同步路由（3 端点） |
| modify | `server/src/api/admin/__init__.py` | 注册 init_index_basic 路由 |

## 实现规格

### 后端部分

#### 1. IndexDataInitService（data_init_index.py）

范式对齐 `server/src/services/data_init_etf.py`（EtfDataInitService）：session 注入 + `set_progress_callback` / `set_cancel_check` + pg upsert（`sqlalchemy.dialects.postgresql.insert`）。

**构造函数与回调**（照抄 EtfDataInitService 范式）：
```python
class IndexDataInitService:
    def __init__(self, session: Optional[AsyncSession] = None):
        self.session = session
        self._progress_callback = None
        self._cancel_check = None
    def set_session(self, session): self.session = session
    def set_progress_callback(self, cb): self._progress_callback = cb
    def set_cancel_check(self, cb): self._cancel_check = cb
    async def _check_cancelled(self): ...  # 同 EtfDataInitService
    async def _update_progress(self, cur, total, msg): ...  # 同 EtfDataInitService
```

**sync_index_basic()** — 指数清单同步：
- 调 `DataSourceFactory.create().get_index_basic()` 拉全量
- 字段映射（ts_code/name/market/publisher/category/base_date/base_point/list_date 直取，is_watched 默认 false）
- pg upsert index_basic（冲突键 ts_code，on_conflict_do_update 覆盖除 is_watched 外的字段——**注意：upsert 不能覆盖 is_watched**，否则会重置用户关注配置）
- upsert 完成后，执行预置 14 只 `UPDATE index_basic SET is_watched=true WHERE ts_code IN (...)`（仅首次同步时设置，用 WHERE is_watched IS NULL 或 WHERE ts_code IN 预置清单 AND NOT EXISTS 已关注记录）
- 返回 `{"added": N, "updated": 0, "failed": 0}`

**backfill_index_history(start_date, end_date)** — 历史回填：
- 查交易日历获取日期范围内的交易日列表（升序），复用 `TradingCalendar`
- 查 `index_basic WHERE is_watched=true` 获取关注指数清单
- 逐交易日循环：对每个交易日，逐关注指数调 `get_index_daily` / `get_index_dailybasic`，同月只调一次 `get_index_weight`（用集合记录已拉取的月份）
- 每个交易日完成后 upsert 入库 + `_update_progress(current, total_trading_days, msg)`
- 单指数单日失败不中断，记 error 继续
- 返回 `{"trading_days": N, "daily_records": N, "basic_records": N, "weight_records": N, "errors": [...]}`

**sync_index_daily(trade_date)** — 当日增量采集：
- 查关注指数清单
- 逐指数调 `get_index_daily(trade_date)` + `get_index_dailybasic(trade_date)` upsert
- 调 `get_index_weight(当月)` 如当月未入库
- 返回计数 dict

**upsert 辅助方法**：
- index_daily: 冲突键 (trade_date, ts_code)
- index_dailybasic: 冲突键 (trade_date, ts_code)
- index_weight: 冲突键 (index_code, con_code, trade_date)

**可观测性（架构 §8.5）**：每个方法加 `logger.info`（开始/完成/条数），失败加 `logger.warning`，与 EtfDataInitService 一致。使用项目现有 logging。

#### 2. Admin 同步路由（init_index_basic.py）

范式对齐 `server/src/api/admin/init_etf_daily.py`。

**路由声明**：
```python
router = APIRouter(prefix="/init", tags=["Admin - Index"])
```
最终路径：admin 挂 `/v1/admin` + 路由 prefix `/init` + 端点 = `/api/v1/admin/init/index-basic`

**3 个 POST 端点**（范式对齐 init_etf_daily.py：并发保护 + TaskManager.create_task + 返回 task_id）：

每个端点的标准结构（以 /index-basic 为例）：
```python
@router.post("/index-basic", response_model=ApiResponse[dict])
async def init_index_basic(
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    # 1. 并发保护：检查同类型 pending/running 任务
    running = await session.execute(
        select(AsyncTask).where(and_(
            AsyncTask.task_type == TaskType.SYNC_INDEX_BASIC.value,
            AsyncTask.status.in_(["pending", "running"]),
        ))
    )
    if running.scalar_one_or_none():
        return ApiResponse(success=False, data=None, message="已有指数清单同步任务正在运行")

    # 2. 创建任务（TaskManager 范式）
    from src.services.task_manager import TaskManager
    manager = TaskManager(session)
    task = await manager.create_task(
        task_type=TaskType.SYNC_INDEX_BASIC.value,
        params={}, max_retries=3, timeout_seconds=3600,
        created_by=_admin.id,
    )
    await session.commit()
    return ApiResponse(success=True, data={"task_id": task.task_id})
```

三个端点差异：
- `POST /index-basic`：无 body，task_type=SYNC_INDEX_BASIC，params={}
- `POST /index-history`：body `{start_date, end_date}`，task_type=BACKFILL_INDEX_HISTORY，params={start_date, end_date}
- `POST /index-daily`：无 body，task_type=SYNC_INDEX_DAILY，params={}

**权限校验**：使用 `Depends(require_admin)`（从 `src.api.deps` 导入，与 init_etf_daily.py 一致）。

**import 确认**：
- `from src.api.deps import get_session, require_admin`
- `from src.api.schemas.response import ApiResponse`
- `from src.models.async_task import AsyncTask`
- `from src.models.user import User`
- `from src.services.task_handlers import TaskType`
- `from sqlalchemy import select, and_`

#### 3. TaskType 枚举 + Handler 注册（task_handlers.py）

**TaskType 枚举**（`server/src/services/task_handlers.py` L27 的 `class TaskType`，str Enum）：
```python
SYNC_INDEX_BASIC = "sync_index_basic"
BACKFILL_INDEX_HISTORY = "backfill_index_history"
SYNC_INDEX_DAILY = "sync_index_daily"
```
加在现有 ETF 枚举（L69-75）之后。

**Handler 注册**（task_handlers.py，范式对齐 `sync_etf_daily_task` L1257 和 `backfill_etf_history_task` L1298）：

每个 handler 用 `@TaskRegistry.register(TaskType.XXX)` 装饰，签名 `(task_id, params, manager)`：

```python
@TaskRegistry.register(TaskType.SYNC_INDEX_BASIC)
async def sync_index_basic_task(task_id, params, manager):
    from src.services.data_init_index import IndexDataInitService
    await manager.log_message(task_id, "INFO", "Starting index basic sync")
    service = IndexDataInitService(manager.db)
    callback = await _make_progress_callback(manager, task_id)
    service.set_progress_callback(callback)
    result = await service.sync_index_basic()
    await manager.log_message(task_id, "INFO", f"Index basic sync completed: {result}")

@TaskRegistry.register(TaskType.BACKFILL_INDEX_HISTORY)
async def backfill_index_history_task(task_id, params, manager):
    # 从 params 取 start_date/end_date
    # service.backfill_index_history(start_date, end_date)

@TaskRegistry.register(TaskType.SYNC_INDEX_DAILY)
async def sync_index_daily_task(task_id, params, manager):
    # service.sync_index_daily(today)
```

**关键细节**：
- `service = IndexDataInitService(manager.db)` — session 从 manager.db 获取（不是构造函数注入）
- `callback = await _make_progress_callback(manager, task_id)` — 复用现有进度回调工厂函数
- handler 内 import service 避免循环依赖
- `manager.log_message(task_id, "INFO/ERROR", msg)` 记录日志

**`__all__` 或模块变量列表更新**：task_handlers.py L651-652 有一个 handler 函数名列表（`"sync_etf_daily_task"` 等），需追加 3 个指数 handler 名。

#### 4. 路由注册（admin/__init__.py）

```python
from .init_index_basic import router as init_index_basic_router
# ...
router.include_router(init_index_basic_router)  # /api/v1/admin/init/index-*
```

**复用声明调用细节**：
- `DataSourceFactory.create()` → `from src.services.data_acquisition import DataSourceFactory`，返回 TushareDataSource 实例
- `TaskManager` → `from src.services.task_manager import TaskManager`，构造函数 `TaskManager(session)`，方法 `create_task(task_type, params, max_retries, timeout_seconds, created_by)` 返回含 `task_id` 的对象；`manager.db` 是 AsyncSession；`manager.log_message(task_id, level, msg)` 记日志；参考 init_etf_daily.py L65-75
- `TaskType` 枚举 → `from src.services.task_handlers import TaskType`（str Enum 类，L27），注册 handler 用 `@TaskRegistry.register(TaskType.XXX)`，handler 签名 `(task_id, params, manager)`；参考 sync_etf_daily_task L1257-1293
- `_make_progress_callback` → task_handlers.py 内的工厂函数，`callback = await _make_progress_callback(manager, task_id)`，传给 service.set_progress_callback；参考 backfill_etf_history_task L1330
- `require_admin` → `from src.api.deps import require_admin`，FastAPI Depends 用法
- `ApiResponse` → `from src.api.schemas.response import ApiResponse`，响应包裹
- `TradingCalendar` → `from src.services.trading_calendar import TradingCalendar`，参考 data_init_etf.py 的 `is_trading_day` 和交易日范围获取
- pg upsert → `from sqlalchemy.dialects.postgresql import insert as pg_insert`，参考 data_init_etf.py 的 `on_conflict_do_update` 用法

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
|---|------|------|------|------|
| 1 | 创建 IndexDataInitService 基础结构 | backend | done | session/progress/cancel 回调 |
| 2 | 实现 sync_index_basic() | backend | done | 全量拉取+upsert+预置14只 |
| 3 | 实现 backfill_index_history() | backend | done | 逐交易日逐指数采集 |
| 4 | 实现 sync_index_daily() | backend | done | 当日增量 |
| 5 | task_handlers.py 加 TaskType 枚举 + 3 个 handler | backend | done | @TaskRegistry.register + manager.db + _make_progress_callback |
| 6 | 创建 init_index_basic.py 路由 | backend | done | 3个POST：并发保护+TaskManager.create_task |
| 7 | 注册路由到 admin/__init__.py | backend | done | include_router |

## 验收标准

### 清单同步验收（AC-08a）

- [ ] AC-08a `POST /api/v1/admin/init/index-basic` 返回 task_id
- [ ] AC-08a 任务完成后 index_basic 表有 ≥10000 条记录
- [ ] AC-08a 14 只预置指数 is_watched=true
- [ ] AC-08a 重复同步不产生重复记录（upsert 幂等）
- [ ] AC-08a 重复同步不重置已关注的 is_watched 标记

### 回填验收（AC-08b）

- [ ] AC-08b `POST /api/v1/admin/init/index-history` body `{start_date: "2025-08-10", end_date: "2026-08-10"}` 返回 task_id
- [ ] AC-08b 任务完成后 index_daily 有关注指数近1年行情数据（每只≥200条）
- [ ] AC-08b index_dailybasic 有 6 只有估值的指数数据
- [ ] AC-08b index_weight 有沪深300 等成分权重数据
- [ ] AC-08b 进度通过 AsyncTask 可查询（progress/total）

### 数据真实性验收（AC-09）

- [ ] AC-09 入库的收盘价/涨跌幅/PE_TTM 与 plan-01 采集方法返回的原始值一致

### 执行验证（task handler 必须）

- [ ] 任务创建成功（返回 task_id 非 null）
- [ ] 任务执行成功（status=completed）
- [ ] 目标表数据正确写入（行数 > 0，字段值非 null）

## 验证命令

```bash
cd server && source ../.venv/bin/activate

# 启动服务
uvicorn src.main:app --reload &

# 1. 清单同步
curl -X POST http://localhost:8000/api/v1/admin/init/index-basic \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json"
# 预期: {"task_id": "xxx"}

# 等任务完成后验证数据
psql -c "SELECT COUNT(*) FROM index_basic;"  # 预期 ≥10000
psql -c "SELECT COUNT(*) FROM index_basic WHERE is_watched = true;"  # 预期 14

# 2. 历史回填
curl -X POST http://localhost:8000/api/v1/admin/init/index-history \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"start_date":"2025-08-10","end_date":"2026-08-10"}'

# 等任务完成后验证
psql -c "SELECT COUNT(*) FROM index_daily;"  # 预期 >2000
psql -c "SELECT COUNT(*) FROM index_dailybasic WHERE ts_code='000300.SH';"  # 预期 >200
psql -c "SELECT COUNT(*) FROM index_weight WHERE index_code='000300.SH';"  # 预期 300
```

## 交接上下文

- **架构章节**: §6.1（清单同步链路）、§6.2（历史回填链路）、§6.3（当日增量链路）、§7.3（Admin API 边界）
- **相关代码**: `server/src/services/data_init_etf.py`（采集服务范式锚点）、`server/src/api/admin/init_etf_daily.py`（admin 路由锚点）
- **契约/数据对象**: AsyncTask（task_type: sync_index_basic / backfill_index_history / sync_index_daily）
- **下游消费方**: plan-03（查询 API 读这些表）、plan-04（前端通过 adminApi 调这些端点）

## 风险与边界

- **执行顺序**: 先实现服务（Task 1-4），再注册 task_type（Task 5），再建路由（Task 6-7）
- **验证失败排查方向**: 检查 AsyncTask 是否正确注册新 task_type、BackgroundTasks 是否正确传递 session、upsert 冲突键是否匹配唯一约束
- **允许修改的额外文件**: 后端 TaskType 枚举定义文件（如需加成员）
- **暂停条件**: task_type 注册位置不明确时暂停确认

### 后端边界场景

| 场景 | 处理方式 | 状态 |
|------|---------|------|
| upsert 覆盖 is_watched | on_conflict_do_update 排除 is_watched 字段 | done |
| 历史回填中途某交易日失败 | 记 error 继续，不中断（架构 §6.2 实现原则） | done |
| 重复回填同日期 | upsert 幂等覆盖（架构 §6.2 实现原则） | done |
| 清单未同步时触发回填 | 前端禁用 + 后端校验 index_basic 非空 | done |
| 无估值指数采集 dailybasic | 返回空列表，跳过 upsert | done |
| 权重月度缓存 | 集合记录已拉取月份，同月不重复 | done |
