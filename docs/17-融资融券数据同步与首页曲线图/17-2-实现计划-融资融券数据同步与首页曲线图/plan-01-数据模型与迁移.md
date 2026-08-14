---
feat_id: "plan-01"
title: "数据模型与迁移"
dimension: backend
phase: 1
status: done
depends_on: []
---

# plan-01: 数据模型与迁移

## 功能概要

- **目标**: 建立 `market_margin_daily` 表模型与 Alembic 建表迁移，成为融资融券全市场日汇总的唯一存储（每交易日唯一一行，六指标 Numeric(20,2)）。**交易日历表 `trading_calendar_days` 已由 16 期 plan-01 交付，本期直接复用、不重建**。
- **完成后可观察结果**: 迁移执行后数据库出现 `market_margin_daily` 新表，含 trade_date 唯一约束与索引、六指标列与 created_at/updated_at；`from src.models import MarketMarginDaily` 可直接导入；`alembic downgrade -1` 可回退、再次 upgrade 可恢复。后续汇总服务（plan-03）、查询 API（plan-06）都只读写这张表。
- **依赖**: 无
- **关联验收标准**: 无直接承接（AC-1 聚合复算 / AC-2 幂等 upsert / AC-5 缺口查询的存储基础，由 plan-03/plan-06 验收）
- **涉及架构模块**: 数据模型与迁移（spec 代码地图"后端 — 新增"第 1/2 项，对应 16 期 plan-01 的模型部分）
- **前置条件**: 本地 PostgreSQL 可用；迁移链 head 为 `a7d2e9f4c1b8`。
- **不在范围**: 采集方法 `get_margin`（plan-02）；汇总服务与 upsert 逻辑（plan-03）；交易日历任何改动（16 期已交付，spec 明确仅复用）。

## 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| create | `server/src/models/market_margin_daily.py` | MarketMarginDaily 日汇总模型（仿 market_daily_metric.py） |
| modify | `server/src/models/__init__.py` | 导出 MarketMarginDaily（L33/L73 惯式旁追加） |
| create | `server/alembic/versions/2026_08_15_0002-<rev12>_add_market_margin_daily.py` | 建表迁移，`down_revision='a7d2e9f4c1b8'` |
| create | `server/tests/models/test_market_margin_daily_model.py` | 模型元数据断言测试（表/约束/列型） |

## 实现规格

### 后端部分

#### 1. MarketMarginDaily 模型（spec REQ-2）

表 `market_margin_daily`，仿 `server/src/models/market_daily_metric.py` 逐项对照（列全部带中文 comment）：

- `id` Integer PK autoincrement
- `trade_date` Date nullable=False，`UniqueConstraint(name='uq_market_margin_daily_trade_date')` + `Index('idx_market_margin_daily_trade_date', 'trade_date')`
- 六指标列全部 `Numeric(precision=20, scale=2)`、nullable=True：
  - `rzye` 融资余额（元）
  - `rqye` 融券余额（元）
  - `rzmre` 融资买入额（元）
  - `rzche` 融资偿还额（元）
  - `rqmcl` 融券卖出量（股）
  - `rzrqye` 两融合计余额（元；服务层重算 = rzye+rqye 之和，见 plan-03）
- `created_at` DateTime(timezone=True) server_default=func.now()；`updated_at` DateTime(timezone=True) server_default=func.now() + onupdate=func.now()
- `from .base import Base`；带 `__repr__`
- **注意（16 期 S1 教训）**：ORM `onupdate` 不会在 `on_conflict_do_update` 路径触发——updated_at 显式刷新由 plan-03 的 `_atomic_upsert` 在 `set_` 中写 `func.now()` 承担，模型层保持与 market_daily_metric.py 同款双机制即可
- tushare `margin` 返回的 `rqyl`（融券余量，股）**不入库**（spec REQ-2 存储字段不含 rqyl），在 plan-02 采集层保留原样、plan-03 聚合时丢弃

#### 2. models/__init__.py 注册

- `from .market_margin_daily import MarketMarginDaily`（与 L33 `MarketDailyMetric` 导入并列）
- `__all__` 列表追加 `"MarketMarginDaily"`（L73 旁）

#### 3. Alembic 迁移

- 文件名 `2026_08_15_0002-<rev12>_add_market_margin_daily.py`（spec 代码地图写 `2026_08_14_XXXX`，因迁移链 head 已推进至 `2026_08_15_0001-a7d2e9f4c1b8`，按文件名单调递增惯例顺延为 `2026_08_15_0002`，属命名偏离、链条事实以 `down_revision` 为准）
- `revision` 自生成 12 位 hex；`down_revision='a7d2e9f4c1b8'`
- `op.create_table('market_margin_daily', ...)` + `op.create_index('idx_market_margin_daily_trade_date', ...)`，列带 comment，范式照抄 `server/alembic/versions/2026_08_14_0001-c4b9e2a7f813_add_market_metrics_and_calendar.py`
- downgrade 逆序 drop index → drop table；不夹带无关 schema drift
- **不建任何日历表**（16 期已交付 `trading_calendar_days`，本期迁移只含一张新表）

#### 4. 模型元数据测试

`server/tests/models/test_market_margin_daily_model.py`（新建 `server/tests/models/` 目录与 `__init__.py` 惯例参照 tests 目录现状，若 flat 惯例冲突则放 `server/tests/test_market_margin_daily_model.py`）：

- 断言 `MarketMarginDaily.__tablename__ == 'market_margin_daily'`
- 断言表在 `Base.metadata.tables` 中，`uq_market_margin_daily_trade_date` 唯一约束与 `idx_market_margin_daily_trade_date` 索引存在
- 断言六指标列均 `Numeric(20,2)`、`trade_date` 不可空、`created_at/updated_at` 存在

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | 创建 MarketMarginDaily 模型 | backend | done | 六指标 Numeric(20,2) + 唯一约束 + 索引 + 双时间戳 |
| 2 | models/__init__.py 注册导出 | backend | done | import + __all__ |
| 3 | 编写 Alembic 迁移（down_revision=a7d2e9f4c1b8） | backend | done | 单表 create/drop 对称 |
| 4 | 编写模型元数据测试 | backend | done | 表/约束/索引/列型断言 |

## 验收标准

### 后端验收

- [x] `alembic upgrade head` 成功创建 `market_margin_daily`（含唯一约束与索引，列 comment 齐全）；`alembic downgrade -1` 可回退，再次 upgrade 恢复（revision `63164af1c44c`）
- [x] `alembic check` 无新 drift（迁移与模型定义一致；注：仓库存在 16 期之前的存量 drift——`sector_classification` 表与若干旧表 comment/索引，与本功能无关，drift 操作集合与基线逐项一致，`market_margin_daily` 仅出现一条 "assuming SERIAL and omitting" INFO 行）
- [x] `from src.models import MarketMarginDaily` 成功；`trading_calendar_days` 表未被触碰（复用 16 期，无新建日历迁移；迁移往返后列数仍为 6）
- [x] 模型元数据测试通过（9 passed：唯一约束名/索引名/Numeric(20,2)/trade_date 非空/rqyl 不入库）
- [x] E2E 不适用：纯数据层功能，无用户可见界面；其用户可见效果由 plan-07 面板与 plan-08 同步面板间接验证

## 验证命令

```bash
cd server && source .venv/bin/activate

# 1. 迁移与回退
alembic upgrade head
alembic downgrade -1 && alembic upgrade head
alembic check

# 2. 模型注册
python -c "from src.models import MarketMarginDaily; print(MarketMarginDaily.__tablename__)"

# 3. 模型元数据测试（--no-cov 规避 pytest.ini 全局 80% 覆盖率门槛）
pytest tests/models/test_market_margin_daily_model.py -v --no-cov
```

## 交接上下文

- **spec 章节**: 边界（必须/禁止）、REQ-2（存储）、代码地图（后端新增 1/2 项）、任务清单 T1
- **相关代码**: `server/src/models/market_daily_metric.py`（模型范式，唯一约束+索引+双时间戳逐项对照）、`server/alembic/versions/2026_08_14_0001-c4b9e2a7f813_add_market_metrics_and_calendar.py`（迁移范式）、`server/src/models/__init__.py`（L33/L73 注册惯式）
- **契约 / 数据对象**: `MarketMarginDaily`（六指标列名与 tushare `margin` 字段同名：rzye/rqye/rzmre/rzche/rqmcl/rzrqye）
- **下游消费方**: plan-03（`_atomic_upsert` 写入）、plan-06（LEFT JOIN 读取）、plan-04 执行验证（查库断言）
- **路径偏离标注**: 迁移文件名 `2026_08_15_0002-*` 替代 spec 的 `2026_08_14_XXXX-*`（head 已是 2026_08_15_0001，保持文件名单调）；`server/tests/models/` 为新子目录，若与现有 flat 测试布局冲突则退化为 `server/tests/test_market_margin_daily_model.py`

## 风险与边界

- **执行顺序**: 按 Task 列表顺序执行；迁移依赖模型定义
- **验证失败排查方向**: 迁移失败先查 `down_revision` 是否指向当前 head `a7d2e9f4c1b8`；`alembic check` 报 drift 查列 comment 与 server_default 是否与模型一致
- **允许修改的额外文件**: 无
- **暂停条件**: 若 `alembic heads` 显示多个 head（分叉），暂停并上报，不得强行指定 down_revision
- **风险备注**: Numeric(20,2) 上限 10^18，两融余额量级（万亿=10^12 元）余量充足；rqyl 不入库是 spec 冻结决策，不要"顺手"加列

### 后端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| 迁移前库中已有同名表（人工建过） | `alembic upgrade` 报 duplicate table，人工核对后处理，不在代码层吞错 | done |
| downgrade 后残留索引 | drop index 先于 drop table，顺序对称 | done |
| 六指标全为 NULL 的行 | 模型允许（nullable），由 plan-03 聚合失败守卫保证不会产生 | done |
