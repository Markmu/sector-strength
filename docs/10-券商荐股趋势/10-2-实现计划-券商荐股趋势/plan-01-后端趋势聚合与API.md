---
feat_id: "plan-01"
title: "后端趋势聚合与趋势 API（repository 3 方法 + service 趋势聚合 + 1 个 v1 端点）"
dimension: backend
phase: 1
status: done
depends_on: []
---

# plan-01: 后端趋势聚合与趋势 API

## 功能概要

- **目标**: 交付券商荐股"推荐趋势"视图的后端：在 09 已有的 `BrokerRecommendRepository` 新增 3 个跨月聚合方法、在 `BrokerRecommendAnalysisService` 新增 `get_trend_ranking`（连续性计算 + 多级排序 + 分页 + 行业 JOIN + 展开券商预加载）、在用户侧路由新增 `GET /trend-ranking` 端点。完成后前端（plan-02）可消费趋势榜 API 契约。
- **完成后可观察结果**: 对 `broker_recommend` 表做 curl 请求 `GET /api/v1/broker-recommend-analysis/trend-ranking`：返回跨全部已同步月份聚合的趋势榜，items 按"连续被推荐月数"降序（多级排序：连续月数↓→累计家数↓→最新月家数↓→代码↑），每项含 symbol/name/industries/consecutiveMonths/cumulativeBrokerCount/latestMonthBrokerCount/monthlySeries（折线图数据源，旧→新升序）/monthlyBrokers（展开明细，新→旧降序，含各月前 3 券商）。响应 `{success:true, data:{...}}` 包裹，data 字段 camelCase，query 参数 snake_case（无 month 参数，趋势固定全窗口）。无数据时 hasData=false；仅单月时连续月数均为 1；搜索为服务端全量重查，分页 total 与搜索条件一致。
- **依赖**: 无（复用 09 已有的 `broker_recommend` 表、`BrokerRecommend` 模型、`BrokerRecommendAnalysisService` 类、`broker_recommend_analysis.py` 路由）
- **关联验收标准**: [AC-02, AC-03, AC-04, AC-06, AC-07, AC-08, AC-09, AC-11, AC-12]
- **涉及架构模块**: BrokerRecommendRepository（扩展）、BrokerRecommendAnalysisService（扩展）、趋势 API 端点（架构 §4.2 / §6.1 / §7.2 / §7.3 / §9 Phase A）
- **前置条件**: 09 plan-01/02/03 已完成（`broker_recommend` 表可读写、至少一个月数据已同步）；`server/src/services/broker_recommend_analysis_service.py`、`server/src/repositories/broker_recommend_repository.py`、`server/src/api/v1/broker_recommend_analysis.py` 现有范式可参照（含已读确认的行号）
- **不在范围**: 前端趋势视图（plan-02）；数据同步（沿用 09）；缓存层（ADR-7 不做）；时间窗口切换（不做，固定全窗口）；券商维度趋势（不做）

## 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| modify | `server/src/repositories/broker_recommend_repository.py` | 新增 3 个跨月聚合方法：get_trend_aggregations / get_trend_cumulative_counts / get_trend_brokers |
| modify | `server/src/services/broker_recommend_analysis_service.py` | 新增 get_trend_ranking（连续性计算 + 多级排序 + 分页 + 行业 + 展开券商预加载） |
| modify | `server/src/api/v1/broker_recommend_analysis.py` | 新增 GET /trend-ranking 端点 + 4 个 Pydantic 响应 model（TrendMonthPoint/TrendMonthBroker/TrendRankingItem/TrendRankingData） |

## 实现规格

### 后端部分

#### 1. Repository 扩展（`server/src/repositories/broker_recommend_repository.py`）

在现有 `BrokerRecommendRepository` 类内新增 3 个方法。继承与 import 已就绪（`BaseRepository[BrokerRecommend]`，`from sqlalchemy import and_, func, or_, select`，`from src.models.stock import Stock`，`from src.services.shareholder_analysis_service import _escape_like_keyword`）。

**搜索过滤公共 WHERE（架构链路 6.1 累计家数算法约束）**：三个方法凡涉及 search 的，搜索条件必须完全同口径（`symbol LIKE :search% OR name ILIKE %:search%`，name 来自 LEFT JOIN stocks），抽公共条件构建避免主聚合与累计家数两查询命中不同 symbol 集合。

- `async def get_trend_aggregations(self, all_months: list[date], search: Optional[str]) -> list`：
  - 跨月 `GROUP BY symbol, month` + `COUNT(DISTINCT broker)`，返回窗口内所有 `(symbol, month, broker_count)` 三元组（Python 阶段连续性计算的数据源）
  - SQL：`select(BrokerRecommend.symbol, BrokerRecommend.month, func.count(func.distinct(BrokerRecommend.broker)).label("broker_count")).select_from(BrokerRecommend).outerjoin(Stock, Stock.symbol == BrokerRecommend.symbol).where(BrokerRecommend.month.in_(all_months))`；search 时追加 `.where(or_(BrokerRecommend.symbol.like(escaped + "%"), Stock.name.ilike("%" + escaped + "%")))`（escaped = `_escape_like_keyword(search)`）
  - `.group_by(BrokerRecommend.symbol, BrokerRecommend.month)`
  - 返回 `result.all()`（每行可按 row.symbol / row.month / row.broker_count 访问）

- `async def get_trend_cumulative_counts(self, all_months: list[date], search: Optional[str]) -> dict`：
  - 跨月 `GROUP BY symbol` + `COUNT(DISTINCT broker)`（累计去重家数）
  - SQL：`select(BrokerRecommend.symbol, func.count(func.distinct(BrokerRecommend.broker)).label("cumulative_count")).select_from(BrokerRecommend).outerjoin(Stock, Stock.symbol == BrokerRecommend.symbol).where(BrokerRecommend.month.in_(all_months))`；search 追加同口径条件
  - `.group_by(BrokerRecommend.symbol)`
  - 返回 `{row.symbol: row.cumulative_count for row in result.all()}`

- `async def get_trend_brokers(self, all_months: list[date], symbols: list[str]) -> dict`：
  - 当页股票窗口内全部 `(symbol, month, broker)`，供 service 按 (symbol, month) 分组取前 3
  - 若 symbols 为空返回 `{}`
  - SQL：`select(BrokerRecommend.symbol, BrokerRecommend.month, BrokerRecommend.broker).where(BrokerRecommend.month.in_(all_months), BrokerRecommend.symbol.in_(symbols))`
  - 返回 `{(symbol, month): [broker, ...]}`（service 层按需取前 3 + 计数）

#### 2. 查询服务扩展（`server/src/services/broker_recommend_analysis_service.py`）

在现有 `BrokerRecommendAnalysisService` 类内新增 `get_trend_ranking`。import 已就绪（`from datetime import date, datetime`，行业 JOIN `_get_industry_for_stocks`，`_to_float`）。

- `async def get_trend_ranking(self, search: Optional[str], page: int, page_size: int) -> dict`：
  1. **窗口月份序列**：`months = await self.repo.get_months()`（09 已有方法，DISTINCT month DESC）；`months` 为空 → 返回 `{"has_data": False, "total": 0, "page": page, "page_size": page_size, "items": []}`（AC-12 复用 09 整页空状态）
  2. **SQL 取数**：`escaped_search = _escape_like_keyword(search.strip()) if search else None`；`aggregations = await self.repo.get_trend_aggregations(months, escaped_search)`；`cumulative_map = await self.repo.get_trend_cumulative_counts(months, escaped_search)`
  3. **Python 阶段构建 symbol → {month: broker_count}**：遍历 aggregations，构建 `stock_month_counts: dict[str, dict[date, int]]`（每个 symbol 的各月家数映射）
  4. **连续性计数（ADR-3 算法，AC-07）**：对每只股票，从 `months[0]`（全局最新月）沿 `months` 序列向前遍历，该月有记录（broker_count > 0）则 consecutive +1，遇到无记录月即 break：
     ```
     for symbol, month_counts in stock_month_counts.items():
         consecutive = 0
         for m in months:              # months 已是降序（最新月在前）
             if m in month_counts:
                 consecutive += 1
             else:
                 break
         # 注意：若该股在 months[0] 无记录，consecutive 为 0
     ```
     沿"已同步月份序列"（months）而非自然月，确保窗口内非连续自然月场景正确。
  5. **计算其余指标**：
     - `cumulative_broker_count` = `cumulative_map.get(symbol, 0)`
     - `latest_month_broker_count` = `month_counts.get(months[0], 0)`（最新月家数，与 09 股票维度同月同口径，AC-04 天然一致）
     - `monthly_series`：按 `months` 升序（旧→新，reverse months 后遍历）构建 `[{month: m.isoformat(), broker_count: month_counts.get(m, 0)}]`（窗口内全部已同步月份，无推荐的月份 broker_count=0）
  6. **多级排序（AC-03）**：对 stock 列表按 `consecutive_months DESC, cumulative_broker_count DESC, latest_month_broker_count DESC, symbol ASC` 排序（Python `sorted(key=lambda x: (-x.consecutive, -x.cumulative, -x.latest, x.symbol))`）
  7. **分页（AC-08）**：`total = len(sorted_list)`；`offset = (page-1)*page_size`；`page_items = sorted_list[offset:offset+page_size]`
  8. **当页补充数据**：
     - 行业：`symbols = [s.symbol for s in page_items]`；`industries_map = await self._get_industry_for_stocks(symbols)`（复用 09，L42-87）
     - 展开券商：`brokers_map = await self.repo.get_trend_brokers(months, symbols)`；按 (symbol, month) 分组，对每月取前 3 家 broker 名（`top_brokers`）
  9. **组装 items（snake_case，路由层转 camelCase）**：每项 `{symbol, name, industries, consecutive_months, cumulative_broker_count, latest_month_broker_count, monthly_series, monthly_brokers}`：
     - name 取 `industries_map[symbol]["stock_name"]`（无匹配 None）
     - monthly_brokers 按 months 降序（新→旧）构建 `[{month, broker_count, top_brokers}]`，broker_count 取 month_counts，top_brokers 取 brokers_map[(symbol, month)] 前 3（无记录则空数组）
  10. 返回 `{"has_data": True, "total": total, "page": page, "page_size": page_size, "items": items}`

**可观测性（架构 §8.5）**：service 层在异常时 logger.warning 记录（范式参照 09 既有 service 的 logging）。趋势聚合为只读查询，无任务日志需求。

#### 3. API 端点（`server/src/api/v1/broker_recommend_analysis.py`）

在现有路由文件追加端点与 Pydantic model。复用既有 `_dict_to_camel` / `_serialize_value` helper（L141-166）、`Depends(get_current_user)` 认证。

- Pydantic 响应 model（snake_case 字段 + `model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)`，范式参照 09 既有 `StockRankingItem`）：
  - `TrendMonthPoint`：`month: str` / `broker_count: int`
  - `TrendMonthBroker`：`month: str` / `broker_count: int` / `top_brokers: list[str] = Field(default_factory=list)`
  - `TrendRankingItem`：`symbol: str` / `name: Optional[str]` / `industries: list[str]` / `consecutive_months: int` / `cumulative_broker_count: int` / `latest_month_broker_count: int` / `monthly_series: list[TrendMonthPoint]` / `monthly_brokers: list[TrendMonthBroker]`
  - `TrendRankingData`：`has_data: bool` / `total: int` / `page: int` / `page_size: int` / `items: list[TrendRankingItem] = Field(default_factory=list)`
- 端点：
  ```python
  @router.get("/trend-ranking")
  async def get_trend_ranking(
      search: Optional[str] = Query(None, description="股票代码前缀或名称包含"),
      page: int = Query(1, ge=1, description="页码"),
      page_size: int = Query(20, ge=1, le=100, description="每页条数"),
      current_user: User = Depends(get_current_user),
      session: AsyncSession = Depends(get_session),
  ):
      service = BrokerRecommendAnalysisService(session)
      result = await service.get_trend_ranking(search, page, page_size)
      return {"success": True, "data": _dict_to_camel(result)}
  ```
  注意：**无 month 参数**（趋势固定全窗口，架构 §7.3）。

### 前后端契约四件套校验结论（架构 §7.3 + 锚点 09 既有路由 / api.ts）

- **路径拼接**：前端 `apiClient.baseURL` 已含 `/api/v1`。前端 endpoint 写 `/broker-recommend-analysis/trend-ranking`（不带 /v1），后端 router prefix `/broker-recommend-analysis` + v1 主路由 `/api/v1`，最终路径 `/api/v1/broker-recommend-analysis/trend-ranking`。✅ 无双前缀。
- **HTTP 方法存在性**：GET 端点；`apiClient.get` 继承自 `ApiClient`，携带 Authorization 头。✅ 与 09 既有 4 端点一致。
- **query 参数命名**：后端 FastAPI Query 定义 snake_case（`page_size`），前端 `brokerRecommendApi.getTrendRanking` 写 query 时必须传 `page_size`（**不**写 `pageSize`）——FastAPI Query 不经 alias 转换。✅ 锚点 09 `brokerRecommendApi.getStockRanking` 已验证此约定。
- **响应字段命名**：后端 Pydantic 字段 snake_case（`consecutive_months`/`cumulative_broker_count`/`latest_month_broker_count`/`monthly_series`/`monthly_brokers`），`ConfigDict(alias_generator=to_camel)` 转输出 camelCase（`consecutiveMonths`/`cumulativeBrokerCount`/`latestMonthBrokerCount`/`monthlySeries`/`monthlyBrokers`）；路由层 `_dict_to_camel` 把 service 返回的 snake_case dict 递归转 camelCase。前端消费 camelCase（plan-02 类型定义对齐架构 §7.2）。✅ 后端语言层变量名（snake）与 API 输出字段名（camel）分离。
- **序列化**：month 字段 → isoformat()（"YYYY-MM-01"）；本功能数值均为 int（consecutive_months/cumulative_broker_count/latest_month_broker_count/broker_count），无 Decimal 风险；`_serialize_value` 递归处理嵌套 dict/list。✅
- **响应包裹**：统一 `{success: true, data: {...}}`，前端解包 `res.data.data`。✅

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | Repository 新增 get_trend_aggregations（跨月 GROUP BY symbol,month + COUNT DISTINCT broker + search） | backend | done | 数据源为 09 broker_recommend 表；search 用 _escape_like_keyword |
| 2 | Repository 新增 get_trend_cumulative_counts（跨月 GROUP BY symbol + COUNT DISTINCT broker + 同口径 search） | backend | done | 必须与 #1 搜索条件同口径，抽公共 WHERE |
| 3 | Repository 新增 get_trend_brokers（当页 symbols 窗口内 (symbol,month,broker)） | backend | done | 供 service 按 (symbol,month) 分组取前 3 |
| 4 | Service 新增 get_trend_ranking（连续性计数 ADR-3 + 多级排序 AC-03 + 分页 AC-08 + 行业 JOIN + 展开券商预加载） | backend | done | 核心算法见实现规格 #2；Python 阶段计算 |
| 5 | API 新增 GET /trend-ranking 端点 + 4 个 Pydantic model（TrendMonthPoint/TrendMonthBroker/TrendRankingItem/TrendRankingData） | backend | done | 范式参照 09 既有端点；query snake_case；无 month 参数 |
| 6 | curl 验证趋势端点（连续月数/多级排序/搜索/分页/单月降级/空状态/口径一致） | backend | done | 由 plan-01 pytest 覆盖（test_session INSERT 多月数据 + 趋势聚合验证） |

## 验收标准

### 趋势聚合验收（AC-02/03/04/07/09）

- [ ] AC-02 GET /trend-ranking 跨全部已同步月份聚合，items 按 consecutiveMonths 降序；每项含 symbol/name（无匹配 null）/industries/consecutiveMonths/cumulativeBrokerCount/latestMonthBrokerCount/monthlySeries/monthlyBrokers；仅含窗口内至少被推荐过一次的股票
- [ ] AC-03 多级排序：consecutiveMonths 相同时按 cumulativeBrokerCount 降序；再相同按 latestMonthBrokerCount 降序；最后按 symbol 升序
- [ ] AC-04 latestMonthBrokerCount 与 09 股票维度排行同月 broker_count 一致（均按券商名称 COUNT DISTINCT 去重）
- [ ] AC-07 连续月数从最新已同步月份向前不间断计数，遇断档即停；断档前的更早月份仍参与 cumulativeBrokerCount 与 monthlySeries
- [ ] AC-09 search 服务端全量重查（symbol LIKE 前缀 OR name ILIKE 包含）；无匹配 items=[] + total=0

### 分页与展开验收（AC-06/08）

- [ ] AC-06/08 total = 全窗口+搜索条件下的股票总数（非当前页条数）；page/page_size 分页生效；monthlyBrokers 含各月家数与前 3 券商（随列表预加载，无二次请求）

### 降级验收（AC-11/12）

- [ ] AC-11（单月）仅一个已同步月份时正常返回，consecutiveMonths 均为 1，monthlySeries 仅一个数据点，落入次级排序
- [ ] AC-12 broker_recommend 表无数据时 hasData=false（前端整页空状态，复用 09）

### E2E / 集成验收

- [ ] pytest 用例覆盖趋势聚合（test_session INSERT 多月 broker_recommend 数据，断言连续月数/累计家数/最新月家数/走势序列/多级排序/搜索/分页/单月/空状态）
- [ ] curl 实测：跨月数据下，榜首股票为"最新月有推荐且从最新月向前连续最久"的股票

### 性能验收（架构 §8.1 目标）

- [ ] GET /trend-ranking 响应时间 < 2s（窗口内数万行聚合 + Python 连续性计算上千股 + 排序分页，预估 < 500ms，DevTools Network 面板人工确认）

## 验证命令

```bash
cd server
# 单元测试（pytest，--asyncio-mode=auto，覆盖趋势聚合）
pytest tests/ -k "trend" -v

# 启动后端，curl 验证端点（需先有同步数据）
uvicorn src.main:app --reload
# 另开终端：
# curl -H "Authorization: Bearer <token>" "http://localhost:8000/api/v1/broker-recommend-analysis/trend-ranking?page=1&page_size=20"
# curl 带 search：
# curl -H "Authorization: Bearer <token>" "http://localhost:8000/api/v1/broker-recommend-analysis/trend-ranking?search=600519"
```

端到端测试由 plan-02 前端 E2E 覆盖（趋势视图 UI + 后端契约联调）；本功能为纯后端 API，pytest 是主质量门，curl 为辅助验证。

## 交接上下文

- **架构章节**: §4.2 模块职责（Repository/Service/API 扩展点）、§6.1 趋势榜加载链路（核心算法）、§7.2 最小 Schema（TrendRankingItem 等）、§7.3 API 边界（/trend-ranking）、§9 Phase A
- **相关代码**:
  - `server/src/repositories/broker_recommend_repository.py`（扩展目标，现有方法 get_months/get_stock_ranking/get_stock_brokers 等可参照）
  - `server/src/services/broker_recommend_analysis_service.py`（扩展目标，现有 _get_industry_for_stocks/_to_float/_resolve_month 可复用）
  - `server/src/api/v1/broker_recommend_analysis.py`（扩展目标，现有 _dict_to_camel/_serialize_value/StockRankingItem 等范式可参照）
  - `server/src/models/broker_recommend.py`（09 模型，字段 month/symbol/broker/reason）
- **契约 / 数据对象**: TrendRankingItem（架构 §7.2）；GET /trend-ranking（架构 §7.3，参数 search/page/page_size，无 month）
- **下游消费方**: plan-02（前端 `brokerRecommendApi.getTrendRanking` + `useBrokerTrendRanking` hook + `BrokerTrendRanking` 组件 + `Sparkline` 组件）
- **复用声明调用细节**:
  - 复用 `_escape_like_keyword`：`from src.services.shareholder_analysis_service import _escape_like_keyword`（09 已用，search 通配符转义）
  - 复用 `_get_industry_for_stocks`：本类实例方法（L42-87），签名 `(symbols: list[str], sector_type='industry')`，返回 `{symbol: {stock_name, industries}}`
  - 复用 `_to_float`：本类静态方法（L91-98）
  - 复用 `_dict_to_camel` / `_serialize_value`：路由文件模块级函数（L141-166）
  - 复用 `get_months`：本类 repo 方法（09 已有），返回 list[date] 降序
  - 复用 `BaseRepository[BrokerRecommend]`：09 repo 已继承，新增方法直接加在同类内

## 风险与边界

- **执行顺序**: 按 Task 列表顺序执行（#1→#2→#3 repo 三方法 → #4 service → #5 API → #6 验证）。repo #1/#2 搜索条件必须同口径（架构链路 6.1 约束）。
- **验证失败排查方向**: ①连续月数异常 → 检查是否沿 `months` 降序序列而非自然月计数；②累计家数与主聚合结果不一致 → 检查两查询搜索条件是否同口径；③latestMonthBrokerCount 与 09 不一致 → 检查是否用 `months[0]`（全局最新月）而非该股最后被推荐月；④camelCase 输出异常 → 检查 `_dict_to_camel` 是否递归处理 monthlySeries/monthlyBrokers 嵌套。
- **允许修改的额外文件**: `server/tests/`（新增趋势聚合 pytest 用例，范式参照 09 既有 service 测试）
- **暂停条件**: 发现 09 既有 `broker_recommend` 表实际字段与 `BrokerRecommend` 模型不符（阻塞，需回查 09 迁移）
- **E2E 不适用说明**: 本功能为纯后端 API，无独立 UI；用户可观察验证由 plan-02 E2E 覆盖（趋势视图 UI 联调）。本功能质量门为 pytest + curl。
- **风险备注**: ①连续月数是序列连续性问题，纯 SQL 难表达，Python 计算是正确选择但需测试覆盖断档场景（AC-07）；②窗口内股票全量加载到内存排序分页，数据量 < 1MB 可控，但需 pytest 用大窗口数据验证性能。

### 后端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| broker_recommend 表无数据 | get_months 返回空 → hasData=false（AC-12） | done |
| 仅一个已同步月份 | 连续月数均为 1，monthlySeries 单点（AC-11） | done |
| 某股窗口中间断档 | 连续月数从最新月向前计到断档即停；累计家数与走势序列仍含断档前月份（AC-07） | done |
| 某股最新月无推荐 | 连续月数为 0，但仍出现在榜中（若历史有推荐），按次级排序靠后 | done |
| 搜索无匹配 | items=[] + total=0（AC-09） | done |
| search 含 LIKE 通配符 %/_ | `_escape_like_keyword` 转义防注入 | done |
| 主聚合与累计家数两查询搜索条件不一致 | 抽公共 WHERE 片段复用，禁止各自手写（架构链路 6.1 约束） | done |
| monthlyBrokers 某 month 无券商 | top_brokers 空数组，broker_count=0 | done |
