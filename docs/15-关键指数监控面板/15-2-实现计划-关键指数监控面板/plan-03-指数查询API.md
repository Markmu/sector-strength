---
feat_id: "plan-03"
title: "指数查询 API"
dimension: backend
phase: 2
status: done
depends_on: ["plan-02"]
---

# plan-03: 指数查询 API

## 功能概要

- **目标**: 新建 `/api/v1/index-monitor` 查询路由，提供 6 个端点（总览/走势/估值/权重/关注清单读/关注清单写），为主页面板和数据管理页提供数据查询能力。
- **完成后可观察结果**: 通过 curl 调用各端点返回真实指数数据（非空、非模拟）。/overview 返回关注指数当日行情卡片数据；/trend 返回多指数走势序列；/valuation 返回单指数 PE/PB 序列（无估值指数返回 has_data=false）；/weights 返回前 N 权重股 + 集中度；/watchlist 返回关注清单，PUT 可更新。
- **依赖**: plan-02（数据已入库）
- **关联验收标准**: [AC-01, AC-02, AC-03, AC-04, AC-07, AC-12]
- **涉及架构模块**: index_monitor.py 查询 API
- **前置条件**: plan-02 完成（数据已同步入库）
- **不在范围**: 前端页面（plan-04）

## 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
|------|------|------|
| create | `server/src/api/v1/index_monitor.py` | 查询路由（6 端点） |
| modify | `server/src/api/v1/__init__.py` | 注册 index_monitor 路由 |

## 实现规格

### 后端部分

#### 1. 路由声明与 Helper

范式对齐 `server/src/api/v1/etf_monitor.py`。

```python
from fastapi import APIRouter, Depends, Query
from pydantic.alias_generators import to_camel
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.deps import get_current_user, get_session

router = APIRouter(prefix="/index-monitor", tags=["IndexMonitor"])
```

**Helper 照抄 etf_monitor.py**：
- `_serialize_value(val)` — Decimal → float, date → isoformat
- `_dict_to_camel(d)` — snake_case 键 → camelCase（递归）

**响应包裹**：统一 `{success: bool, data: {...}}`

**路径拼接确认**：前端 endpoint `/index-monitor/overview` × baseURL `${API_BASE_URL}/api/v1` = 后端 `/api/v1/index-monitor/overview` ✓

#### 2. GET /overview — 关注指数总览

参数：无（默认查最新有数据交易日）
逻辑：
- `SELECT MAX(trade_date) FROM index_daily` 获取最近交易日
- 查 `index_basic WHERE is_watched=true` 获取关注指数
- 对每只关注指数查 index_daily 当日行情（close/pct_chg/amount）
- LEFT JOIN index_dailybasic 取 pe_ttm（无估值为 null）
- amount 后端 ÷10000 转亿元再输出
- 返回 `{success, data: {indices: [...], tradeDate: "..."}}`

#### 3. GET /trend — 多指数走势

参数：`ts_codes: str`（逗号分隔）、`start_date: date`（可选）、`end_date: date`（可选，默认近1年）
逻辑：
- 拆分 ts_codes（逗号分隔），不限制数量
- 查 index_daily：`WHERE ts_code IN (...) AND trade_date BETWEEN start AND end`，按 trade_date 升序
- 按 ts_code 分组为 series
- 返回 `{success, data: {series: [{tsCode, name, points: [...]}], hasData: bool}}`

**query 参数命名确认**：前端传 `ts_codes`（snake_case），后端接收 `ts_codes`，一致 ✓

#### 4. GET /valuation — 估值水位

参数：`ts_code: str`、`start_date`/`end_date`（可选）
逻辑：
- 查 index_dailybasic：`WHERE ts_code=? AND trade_date BETWEEN ...`
- 如无数据返回 `{success, data: {tsCode, points: [], hasData: false}}`
- 返回 `{success, data: {tsCode, points: [{tradeDate, peTtm, pb, turnoverRate}], hasData: true}}`

#### 5. GET /weights — 成分权重

参数：`index_code: str`、`top_n: int`（默认 20，可选 10/20/30）
逻辑：
- 查 index_weight：`WHERE index_code=? ORDER BY weight DESC`（取最近月）
- 取前 N 条
- LEFT JOIN stocks 表取成分股 name（`Stock` 模型有 name 字段，JOIN 条件 `IndexWeight.con_code == Stock.ts_code` 或用 symbol 匹配——**注意 con_code 格式是 600519.SH，stocks 表的 ts_code 也是 .SH/.SZ 格式，可直接 JOIN**）；如无匹配显示 con_code
- 计算集中度：前5合计 weight、前10合计 weight
- 返回 `{success, data: {indexCode, tradeDate, weights: [...], concentration: {top5, top10}}}`

#### 6. GET /watchlist — 关注清单

参数：无
逻辑：查 `index_basic WHERE is_watched=true` 返回 `{tsCode, name, market, hasValuation(是否在 dailybasic 有数据)}`
返回 `{success, data: {watchlist: [...]}}`

#### 7. PUT /watchlist — 更新关注清单

参数：body `{ts_codes: [str]}` — 全量关注列表
逻辑：
- 先 `UPDATE index_basic SET is_watched=false`（清空）
- 再 `UPDATE index_basic SET is_watched=true WHERE ts_code IN (...)`（设置新列表）
- 返回 `{success, data: {updated: N}}`

**安全要求**：所有端点用 `Depends(get_current_user)` 鉴权（与 etf_monitor 一致）。

**可观测性（架构 §8.5）**：关键查询加 logger.debug（查询参数 + 返回行数），与 etf_monitor_service 一致。

#### 8. 路由注册（v1/__init__.py）

```python
from .index_monitor import router as index_monitor_router
# ...
router.include_router(index_monitor_router)  # /api/v1/index-monitor/*
```

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
|---|------|------|------|------|
| 1 | 创建 index_monitor.py 路由+helper | backend | done | prefix/helper/包裹 |
| 2 | 实现 GET /overview | backend | done | 最近交易日+关注指数行情+估值JOIN |
| 3 | 实现 GET /trend | backend | done | 多指数时间序列，最多6只 |
| 4 | 实现 GET /valuation | backend | done | 单指数PE/PB序列+hasData |
| 5 | 实现 GET /weights | backend | done | 前N权重+集中度+JOIN stocks取name |
| 6 | 实现 GET /watchlist | backend | done | 关注清单查询 |
| 7 | 实现 PUT /watchlist | backend | done | 全量更新关注标记 |
| 8 | 注册路由到 v1/__init__.py | backend | done | include_router |

## 验收标准

### 总览验收（AC-01）

- [ ] AC-01 `GET /overview` 返回 ≥14 只关注指数，每只含 close/pctChg/amount（亿元）/peTtm
- [ ] AC-01 有估值的 6 只 peTtm 非 null，无估值的 8 只 peTtm 为 null
- [ ] AC-12 当日无数据时返回最近有数据交易日，tradeDate 字段标注

### 走势验收（AC-02）

- [ ] AC-02 `GET /trend?ts_codes=000300.SH,000001.SH&start_date=2026-08-01&end_date=2026-08-08` 返回 2 条 series，每个含按日期升序的 close 序列
- [ ] AC-02 传任意数量 ts_codes 全部生效（不截断）

### 估值验收（AC-03）

- [ ] AC-03 `GET /valuation?ts_code=000300.SH` 返回 peTtm/pb/turnoverRate 序列，hasData=true
- [ ] AC-03 `GET /valuation?ts_code=000688.SH`（科创50）返回空序列，hasData=false

### 权重验收（AC-04）

- [ ] AC-04 `GET /weights?index_code=000300.SH&top_n=20` 返回前 20 权重股，含 conCode/name/weight
- [ ] AC-04 返回 concentration.top5 和 concentration.top10 合计占比

### 关注清单验收（AC-07）

- [ ] AC-07 `GET /watchlist` 返回当前关注指数列表
- [ ] AC-07 `PUT /watchlist` body `{ts_codes: ["000300.SH"]}` 后，GET 返回只剩 1 只

### 响应格式验收

- [ ] 所有响应外层为 `{success: true, data: {...}}`
- [ ] data 内字段经 camelCase 转换（如 tsCode / peTtm / pctChg）
- [ ] 日期序列化为 ISO 字符串（YYYY-MM-DD）
- [ ] Decimal 序列化为 float

### 性能验收（架构 §8.1 目标）

- [ ] /overview 响应 ≤ 2 秒（14 指数）
- [ ] /trend 响应 ≤ 1 秒
- [ ] /valuation 响应 ≤ 500ms
- [ ] /weights 响应 ≤ 500ms

## 验证命令

```bash
cd server && source ../.venv/bin/activate
uvicorn src.main:app --reload &

# 各端点（需有效 TOKEN）
curl -s http://localhost:8000/api/v1/index-monitor/overview -H "Authorization: Bearer $TOKEN" | python -m json.tool
curl -s "http://localhost:8000/api/v1/index-monitor/trend?ts_codes=000300.SH,000001.SH&start_date=2026-08-01&end_date=2026-08-08" -H "Authorization: Bearer $TOKEN" | python -m json.tool
curl -s "http://localhost:8000/api/v1/index-monitor/valuation?ts_code=000300.SH" -H "Authorization: Bearer $TOKEN" | python -m json.tool
curl -s "http://localhost:8000/api/v1/index-monitor/valuation?ts_code=000688.SH" -H "Authorization: Bearer $TOKEN" | python -m json.tool  # hasData=false
curl -s "http://localhost:8000/api/v1/index-monitor/weights?index_code=000300.SH&top_n=20" -H "Authorization: Bearer $TOKEN" | python -m json.tool
curl -s http://localhost:8000/api/v1/index-monitor/watchlist -H "Authorization: Bearer $TOKEN" | python -m json.tool
curl -s -X PUT http://localhost:8000/api/v1/index-monitor/watchlist -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"ts_codes":["000300.SH"]}' | python -m json.tool
```

## 交接上下文

- **架构章节**: §7.3（API 边界）、§7.6（命名与标识规则）、§6.4（主页查询链路）
- **相关代码**: `server/src/api/v1/etf_monitor.py`（路由+helper 范式锚点）、`server/src/models/stock.py`（weights JOIN stocks.name）
- **契约/数据对象**: IndexOverviewItem / IndexTrendResponse / IndexValuationResponse / IndexWeightResponse（见架构 §7.2 API 响应 Schema）
- **下游消费方**: plan-04（前端 indexMonitorApi 调用这些端点）

## 风险与边界

- **执行顺序**: 按 Task 列表顺序（路由骨架 → 各端点 → 注册）
- **验证失败排查方向**: 检查路由 prefix、query 参数命名、_dict_to_camel 转换、SQLAlchemy JOIN 语法
- **允许修改的额外文件**: 无
- **暂停条件**: weights JOIN stocks 取 name 不成功时（检查 con_code 与 stocks 表 ts_code 格式是否匹配）

### 后端边界场景

| 场景 | 处理方式 | 状态 |
|------|---------|------|
| 指数无行情数据 | /overview 该指数 peTtm=null，其余字段尽量填或跳过 | done |
| 指数无估值数据 | /valuation 返回 hasData=false，空序列 | done |
| 权重成分股无 name 匹配 | 显示 con_code 作为 fallback | done |
| ts_codes 任意数量 | /trend 全部生效，不截断 | done |
| 当日无数据 | /overview 回退最近有数据交易日 | done |
| 关注清单为空 | /overview 返回空数组，不报错 | done |
