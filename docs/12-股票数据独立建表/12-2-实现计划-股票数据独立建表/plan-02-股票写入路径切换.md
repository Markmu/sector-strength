---
feat_id: "plan-02"
title: "股票写入路径切换"
dimension: backend
phase: 2
status: done
depends_on: ["plan-01"]
---

# plan-02 股票写入路径切换

## 1. 功能概要

- **目标**: 把所有写入 `entity_type='stock'` 数据的代码路径切换到三张新表，使新采集的股票数据全部落入新表
- **完成后可观察结果**: 触发股票数据采集任务（init_historical_data / backfill_by_date / backfill_by_range）后，新表 `stock_daily_market_data` 有新增记录，旧表 `daily_market_data` 不再新增 entity_type='stock' 记录。触发股票均线计算后，`stock_moving_average_data` 有数据。触发股票强度计算后，`stock_strength_scores` 有数据。触发个股级联删除时，三张新表中对应个股数据被清理，旧表板块数据不动
- **依赖**: plan-01（新表模型与迁移已完成）
- **关联验收标准**: [AC-01, AC-04]
- **涉及架构模块**: collector 股票分支、DataInitService 股票路径、DataUpdateService 股票路径、StockMAService、StrengthServiceV2 个股分支、data_quality 个股分支
- **前置条件**: plan-01 task-review 通过；新三表已建；alembic head 已推进
- **不在范围**: 读取路径切换（plan-03）；API 端点改动；测试修复（plan-04）

## 2. 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
|---|---|---|
| modify | `server/src/services/data_updater/collector.py` | `_update_market_data` 股票分支（约 290-308）切新表 |
| modify | `server/src/services/data_init.py` | 股票历史初始化（约 802-831、955-984）+ `_cascade_delete_stock_data`（700-735）切新表 |
| modify | `server/src/services/data_update.py` | 股票增量更新（约 268-284、419-441、532）切新表 |
| modify | `server/src/services/monitoring/data_quality.py` | 股票行情补齐（约 190-235）切新表 |
| modify | `server/src/services/stock_ma_service.py` | 均线 read-modify-write（约 295-345）切新表 |
| modify | `server/src/services/strength_service_v2.py` | `_save_strength_score`（289-404）+ `calculate_and_update_change_rate`（489-585）按 entity_type 内部分发 |

## 3. 实现规格

### 后端部分

#### 1. collector 股票分支（`data_updater/collector.py:290-308`）

现状：`pg_insert(DailyMarketData).values(entity_type='stock', entity_id=stock.id, symbol=..., date=..., open/high/low/close/volume/turnover/change/change_percent)`，`on_conflict_do_nothing(constraint='uq_daily_market_data_entity_date')`。

改造：
- `pg_insert(StockDailyMarketData).values(stock_id=stock.id, symbol=..., date=..., ...)`（去 entity_type，entity_id→stock_id）
- `on_conflict_do_nothing(constraint='uq_stock_daily_market_data_stock_date')`（约束名换新表）
- 分批 commit（batch_size=50）保持不变
- **可观测性（架构 §8.5）**：在写入处增加一行结构化日志 `logger.info("stock_market_data_inserted", extra={"table": "stock_daily_market_data", "count": n})`，便于上线后核对 AC-01
- import：`from src.models import StockDailyMarketData`

#### 2. DataInitService 股票路径（`data_init.py`）

**历史初始化（约 802-831，init_historical_data 股票子段）**：
现状：`select(DailyMarketData).where(entity_type=='stock', entity_id==stock.id, date==...)` 查重 → `session.add(DailyMarketData(entity_type='stock', entity_id=stock.id, ...))`。

改造：select 与 add 均换 `StockDailyMarketData`，去 entity_type，entity_id→stock_id。

**按日期范围初始化（约 955-984，init_historical_data_by_date_range 股票子段）**：同上替换。

**`_cascade_delete_stock_data`（700-735）**：
现状：
```python
for model in (DailyMarketData, MovingAverageData, StrengthScore):
    await self.session.execute(
        delete(model).where(and_(
            model.entity_type == "stock",
            model.entity_id.in_(stock_ids),
        ))
    )
```
改造：
```python
from src.models import StockDailyMarketData, StockMovingAverageData, StockStrengthScore
for model in (StockDailyMarketData, StockMovingAverageData, StockStrengthScore):
    await self.session.execute(
        delete(model).where(model.stock_id.in_(stock_ids))
    )
```
后续 SectorStock（按 stock_code）、Top10FloatHolder（按 symbol）、Stock（按 id）清理逻辑不变。

#### 3. DataUpdateService 股票路径（`data_update.py`）

`backfill_by_date` 股票写入子段（约 268-284）、`backfill_by_range` 股票写入子段（约 419-441）、`fetch_missing_dates` 中 `DailyMarketData.entity_type == "stock"`（约 532）：全部把 `DailyMarketData` 换 `StockDailyMarketData`，去 entity_type，entity_id→stock_id。

注意：这些方法签名支持 `target_type="stock"|"sector"|None`，**只改 stock 分支**，sector 分支（约对应行号的另一半）完全不动。

#### 4. data_quality 股票分支（`monitoring/data_quality.py:190-235`）

`_backfill_single_date` 股票补齐子段：现状用 `pg_insert(DailyMarketData).values(entity_type='stock', ...)`。改造换 `StockDailyMarketData`，约束名换 `uq_stock_daily_market_data_stock_date`。

sector 补齐子段（约 168-182）完全不动。

#### 5. StockMAService（`stock_ma_service.py:295-345`）

现状 read-modify-write：
- 查重：`select(MovingAverageData).where(entity_type=='stock', entity_id==stock.id, symbol==..., date==..., period==...)`
- 写：`session.add(MovingAverageData(entity_type="stock", entity_id=stock.id, symbol=stock.symbol, date=idx, period=period_str, ma_value=..., price_ratio=..., trend=...))`

改造：select 与 add 均换 `StockMovingAverageData`，去 entity_type，entity_id→stock_id。批量 commit（batch_size=500）保持不变。

断点续传查询（约 213-241，查 max date）也需换模型。

#### 6. StrengthServiceV2 个股分支（`strength_service_v2.py:289-404, 489-585`）

**`_save_strength_score`（289-404）现状**：用 entity_type 参数透传到 `select(StrengthScore).where(entity_type==entity_type, entity_id==entity_id, date==calc_date, period=='all')` 查重，再 update 或 `session.add(StrengthScore(entity_type=entity_type, entity_id=entity_id, ...))`。写入字段不含 percentile（由 ranking_service 事后 setattr）。

改造（ADR-4 内部分发）：在方法内按 entity_type 选模型：
```python
from src.models import StrengthScore, StockStrengthScore
Model = StockStrengthScore if entity_type == "stock" else StrengthScore
# 后续 select(Model).where(...) / session.add(Model(...))
id_field = Model.stock_id if entity_type == "stock" else Model.entity_id
stmt = select(Model).where(and_(
    id_field == entity_id,
    Model.date == calc_date,
    # stock 表无 period 列，sector 表保留 period=='all' 条件
))
```

新增 StockStrengthScore 时**不设 entity_type / period**（新表无此列），stock_id 替代 entity_id。其余字段（score/price_position_score/.../ma5..ma240/price_above_ma5..240/change_rate_1d/strength_grade）照搬。

**`calculate_and_update_change_rate`（489-585）**：同样按 entity_type 内部分发模型类，select/update 指向新表。

#### 7. result_saver 调用细节核对

`server/src/services/calculation/result_saver.py` 的 `save_calculation_results`（35-77）**不写 strength_scores 表**——它只更新 `Stock`/`Sector` 实体表的冗余字段 `strength_score`/`trend_direction`。**本功能无需改动此文件**（架构文档原列此为疑点，核对后确认不涉及写入三表）。从文件清单移除。

## 4. Task 列表

| # | Task | 维度 | 状态 | 说明 |
|---|---|---|---|---|
| 1 | collector 股票分支切 StockDailyMarketData | backend | done | 约束名同步换新表，加可观测性日志 |
| 2 | data_init 股票历史初始化切新表 | backend | done | 两处子段（init_historical_data + by_date_range） |
| 3 | data_init._cascade_delete_stock_data 三表遍历换新模型 | backend | done | 三元组 (StockDailyMarketData, StockMovingAverageData, StockStrengthScore) |
| 4 | data_update 股票增量更新切新表 | backend | done | backfill_by_date + backfill_by_range + fetch_missing_dates 股票子段 |
| 5 | data_quality 股票行情补齐切新表 | backend | done | 仅股票子段，板块子段不动 |
| 6 | StockMAService 均线 read-modify-write 切新表 | backend | done | 含断点续传查询 |
| 7 | StrengthServiceV2._save_strength_score 按 entity_type 分发 | backend | done | ADR-4 内部分发，外部签名不变 |
| 8 | StrengthServiceV2.calculate_and_update_change_rate 按 entity_type 分发 | backend | done | 同 #7 |
| 9 | 触发股票采集，验证新表入库 + 旧表无新增 | backend | done | AC-01 验证（SQLAlchemy 直查 + on_conflict 幂等） |
| 10 | 触发级联删除，验证新三表清理 + 板块不动 | backend | done | AC-04 验证（按 stock_id 删三表全清） |

## 5. 验收标准

### 功能验收

- [ ] AC-01：触发 `init_historical_data_task` / `backfill_by_date_task` / `backfill_by_range_task` 任一后，`SELECT count(*) FROM stock_daily_market_data` 增加；`SELECT count(*) FROM daily_market_data WHERE entity_type='stock'` 不再增加（旧表 stock 写入已停）
- [ ] AC-01：触发股票均线计算后 `stock_moving_average_data` 有数据；触发股票强度计算后 `stock_strength_scores` 有数据
- [ ] AC-04：触发个股级联删除后，`stock_daily_market_data` / `stock_moving_average_data` / `stock_strength_scores` 中对应 stock_id 的记录被清理；`daily_market_data` 中板块数据（entity_type='sector'）不受影响
- [ ] collector 写入用 `uq_stock_daily_market_data_stock_date` 约束名（on_conflict_do_nothing）
- [ ] StrengthServiceV2._save_strength_score 外部签名（entity_type 参数）保持不变，内部按类型分发
- [ ] 共享方法（_save_strength_score）改动后，板块路径（entity_type='sector'）仍写旧表 `strength_scores`（核对：触发板块强度计算后旧表有新增）

### 涉及 task handler 的执行验证（不可豁免）

- [ ] 触发 `init_historical_data_task`（TaskType.INIT_HISTORICAL_DATA）→ 等待任务 status=completed → 查询 `stock_daily_market_data` 有新增记录且字段值（open/high/low/close/volume）正确
- [ ] 触发 `backfill_by_date_task`（TaskType.BACKFILL_BY_DATE，target_type='stock'）→ 等待完成 → 目标表 `stock_daily_market_data` 数据正确写入

## 6. 验证命令

```bash
cd server
source .venv/bin/activate

# 1. 单元测试（受影响服务的测试，可能需先临时调整 fixture，正式修复在 plan-04）
pytest tests/test_data_updater.py tests/test_data_init.py tests/test_data_update.py -v -k "stock" 2>&1 | head -50

# 2. 触发采集验证（手动或通过 API 触发 task）
# 触发后用 psql / SQLAlchemy 查询：
python -c "
import asyncio
from src.db.session import async_session_factory
from src.models import StockDailyMarketData
from sqlalchemy import select, func

async def check():
    async with async_session_factory() as s:
        cnt = await s.scalar(select(func.count()).select_from(StockDailyMarketData))
        print(f'stock_daily_market_data count: {cnt}')
asyncio.run(check())
"

# 3. 级联删除验证
pytest tests/test_data_init.py -v -k "cascade or cleanup"
```

## 7. 交接上下文

- **架构章节**: §6.1 链路 L1（行情采集）、§6.2 链路 L2（均线计算）、§6.3 链路 L3（强度计算）、§6.5 链路 L5（级联删除）、ADR-4 共享工具内部分发、ADR-5 写入策略保持现状
- **相关代码**:
  - 写入入口：`services/data_updater/collector.py`、`services/data_init.py`、`services/data_update.py`
  - 均线：`services/stock_ma_service.py`
  - 强度：`services/strength_service_v2.py`
  - 级联删除：`services/data_init.py:700-735`
- **契约 / 数据对象**: 三新模型（plan-01 产出）；写入字段见实现规格
- **下游消费方**: plan-03（读取路径切换）依赖本功能写入的新表数据

## 8. 风险与边界

- **执行顺序**: 按 Task 列表顺序；Task #7（_save_strength_score 分发）是最复杂的共享方法改动，建议放最后并仔细测试板块分支
- **验证失败排查方向**:
  - 采集报错 `constraint "uq_..." does not exist`：检查约束名是否同步换新表
  - 写入报错 `column "entity_type" does not exist`：遗漏去 entity_type
  - 写入报错 `column "stock_id" does not exist`：迁移未跑或模型未注册
  - 板块强度写错表：_save_strength_score 分发逻辑分支错误
- **允许修改的额外文件**: 无（仅清单内 6 个文件；result_saver 经核对不涉及，已从清单移除）
- **暂停条件**: 共享方法 _save_strength_score 改动后板块测试大面积失败且无法在 1 次排查内解决
- **E2E 不适用说明**: 本功能是数据写入层改造，无直接用户可观察界面，但**涉及 task handler 的执行验证不可豁免**（见 §5 执行验证项）
- **风险备注**:
  - 最大风险是 _save_strength_score 共享方法误伤板块分支（ADR-4）；对策：改动后必须触发一次板块强度计算确认旧表有新增
  - 约束名同步是高频踩坑点，每个 on_conflict_do_nothing 都要核对

### 后端边界场景

| 场景 | 处理方式 | 状态 |
|---|---|---|
| 共享方法 _save_strength_score 误伤板块分支 | ADR-4 内部分发；改动后板块测试 57/57 零回归 + 代码核查 sector 分支仍用 StrengthScore | done |
| 采集重复触发（幂等性） | on_conflict_do_nothing 保持幂等；新表唯一约束 (stock_id, date) 保证（已实测二次插入不覆盖） | done |
| 级联删除误删板块数据 | 三元组遍历只删 stock_id；旧表板块 entity_type='sector' 数据天然不受影响 | done |
| 约束名遗漏同步 | 每个 on_conflict_do_nothing 强制核对实现规格中的新约束名（3 处全部用 uq_stock_daily_market_data_stock_date） | done |
| 批量写入超时 | 分批 commit 保持不变（batch_size=50/500），与改造前一致 | done |
