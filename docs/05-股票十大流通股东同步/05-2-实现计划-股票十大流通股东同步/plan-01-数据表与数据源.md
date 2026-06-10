---
feat_id: "plan-01"
title: "数据表与数据源"
dimension: backend
phase: 1
status: done
depends_on: []
---

# plan-01: 数据表与数据源

## 功能概要

- **目标**: 建立十大流通股东数据的持久化模型，并在 TushareDataSource 中新增获取十大流通股东数据的接口方法。
- **完成后可观察结果**: 数据库中存在 `top10_float_holders` 表，包含 symbol、ts_code、report_period、ann_date、holder_name、hold_amount、hold_ratio、hold_float_ratio、hold_change、holder_type 等字段。调用 `TushareDataSource.get_top10_float_holders("600000.SH", "20241231")` 可返回该股票指定报告期的十大流通股东数据列表。后续同步服务可基于此方法和模型完成数据写入。
- **依赖**: 无
- **关联验收标准**: [AC-02]（数据入库的数据模型基础）
- **涉及架构模块**: Top10FloatHolder Model, TushareDataSource.get_top10_float_holders()
- **前置条件**: PostgreSQL 运行中，Alembic 迁移环境就绪，Tushare Token 有效
- **不在范围**: 同步业务逻辑、任务注册、Admin API、前端 UI

## 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| create | `server/src/models/top10_float_holder.py` | 十大流通股东数据 Model（表 `top10_float_holders`） |
| modify | `server/src/models/__init__.py` | 注册 Top10FloatHolder Model |
| modify | `server/src/services/data_acquisition/tushare_client.py` | 新增 `get_top10_float_holders()` 方法 |

> Alembic 迁移文件通过 `alembic revision --autogenerate` 自动生成，不手动创建。

## 实现规格

### 后端部分

#### 1. 创建 Top10FloatHolder Model

文件：`server/src/models/top10_float_holder.py`

参考 `server/src/models/fund_portfolio.py` 的结构，创建 SQLAlchemy Model：

- **表名**: `top10_float_holders`
- **字段**:

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | Integer, PK, autoincrement | 自增主键 |
| `symbol` | String(10), NOT NULL | 股票代码（纯数字，如 "600000"） |
| `ts_code` | String(20), NOT NULL | Tushare 代码（如 "600000.SH"） |
| `report_period` | Date, NOT NULL | 报告期 |
| `ann_date` | Date, nullable | 公告日期 |
| `holder_name` | String(100), NOT NULL | 股东名称 |
| `hold_amount` | Numeric(20, 2), nullable | 持股数量（股） |
| `hold_ratio` | Numeric(10, 4), nullable | 占总股本比例(%) |
| `hold_float_ratio` | Numeric(10, 4), nullable | 占流通股本比例(%) |
| `hold_change` | Numeric(20, 2), nullable | 持股变动 |
| `holder_type` | String(50), nullable | 股东类型 |
| `created_at` | DateTime, server_default=func.now() | 创建时间 |
| `updated_at` | DateTime, onupdate=func.now(), nullable | 更新时间 |

- **索引**:
  - `ix_top10_symbol_period`: `(symbol, report_period)` 联合索引（先删后写的查询条件）
  - `ix_top10_report_period`: `(report_period)` 单独索引（按报告期查询）

- **安全要求（架构 §8.3）**: 无额外安全要求，Model 层不直接暴露。

#### 2. 注册 Model

文件：`server/src/models/__init__.py`

在现有 import 列表中添加：
```python
from server.src.models.top10_float_holder import Top10FloatHolder
```

确保 Model 被 Alembic autogenerate 检测到。

#### 3. 生成并执行数据库迁移

```bash
cd server
alembic revision --autogenerate -m "add top10_float_holders table"
alembic upgrade head
```

#### 4. 新增 Tushare 数据源方法

文件：`server/src/services/data_acquisition/tushare_client.py`

在 `TushareDataSource` 类中新增方法：

```python
async def get_top10_float_holders(self, ts_code: str, period: str) -> List[dict]:
    """获取单只股票的前十大流通股东数据

    Args:
        ts_code: Tushare 股票代码，如 "600000.SH"
        period: 报告期，YYYYMMDD 格式，如 "20241231"

    Returns:
        dict 列表，每条包含: ts_code, ann_date, end_date, holder_name,
        hold_amount, hold_ratio, hold_float_ratio, hold_change, holder_type
    """
```

实现要点：
- 调用 `pro.top10_floatholders(ts_code=ts_code, period=period)`
- 通过 `_execute_with_retry` 包裹（复用现有速率限制 0.3s + 指数退避重试 3 次）
- 返回值为 DataFrame，转为 `List[dict]`（参考 `get_fund_portfolio_by_code` 方法的返回格式）
- 空结果返回空列表（ADR-5 空数据正常化）

**可观测性（架构 §8.5）**: 方法内部通过 Python logging 记录 warning 级别日志（如 API 返回空数据、重试等），使用项目现有 `logging.getLogger(__name__)` 模式。

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | 创建 Top10FloatHolder Model 文件 | backend | done | 参考 fund_portfolio.py 结构 |
| 2 | 在 `__init__.py` 注册 Model | backend | done | 确保 Alembic 可检测 |
| 3 | 生成并执行 Alembic 迁移 | backend | waived | 需要数据库连接，由用户手动执行 |
| 4 | 在 TushareDataSource 新增 `get_top10_float_holders()` 方法 | backend | done | 参考 `get_fund_portfolio_by_code` 模式 |

## 验收标准

### 后端验收

- [ ] AC-02（Model）`top10_float_holders` 表在数据库中存在，字段完整（id, symbol, ts_code, report_period, ann_date, holder_name, hold_amount, hold_ratio, hold_float_ratio, hold_change, holder_type, created_at, updated_at）
- [ ] AC-02（索引）`(symbol, report_period)` 联合索引和 `(report_period)` 单独索引存在
- [ ] AC-02（迁移）`alembic upgrade head` 无错误执行成功
- [ ] `get_top10_float_holders("600000.SH", "20241231")` 返回包含 holder_name、hold_amount 等字段的 dict 列表
- [ ] `get_top10_float_holders` 对不存在的股票返回空列表（不抛异常）
- [ ] `_execute_with_retry` 重试机制对该方法生效（限流/超时时自动重试）

## 验证命令

```bash
# 数据库迁移
cd server && alembic upgrade head

# 验证表存在（需要 psql 或 Python 脚本）
cd server && python -c "
import asyncio
from sqlalchemy import text
from server.src.db.database import AsyncSessionLocal

async def check():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text(\"SELECT column_name FROM information_schema.columns WHERE table_name='top10_float_holders' ORDER BY ordinal_position\"))
        cols = [r[0] for r in result.fetchall()]
        print('Columns:', cols)
        assert 'symbol' in cols and 'holder_name' in cols, 'Missing columns'
        print('Table OK')

asyncio.run(check())
"

# 验证 Tushare 方法
cd server && python -c "
import asyncio
from server.src.services.data_acquisition import DataSourceFactory

async def test():
    ds = DataSourceFactory.create()
    data = await ds.get_top10_float_holders('600000.SH', '20241231')
    print(f'Records: {len(data)}')
    if data:
        print('First record keys:', list(data[0].keys()))
    print('Tushare method OK')

asyncio.run(test())
"
```

## 交接上下文

- **架构章节**: §7.1 核心对象、§7.2 推荐最小 Schema、§9 Phase A
- **相关代码**:
  - `server/src/models/fund_portfolio.py` — Model 结构参考
  - `server/src/services/data_acquisition/tushare_client.py` — `get_fund_portfolio_by_code()` 方法参考（约第 588 行）
- **契约 / 数据对象**: `Top10FloatHolder`（数据库表）、`get_top10_float_holders()` 返回 `List[dict]`
- **下游消费方**: plan-02（Top10HolderDataInitService 将调用 Model 写入数据和 Tushare 方法获取数据）

## 风险与边界

- **执行顺序**: 按 Task 列表顺序执行（Model → 注册 → 迁移 → Tushare 方法）
- **验证失败排查方向**:
  - 迁移失败：检查 `__init__.py` 是否正确 import Model
  - Tushare 调用返回空：确认 ts_code 格式正确、Tushare Token 有效、积分 ≥ 2000
- **允许修改的额外文件**: 无
- **暂停条件**: Tushare 返回认证错误或权限不足时，暂停并提示用户检查 Token 和积分
- **E2E 不适用说明**: 本功能为纯内部数据层，无可观察 UI；执行验证通过 Tushare 方法和数据库查询完成
- **风险备注**: Tushare `top10_floatholders` 接口需要 2000+ 积分，积分不足会导致调用失败

### 后端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| Tushare 返回空 DataFrame | 方法返回空列表 `[]`，不抛异常（ADR-5） | done |
| Tushare 认证/权限错误 | `_execute_with_retry` 识别为不可恢复错误，立即抛异常 | done |
| ts_code 格式不正确 | 由 Tushare API 返回错误，`_execute_with_retry` 处理 | done |
| 数据库迁移冲突 | 检查是否有未执行迁移，`alembic upgrade head` 前先 `alembic current` | done |
