---
feat_id: "plan-01"
title: "指数数据模型与采集方法"
dimension: backend
phase: 1
status: done
depends_on: []
---

# plan-01: 指数数据模型与采集方法

## 功能概要

- **目标**: 新建 4 张指数数据表（index_basic / index_daily / index_dailybasic / index_weight）并在 TushareDataSource 中新增 4 个采集方法，为后续采集服务和查询 API 提供数据基础。
- **完成后可观察结果**: Alembic 迁移执行成功，4 张表在 PostgreSQL 中创建完毕。通过 Python 交互式调用 `TushareDataSource` 的 4 个新方法，可以拉取到真实的指数清单（约 1 万条）、日线行情、估值指标和成分权重数据。14 只预置关注指数在 index_basic 中 is_watched=true。
- **依赖**: 无
- **关联验收标准**: [AC-09]（真实数据源头验证——采集方法返回的数据值与数据源一致）
- **涉及架构模块**: TushareDataSource（扩展）、IndexBasic / IndexDaily / IndexDailyBasic / IndexWeight 模型
- **前置条件**: `.env` 中 TUSHARE_API_URL 和 TUSHARE_TOKEN 已配置；PostgreSQL 运行中
- **不在范围**: 采集服务编排（plan-02）、查询 API（plan-03）、前端（plan-04）

## 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
|------|------|------|
| create | `server/src/models/index_monitor.py` | 4 个 SQLAlchemy 模型 |
| modify | `server/src/models/__init__.py` | 注册 4 个模型 import + __all__ |
| create | `server/alembic/versions/2026_08_10_0001-<hex>_add_index_monitor_tables.py` | 建表迁移 |
| modify | `server/src/services/data_acquisition/tushare_client.py` | 新增 4 个采集方法 |

## 实现规格

### 后端部分

#### 1. 数据模型（index_monitor.py）

范式对齐 `server/src/models/etf.py`：Integer 自增主键 + created_at/updated_at + Numeric 精度字段 + UniqueConstraint + Index。

**IndexBasic**（表 `index_basic`，ts_code 唯一）：
- `ts_code: String(20), unique=True, nullable=False` — 指数代码（如 000300.SH）
- `name: String(50)` — 简称
- `market: String(10)` — 市场（SSE/SZSE/CSI/SW）
- `publisher: String(100)` — 发布方
- `category: String(50)` — 类别
- `base_date: Date` — 基期
- `base_point: Numeric(20,4)` — 基点
- `list_date: Date` — 发布日期
- `is_watched: Boolean, default=false` — 是否关注（ADR-2）

**IndexDaily**（表 `index_daily`，唯一约束 trade_date+ts_code）：
- `trade_date: Date, nullable=False` / `ts_code: String(20), nullable=False`
- `open/high/low/close: Numeric(20,4)` / `pre_close: Numeric(20,4)` / `change: Numeric(20,4)`
- `pct_chg: Numeric(10,4)` — 涨跌幅 %
- `vol: Numeric(20,2)` — 成交量（手）/ `amount: Numeric(20,2)` — 成交额（千元）
- UniqueConstraint("trade_date", "ts_code", name="uq_index_daily_date_code")
- Index("idx_index_daily_date", "trade_date") + Index("idx_index_daily_code_date", "ts_code", "trade_date")

**IndexDailyBasic**（表 `index_dailybasic`，唯一约束 trade_date+ts_code）：
- `trade_date: Date` / `ts_code: String(20)`
- `total_mv/float_mv: Numeric(24,2)` — 总/流通市值（元）
- `total_share/float_share/free_share: Numeric(24,0)` — 总/流通/自由流通股本（股）
- `turnover_rate/turnover_rate_f: Numeric(10,4)` — 换手率 %
- `pe/pe_ttm/pb: Numeric(10,4)` — 市盈率/TTM/市净率
- UniqueConstraint("trade_date", "ts_code")

**IndexWeight**（表 `index_weight`，唯一约束 index_code+con_code+trade_date）：
- `index_code: String(20)` / `con_code: String(20)` / `trade_date: Date` / `weight: Numeric(10,4)` — 权重 %
- UniqueConstraint("index_code", "con_code", "trade_date")
- Index("idx_index_weight_code", "index_code")

#### 2. 模型注册（__init__.py）

在 `from .limit import ...` 后加：
```python
from .index_monitor import IndexBasic, IndexDaily, IndexDailyBasic, IndexWeight
```
`__all__` 列表末尾加：`"IndexBasic", "IndexDaily", "IndexDailyBasic", "IndexWeight"`

#### 3. Alembic 迁移

在 `server/` 下执行 `alembic revision --autogenerate -m "add index monitor tables"`，生成的迁移文件 down_revision 接当前 head。检查 upgrade() 包含 4 张表的 op.create_table，downgrade() 包含对应的 drop。执行 `alembic upgrade head` 确认建表成功。

迁移后需执行一次性 SQL 设置预置关注指数：
```sql
UPDATE index_basic SET is_watched = true WHERE ts_code IN (
  '000001.SH','000300.SH','000016.SH','000905.SH','000852.SH',
  '399001.SZ','399006.SZ','399102.SZ','399673.SZ',
  '000688.SH','000698.SH','000699.SH','931643.CSI','899050.BJ'
);
```
（此 SQL 在 plan-02 的 sync_index_basic 完成后执行，因为需要先有数据。迁移本身只建表。）

#### 4. TushareDataSource 采集方法（tushare_client.py）

在申万行业区块后新增指数采集区块。每个方法范式对齐 `get_sw_index_classify`（使用 `_execute_with_retry` + `_get_pro_api()`，返回原始 dict 列表保留 Tushare 键名）。

**get_index_basic(market=None, ts_code=None)**：
```python
def get_index_basic(self, market=None, ts_code=None) -> List[dict]:
    pro = self._get_pro_api()
    def _fetch():
        params = {}
        if market: params["market"] = market
        if ts_code: params["ts_code"] = ts_code
        return pro.index_basic(**params)
    df = self._execute_with_retry(_fetch)
    # df → dict 列表（pd.isna → None），与 get_sw_index_classify 一致
```
注意：`name` 参数在代理上不生效（已验证），不要传 name 过滤。

**get_index_daily(ts_code, start_date, end_date)**：
```python
def get_index_daily(self, ts_code, start_date, end_date) -> List[dict]:
    # start_date/end_date 是 date 对象，需 strftime("%Y%m%d")
    # pro.index_daily(ts_code=..., start_date=..., end_date=...)
```

**get_index_dailybasic(ts_code, start_date, end_date)**：同上，`pro.index_dailybasic(...)`。无估值的指数返回空列表。

**get_index_weight(index_code, start_date, end_date)**：`pro.index_weight(index_code=..., start_date=..., end_date=...)`。注意参数名是 `index_code`（不是 ts_code）。

**可观测性（架构 §8.5）**：每个方法内加 `logger.info(f"[Tushare] 正在获取指数... (xxx)")` 和完成日志，与现有方法一致。

**安全要求**：无额外安全要求，采集方法不涉及用户输入。

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
|---|------|------|------|------|
| 1 | 创建 index_monitor.py 4 个模型 | backend | done | 范式对齐 etf.py |
| 2 | 注册模型到 __init__.py | backend | done | import + __all__ |
| 3 | 生成并执行 Alembic 迁移 | backend | done | autogenerate + upgrade head |
| 4 | 新增 get_index_basic 方法 | backend | done | 全量拉取，返回 dict 列表 |
| 5 | 新增 get_index_daily 方法 | backend | done | 按指数+日期区间 |
| 6 | 新增 get_index_dailybasic 方法 | backend | done | 无估值返回空列表 |
| 7 | 新增 get_index_weight 方法 | backend | done | 参数名 index_code |

## 验收标准

### 后端验收

- [x] AC-09（数据源）`alembic upgrade head` 成功，4 张表在数据库中可见
- [x] AC-09（数据源）Python 交互调用 `TushareDataSource().get_index_basic()` 返回 ≥10000 条，含 000300.SH 沪深300 — 实测 11612 条
- [x] AC-09（数据源）`get_index_daily("000300.SH", date(2026,8,1), date(2026,8,8))` 返回 ≥5 条，字段含 close/pct_chg/vol/amount — 实测 5 条
- [x] AC-09（数据源）`get_index_dailybasic("000300.SH", date(2026,8,1), date(2026,8,8))` 返回数据，字段含 pe_ttm/pb — 实测 5 条，pe_ttm=14.4663/pb=1.4714
- [x] AC-09（数据源）`get_index_dailybasic("000688.SH", ...)` 返回空列表（科创50 无估值）— 实测 0 条
- [x] AC-09（数据源）`get_index_weight` 返回 300 条，字段含 con_code/weight — 实测 `2026-07-30~07-31` 返回 300 条（con_code=300750.SZ/weight=4.012）。注意 `index_weight` 仅在月末/调整日刷新，原验证窗口 `2026-08-01~08` 内无快照返回 0 条（符合边界场景"返回空列表不抛异常"），改用含最近调整日的窗口验证

### 性能验收（架构 §8.1 目标）

- [x] 单次 get_index_daily 调用响应时间 ≤ 3 秒（含代理网络延迟）— 实测 2.46s

## 验证命令

```bash
cd server && source ../.venv/bin/activate

# 1. 迁移
alembic upgrade head

# 2. 模型注册检查
python -c "from src.models import IndexBasic, IndexDaily, IndexDailyBasic, IndexWeight; print('OK')"

# 3. 采集方法验证（需 TUSHARE_TOKEN 有效）
python -c "
from datetime import date
from src.services.data_acquisition import DataSourceFactory
ds = DataSourceFactory.create()
basic = ds.get_index_basic()
print(f'index_basic: {len(basic)} 条')
daily = ds.get_index_daily('000300.SH', date(2026,8,1), date(2026,8,8))
print(f'index_daily 沪深300: {len(daily)} 条')
db = ds.get_index_dailybasic('000300.SH', date(2026,8,1), date(2026,8,8))
print(f'index_dailybasic 沪深300: {len(db)} 条, pe_ttm={db[0].get(\"pe_ttm\") if db else \"N/A\"}')
w = ds.get_index_weight('000300.SH', date(2026,8,1), date(2026,8,8))
print(f'index_weight 沪深300: {len(w)} 条')
"
```

## 交接上下文

- **架构章节**: §7.1-7.2（领域对象与 Schema）、§4.2（TushareDataSource 扩展）、§6.1（清单同步链路）
- **相关代码**: `server/src/models/etf.py`（模型范式锚点）、`server/src/services/data_acquisition/tushare_client.py`（采集方法锚点，参考 get_sw_index_classify）
- **契约/数据对象**: IndexBasic / IndexDaily / IndexDailyBasic / IndexWeight（见架构 §7.2 Schema）
- **下游消费方**: plan-02（IndexDataInitService 调用这些采集方法入库）、plan-03（查询 API 读这些表）

## 风险与边界

- **执行顺序**: 按 Task 列表顺序执行（模型 → 注册 → 迁移 → 采集方法）
- **验证失败排查方向**: 检查 TUSHARE_TOKEN 是否有效、代理地址是否可达、Alembic head 是否正确
- **允许修改的额外文件**: 无
- **暂停条件**: Alembic 迁移冲突（down_revision 不对）时暂停
- **风险备注**: `index_basic(name=...)` 参数在代理上不生效，不能靠 name 过滤

### 后端边界场景

| 场景 | 处理方式 | 状态 |
|------|---------|------|
| 采集方法返回空 DataFrame | 返回空列表 `[]`，不抛异常（与 get_sw_index_classify 一致） | done（科创50 dailybasic 与 8/1-8/8 weight 窗口均验证返回空） |
| 代理网络超时 | `_execute_with_retry` 3 次重试 + 指数退避 | done（复用现有重试机制） |
| 不可恢复错误（权限不足/token 错） | `_execute_with_retry` 短路抛 DataFetchError | done（复用现有 _NON_RETRYABLE_KEYWORDS） |
| 迁移 down_revision 冲突 | 暂停，人工确认当前 head | done（down_revision=a2c4e6f8b1d3 接当前 head，无冲突） |
