---
feat_id: "plan-02"
title: "后端 DataStatusAPI 与 Task Handlers"
dimension: backend
phase: 2
status: done
depends_on: ["plan-01"]
---

# plan-02: 后端 DataStatusAPI 与 Task Handlers

## 1. 功能概要

- **目标**: 新增 DataStatusAPI 路由（状态查询 + 补齐触发）和 3 个新 task type 封装补齐逻辑
- **完成后可观察结果**: 通过 `curl GET /api/v1/admin/data/status` 能获取三类数据的完整状态 JSON。通过 `curl POST /api/v1/admin/data/backfill/history` 能创建补齐任务并返回 task_id。已有活跃任务时重复请求返回 409 冲突。无缺失数据时返回 400。补齐任务在 TaskExecutor 中正常执行，进度通过 AsyncTask 表更新。
- **依赖**: plan-01（DataStatusService）
- **关联验收标准**: [AC-03, AC-05]
- **涉及架构模块**: DataStatusAPI, TaskRegistry, DataUpdateService, SectorMAService, SectorStrengthService
- **前置条件**: plan-01 已完成；现有 TaskExecutor / TaskManager / AsyncTask 体系可用
- **不在范围**: 前端展示（由 plan-03 接管）；个股数据补齐

## 2. 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| create | `server/src/api/admin/data_status.py` | 状态查询和补齐触发 API 路由 |
| modify | `server/src/services/task_handlers.py` | 新增 3 个 TaskType 枚举值和对应 handler |
| modify | `server/src/api/admin/__init__.py` | 注册 data_status 路由 |

## 3. 实现规格

### 后端部分

#### 1. 新增 TaskType 枚举值

在 `server/src/services/task_handlers.py` 的 `TaskType` 枚举中添加：

```python
class TaskType(str, Enum):
    # ... 现有值 ...

    # 数据状态补齐任务
    BACKFILL_HISTORY = "backfill_history"
    BACKFILL_MA = "backfill_ma"
    BACKFILL_STRENGTH = "backfill_strength"
```

#### 2. 注册 3 个新 task handler

在 `task_handlers.py` 末尾（`__all__` 之前）添加：

**backfill_history handler**:
- 参数: `{ "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD" }`
- 内部: 调用 `DataUpdateService.backfill_by_range(start_date, end_date, target_type="sector")`
- 设置进度回调

**backfill_ma handler**:
- 参数: `{ "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD" }`
- 内部: 对日期范围内每个交易日调用 `SectorMAService.backfill_sector_ma(target_date)`
- 逐日循环 + 进度回调（`progress_callback(current, total, message)`）
- 需用 TradingCalendar 获取日期范围内的交易日列表
- 单日失败时记录 WARNING 日志并继续下一日，最终汇总成功/失败天数通过 progress_callback 报告

**backfill_strength handler**:
- 参数: `{ "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD" }`
- 内部: 调用 `SectorStrengthService.calculate_sector_strength_by_range(start_date, end_date)`
- 设置进度回调

更新 `__all__` 列表添加 3 个新函数名。

参考现有 handler 模式（如 `backfill_by_range_task`、`backfill_sector_ma_by_date_task`）保持一致性。

**安全要求（架构 §8.3）**：task handler 只接受 start_date / end_date 参数，不做额外参数注入。进度回调通过 TaskManager 安全传递。

#### 3. 新建 API 路由

创建 `server/src/api/admin/data_status.py`：

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.database import get_db
from src.services.data_status import DataStatusService
from src.services.task_manager import TaskManager
from src.services.task_handlers import TaskType

router = APIRouter(prefix="/data", tags=["Data Status"])
```

**GET /status**:
- 调用 `DataStatusService(db).get_status()`
- 返回 `{ "data": { "items": [...] } }`

**POST /backfill/{type}**:
- `type` 路径参数限定为 `Literal["history", "ma", "strength"]`
- 实例化 `DataStatusService(db)`
- 先检查 `has_active_task(type)` → 若有活跃任务，返回 409 `{ "detail": "该类数据已有补齐任务正在执行" }`
- 调用 `get_backfill_range(type)` → 若返回 None，返回 400 `{ "detail": "该类数据无缺失" }`
- 调用 `TaskManager(db).create_task(task_type=对应type, params={"start_date": start.isoformat(), "end_date": end.isoformat()})`
- 返回 `{ "data": { "task_id": "..." } }`

数据类型到 task_type 映射：
- `history` → `TaskType.BACKFILL_HISTORY`
- `ma` → `TaskType.BACKFILL_MA`
- `strength` → `TaskType.BACKFILL_STRENGTH`

**安全要求（架构 §8.3）**：
- `type` 参数使用 `Literal` 做路径参数校验，不接受任意字符串
- 路由注册在 admin 路由下，自动继承 RBAC 权限检查

#### 4. 注册路由

修改 `server/src/api/admin/__init__.py`，添加：

```python
from .data_status import router as data_status_router
router.include_router(data_status_router)  # /api/v1/admin/data/status, /api/v1/admin/data/backfill/{type}
```

#### 5. 确认 RBAC 保护

检查现有 admin 路由保护方式，确认新路由自动继承 admin 权限检查。现有 admin 路由通过 `router.include_router()` 注册到 admin 模块即可继承。

## 4. Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | 在 TaskType 枚举中添加 BACKFILL_HISTORY / BACKFILL_MA / BACKFILL_STRENGTH | backend | done | |
| 2 | 实现 backfill_history task handler | backend | done | 调用 DataUpdateService.backfill_by_range |
| 3 | 实现 backfill_ma task handler | backend | done | 逐日循环调用 SectorMAService.backfill_sector_ma |
| 4 | 实现 backfill_strength task handler | backend | done | 调用 SectorStrengthService.calculate_sector_strength_by_range |
| 5 | 创建 data_status.py API 路由（GET /status + POST /backfill/{type}） | backend | done | |
| 6 | 在 admin __init__.py 注册 data_status 路由 | backend | done | |
| 7 | 确认路由受 admin RBAC 保护 | backend | done | 两个端点均使用 Depends(require_admin) |

## 5. 验收标准

### 后端验收

- [ ] AC-03 `POST /admin/data/backfill/{type}` 能成功创建补齐任务，返回 `{ "data": { "task_id": "..." } }`
- [ ] AC-03 自动检测缺口范围，无需手动填写日期
- [ ] AC-03 同类型已有活跃任务时返回 409 冲突
- [ ] AC-03 无缺失数据时返回 400
- [ ] AC-03 type 参数不接受 history/ma/strength 以外的值（422 校验）
- [ ] AC-05 task handler 正常执行并更新进度
- [ ] AC-01 `GET /admin/data/status` 返回三类数据的完整状态
- [ ] 补齐任务执行后，再次查询状态 API，latest_date 已更新
- [ ] E2E-TDD：curl 验证 API 端点（red 先因路由未注册失败，green 后通过）

### 性能验收（架构 §8.1 目标）

- [ ] `GET /admin/data/status` 响应时间 < 2s（DevTools 或 curl 计时确认）

## 6. 验证命令

```bash
# 查看状态
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/admin/data/status

# 触发补齐（假设 history 有缺失）
curl -X POST -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/admin/data/backfill/history

# 重复触发应返回 409
curl -X POST -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/admin/data/backfill/history

# 无缺失时应返回 400
curl -X POST -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/admin/data/backfill/strength

# 非法 type 应返回 422
curl -X POST -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/admin/data/backfill/invalid
```

## 7. 交接上下文

- **架构章节**: §6.2 一键补齐链路, §7.3 API 边界, ADR-2
- **相关代码**:
  - `server/src/services/data_status.py` — plan-01 产出的 DataStatusService
  - `server/src/services/task_handlers.py` — 现有 task handler 注册模式
  - `server/src/services/task_manager.py` — TaskManager.create_task()
  - `server/src/services/data_update.py` — DataUpdateService.backfill_by_range()
  - `server/src/services/sector_ma_service.py` — SectorMAService.backfill_sector_ma()
  - `server/src/services/sector_strength_service.py` — SectorStrengthService.calculate_sector_strength_by_range()
- **契约 / 数据对象**: `BackfillResponse`（架构 §7.2）
- **下游消费方**: plan-03（前端调用本 API）

## 8. 风险与边界

- **执行顺序**: 按 Task 列表顺序执行（1→2→3→4→5→6→7）
- **验证失败排查方向**: 检查后端日志确认路由注册；检查 TaskExecutor 是否正常轮询；检查数据库连接
- **允许修改的额外文件**: 无
- **暂停条件**: plan-01 的 DataStatusService 不可用；TaskManager 创建任务失败
- **E2E 不适用说明**: 本功能为纯后端 API 层，E2E 通过 curl 命令验证
- **风险备注**: backfill_ma handler 需逐日循环，大量缺失日期时执行时间较长；已有任务超时机制（4h）

### 后端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| 补齐期间产生新缺口 | 不自动链式补齐，需再次点击 | done |
| backfill_ma 大量缺失日期 | 逐日循环 + 进度回调，已有 4h 超时机制 | done |
| TaskExecutor 未运行 | 任务创建成功但停留在 pending，前端正常展示 | done |
| DataUpdateService.backfill_by_range 内部异常 | handler 捕获异常，标记任务 failed | done |
