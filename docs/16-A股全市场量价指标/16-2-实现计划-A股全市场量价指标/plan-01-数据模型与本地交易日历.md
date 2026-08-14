---
feat_id: "plan-01"
title: "数据模型与本地交易日历"
dimension: backend
phase: 1
status: done
depends_on: []
---

# plan-01: 数据模型与本地交易日历

## 功能概要

- **目标**: 建立 `market_daily_metrics` 与 `trading_calendar_days` 两张业务支持表及 Alembic 迁移；扩展采集层新增 `get_trading_calendar_range(start, end)`（闭区间全量开/休市记录）；新建 `TradingCalendarRepository` 负责闭区间完整性校验与单批次原子 upsert，成为同步拆分、非交易日守卫和首页缺口轴的唯一日历入口。
- **完成后可观察结果**: 迁移执行后数据库出现两张新表；通过 `get_trading_calendar_range` 拉取任意闭区间可得到每个自然日一条的 `TradingCalendarEntry`（含开市/休市标记）；Repository 对部分、重复、越界的 Provider 响应拒绝提交，对合法响应单事务写入并以 `refresh_batch_id/refreshed_at` 标识批次；旧 `get_trading_calendar()` 调用方行为不变。后续同步任务与首页查询都只读本地表。
- **依赖**: 无
- **关联验收标准**: [AC-09]（非交易日守卫的数据基础）
- **涉及架构模块**: 采集与本地日历适配（架构 §4.2 模块 1）
- **前置条件**: 本地 PostgreSQL 可用（`server/tests/conftest.py` 拒绝 SQLite）；`TUSHARE_TOKEN` 有效（仅真实冒烟需要）。
- **不在范围**: daily/suspend_d/stock_basic 采集方法（plan-02）；汇总服务（plan-03）；首页查询（plan-06）。

## 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| create | `server/src/models/market_daily_metric.py` | MarketDailyMetric 日汇总模型 |
| create | `server/src/models/trading_calendar_day.py` | TradingCalendarDay 本地交易日历模型 |
| modify | `server/src/models/__init__.py` | 导出两个新模型 |
| create | `server/alembic/versions/2026_08_14_0001-<rev12>_add_market_metrics_and_calendar.py` | 两表迁移，`down_revision='7e3309ce89da'` |
| modify | `server/src/services/data_acquisition/models.py` | 新增 Pydantic `TradingCalendarEntry` |
| modify | `server/src/services/data_acquisition/base.py` | 新增抽象方法 `get_trading_calendar_range` |
| modify | `server/src/services/data_acquisition/tushare_client.py` | 实现 `get_trading_calendar_range`（旧 `get_trading_calendar()` 不动，见 tushare_client.py:155-175） |
| create | `server/src/services/trading_calendar_repository.py` | 闭区间校验 + 单批 upsert + 只读查询 |
| create | `server/tests/services/test_trading_calendar_repository.py` | Repository 校验/写入/查询测试 |

## 实现规格

### 后端部分

#### 1. MarketDailyMetric 模型（架构 §7.2）

表 `market_daily_metrics`，列全部带中文 comment（惯例见 `src/models/index_monitor.py`）：

- `id` Integer PK autoincrement
- `trade_date` Date，`UniqueConstraint(name='uq_market_daily_metrics_trade_date')` + `Index('idx_market_daily_metrics_trade_date', 'trade_date')`
- `volume_shares` Numeric(24,2)（股）、`amount_yuan` Numeric(24,2)（元）、`average_price` Numeric(16,4)（元，存 4 位）
- `expected_stock_count` / `daily_quote_count` / `suspended_stock_count` / `final_stock_count` Integer
- `created_at` DateTime(timezone=True) server_default=func.now()；`updated_at` DateTime(timezone=True) onupdate=func.now()
- `from .base import Base`（同 index_monitor.py 惯例）；带 `__repr__`

#### 2. TradingCalendarDay 模型（架构 §7.2 / §8.2-5）

表 `trading_calendar_days`：

- `id` Integer PK；`cal_date` Date unique（`uq_trading_calendar_days_cal_date`）
- `is_open` Boolean nullable=False
- `refresh_batch_id` String(36)（UUID，同批次同值）；`refreshed_at` DateTime(timezone=True)
- `Index('idx_trading_calendar_days_cal_date_is_open', 'cal_date', 'is_open')`

#### 3. Alembic 迁移

- 文件名 `2026_08_14_0001-<rev12>_add_market_metrics_and_calendar.py`，`revision` 自生成 12 位 hex，`down_revision='7e3309ce89da'`（当前 head，见 `server/alembic/versions/2026_08_13_2234-7e3309ce89da_add_index_basic_sort_order.py`）
- 逐表 `op.create_table` + `op.create_index`，列带 comment；downgrade 逆序 drop（范式照抄 `2026_08_10_0001-f92bfffc49c3_add_index_monitor_tables.py`）
- 不夹带无关 drift

#### 4. TradingCalendarEntry 契约（架构 §7.2）

`data_acquisition/models.py` 新增 Pydantic 模型：`TradingCalendarEntry { cal_date: date; is_open: bool }`。

#### 5. BaseDataSource 抽象扩展

`base.py` 新增抽象方法（与现有 `get_trading_calendar() -> List[date]` 并存，base.py:99-100 旧方法不动）：

```python
@abstractmethod
def get_trading_calendar_range(self, start_date: date, end_date: date) -> List[TradingCalendarEntry]:
    """闭区间全量开/休市记录，无 is_open 过滤"""
```

注意：仓库内仅 `TushareDataSource` 一个实现（`DataSourceFactory.create()`）。若测试替身继承 `BaseDataSource` 导致抽象方法破坏，为替身补最小实现（返回空列表即可），不削弱真实现。

#### 6. TushareDataSource.get_trading_calendar_range（架构 §6.2.1）

- 调用 `pro.trade_cal(exchange='SSE', start_date=YYYYMMDD, end_date=YYYYMMDD, fields='cal_date,is_open')`，**明确不传 `is_open` 过滤**；整个调用包在 `_execute_with_retry`（3 次退避）内
- 逐行映射为 `TradingCalendarEntry`（`cal_date` 字符串转 `date`，`is_open` 转 bool）
- 旧 `get_trading_calendar()`（L155-175）保持原样，本需求任何调用点不得使用

#### 7. TradingCalendarRepository（架构 §6.2.1 / §8.2-5 / §8.6 末行）

`class TradingCalendarRepository(session: AsyncSession)`，方法：

- `async refresh_range(start: date, end: date) -> tuple[int, int]`：
  1. 调 `DataSourceFactory.create().get_trading_calendar_range(start, end)`（Provider 失败直接抛，不提交、不改旧行）
  2. **内存集合严格校验**：闭区间每个自然日一一对应（`expected_days = (end-start).days+1`，行数相等且 `set(cal_date) == 全部自然日`）；无重复、无越界（日期在区间外）。任一不满足抛 `ValueError`（带缺失/重复/越界样本），不建任务、不执行日更
  3. 单事务内生成 `refresh_batch_id = uuid4()`、`refreshed_at = now()`，对区间全部自然日 `pg_insert(...).on_conflict_do_update(cal_date)` upsert（开/休市都写）
  4. 返回 `(open_count, closed_count)`；结构化日志：刷新范围、开/休市行数、refreshed_at（架构 §8.5）
- 只读查询（供 plan-03/05/06 复用）：`get_record(day)`、`get_trading_days(start, end) -> list[date]`（is_open=true 升序）、`get_recent_open_days(n) -> list[date]`（降序取 N 再反转升序）、`has_any_open_day() -> bool`
- **写侧禁止用旧批次降级**：Provider 失败/响应不完整时直接失败，旧行仅供读侧继续使用

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | 创建 MarketDailyMetric / TradingCalendarDay 模型并注册 `models/__init__.py` | backend | done | 列 comment / 唯一键 / 索引按实现规格 1-2 |
| 2 | 编写 Alembic 迁移（down_revision=7e3309ce89da） | backend | done | 双表 + 索引，upgrade/downgrade 对称 |
| 3 | 新增 TradingCalendarEntry 与 BaseDataSource 抽象方法 | backend | done | 修复可能的测试替身破坏 |
| 4 | 实现 get_trading_calendar_range | backend | done | trade_cal 无 is_open 过滤，_execute_with_retry 包裹 |
| 5 | 实现 TradingCalendarRepository.refresh_range 校验与单批 upsert | backend | done | 闭区间一一对应/无重复/无越界 |
| 6 | 实现 Repository 只读查询方法 | backend | done | get_record/get_trading_days/get_recent_open_days/has_any_open_day |
| 7 | 编写 test_trading_calendar_repository.py | backend | done | 覆盖合法刷新、部分/重复/越界拒绝、upsert 覆盖旧批、只读查询 |

## 验收标准

### 后端验收

- [ ] AC-09（数据基础）`refresh_range` 后本地表对闭区间每个自然日恰有一行，`get_record(休市日).is_open=False`；后续功能可据此跳过非交易日
- [ ] 部分响应（缺日）、重复行、越界行三种场景均抛错且**不提交任何行**，旧批次数据原样保留（架构 §8.2-5）
- [ ] 同一日期重复 `refresh_range` 为 upsert 覆盖，不产生重复行，`refresh_batch_id/refreshed_at` 更新为新批次
- [ ] Provider 抛错时 `refresh_range` 透传失败，不吞异常
- [ ] 旧 `get_trading_calendar()` 行为不变（现有测试回归通过）
- [ ] `alembic upgrade head` 成功且 `alembic downgrade -1` 可回退
- [ ] E2E 不适用：纯数据层功能，无用户可见界面；其用户可见效果由 plan-07 首页缺口轴与 plan-05 非交易日跳过间接验证

### 性能验收（架构 §8.1）

- [ ] `get_recent_open_days(250)` 只走 `cal_date/is_open` 索引（EXPLAIN 无 seq scan，测试断言查询行数 ≤250）

## 验证命令

```bash
cd server && source .venv/bin/activate

# 1. 迁移与模型注册
alembic upgrade head
python -c "from src.models import MarketDailyMetric, TradingCalendarDay; print('OK')"

# 2. Repository 单测（--no-cov 规避 pytest.ini 全局 80% 覆盖率门槛）
pytest tests/services/test_trading_calendar_repository.py -v --no-cov

# 3. 真实采集冒烟（需 TUSHARE_TOKEN；验证闭区间含开/休市全量记录）
python -c "
from datetime import date
from src.services.data_acquisition import DataSourceFactory
entries = DataSourceFactory.create().get_trading_calendar_range(date(2026,1,1), date(2026,1,10))
assert len(entries) == 10 and all(e.is_open in (True, False) for e in entries)
print('calendar range OK:', [(e.cal_date.isoformat(), e.is_open) for e in entries[:3]])
"

# 4. 旧方法回归
pytest tests/ -k "trading or calendar" -v --no-cov
```

## 交接上下文

- **架构章节**: §4.2 模块 1、§6.2.1、§7.2、§8.2-5、§8.5、§8.6
- **相关代码**: `server/src/models/index_monitor.py`（模型范式）、`server/alembic/versions/2026_08_10_0001-f92bfffc49c3_add_index_monitor_tables.py`（迁移范式）、`server/src/services/data_acquisition/tushare_client.py:155-175`（旧日历方法，勿改）
- **契约 / 数据对象**: `TradingCalendarEntry { cal_date, is_open }`；`MarketDailyMetricRecord`（架构 §7.2）
- **下游消费方**: plan-03（sync_date 日历守卫）、plan-05（路由刷新日历 + 非交易日拆分 + collector 日更守卫）、plan-06（最近 N 开市日左连接）
- **实现级补充项**: Repository 只读查询方法服务于 AC-09/AC-06（服务端交易日轴），非新造 AC

## 风险与边界

- **执行顺序**: 按 Task 列表顺序执行；迁移依赖模型定义
- **验证失败排查方向**: 迁移失败查 `down_revision` 是否指向当前 head `7e3309ce89da`；Repository 校验失败优先检查自然日集合构造（含起止两端）
- **允许修改的额外文件**: 测试替身若因新增抽象方法破坏，可为其补最小实现（返回空列表）
- **暂停条件**: 若发现 `BaseDataSource` 存在第二个真实实现（非测试替身），暂停并请求确认抽象方法放置方式
- **风险备注**: Tushare `trade_cal` 偶发缺行会直接导致任务不创建——这是架构 §8.2-5 有意行为，不要"宽容"部分响应

### 后端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| Provider 响应行数 < 自然日数 | 抛 ValueError，不提交 | done |
| Provider 响应含重复 cal_date | 抛 ValueError，不提交 | done |
| Provider 响应含区间外日期 | 抛 ValueError，不提交 | done |
| 闭区间仅 1 天（start==end） | 正常处理（日更路径依赖） | done |
| 二次刷新覆盖旧批次 | upsert 覆盖，batch_id 全量更新 | done |
