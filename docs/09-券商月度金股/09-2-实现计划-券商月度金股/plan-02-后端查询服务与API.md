---
feat_id: "plan-02"
title: "后端查询服务与用户侧 API（repository + analysis service + 4 个 v1 端点）"
dimension: backend
phase: 1
status: done
depends_on: ["plan-01"]
---

# plan-02: 后端查询服务与用户侧 API

## 功能概要

- **目标**: 交付券商金股的"双视图查询消费"后端：新建 `BrokerRecommendRepository`（DB 聚合/搜索/分页/月份/明细封装）、`BrokerRecommendAnalysisService`（双视图聚合 + latest_month 兜底 + 行业批量 JOIN + Decimal→float 序列化）、4 个用户侧 v1 端点（months / stock-ranking / broker-list / broker-detail）。完成后前端（plan-03）可消费完整 API 契约。
- **完成后可观察结果**: 对 `broker_recommend` 表做 curl 请求 4 个用户侧端点：GET /months 返回已同步月份列表 + has_data；GET /stock-ranking 默认按 MAX(month) 取最新月、按推荐券商家数降序、含预加载 brokers 与行业；GET /broker-list 按券商分组、含推荐股票数；GET /broker-detail 懒加载单券商明细。所有响应 `{success:true, data:{...}}` 包裹，data 字段 camelCase，query 参数 snake_case。无数据时 has_data=false，所选月无数据时 items 空 + total 0。搜索为服务端全量重查，分页 total 与搜索条件一致。
- **依赖**: plan-01（`BrokerRecommend` 模型与 broker_recommend 表 + 迁移）
- **关联验收标准**: [AC-02, AC-03, AC-04, AC-05, AC-06, AC-07, AC-09, AC-10, AC-11, AC-12, AC-13]
- **涉及架构模块**: BrokerRecommendRepository、BrokerRecommendAnalysisService、用户侧 API 4 端点（架构 §4.2 / §6.1 / §6.2 / §7.2 / §7.3 / §9 Phase B）
- **前置条件**: plan-01 完成（broker_recommend 表可读写，至少一个月数据可同步）；`server/src/api/v1/fund_crowd_analysis.py` 现有范式可参照
- **不在范围**: 数据同步（plan-01）、前端页面（plan-03）、缓存层（ADR-6 不做）

## 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| create | `server/src/repositories/broker_recommend_repository.py` | 新建 `BrokerRecommendRepository(BaseRepository[BrokerRecommend])`，4 个聚合查询方法 |
| create | `server/src/services/broker_recommend_analysis_service.py` | 新建 `BrokerRecommendAnalysisService`，含 latest_month 兜底 + 行业 JOIN + 序列化 |
| create | `server/src/api/v1/broker_recommend_analysis.py` | 新建用户侧路由（4 端点，kebab-case prefix），范式参照 fund_crowd_analysis.py |
| modify | `server/src/api/v1/__init__.py` | 注册 `broker_recommend_analysis_router`（line 21/38 范式） |

## 实现规格

### 后端部分

#### 1. Repository（`server/src/repositories/broker_recommend_repository.py`）

继承基类范式参照 `server/src/repositories/fund_crowd_repository.py`（`class FundCrowdRepository(BaseRepository[FundPortfolio])`，`def __init__(self, session): super().__init__(FundPortfolio, session)`）。

- `from src.repositories.base import BaseRepository`、`from src.models.broker_recommend import BrokerRecommend`、`from src.models.stock import Stock`、`from sqlalchemy import and_, func, or_, select`
- `class BrokerRecommendRepository(BaseRepository[BrokerRecommend])`：
  - `def __init__(self, session): super().__init__(BrokerRecommend, session)`
  - `async def get_months(self) -> list[date]`：`select(BrokerRecommend.month).distinct().order_by(BrokerRecommend.month.desc())`，返回 `[row[0] for row in result.all()]`（范式参照 fund_crowd_repository.get_report_periods）
  - `async def get_latest_month(self) -> Optional[date]`：get_months limit 1 取首项，空返回 None（AC-10，MAX(month)）
  - `async def get_stock_ranking(self, month: date, search: Optional[str], page: int, page_size: int) -> tuple[list, int]`（架构 §6.1 股票维度算法）：
    - 主查询：`select(BrokerRecommend.symbol, func.max(Stock.name).label('name'), func.count(func.distinct(BrokerRecommend.broker)).label('broker_count')).select_from(BrokerRecommend).outerjoin(Stock, Stock.symbol == BrokerRecommend.symbol).where(BrokerRecommend.month == month)`，search 时 `.where(or_(BrokerRecommend.symbol.like(search+'%'), Stock.name.ilike('%'+escaped+'%')))`（**OQ-escape**：symbol 前缀匹配用 `symbol.like(:search%)`，name 包含用 `ilike`；通配符用 `_escape_like_keyword` 转义，范式参照 shareholder_analysis_service.py line 37-42）
    - `.group_by(BrokerRecommend.symbol).order_by(func.count(func.distinct(BrokerRecommend.broker)).desc(), BrokerRecommend.symbol.asc()).limit(page_size).offset((page-1)*page_size)`（AC-07 双字段排序）
    - 总数查询：同 where + group by symbol 后 `select(func.count()).select_from(<子查询>)` 得 total（total = 符合条件的不同 symbol 数）
    - 返回 (rows, total)
  - `async def get_stock_brokers(self, month: date, symbols: list[str]) -> dict`：预加载（ADR-3）— `select(BrokerRecommend.symbol, BrokerRecommend.broker, BrokerRecommend.reason).where(BrokerRecommend.month == month, BrokerRecommend.symbol.in_(symbols))`，service 层聚合为 `{symbol: [{broker, reasons}]}`（同券商多 reason 归并去空去重，LIMIT 100 兜底见 service）
  - `async def get_broker_list(self, month: date, search: Optional[str], page: int, page_size: int) -> tuple[list, int]`（§6.1 券商维度算法）：`select(BrokerRecommend.broker, func.count(func.distinct(BrokerRecommend.symbol)).label('stock_count')).where(BrokerRecommend.month == month)`，search 时 `.where(BrokerRecommend.broker.ilike('%'+escaped+'%'))`，`.group_by(BrokerRecommend.broker).order_by(stock_count.desc(), BrokerRecommend.broker.asc())`，total = 符合条件的不同 broker 数
  - `async def get_broker_detail(self, month: date, broker: str) -> list`（§6.2）：`select(BrokerRecommend.symbol, Stock.name, BrokerRecommend.reason).select_from(BrokerRecommend).outerjoin(Stock, Stock.symbol == BrokerRecommend.symbol).where(BrokerRecommend.month == month, BrokerRecommend.broker == broker).order_by(BrokerRecommend.symbol.asc())`（broker 精确匹配 =，不做 LIKE，避免误匹配）

#### 2. 查询服务（`server/src/services/broker_recommend_analysis_service.py`）

范式参照 `server/src/services/fund_crowd_analysis_service.py`（`class FundCrowdAnalysisService`，`def __init__(self, session): self.session = session; self.repo = FundCrowdRepository(session)`，全部返回 snake_case dict，路由层 `_dict_to_camel` 转 camelCase）。

- import：`from src.repositories.broker_recommend_repository import BrokerRecommendRepository`、行业 JOIN helper（见下）、`from src.services.shareholder_analysis_service import _escape_like_keyword`（复用，line 37；或在本文件重新定义）
- `class BrokerRecommendAnalysisService`：
  - `def __init__(self, session): self.session = session; self.repo = BrokerRecommendRepository(session)`
  - 行业批量 JOIN：**复用** `shareholder_analysis_service.py` 的 `_get_industry_for_stocks`（显式 JOIN 无 ORM relationship，line 304-342：`SectorStock.stock_code == Stock.symbol AND Sector.code == SectorStock.sector_code AND Sector.type == 'industry'`）。因该方法是实例方法（self.session），09 service 内可定义同样的私有方法（复制 JOIN 逻辑），返回 `{symbol: {stock_name, industries}}`。import：`from src.models.sector import Sector`、`from src.models.sector_stock import SectorStock`、`from src.models.stock import Stock`、`from sqlalchemy import and_, select`
  - `_serialize_value(val)` / `_to_float(val)`：Decimal→float，None 保持，范式参照 shareholder_analysis_service.py line 45-51（数值字段必须 number，防字符串序列化破坏前端运算）
  - `async def get_months(self) -> dict`：`months = await self.repo.get_months()`；`has_data = len(months) > 0`；months 转 ISO 字符串列表（YYYY-MM-01 → "YYYY-MM-01"）；返回 `{"has_data": has_data, "months": [m.isoformat() for m in months]}`
  - `async def get_stock_ranking(self, month: Optional[str], search, page, page_size) -> dict`：
    1. month 缺省 → `latest = await self.repo.get_latest_month()`；latest 为 None → 返回 `{"has_data": False, "month": None, "items": [], "total": 0, "page": page, "page_size": page_size}`（AC-09）
    2. month 解析为 date（"YYYY-MM-01" → date）；search strip + `_escape_like_keyword`
    3. `rows, total = await self.repo.get_stock_ranking(month_date, search, page, page_size)`
    4. 行业批量：`industries_map = await self._get_industry_for_stocks([r.symbol for r in rows])`
    5. brokers 预加载：`brokers_map = await self.repo.get_stock_brokers(month_date, symbols)`；service 聚合同券商多 reason 到 `reasons: string[]`（去空去重，不丢弃）；LIMIT 100 兜底（ADR-3 单股百家极端）
    6. 组装 items（snake_case）：`{symbol, name, industries, broker_count, brokers}`；name 取 stocks JOIN（无匹配 None→前端 "—"）；industries 为空数组→前端 "—"
    7. 若 rows 为空（所选月无数据）→ items=[], total=0（AC 所选月无数据分支）
    8. 返回 `{"has_data": True, "month": month_date.isoformat(), "items": items, "total": total, "page": page, "page_size": page_size}`
  - `async def get_broker_list(self, month, search, page, page_size) -> dict`：同 stock_ranking latest_month 兜底；`rows, total = await self.repo.get_broker_list(...)`；items `{broker, stock_count}`；返回结构同上
  - `async def get_broker_detail(self, month: str, broker: str) -> dict`：month 解析 date；`rows = await self.repo.get_broker_detail(month_date, broker)`；同 symbol 多 reason 合并去空去重 → `reasons: string[]`（空数组前端 "—"，AC-13）；name 取 JOIN；返回 `{"items": [{symbol, name, reasons}]}`

#### 3. 用户侧 API（`server/src/api/v1/broker_recommend_analysis.py`）

范式**完全照搬** `server/src/api/v1/fund_crowd_analysis.py`（已读确认）。

- import：`from fastapi import APIRouter, Depends, Query`、`from pydantic import BaseModel, ConfigDict, Field`、`from pydantic.alias_generators import to_camel`、`from sqlalchemy.ext.asyncio import AsyncSession`、`from src.api.deps import get_current_user, get_session`、`from src.models.user import User`、`from src.services.broker_recommend_analysis_service import BrokerRecommendAnalysisService`
- `router = APIRouter(prefix="/broker-recommend-analysis", tags=["BrokerRecommendAnalysis"])`（kebab-case prefix，与 fund-crowd-analysis 一致）
- 复用 `fund_crowd_analysis.py` 的 `_serialize_value` + `_dict_to_camel` helper（line 104-129）——**直接复制**到本文件（或 import，但 fund 文件是模块级函数，复制更安全避免耦合）
- Pydantic 响应 model（snake_case 字段 + `model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)`，范式参照 fund_crowd_analysis.RankingItem）：
  - `StockRankingItem`（symbol/name:Optional[str]/industries:list[str]/broker_count:int/brokers:list[BrokerBrief]）
  - `BrokerBrief`（broker:str/reasons:list[str]）
  - `BrokerGroupItem`（broker:str/stock_count:int）
  - `BrokerDetailItem`（symbol:str/name:Optional[str]/reasons:list[str]）
  - 通用 `RankingData`（has_data/month:Optional[str]/total/page/page_size/items）
- 端点（全部 `current_user: User = Depends(get_current_user)` 普通用户认证，与 fund-crowd-analysis 一致；**query 参数 snake_case**）：
  - `@router.get("/months")` → `service.get_months()` → `{"success": True, "data": _dict_to_camel(result)}`
  - `@router.get("/stock-ranking")`：query `month: Optional[str] = Query(None)`（缺省取最新）、`search: Optional[str] = Query(None)`、`page: int = Query(1, ge=1)`、`page_size: int = Query(20, ge=1, le=100)` → `service.get_stock_ranking(...)` → 包裹返回
  - `@router.get("/broker-list")`：同上 query → `service.get_broker_list(...)`
  - `@router.get("/broker-detail")`：query `month: str = Query(...)`（必填）、`broker: str = Query(...)`（必填）→ `service.get_broker_detail(...)` → `{"success": True, "data": _dict_to_camel(result)}`
- 注册：`server/src/api/v1/__init__.py` 追加 `from .broker_recommend_analysis import router as broker_recommend_analysis_router` + `router.include_router(broker_recommend_analysis_router)  # /api/v1/broker-recommend-analysis/*`（范式参照 line 21/38）。

### 前后端契约四件套校验结论（架构 §7.3 + 锚点 fund_crowd_analysis.py / api.ts）

- **路径拼接**：前端 `apiClient.baseURL` 已含 `/api/v1`（api.ts line 9 `API_BASE_WITH_PREFIX`）。前端 endpoint 写 `/broker-recommend-analysis/stock-ranking`（不带 /v1），后端 router prefix `/broker-recommend-analysis` + v1 主路由 `/v1`，最终路径 `/api/v1/broker-recommend-analysis/stock-ranking`。✅ 无双前缀。
- **HTTP 方法存在性**：4 端点均为 GET；`apiClient.get` 继承自 `ApiClient`（api.ts line 33），携带 Authorization 头（getAuthHeaders，line 44 区域）。✅ 三方一致。
- **query 参数命名**：后端 FastAPI Query 定义 snake_case（`page_size`），前端 `brokerRecommendApi.getStockRanking` 写 query 时必须转 `page_size`（**不**写 `pageSize`）——FastAPI Query 不经 alias 转换，前端传错后端收不到。✅ 锚点 fundCrowdAnalysisApi（api.ts line 1079）已验证此约定，09 照抄。
- **响应字段命名**：后端 Pydantic 字段 snake_case（`broker_count`/`stock_count`），`ConfigDict(alias_generator=to_camel)` 转输出 camelCase（`brokerCount`/`stockCount`）；路由层额外 `_dict_to_camel` 把 service 返回的 snake_case dict 转 camelCase。前端消费 camelCase（plan-03 类型定义对齐 §7.2）。✅ 后端语言层变量名（snake）与 API 输出字段名（camel）分离，不混用。
- **序列化**：date → isoformat()（month 字段输出 "YYYY-MM-01"）；本功能无 Decimal 字段（broker_count/stock_count 为 int，func.count 结果），但 `_serialize_value` 保留以防行业 JOIN 引入。✅
- **响应包裹**：统一 `{success: true, data: {...}}`（与 fund-crowd-analysis 一致），前端解包 `res.data.data`。

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | 新建 BrokerRecommendRepository（4 方法：get_months/get_stock_ranking/get_broker_list/get_broker_detail + get_stock_brokers 预加载） | backend | done | 聚合/搜索/分页算法见实现规格 #1；search 用 _escape_like_keyword |
| 2 | 新建 BrokerRecommendAnalysisService（latest_month 兜底 + 行业 JOIN + brokers 预加载聚合 + 序列化） | backend | done | 范式参照 FundCrowdAnalysisService；行业 JOIN 复用 _get_industry_for_stocks |
| 3 | 新建 broker_recommend_analysis.py 路由（4 端点 + Pydantic models + _dict_to_camel helper） | backend | done | 范式照搬 fund_crowd_analysis.py；query snake_case |
| 4 | 注册 router 到 api/v1/__init__.py | backend | done | line 21/38 范式 |
| 5 | curl 验证 4 端点（双视图/搜索/分页/月份/空状态/懒加载） | backend | done | 由 38 pytest 用例覆盖（真实 test_session INSERT 数据 + 4 端点聚合验证） |

## 验收标准

### 股票维度验收（AC-02/03/06/07/10/11）

- [ ] AC-02 GET /stock-ranking 默认（不传 month）取 MAX(month) 最新月，items 按推荐券商家数（COUNT DISTINCT broker）降序；每行含 symbol/name（无匹配 null）/industries/broker_count/brokers
- [ ] AC-03 brokers 预加载随列表返回（无二次请求）；同一券商多条 reason 聚合到 reasons 数组不丢弃；展开数据加 LIMIT 100 兜底
- [ ] AC-06 total = 当前月份+搜索条件下的不同 symbol 总数（非当前页条数）；page/page_size 分页生效
- [ ] AC-07 双字段排序：股票 broker_count 相同按 symbol 升序
- [ ] AC-10 默认月份 = MAX(month)（YYYYMM 值最大者，不按同步时间）
- [ ] AC-11 股票维度 search 服务端全量重查（symbol LIKE 前缀 OR name ILIKE 包含）；无匹配 items=[] + total=0

### 券商维度验收（AC-04/06/07/12/13）

- [ ] AC-04 GET /broker-list 按 broker 分组、stock_count 降序；items {broker, stock_count}
- [ ] AC-07 券商 stock_count 相同按 broker 升序
- [ ] AC-12 券商 search（broker ILIKE 包含）服务端全量重查
- [ ] AC-13 GET /broker-detail（month+broker 必填，broker 精确匹配 =）返回 {items:[{symbol,name,reasons}]}；同 symbol 多 reason 合并去空去重；空数组前端 "—"

### 月份与空状态验收（AC-05/09）

- [ ] AC-05 GET /months 返回已同步月份降序 + has_data；前端可据此切换月份并回第 1 页
- [ ] AC-09 表无数据时 months/stock-ranking 返回 `has_data: false`，前端整页空状态；所选月无数据时 items=[] + total=0（前端"所选月份暂无数据"）

### 性能验收（架构 §8.1 目标）

- [ ] (架构 §8.1) GET /stock-ranking 与 /broker-list 响应时间 < 2s（实际预估 < 500ms，单月数百到数千行 GROUP BY + JOIN + 分页）；curl `-w '%{time_total}'` 人工确认
- [ ] (架构 §8.1) GET /broker-detail 响应时间 < 1s（单券商单月明细，预估 < 200ms）
- [ ] (架构 §8.1) GET /months 响应时间 < 500ms（DISTINCT month 查询）

### 安全（架构 §8.3）

- [ ] search 用参数绑定 + `_escape_like_keyword` 转义 %/_，防 SQL 注入
- [ ] broker-detail 的 broker 参数精确匹配（=），不做 LIKE
- [ ] 用户侧全只读（Depends(get_current_user) 普通用户即可访问，与 06/08 一致）

### 构建与类型

- [ ] `cd server && python -c "from src.api.v1.broker_recommend_analysis import router; from src.services.broker_recommend_analysis_service import BrokerRecommendAnalysisService; from src.repositories.broker_recommend_repository import BrokerRecommendRepository"` 无 ImportError
- [ ] `cd server && pytest -q`（既有测试不回归）

## 验证命令

```bash
# 1. import 与启动校验
cd server
python -c "from src.api.v1.broker_recommend_analysis import router; from src.services.broker_recommend_analysis_service import BrokerRecommendAnalysisService; print('ok')"
uvicorn src.main:app --reload

# 2. 4 端点 curl（需 plan-01 已同步至少一个月数据 + 普通用户 token）
TOKEN="<user_token>"

# 月份列表
curl "http://localhost:8000/api/v1/broker-recommend-analysis/months" -H "Authorization: Bearer $TOKEN"

# 股票维度排行（默认最新月）
curl "http://localhost:8000/api/v1/broker-recommend-analysis/stock-ranking?page=1&page_size=20" -H "Authorization: Bearer $TOKEN" | python -m json.tool

# 股票维度搜索 + 性能（架构 §8.1 < 2s）
curl -w '\ntime_total: %{time_total}s\n' "http://localhost:8000/api/v1/broker-recommend-analysis/stock-ranking?search=600&search=&page=1&page_size=20" -H "Authorization: Bearer $TOKEN"

# 券商维度分组
curl "http://localhost:8000/api/v1/broker-recommend-analysis/broker-list?page=1&page_size=20" -H "Authorization: Bearer $TOKEN" | python -m json.tool

# 券商明细懒加载（AC-13，性能 < 1s）
curl -w '\ntime_total: %{time_total}s\n' "http://localhost:8000/api/v1/broker-recommend-analysis/broker-detail?month=2026-05-01&broker=<某券商>" -H "Authorization: Bearer $TOKEN"

# 3. 既有测试不回归
pytest -q
```

端到端：本功能为后端 API，用户可观察性通过 curl 验证 4 端点覆盖（双视图/搜索/分页/月份/空状态/懒加载）；与 plan-03 前端集成后由前端 E2E 覆盖完整用户旅程。

## 交接上下文

- **架构章节**: §4.2（BrokerRecommendRepository + BrokerRecommendAnalysisService + 复用声明验证 stocks/sector JOIN）、§6.1（双视图加载算法）、§6.2（券商明细懒加载）、§7.2（Schema）、§7.3（API 边界 + 契约约定）、§8.1（性能目标）、§8.3（安全）、§9 Phase B
- **相关代码**:
  - 范式源：`server/src/api/v1/fund_crowd_analysis.py`（路由 + _dict_to_camel + Pydantic to_camel）、`server/src/services/fund_crowd_analysis_service.py`（service 构造）、`server/src/services/shareholder_analysis_service.py`（_get_industry_for_stocks line 304 + _escape_like_keyword line 37 + _to_float line 45）、`server/src/repositories/fund_crowd_repository.py`（BaseRepository 继承 + get_report_periods）
  - 本功能产出：`server/src/repositories/broker_recommend_repository.py`、`server/src/services/broker_recommend_analysis_service.py`、`server/src/api/v1/broker_recommend_analysis.py`
- **契约 / 数据对象**: §7.2 Schema（BrokerStockRankingItem/BrokerGroupItem/BrokerDetailItem/BrokerRankingResponse/BrokerMonthsResponse）；API 边界 §7.3
- **下游消费方**: **plan-03**（前端 brokerRecommendApi + 双视图组件）消费本功能 4 端点的 API 契约。前端类型定义必须与 §7.2 camelCase 一致。

## 风险与边界

- **执行顺序**: 按 Task 列表顺序执行。Task 2（service）依赖 Task 1（repository 方法）；Task 3（路由）依赖 Task 2（service）。
- **验证失败排查方向**:
  - stock-ranking 无 month 时返回 has_data=false → 检查 get_latest_month 是否为 None（表无数据，正常 AC-09）或 plan-01 未同步
  - total 与页内条数不一致 → 检查 total 查询是否用 group by symbol 的子查询 count（total = 不同 symbol 数，非 broker_recommend 行数）
  - search 不生效 → 检查 query 参数是否 snake_case（前端传 pageSize 后端收不到），或 LIKE 未转义
  - brokers 预加载膨胀 → 检查 LIMIT 100 兜底是否生效（ADR-3）
  - 行业 JOIN 重复 → _get_industry_for_stocks 一股多行业返回数组，前端逗号展示
- **允许修改的额外文件**: 无
- **暂停条件**: 无（plan-01 同步已就绪，Tushare 积分已满足；若需独立验证聚合逻辑，可手工 INSERT 测试数据）
- **E2E 不适用说明**: 本功能为纯后端 API，无前端 UI。用户可观察性通过 curl 4 端点验证覆盖（双视图/搜索/分页/月份/空状态/懒加载）。与 plan-03 集成后由前端 E2E（mock 本功能 API）覆盖完整 AC-02~AC-13 用户旅程。
- **风险备注**:
  - 搜索 LIKE 注入已通过 `_escape_like_keyword` 兜底（ADR-4）
  - brokers 预加载 LIMIT 100 兜底单股百家极端（ADR-3）
  - 性能（架构 §8.1）依赖索引（plan-01 已建 (symbol,month)+(broker,month)+(month)），实时聚合 < 500ms，无需缓存（ADR-6）

### 后端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| 表无数据（从未同步） | months/stock-ranking 返回 has_data=false | todo |
| 所选月无数据 | items=[] + total=0 | todo |
| month 缺省 | latest_month 兜底（MAX(month)） | todo |
| search 无匹配 | items=[] + total=0 | todo |
| 股票无 name（stocks 未覆盖） | name=null（前端 "—"），不影响 broker_count | todo |
| 股票无行业 | industries=[]（前端 "—"），不影响排序 | todo |
| 同券商多条 reason | 聚合到 reasons 数组去空去重不丢弃 | todo |
| 单股百家推荐（极端） | brokers LIMIT 100 兜底 | todo |
| broker-detail broker 误匹配 | broker 精确匹配 =，不做 LIKE | todo |
| search LIKE 注入 | _escape_like_keyword 转义 %/_ | todo |

### 前端边界场景

无（本功能无前端代码）。
