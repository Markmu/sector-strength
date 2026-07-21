---
feat_id: "plan-03"
title: "股票读取路径切换"
dimension: backend
phase: 3
status: done
depends_on: ["plan-02"]
---

# plan-03 股票读取路径切换

## 1. 功能概要

- **目标**: 把所有读取 `entity_type='stock'` 数据的代码路径切换到三张新表，使个股接口与计算逻辑从新表读取数据
- **完成后可观察结果**: 调用个股相关 API（个股强度、个股排名、个股强度历史、强度统计 stock 类型）返回的数据来源于新表，行为与改造前一致。个股强度计算（fallback 重算）能从新表读行情与均线数据。长周期指标（如 ma240）在新表无数据时返回空，按"数据不足"方式呈现，前端无报错。板块所有读路径完全不受影响（仍读旧表）
- **依赖**: plan-02（写入路径已切换，新表有数据）
- **关联验收标准**: [AC-02, AC-07]
- **涉及架构模块**: MADataLoader、StockMAService（读部分）、StrengthServiceV2（读部分）、RankingService、StrengthHistoryService、StrengthSnapshotService、data_quality 读分支、API 股票端点
- **前置条件**: plan-02 task-review 通过；新表已有采集数据
- **不在范围**: 写入路径（plan-02 已完成）；测试修复（plan-04）；板块代码改动

## 2. 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
|---|---|---|
| modify | `server/src/services/calculation/ma_system/ma_data_loader.py` | load_ma_values/load_current_price/load_data_for_calculation/_get_available_days 按 entity_type 内部分发 |
| modify | `server/src/services/stock_ma_service.py` | 全部 select（断点续传/查重/最新值）切新表 |
| modify | `server/src/services/strength_service_v2.py` | 读分支（_get_symbol、_save_strength_score 内的 select 查重等）切新表 |
| modify | `server/src/services/ranking_service.py` | calculate_rankings 循环内按 entity_type 选模型 |
| modify | `server/src/services/strength_history_service.py` | stock 分支（约 60 行）切新表，sector 分支（约 118 行）不动 |
| modify | `server/src/services/strength_snapshot_service.py` | stock 快照循环（100-141）+ _update_ranks_and_percentiles（322-378）按 entity_type 分发 |
| modify | `server/src/services/monitoring/data_quality.py` | `_check_invalid_strength_scores`（289-310）股票分支切新表 |
| modify | `server/src/api/v1/rankings.py` | v2 个股排名（173-238）+ v2 stats（306-341）stock 分支 + batch-calculate（392-404）切新表 |
| modify | `server/src/api/v1/stocks.py` | 个股强度查询（251-265）+ fallback 重算（267-277）切新表 |
| modify | `server/src/api/v1/strength.py` | `_build_strength_data`（31-112）stock 分支切新表 |

## 3. 实现规格

### 后端部分

#### 1. MADataLoader（`services/calculation/ma_system/ma_data_loader.py`，最易误伤板块）

**`load_ma_values`（57-162）**：
现状：子查询 + 主查询都用 `MovingAverageData.entity_type == entity_type`、`MovingAverageData.entity_id == entity_id`。

改造（ADR-4 内部分发）：
```python
from src.models import MovingAverageData, StockMovingAverageData
Model = StockMovingAverageData if entity_type == "stock" else MovingAverageData
id_field = Model.stock_id if entity_type == "stock" else Model.entity_id
# 子查询与主查询全部用 Model + id_field 替换
```
period 字段：均线表 period 是真实业务字段（'5d'/'10d'...），stock 与 sector 表都保留，**无需特殊处理**。

**`load_current_price`（164-202）**、**`_get_available_days`（239-274）**：同样按 entity_type 在 `DailyMarketData` 与 `StockDailyMarketData` 之间分发。

**缓存 key**：`_make_cache_key`（43-55）返回 `f"{entity_type}:{entity_id}:{calc_date}"`，**保持不变**（ADR：缓存 key 命名不动）。

**重点测试**：本方法是共享工具，同时服务 stock 与 sector。改完必须跑两套数据验证。

#### 2. StockMAService 读部分（`stock_ma_service.py`）

断点续传查询（约 213-241，查 max date）、查重 select（约 295-305）、最新值查询（约 400）等全部把 `MovingAverageData` 换 `StockMovingAverageData`，where 条件去 entity_type，entity_id→stock_id。

#### 3. StrengthServiceV2 读部分（`strength_service_v2.py`）

- `_get_symbol`（406-433）：stock 分支取 `Stock.symbol`，**不涉及三表，无需改**
- `_save_strength_score` 内的 select 查重：plan-02 已切（按 entity_type 分发）
- `calculate_and_update_change_rate`（489-585）内的 select：plan-02 已切
- 其他读方法（如 `_calculate_single`、`batch_calculate`）：核对是否有直接 select StrengthScore，按 entity_type 分发

#### 4. RankingService（`ranking_service.py:35-114`）

现状：
```python
for entity_type in entity_types:  # ['stock', 'sector']
    stmt = select(StrengthScore).where(entity_type == entity_type, date == calc_date, period == 'all', score.isnot(None))
    ...
    for i, score in enumerate(sorted_scores):
        score.rank = rank
        score.percentile = round((1 - rank / total) * 100, 2)  # line 91
```

改造：循环内按 entity_type 选模型：
```python
from src.models import StrengthScore, StockStrengthScore
Model = StockStrengthScore if entity_type == "stock" else StrengthScore
stmt = select(Model).where(Model.date == calc_date, Model.score.isnot(None))
if entity_type == "stock":
    stmt = stmt.where(...)  # stock 表无 period 列
else:
    stmt = stmt.where(Model.period == 'all')
```
percentile setattr（line 91）保持不变——新表已有 percentile 列（plan-01 保证）。

#### 5. StrengthHistoryService（`strength_history_service.py`）

`get_stock_history`（stock 分支约 60 行）：select 换 `StockStrengthScore`，where 去 entity_type，entity_id→stock_id，去 period=='all' 条件（stock 表无 period）。

`get_sector_history`（约 118 行）**完全不动**。

#### 6. StrengthSnapshotService（`strength_snapshot_service.py`）

- stock 快照循环（100-141）：select 换 `StockStrengthScore`
- sector 快照循环（143-189）：不动
- `_update_ranks_and_percentiles`（322-378）：含 percentile 写库逻辑，按 entity_type 分发模型

#### 7. data_quality 读分支（`monitoring/data_quality.py:289-310`）

`_check_invalid_strength_scores` 股票分支：select 换 `StockStrengthScore`。sector 分支不动。

#### 8. API 股票端点

**`api/v1/rankings.py`**：
- `get_stock_rankings_v2`（173-238）：`select(StrengthScoreModel, StockModel).join(...).where(entity_type=='stock', period=='all')` → `select(StockStrengthScoreModel, StockModel).join(...)`（去 entity_type/period 条件）
- `get_strength_stats`（306-341）：entity_type 参数为 'stock' 时查新表，'sector' 时查旧表；内部分发
- `batch_calculate_strength`（392-404）：硬编码 entity_type='stock'，调 StrengthServiceV2.batch_calculate（已在 plan-02 切新表）

**`api/v1/stocks.py:251-277`**：
- `strength_stmt`：`select(StrengthScoreModel).where(entity_type=='stock', entity_id==stock.id, period=='all')` → `select(StockStrengthScoreModel).where(stock_id==stock.id)`
- fallback（267-277）：调 `StrengthServiceV2.calculate_stock_strength`，已切新表

**`api/v1/strength.py:31-112`**（`_build_strength_data`）：
- stock 分支：select MovingAverageData / StrengthScore 换新表模型
- sector 分支：不动

**响应 schema 不动**：所有响应继续用 `StockStrengthResponse` / `StrengthRankingResponse` 等 schema，`entity_type` 字段硬填 "stock"（AC-06）。前端零依赖 entity_type（已确认 web/src 0 命中）。

## 4. Task 列表

| # | Task | 维度 | 状态 | 说明 |
|---|---|---|---|---|
| 1 | MADataLoader 四方法按 entity_type 内部分发 | backend | done | load_ma_values/load_current_price/_get_available_days 内部分发；板块测试 44/44 零回归 |
| 2 | StockMAService 全部 select 切新表 | backend | done | plan-02 已切全部 select；本期仅清理未用 import |
| 3 | StrengthServiceV2 读分支切新表 | backend | done | plan-02 已切 _save_strength_score/calculate_and_update_change_rate；核对无其他直接 select StrengthScore 读路径 |
| 4 | RankingService 循环内按 entity_type 选模型 | backend | done | calculate_rankings 内部分发；percentile setattr(line 91) 保持不变，直查验证写入成功 |
| 5 | StrengthHistoryService stock 分支切新表 | backend | done | get_stock_history/get_history_stats/get_latest_score 切新表；get_sector_history 不动 |
| 6 | StrengthSnapshotService stock 循环 + _update_ranks 分发 | backend | done | _update_ranks_and_percentiles + get_snapshot_status stock 分支切新表；sector 分支不动 |
| 7 | data_quality._check_invalid_strength_scores 股票分支切新表 | backend | done | 股票分支查 StockStrengthScore；sector 分支（查 Sector 表）不动 |
| 8 | rankings.py 个股排名 + stats stock 分支切新表 | backend | done | get_stock_rankings_v2 + get_strength_stats(stock) 切新表；get_sector_rankings_v2 不动；响应 schema 不动 |
| 9 | stocks.py 个股强度查询 + fallback 切新表 | backend | done | strength_stmt 切 StockStrengthScoreModel；响应 period='all'/change_rate_5d=None 硬填（AC-06） |
| 10 | strength.py _build_strength_data stock 分支切新表 | backend | done | stock 分支查 StockMovingAverageDataModel；sector 分支不动 |
| 11 | 验证个股接口返回新表数据 | backend | done | AC-02：SQLAlchemy 直查确认 stocks.py/rankings.py v2 查询命中 stock_strength_scores |
| 12 | 验证空窗期呈现（ma240 缺失返回空） | backend | done | AC-07：load_ma_values 在新表无 ma240 时返回 dict 不含 240 键 |

## 5. 验收标准

### 功能验收

- [ ] AC-02：调用 `GET /api/v1/stocks/{stock_id}/strength` 返回数据来源于 `stock_strength_scores`（可在 SQL 日志确认查询表名）
- [ ] AC-02：调用 `GET /api/v1/rankings/v2/stocks` 返回数据来源于新表，分页/排序行为与改造前一致
- [ ] AC-02：调用 `GET /api/v1/rankings/v2/stats?entity_type=stock` 返回数据来源于新表
- [ ] AC-02：个股强度 fallback 重算能从 `stock_daily_market_data` / `stock_moving_average_data` 读数据
- [ ] AC-07：新表无 ma240 数据时，`ma_data_loader.load_ma_values` 返回的 dict 不含 240 键，调用方按"数据不足"方式呈现，前端无报错
- [ ] RankingService.percentile setattr（line 91）能正常写入新表 percentile 列（无 "column does not exist" 错误）
- [ ] 响应字段名、类型、结构与改造前一致（AC-06 的前置，正式核对在 plan-04）
- [ ] 板块所有读路径完全不受影响（plan-05 正式回归验证）

### 性能验收（架构 §8.1 目标）

- [ ] 个股强度接口响应时间与改造前持平（去 entity_type 段反而更精简，预期不退化）

### 后端边界场景验收

- [ ] MADataLoader 改动后，板块查询（entity_type='sector'）仍读旧表 `moving_average_data` / `daily_market_data`，行为不变
- [ ] RankingService 改动后，板块排名（entity_type='sector'）仍读旧表 `strength_scores`，行为不变

## 6. 验证命令

```bash
cd server
source .venv/bin/activate

# 1. 共享方法测试（最易误伤板块）
pytest tests/services/test_sector_ma_service.py -v  # 板块 MA 不回归
pytest tests/services/test_strength_snapshot_service.py -v
pytest tests/services/test_strength_scatter_service.py -v

# 2. 个股接口测试
pytest tests/test_strength_api.py tests/test_api/test_stocks_api.py tests/test_api/test_rankings_heatmap_api.py -v

# 3. 手动 API 验证（启动服务后）
# curl http://localhost:8000/api/v1/stocks/{stock_id}/strength
# curl http://localhost:8000/api/v1/rankings/v2/stocks
# curl 'http://localhost:8000/api/v1/rankings/v2/stats?entity_type=stock'
# 对比改造前后响应字段

# 4. percentile 列写入验证（触发排名计算后）
python -c "
import asyncio
from src.db.session import async_session_factory
from src.models import StockStrengthScore
from sqlalchemy import select

async def check():
    async with async_session_factory() as s:
        result = await s.execute(select(StockStrengthScore.percentile).where(StockStrengthScore.percentile.isnot(None)).limit(1))
        row = result.first()
        print(f'percentile written: {row}')
asyncio.run(check())
"
```

## 7. 交接上下文

- **架构章节**: §6.3 链路 L3（强度计算与排名）、§6.4 链路 L4（API 直查）、ADR-4 共享工具内部分发
- **相关代码**:
  - 共享工具：`services/calculation/ma_system/ma_data_loader.py`、`services/ranking_service.py`、`services/strength_history_service.py`、`services/strength_snapshot_service.py`
  - API：`api/v1/rankings.py`、`api/v1/stocks.py`、`api/v1/strength.py`
- **契约 / 数据对象**: 响应 schema（`api/schemas/strength.py`）不动；新模型类（plan-01）
- **下游消费方**: plan-04（测试修复）依赖本功能读路径完整切换；plan-05（板块回归）依赖共享方法未误伤板块

## 8. 风险与边界

- **执行顺序**: Task #1（MADataLoader）是最易误伤板块的共享方法，建议优先做并立即跑板块 MA 测试；其余按 Task 列表顺序
- **验证失败排查方向**:
  - 板块查询误读新表：MADataLoader/RankingService 分发逻辑 entity_type 分支写反
  - 个股接口报错 `column "period" does not exist`：StockStrengthScore 查询带了 period=='all' 条件但新表无 period 列
  - percentile 写入报错：plan-01 迁移遗漏 percentile 列，回 plan-01 修复
  - 响应字段缺失：核对响应 schema 是否保持 `entity_type="stock"` 等硬填字段
- **允许修改的额外文件**: 无（仅清单内 10 个文件）
- **暂停条件**: 板块测试大面积失败（说明共享方法误伤板块，违背 AC-03）；或 percentile 列问题需回退 plan-01
- **E2E 不适用说明**: 本功能通过 API 端到端验证（curl + 接口测试），属于可观察行为。完整 e2e 在 plan-04/05。
- **风险备注**:
  - 最大风险是 StockStrengthScore 无 period 列，所有 stock 分支查询**必须去掉** `period=='all'` 条件，否则报错
  - 共享方法误伤板块是第二大风险，每个共享方法改完立即跑板块测试

### 后端边界场景

| 场景 | 处理方式 | 状态 |
|---|---|---|
| StockStrengthScore 查询带 period 条件报错 | stock 分支去 period=='all'；sector 分支保留 | done |
| MADataLoader 误伤板块 | ADR-4 内部分发；改完立即跑 test_sector_ma_service | done |
| 新表无 ma240 数据（空窗期） | load_ma_values 返回 dict 不含 240 键，调用方呈现"数据不足"（AC-07） | done |
| percentile 列写入失败 | plan-01 保证迁移含 percentile 列；本功能 setattr 保持不变 | done |
| 个股接口 fallback 重算循环 | fallback 逻辑（stocks.py:267-277）保持不变，仅切新表读写 | done |
| 板块查询误读新表 | RankingService/StrengthHistoryService 等的 sector 分支完全不动 | done |
