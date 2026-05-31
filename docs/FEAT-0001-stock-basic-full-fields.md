---
title: '股票基础信息全字段入库'
type: 'feature'
created: '2026-06-01'
status: 'approved'
context: []
---

<frozen-after-approval reason="人工意图 — 除非人类重新协商，否则不可修改">

## 意图

**问题：** Tushare `stock_basic` 接口返回 17 个字段，但当前仅保存 symbol 和 name 到数据库，大量基础信息（行业、交易所、上市状态、地域等）丢弃了。

**方案：** 将 `stock_basic` 返回的全部字段完整保存到数据库 `stocks` 表，补齐 StockInfo 模型、数据库表、数据写入逻辑三层缺失字段，字段命名与 Tushare 文档一致。

## 边界

**必须：**
- StockInfo (Pydantic) 字段与 Tushare `stock_basic` 输出参数对齐
- Stock (SQLAlchemy) 表新增所有缺失列
- `get_stock_list`、`init_stocks`、`_update_stocks` 三处写入逻辑同步更新
- 通过 Alembic 迁移添加新列，所有新列允许 NULL（兼容已有数据）

**先问：** 无

**禁止：**
- 不修改 `stock_basic` 接口的调用参数（保持 `exchange="", list_status="L"`）
- 不删除现有字段（current_price、market_cap、strength_score、trend_direction 保留）
- 不修改前端代码（本次只改后端数据层）

## 需求变更

### 新增

- **REQ-1**: 系统 SHALL 将 Tushare `stock_basic` 返回的全部 17 个字段保存到 `stocks` 数据库表
- **REQ-2**: 系统 SHALL 在 StockInfo Pydantic 模型中定义与 Tushare 文档一致的字段
- **REQ-3**: 系统 SHALL 通过 Alembic 迁移为 `stocks` 表添加新列，所有新列允许 NULL 以兼容历史数据
- **REQ-4**: 系统 SHALL 在股票初始化（`init_stocks`）时保存全部基础字段
- **REQ-5**: 系统 SHALL 在增量更新（`_update_stocks`）时同步更新已变更的基础字段

### 修改

- **REQ-6**: `tushare_client.get_stock_list` 方法 SHALL 提取 `stock_basic` 返回的全部字段（当前仅提取 5 个）
- **REQ-7**: `StockInfo.market` 字段语义对齐 Tushare 文档：原 SH/SZ/BJ（交易所后缀）改由 `exchange` 字段承载，`market` 改为 Tushare 原义（主板/创业板/科创板/CDR）

</frozen-after-approval>

## 代码地图

- `server/src/services/data_acquisition/models.py` -- StockInfo Pydantic 模型，需补齐字段
- `server/src/models/stock.py` -- Stock SQLAlchemy 模型，需新增数据库列
- `server/src/services/data_acquisition/tushare_client.py` -- get_stock_list 方法，需提取全部字段
- `server/src/services/data_init.py` -- init_stocks 方法（第 188-261 行），需保存全部字段
- `server/src/services/data_updater/collector.py` -- _update_stocks 方法（第 159-186 行），需更新全部字段
- `server/alembic/versions/` -- 需新增迁移文件

## 字段映射对照表

### StockInfo (Pydantic) 新增字段

| 字段名 | 类型 | 来源（Tushare 列名） | 说明 |
|---|---|---|---|
| `ts_code` | `str` | `ts_code` | TS 代码（如 000001.SZ） |
| `area` | `Optional[str]` | `area` | 地域（如 深圳） |
| `fullname` | `Optional[str]` | `fullname` | 股票全称 |
| `enname` | `Optional[str]` | `enname` | 英文全称 |
| `cnspell` | `Optional[str]` | `cnspell` | 拼音缩写 |
| `exchange` | `Optional[str]` | `exchange` | 交易所（SSE/SZSE/BSE），替代原 market 的 SH/SZ/BJ 语义 |
| `curr_type` | `Optional[str]` | `curr_type` | 交易货币 |
| `list_status` | `Optional[str]` | `list_status` | 上市状态（L/D/P/G） |
| `delist_date` | `Optional[date]` | `delist_date` | 退市日期 |
| `is_hs` | `Optional[str]` | `is_hs` | 是否沪深港通标的（N/H/S） |
| `act_name` | `Optional[str]` | `act_name` | 实控人名称 |
| `act_ent_type` | `Optional[str]` | `act_ent_type` | 实控人企业性质 |

### StockInfo 字段语义变更

| 字段名 | 原语义 | 新语义 |
|---|---|---|
| `market` | 交易所后缀 SH/SZ/BJ（从 ts_code 推导） | Tushare 原义：主板/创业板/科创板/CDR |

### Stock (SQLAlchemy) 新增数据库列

| 列名 | SQLAlchemy 类型 | 说明 |
|---|---|---|
| `ts_code` | `String(20)` | TS 代码 |
| `area` | `String(50)` | 地域 |
| `industry` | `String(50)` | 所属行业 |
| `fullname` | `String(200)` | 股票全称 |
| `enname` | `String(200)` | 英文全称 |
| `cnspell` | `String(50)` | 拼音缩写 |
| `market` | `String(20)` | 市场类型（主板/创业板/科创板/CDR） |
| `exchange` | `String(20)` | 交易所（SSE/SZSE/BSE） |
| `curr_type` | `String(10)` | 交易货币 |
| `list_status` | `String(5)` | 上市状态 |
| `list_date` | `Date` | 上市日期 |
| `delist_date` | `Date` | 退市日期 |
| `is_hs` | `String(5)` | 是否沪深港通标的 |
| `act_name` | `String(200)` | 实控人名称 |
| `act_ent_type` | `String(100)` | 实控人企业性质 |

> 注：所有新增列均允许 NULL，兼容历史存量数据。`ts_code` 和 `exchange` 建议加索引。

## 任务清单

- [ ] `server/src/services/data_acquisition/models.py` -- StockInfo 模型新增 12 个字段，修改 market 字段语义，新增 ts_code/exchange 等字段的 validator
- [ ] `server/src/services/data_acquisition/tushare_client.py` -- get_stock_list 方法提取全部 17 个字段，正确映射到 StockInfo
- [ ] `server/src/models/stock.py` -- Stock 模型新增 15 个数据库列（含 industry、list_date、market）
- [ ] `server/alembic/versions/` -- 执行 `alembic revision --autogenerate` 生成迁移文件，检查并确认迁移脚本正确
- [ ] `server/src/services/data_init.py` -- init_stocks 方法将 StockInfo 全部字段写入 Stock 记录
- [ ] `server/src/services/data_updater/collector.py` -- _update_stocks 方法增量更新所有基础字段（新增 + 变更检测）
- [ ] `server/src/repositories/stock_repository.py` -- 检查是否需要更新相关查询方法（如有按 industry 筛选等）

## 验收标准

- Given `stocks` 表有历史存量数据（仅含 symbol/name）, when 执行 Alembic 迁移, then 所有新列成功添加且存量数据不受影响
- Given StockInfo 模型已更新, when 调用 `get_stock_list()`, then 返回的每条 StockInfo 包含 Tushare stock_basic 的全部 17 个字段
- Given 数据库为空, when 执行 `init_stocks()`, then 每条 Stock 记录包含全部基础字段（ts_code、area、industry、fullname 等）
- Given 数据库已有股票记录, when 执行 `_update_stocks()` 且 Tushare 返回的字段有变更（如 industry 变化）, then 数据库中对应字段被更新
- Given Tushare 返回某字段为空或 NaN, when 转换为 StockInfo/Stock, then 该字段存储为 NULL 而非空字符串或报错
