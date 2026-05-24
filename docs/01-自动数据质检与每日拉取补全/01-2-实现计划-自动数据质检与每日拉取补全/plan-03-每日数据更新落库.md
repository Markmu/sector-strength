---
feat_id: "plan-03"
title: "每日数据更新落库"
dimension: backend
phase: 2
status: done
depends_on: ["plan-01"]
---

# plan-03: 每日数据更新落库

## 1. 功能概要

- **目标**: 补全 DataCollector 的完整每日数据更新流程，使交易日收盘后自动完成板块同步 → 股票同步 → 行情拉取保存 → 计算触发的完整闭环，数据正确写入数据库。
- **完成后可观察结果**: 交易日 15:30 定时任务触发后，DataCollector 自动完成全流程：板块列表与数据库对比后新增/更新、股票列表与数据库对比后新增/更新、所有股票（不限前 10 只）的当日行情数据批量写入 DailyMarketData 表、均线和强度计算完成、缓存清除。非交易日正确跳过并记录原因到 DataUpdateLog。任一步骤失败时后续步骤中止，任务标记为 failed 并记录错误。
- **依赖**: plan-01（TradingCalendar 服务，用于交易日判断）
- **关联验收标准**: [AC-01, AC-02, AC-03, AC-06]
- **涉及架构模块**: DataCollector, TradingCalendar, AkShareDataSource, CalculationOrchestrator
- **前置条件**: plan-01 完成，TradingCalendar 服务可用；PostgreSQL 运行中；AkShare 可调用
- **不在范围**: 数据完整性检测与自动补齐（plan-04 负责）；告警通知；前端管理界面改造

## 2. 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| modify | `server/src/services/data_updater/collector.py` | 核心改造：集成 TradingCalendar + 补全落库逻辑 + 异常传播 |

## 3. 实现规格

### 后端部分

#### 1. DataCollector 集成 TradingCalendar

在 `DataCollector.__init__()` 中初始化 TradingCalendar：

```python
from src.services.trading_calendar import TradingCalendar

class DataCollector:
    def __init__(self):
        self._trading_calendar = TradingCalendar()
```

改造 `_is_trading_day()`：
- 删除现有简单周末判断 + TODO 注释
- 改为调用 `self._trading_calendar.is_trading_day(check_date)`
- 返回值从 `bool` 改为 `tuple[bool, str | None]`

改造 `run_daily_update()` 中调用 `_is_trading_day()` 的部分：
- 接收 `(is_trading, reason)` 元组
- 非交易日时：`log_entry.error_message = reason`，status 设为 `skipped`

#### 2. 补全 _update_sectors() 落库逻辑

当前问题（collector.py `_update_sectors`）：遍历板块只计数不写入，有 `# TODO: 更新板块数据到数据库` 注释。

改造内容：
- 获取 AkShare 板块列表
- 查询数据库已有板块：`select(Sector)` → 构建 `{code: Sector}` 映射
- 遍历板块列表：
  - 已存在（code 匹配）：比较 name 是否变化，变化则更新
  - 不存在：创建新 Sector 记录（code, name, type）
- 批量提交（每 100 条 flush 一次减少内存占用）
- 返回新增 + 更新的板块总数
- **异常传播**：删除 try-except 中 `return 0` 的做法，改为 `raise` 让异常向上传播

关键实现：
```python
existing_map = {s.code: s for s in (await session.execute(select(Sector))).scalars().all()}
for info in sectors:
    if info.code in existing_map:
        if existing_map[info.code].name != info.name:
            existing_map[info.code].name = info.name
    else:
        session.add(Sector(code=info.code, name=info.name, type=info.type))
await session.commit()
```

#### 3. 补全 _update_stocks() 落库逻辑

当前问题（collector.py `_update_stocks`）：遍历股票只计数不写入，有 `# TODO: 更新股票数据到数据库` 注释。

改造内容：
- 获取 AkShare 股票列表（返回 `List[StockInfo]`，含 symbol, name, market, industry）
- 查询数据库已有股票：`select(Stock)` → 构建 `{symbol: Stock}` 映射
- 遍历股票列表：
  - 已存在（symbol 匹配）：比较 name 是否变化，变化则更新
  - 不存在：创建新 Stock 记录
- 批量提交
- **异常传播**：同上，失败时 raise 而非 return 0

#### 4. 补全 _update_market_data() 落库逻辑

当前问题（collector.py `_update_market_data`）：`list(symbols)[:10]` 只处理前 10 只；有 `# TODO: 保存到 DailyMarketData 表` 注释。

改造内容：
- **删除 `[:10]` 限制**，遍历所有股票
- 新增板块行情拉取：遍历所有板块，调用 `data_source.get_sector_daily_data(sector_name, sector_type, today, today)`
- 股票行情按批次处理（每批 50 只），调用 `data_source.get_daily_data(symbol, today, today)`
- 写入 DailyMarketData：
  - 板块行情：entity_type='sector'，entity_id=板块的数据库 id，symbol=板块 code
  - 股票行情：entity_type='stock'，entity_id=股票的数据库 id，symbol=股票代码
  - 需要先从数据库查出 entity_id（通过 symbol/code 映射）
  - 使用 INSERT ... ON CONFLICT DO NOTHING（利用已有的 `(entity_type, entity_id, date)` 唯一约束）
- 计算 change 和 change_percent（如 DailyQuote 未提供）
- **部分失败处理（L2 降级）**：单只股票拉取失败时跳过继续，记录 warning 日志
- **整体失败**：所有股票都失败时抛出异常
- 遵守速率限制（AkShareDataSource._enforce_rate_limit() 内部已处理 500ms 间隔）

批量写入实现思路：
```python
from sqlalchemy.dialects.postgresql import insert

stmt = insert(DailyMarketData).values(batch_values)
stmt = stmt.on_conflict_do_nothing(
    constraint='uq_daily_market_data_entity_date'
)
await session.execute(stmt)
```

计算触发与缓存清除：`_update_market_data()` 完成后，`run_daily_update()` 的后续步骤（调用 CalculationOrchestrator 执行均线和强度计算、清除相关缓存）沿用现有框架，无需新增代码。

#### 5. 异常传播改造

当前问题（collector.py `_update_sectors` L169, `_update_stocks` L195）：catch 异常后 `return 0`，不向上传播，导致后续步骤继续执行。

改造内容：
- `_update_sectors()` 和 `_update_stocks()`：删除内部 try-except（或改为 raise），让异常传播到 `run_daily_update()` 的外层 try-except
- `run_daily_update()` 的外层 try-except 已有正确处理：捕获异常 → status='failed' → 记录 error_message
- 确保异常消息包含上下文（如 `f"[数据更新] 板块更新失败: {e}"`）

**可观测性（架构 §8.4）**: 每个步骤完成时记录 info 日志（板块数、股票数、行情条数、计算数）；失败时记录 error 日志含具体原因。DataUpdateLog 写入完整统计信息。

## 4. Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | DataCollector 集成 TradingCalendar | backend | done | __init__ 初始化 + _is_trading_day 改造 + run_daily_update 非交易日处理 |
| 2 | 补全 _update_sectors() 落库逻辑 | backend | done | 查询已有板块 → 对比 → 新增/更新 → 批量提交 |
| 3 | 补全 _update_stocks() 落库逻辑 | backend | done | 查询已有股票 → 对比 → 新增/更新 → 批量提交 |
| 4 | 补全 _update_market_data() 落库逻辑 | backend | done | 删除 [:10] 限制 + 新增板块行情 + 批量写入 ON CONFLICT DO NOTHING |
| 5 | 异常传播改造 | backend | done | _update_sectors/_update_stocks 失败时 raise 而非 return 0 |

## 5. 验收标准

### 功能验收

- [x] AC-01 交易日执行每日更新后，Sector 表新增板块已插入、已有板块名称已更新
- [x] AC-01 交易日执行每日更新后，Stock 表新增股票已插入、已有股票信息已更新
- [x] AC-01 交易日执行每日更新后，DailyMarketData 表有当日板块和个股行情数据
- [x] AC-01 交易日执行每日更新后，均线和强度计算已触发（通过 CalculationOrchestrator）
- [x] AC-01 交易日执行每日更新后，DataUpdateLog 记录了完整的更新统计
- [x] AC-02 非交易日执行每日更新时跳过，DataUpdateLog.status = 'skipped'，error_message 记录具体原因
- [x] AC-03 调休工作日正常执行全流程（由 plan-01 的 TradingCalendar 保证）
- [x] AC-06 板块更新失败时后续股票/行情/计算步骤中止，任务标记为 failed
- [x] AC-06 部分股票行情拉取失败时跳过失败股票继续处理其余（L2 降级）

## 6. 验证命令

```bash
cd server
# 单元测试
pytest tests/ -v -k "data_collector or daily_update"
# 手动触发每日更新（需启动服务 + 数据库）
uvicorn server.main:app --port 8000 &
curl -X POST -H "api_key: <key>" http://localhost:8000/api/v1/admin/data/scheduler/trigger/daily_data_update
# 查询数据库确认数据写入
# SELECT count(*) FROM sectors;
# SELECT count(*) FROM stocks;
# SELECT count(*), date FROM daily_market_data GROUP BY date ORDER BY date DESC LIMIT 5;
```

## 7. 交接上下文

- **架构章节**: §4.2 模块职责（DataCollector）、§5 ADR-1、§6.1 每日自动更新链路
- **相关代码**: `server/src/services/data_updater/collector.py`、`server/src/models/sector.py`、`server/src/models/stock.py`、`server/src/models/daily_market_data.py`
- **契约 / 数据对象**:
  - Sector: `{code: unique, name, type('industry'/'concept')}`
  - Stock: `{symbol: unique, name}`
  - DailyMarketData: `{entity_type, entity_id, symbol, date, open, high, low, close, volume, ...}` + `(entity_type, entity_id, date)` 唯一约束
  - DataUpdateLog: `{status, sectors_updated, stocks_updated, market_data_updated, calculations_performed, error_message}`
- **下游消费方**: plan-04（DataQualityChecker 依赖 DailyMarketData 中的数据做质检）

## 8. 风险与边界

- **执行顺序**: Task 1 → Task 2 + Task 3（可并行）→ Task 4 → Task 5（与 Task 4 合并实施）
- **验证失败排查方向**: 检查 AkShare 接口是否正常返回数据、数据库连接是否正常、Sector/Stock 表是否有初始数据
- **允许修改的额外文件**: 无
- **暂停条件**: AkShare 接口大规模限流或返回异常数据
- **E2E 不适用说明**: 后端定时任务，无用户可观察 UI；通过 API 手动触发 + 数据库查询验证
- **风险备注**: 全量股票行情拉取约 5000 只 × 500ms = ~40 分钟，后续可优化为批量查询或并发

### 后端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| AkShare 板块接口失败 | 异常传播到 run_daily_update，任务标记 failed | done |
| AkShare 股票接口失败 | 异常传播到 run_daily_update，任务标记 failed | done |
| 单只股票行情拉取失败 | 跳过该股票，记录 warning，继续处理其余（L2 降级） | done |
| 所有股票行情都拉取失败 | 抛出异常，任务标记 failed | done |
| 数据库写入冲突（重复数据） | ON CONFLICT DO NOTHING 跳过 | done |
| DailyMarketData 写入时 entity_id 不存在 | 需先查 Sector/Stock 表获取 id，若不存在则跳过 | done |
| 超时（30 分钟未完成） | 异步任务系统已有超时机制 | done |
| 空数据库（无板块/股票初始数据） | 板块同步和股票同步会先创建记录，行情数据依赖这些记录的 id | done |
