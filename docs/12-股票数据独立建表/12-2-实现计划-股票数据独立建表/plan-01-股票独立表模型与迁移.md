---
feat_id: "plan-01"
title: "股票独立表模型与迁移"
dimension: backend
phase: 1
status: done
depends_on: []
---

# plan-01 股票独立表模型与迁移

## 1. 功能概要

- **目标**: 新建三张股票独立表（行情/均线/强度）的 SQLAlchemy 模型与 alembic 迁移，作为后续读写切换的基础设施
- **完成后可观察结果**: `alembic upgrade head` 后，PostgreSQL 中新增三张表 `stock_daily_market_data` / `stock_moving_average_data` / `stock_strength_scores`，字段、约束、索引完整。`alembic downgrade -1` 可干净回滚（三张表删除）。旧三表结构与数据完全不变。新模型可被 `from src.models import StockDailyMarketData, StockMovingAverageData, StockStrengthScore` 正常导入
- **依赖**: 无（基础设施工能）
- **关联验收标准**: [AC-01（新表建立部分）, AC-05]
- **涉及架构模块**: 新表模型层
- **前置条件**: PostgreSQL 服务可用；alembic 当前 head 为 `687ec547d98e`
- **不在范围**: 任何读写路径切换（plan-02/03）；测试修复（plan-04）

## 2. 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
|---|---|---|
| create | `server/src/models/stock_daily_market_data.py` | StockDailyMarketData 模型 |
| create | `server/src/models/stock_moving_average_data.py` | StockMovingAverageData 模型 |
| create | `server/src/models/stock_strength_scores.py` | StockStrengthScore 模型（含 percentile 列） |
| modify | `server/src/models/__init__.py` | 注册三个新模型（import + __all__） |
| create | `server/alembic/versions/2026_07_07_HHMM-<rev>_add_stock_independent_tables.py` | 手写建表迁移，down_revision='687ec547d98e' |
| create | `server/tests/test_stock_models.py` | 三新模型单元测试 |

## 3. 实现规格

### 后端部分

#### 1. StockDailyMarketData 模型（参照 `models/daily_market_data.py`）

`__tablename__ = "stock_daily_market_data"`

字段（精度/注释与旧表一致）：
- `id` Integer PK autoincrement
- `stock_id` Integer not null index（原 `entity_id` 改名，指向 stocks.id，**不加外键约束**）
- `symbol` String(20) not null index
- `date` Date not null index
- `open/high/low/close` Numeric(10,2)
- `volume/turnover` Numeric(15,2)
- `change` Numeric(10,2)
- `change_percent` Numeric(10,4)
- `created_at` DateTime(tz) server_default now()

去除：`entity_type` 列

`__table_args__`：
- `UniqueConstraint('stock_id', 'date', name='uq_stock_daily_market_data_stock_date')`
- `CheckConstraint('high >= low', name='check_stock_dmd_high_low')`
- `CheckConstraint('volume >= 0', name='check_stock_dmd_volume_positive')`
- 索引（参照旧表去掉 entity_type 段）：`idx_stock_dmd_stock_date(stock_id, date)`、`idx_stock_dmd_date_range(date, close, volume)`、`idx_stock_dmd_symbol_date(symbol, date)`

#### 2. StockMovingAverageData 模型（参照 `models/moving_average_data.py`）

`__tablename__ = "stock_moving_average_data"`

字段：
- `id` Integer PK
- `stock_id` Integer not null index
- `symbol` String(20) not null index
- `date` Date not null index
- `period` String(10) not null index（**保留**：均线表 period 是真实业务字段 '5d'/'10d' 等）
- `ma_value` Numeric(10,2)
- `price_ratio` Numeric(10,4)
- `trend` Numeric(5,2)
- `created_at` DateTime(tz) server_default now()

去除：`entity_type`

`__table_args__`：
- `UniqueConstraint('stock_id', 'symbol', 'date', 'period', name='uq_stock_moving_average_data_stock_date_period')`
- 索引：`idx_stock_mad_stock_date`、`idx_stock_mad_symbol_date`、`idx_stock_mad_date_period`、`idx_stock_mad_stock_period`、`idx_stock_mad_symbol_period`、`idx_stock_mad_date_desc`

#### 3. StockStrengthScore 模型（参照 `models/strength_score.py`，**最关键**）

`__tablename__ = "stock_strength_scores"`

字段（照搬旧表个股相关字段，**显式新增 percentile 列**）：
- `id` Integer PK
- `stock_id` Integer not null index（原 entity_id 改名）
- `symbol` String(20) not null index
- `date` Date not null index
- `score` Numeric(10,4) not null comment '综合强度得分(0-100)'
- `rank` Integer
- `change_rate` Numeric(10,4) default 0
- `strength_level` String(20)
- `price_position_score` / `ma_alignment_score` Numeric(10,2)
- `ma_alignment_state` String(20)
- `short_term_score` / `medium_term_score` / `long_term_score` Numeric(10,2)
- `current_price` Numeric(10,2)
- `ma5/ma10/ma20/ma30/ma60/ma90/ma120/ma240` Numeric(10,2)
- `price_above_ma5/10/20/30/60/90/120/240` Integer
- `change_rate_1d` Numeric(5,2)
- `strength_grade` String(3)
- `ma5_score/ma10_score/ma20_score/volume_score/momentum_score` Numeric(10,4)（**个股死字段照搬**，当前无写入但保留 schema 完整性）
- `percentile` Numeric(10,4)（**ADR-3 关键**：旧表模型未定义但 ranking_service.py:91 setattr + strength_snapshot_service.py:342/363 写库，DB 必须有列）
- `created_at` / `updated_at` DateTime(tz)

去除：
- `entity_type` 列
- `period` 列（已废弃、恒为 'all'）
- **板块专属字段**：`avg_stock_score` / `strong_stock_ratio` / `up_stock_ratio` / `volume_ratio`

`__table_args__`：
- `CheckConstraint('score >= 0 AND score <= 100', name='chk_stock_strength_score_range')`
- `CheckConstraint('price_above_ma5 IN (0, 1)', ...)` ~ `price_above_ma240`（8 条，照搬）
- **新增唯一约束**：`UniqueConstraint('stock_id', 'date', name='uq_stock_strength_scores_stock_date')`（旧表无，借此硬化去重）
- 索引：`idx_stock_strength_symbol_date(symbol, date DESC)`、`idx_stock_strength_score_desc(score DESC, date DESC)`、`idx_stock_strength_date(date)`、`idx_stock_strength_rank(rank)`、`idx_stock_strength_score(score)`

#### 4. 注册模型

`server/src/models/__init__.py`：
- 第 8-9 行后追加三个 import：`from .stock_daily_market_data import StockDailyMarketData` 等
- `__all__` 列表追加 `"StockDailyMarketData"` 等

#### 5. alembic 迁移（参照 `2026_06_10_2119-..._add_top10_float_holders_table.py` 手写风格）

文件名：`2026_07_07_HHMM-<rev>_add_stock_independent_tables.py`（HHMM 用实际生成时间，rev 用 `alembic revision` 自动生成的 12 位 hex）

- `revision = '<rev>'`，`down_revision = '687ec547d98e'`
- `upgrade()`：三张表 `op.create_table(...)` + `sa.Column(..., comment=...)` + 表内 `sa.UniqueConstraint` / `sa.CheckConstraint` + 表外 `op.create_index(...)`
- `downgrade()`：逆序 `op.drop_index` + `op.drop_table`
- **禁止用 autogenerate**（ADR-6）：手写，仅含三张新表，避免夹带既有 DB 与模型不同步噪音

**关键自检**：迁移中 StockStrengthScore 的 `op.create_table` 必须包含 `sa.Column('percentile', sa.Numeric(precision=10, scale=4), nullable=True)`，否则下游 plan-03 的 ranking_service 写个股排名时会因 DB 无此列报错（ADR-3）。

#### 6. 模型单元测试

`server/tests/test_stock_models.py`：
- 测三模型 `__tablename__` 正确
- 测 StockStrengthScore 含 `percentile` 列（`assert hasattr(StockStrengthScore, 'percentile')` 或检查 `StockStrengthScore.__table__.columns`）
- 测新表无 `entity_type` 列、StockStrengthScore 无 `period` 列、无板块专属字段（`avg_stock_score` 等）
- 测基本 ORM 增删（用 pytest fixture 的内存 SQLite 或 postgresql）

## 4. Task 列表

| # | Task | 维度 | 状态 | 说明 |
|---|---|---|---|---|
| 1 | 创建 stock_daily_market_data.py 模型 | backend | done | 字段/约束/索引按实现规格 #1 |
| 2 | 创建 stock_moving_average_data.py 模型 | backend | done | 按 #2 |
| 3 | 创建 stock_strength_scores.py 模型（含 percentile） | backend | done | 按 #3，percentile 列不可遗漏 |
| 4 | 在 models/__init__.py 注册三新模型 | backend | done | import + __all__ |
| 5 | 创建 alembic 迁移脚本（手写 op.create_table） | backend | done | down_revision='687ec547d98e'，含 percentile |
| 6 | 创建 test_stock_models.py 单元测试 | backend | done | 覆盖字段/约束/percentile |
| 7 | 运行 alembic upgrade head 验证 | backend | done | 三张表创建成功 |
| 8 | 运行 alembic downgrade -1 验证可逆 | backend | done | 三张表删除干净 |

## 5. 验收标准

### 功能验收

- [x] AC-01（部分）：`alembic upgrade head` 成功，三张新表 `stock_daily_market_data` / `stock_moving_average_data` / `stock_strength_scores` 在 DB 中创建
- [x] AC-05：StockStrengthScore 模型与迁移**含 percentile 列**（`grep percentile server/src/models/stock_strength_scores.py` 命中；迁移文件 `sa.Column('percentile', ...)` 存在）
- [x] AC-05：三新模型无 `entity_type` 列；StockStrengthScore 无 `period` 列、无 `avg_stock_score`/`strong_stock_ratio`/`up_stock_ratio`/`volume_ratio` 板块字段
- [x] 新表字段、精度、注释与旧表个股相关字段一一对应（实现规格逐字段核对）
- [x] `alembic downgrade -1` 可干净回滚（三表删除，旧表不受影响）
- [x] `from src.models import StockDailyMarketData, StockMovingAverageData, StockStrengthScore` 导入成功
- [x] test_stock_models.py 全部通过
- [x] 旧三表结构与既有板块数据零影响（`alembic upgrade` 后旧表无 schema 变更）

### 性能验收（架构 §8.1 目标）

- [x] 迁移 upgrade 在本地 DB 执行时间可接受（三张空表创建，预期 < 1s）

## 6. 验证命令

```bash
cd server
source .venv/bin/activate

# 1. 模型导入验证
python -c "from src.models import StockDailyMarketData, StockMovingAverageData, StockStrengthScore; print('import ok')"

# 2. percentile 列存在性验证
python -c "from src.models import StockStrengthScore; assert 'percentile' in StockStrengthScore.__table__.columns; print('percentile ok')"

# 3. 单元测试
pytest tests/test_stock_models.py -v

# 4. 迁移可逆性
alembic upgrade head
alembic current  # 确认指向新 revision
alembic downgrade -1
alembic upgrade head

# 5. 旧表未受影响（手动确认）
# psql 连 DB 检查 daily_market_data / moving_average_data / strength_scores 表结构无变化
```

## 7. 交接上下文

- **架构章节**: §7.2 推荐最小 Schema、ADR-3 字段裁剪规则、ADR-6 alembic 手写迁移
- **相关代码**:
  - 参照模型：`server/src/models/daily_market_data.py`、`moving_average_data.py`、`strength_score.py`
  - 新建范本：`server/src/models/top10_float_holder.py`
  - 迁移范本：`server/alembic/versions/2026_06_10_2119-2a1ba1aca13f_add_top10_float_holders_table.py`
- **契约 / 数据对象**: 见实现规格三个模型字段定义
- **下游消费方**: plan-02（写入路径）、plan-03（读取路径）都依赖三新模型类

## 8. 风险与边界

- **执行顺序**: 按 Task 列表顺序执行（模型 → 注册 → 迁移 → 测试 → 验证）
- **验证失败排查方向**:
  - 迁移失败：检查 down_revision 是否准确为 `687ec547d98e`（`alembic current` 确认）
  - percentile 缺失：grep 迁移文件与模型文件确认 `sa.Column('percentile', ...)` 存在
  - 导入失败：检查 `__init__.py` 是否补 import 与 __all__
- **允许修改的额外文件**: 无（仅清单内 6 个文件）
- **暂停条件**: 迁移 upgrade 报错且无法在 1 次排查内解决；或发现旧表 schema 被意外修改
- **E2E 不适用说明**: 本功能是数据基础设施层（ORM 模型 + DDL 迁移），无用户可观察行为，无 API/前端交互。验收以模型测试 + 迁移可逆性 + DB schema 检查为主，不适用 E2E。但下游 plan-02/03 完成后会有完整执行验证。
- **风险备注**: percentile 列是最大风险点（ADR-3），遗漏会导致 plan-03 ranking 写个股排名时 DB 报错；务必在本功能阶段就显式建模

### 后端边界场景

| 场景 | 处理方式 | 状态 |
|---|---|---|
| 迁移 upgrade 时旧表已有数据 | 新表是全新创建，不涉及旧表数据搬移，旧表数据天然不受影响 | todo |
| 迁移 downgrade 时新表已有数据 | downgrade 直接 drop 三张新表，会丢失新表数据（可接受，本功能阶段新表尚无业务数据） | todo |
| stock_id 无外键约束导致脏数据 | 与 top10_float_holders/broker_recommend 风格一致，业务层保证；本期不引入外键 | todo |
| percentile 列遗漏 | ADR-3 已显式声明，Task #3 与实现规格 #3 强制要求，测试 #6 覆盖 | todo |
