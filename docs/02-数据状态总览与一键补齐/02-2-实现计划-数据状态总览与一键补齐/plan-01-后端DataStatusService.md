---
feat_id: "plan-01"
title: "后端 DataStatusService"
dimension: backend
phase: 1
status: done
depends_on: []
---

# plan-01: 后端 DataStatusService

## 1. 功能概要

- **目标**: 新建 `DataStatusService`，提供三类板块数据（历史、均线、强度）的状态聚合查询和补齐范围计算能力
- **完成后可观察结果**: 调用 `DataStatusService(db).get_status()` 返回三类数据的完整状态：每类数据包含最新日期（max date）、状态标记（normal / missing / no_data）、缺失日期范围、活跃任务信息。调用 `get_backfill_range("history")` 能返回需要补齐的日期范围元组。数据表为空时正确返回 `no_data` 状态。活跃任务查询能关联到对应数据类型的 pending/running 任务。
- **依赖**: 无
- **关联验收标准**: [AC-01, AC-02]
- **涉及架构模块**: DataStatusService, TradingCalendar, Repository 层
- **前置条件**: PostgreSQL 运行中；TradingCalendar 服务已实现（`server/src/services/trading_calendar.py`）；AsyncTask 模型可用
- **不在范围**: API 路由层（由 plan-02 接管）；前端展示（由 plan-03 接管）；个股数据状态

## 2. 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| create | `server/src/services/data_status.py` | DataStatusService 类，聚合三类数据状态 |

## 3. 实现规格

### 后端部分

#### 1. 创建 DataStatusService 类

新建 `server/src/services/data_status.py`：

```python
class DataStatusService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.trading_calendar = TradingCalendar()

    DATA_TYPES = [
        {
            "type": "history",
            "label": "板块历史数据",
            "model": DailyMarketData,
            "task_types": ["backfill_history"],
        },
        {
            "type": "ma",
            "label": "板块均线数据",
            "model": MovingAverageData,
            "task_types": ["backfill_ma"],
        },
        {
            "type": "strength",
            "label": "板块强度数据",
            "model": StrengthScore,
            "task_types": ["backfill_strength"],
        },
    ]
```

导入：
- `from src.models.daily_market_data import DailyMarketData`
- `from src.models.moving_average_data import MovingAverageData`
- `from src.models.strength_score import StrengthScore`
- `from src.models.async_task import AsyncTask`
- `from src.services.trading_calendar import TradingCalendar`
- `from sqlalchemy import select, func`
- `from datetime import date, timedelta`

#### 2. 实现 get_status()

对每类数据执行：

1. 查询 `select(func.max(Model.date)).where(Model.entity_type == 'sector')` 获取 `latest_date`
2. 若 `latest_date` 为 null → `status="no_data"`
3. 若 `latest_date < today`：
   - 调用 `TradingCalendar.get_trading_days_between(latest_date + timedelta(days=1), today)` 获取交易日
   - 过滤后若有交易日 → `status="missing"`，设置 `missing_range={"start": str(first_trading_day), "end": str(last_trading_day)}`
   - 若无交易日 → `status="normal"`
4. 若 `latest_date >= today` → `status="normal"`
5. 步骤 3 中的 TradingCalendar 调用用 `try/except` 包裹，异常时降级为 `status="normal"`、`missing_range=None`（无法判断缺失，架构 L1 降级）
6. 查询 `AsyncTask` 中 `task_type IN (task_types)` 且 `status IN ("pending", "running")` 的最新一条记录作为 `active_task`

返回结构：
```python
{
    "items": [
        {
            "type": "history",
            "label": "板块历史数据",
            "latest_date": "2026-05-26" | None,
            "status": "normal" | "missing" | "no_data",
            "missing_range": {"start": "...", "end": "..."} | None,
            "active_task": {
                "task_id": "...",
                "status": "pending" | "running" | "completed" | "failed",
                "progress": 10,
                "total": 100,
                "error_message": "..." | None,
            } | None,
        },
        ...
    ]
}
```

#### 3. 实现 get_backfill_range(data_type)

1. 根据 `data_type` 找到对应的模型配置
2. 查询 `latest_date`（同 get_status 步骤 1）
3. 若 `latest_date` 为 null → 返回 `None`（无数据无法补齐）
4. 计算 `start = latest_date + timedelta(days=1)`, `end = today`
5. 调用 `TradingCalendar` 获取交易日列表
6. 若无交易日 → 返回 `None`
7. 返回 `(start, end)` 日期元组

#### 4. 实现 has_active_task(data_type)

查询 `AsyncTask` 表中指定 `task_type`（通过 `DATA_TYPES` 映射）且 `status IN ("pending", "running")` 的记录是否存在。返回 `bool`。

**安全要求（架构 §8.3）**：`data_type` 参数限定为 `Literal["history", "ma", "strength"]`，避免注入。

## 4. Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | 创建 DataStatusService 类，定义 DATA_TYPES 配置和构造函数 | backend | done | |
| 2 | 实现 get_status() 方法：聚合三类数据状态（max date + 缺失检测 + 活跃任务） | backend | done | |
| 3 | 实现 get_backfill_range(data_type) 方法 | backend | done | |
| 4 | 实现 has_active_task(data_type) 方法 | backend | done | |

## 5. 验收标准

### 后端验收

- [ ] AC-01 `get_status()` 返回包含 3 个 item 的列表，每项包含 type / label / latest_date / status 字段
- [ ] AC-01 数据表为空时 latest_date 返回 null，status 返回 `no_data`
- [ ] AC-01 有活跃任务（pending/running）时 active_task 字段非空，包含 task_id / status / progress / total / error_message
- [ ] AC-02 `get_status()` 正确检测缺失：latest_date 早于今天且有交易日时 status 为 `missing`，missing_range 正确
- [ ] AC-02 非交易日（周末/节假日）后不误报缺失
- [ ] `get_backfill_range()` 返回正确的日期范围元组或 None
- [ ] `has_active_task()` 正确返回布尔值
- [ ] E2E-TDD：通过 plan-02 的 API 端点验证状态查询结果（red 先因 API 不存在而失败，green 后通过）

## 6. 验证命令

```bash
# plan-02 完成后可通过 curl 验证
# 单元验证：import DataStatusService 无报错
cd server && python -c "from src.services.data_status import DataStatusService; print('OK')"
```

## 7. 交接上下文

- **架构章节**: §6.1 状态查询链路, §6.2 一键补齐链路
- **相关代码**:
  - `server/src/services/trading_calendar.py` — 交易日历服务
  - `server/src/models/daily_market_data.py` — DailyMarketData 模型
  - `server/src/models/moving_average_data.py` — MovingAverageData 模型
  - `server/src/models/strength_score.py` — StrengthScore 模型
  - `server/src/models/async_task.py` — AsyncTask 模型
- **契约 / 数据对象**: `DataStatusResponse`、`DataTypeStatus`（架构 §7.2）
- **下游消费方**: plan-02（DataStatusAPI 调用本 Service）

## 8. 风险与边界

- **执行顺序**: 按 Task 列表顺序执行（1→2→3→4）
- **验证失败排查方向**: 检查数据库是否有 sector 类型数据；检查 TradingCalendar 是否正常工作
- **允许修改的额外文件**: 无
- **暂停条件**: TradingCalendar 不可用或数据库连接失败
- **E2E 不适用说明**: 本功能为纯后端 Service 层，无用户可观察 UI，E2E 通过 plan-02 的 API 端点间接验证
- **风险备注**: TradingCalendar 缓存按日生效，跨日时可能需重新获取

### 后端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| 数据表完全为空 | latest_date 返回 null，status 返回 `no_data` | done |
| latest_date 为今天 | status 返回 `normal`，无 missing_range | done |
| 交易日历服务不可用 | get_status() 降级：只返回 latest_date，不判断 missing（架构 L1 降级） | done |
| 同类型有多个活跃任务 | 只取最新一条作为 active_task | done |
