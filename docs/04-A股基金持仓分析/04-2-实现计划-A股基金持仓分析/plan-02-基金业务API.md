---
feat_id: "plan-02"
title: "基金业务 API"
dimension: backend
phase: 1
status: review
depends_on: ["plan-01"]
---

# plan-02: 基金业务 API

## 功能概要

- **目标**: 实现基金模块的 4 个 GET 业务端点（基金列表、基金详情、基金持仓、股票反查），向 `web` 前端提供符合架构 §7.3 契约的 JSON 响应。
- **完成后可观察结果**: 启动后端后，访问 `GET /api/v1/funds?search=沪深300&market=E&page=1&pageSize=20` 返回 200 响应，包含分页结构 `{data, total, page, pageSize}`，搜索/过滤/分页均生效；访问 `GET /api/v1/funds/510300.SH/portfolio` 返回该基金最新一期持仓（按 stk_mkv_ratio DESC）；访问 `GET /api/v1/funds/reverse-lookup?symbol=600519&page=1&pageSize=20` 返回重仓基金列表（仅占净值比 ≥ 1%）。无数据时返回空数组而非 404。
- **依赖**: plan-01（依赖 `Fund` / `FundPortfolio` 模型 + `BaseRepository`）
- **关联验收标准**: [AC-01, AC-02, AC-03, AC-04]
- **涉及架构模块**: FundAPI、FundRepository（架构 §4.2）
- **前置条件**:
  - plan-01 已完成（模型已建、Alembic 已迁移）
  - `BaseRepository` 已在 `server/src/repositories/base.py` 存在
  - `stocks` 表已存在并含 A 股全市场股票（依赖项目 03 的 stock_basic 同步；架构 §4.2 复用声明验证项）
  - `ApiResponse[T]` 包装在 `server/src/api/schemas/response.py` 已存在
  - `get_session` 依赖在 `server/src/api/deps.py` 已存在
- **不在范围**:
  - 管理员同步 API（POST 类，由 plan-03 负责）
  - 同步数据写入（由 plan-01 负责）
  - 前端 UI（由 plan-04、plan-05 负责）

## 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| create | `server/src/repositories/fund_repository.py` | `FundRepository(BaseRepository[Fund])`，含 `list_with_filters`、`get_by_ts_code`、`get_latest_portfolio`、`reverse_lookup` 方法 |
| create | `server/src/api/v1/funds.py` | 新建 funds router，4 个 GET 端点 |
| modify | `server/src/api/v1/router.py` | 注册新 router |

### 前端维度

无。

## 实现规格

### 后端部分

#### 1. FundRepository（`server/src/repositories/fund_repository.py`）

- `class FundRepository(BaseRepository[Fund])`
- `async def list_with_filters(self, search: str | None, market: str | None, fund_type: str | None, page: int, page_size: int) -> tuple[list[Fund], int]`
  - 构造 WHERE 子句：
    - `search` 不为空时：`(Fund.ts_code.ilike(f"{search}%")) | (Fund.name.ilike(f"%{search}%"))`（**不区分大小写**，使用 `ilike`；架构 §6.1 修复项）
    - `market` 不为空时：`Fund.market == market`
    - `fund_type` 不为空时：`Fund.fund_type == fund_type`
  - **L1 降级支持（架构 §6.2 step 7）**：列表需标注"暂无数据"给无持仓基金，但不 JOIN fund_portfolio（架构 §6.1）。实现方案：在列表查询中增加轻量子查询 `has_portfolio = EXISTS(SELECT 1 FROM fund_portfolio WHERE fund_ts_code = Fund.ts_code)`，利用 `(fund_ts_code, report_period)` 联合索引，性能可控
  - `ORDER BY Fund.ts_code ASC`（架构 §6.1 step 4 / BR-03）
  - `LIMIT page_size OFFSET (page - 1) * page_size`
  - 返回 `(items, total)`
- `async def get_by_ts_code(self, ts_code: str) -> Fund | None`
  - 简单按主键（业务键）查询
- `async def get_latest_portfolio(self, fund_ts_code: str, page: int, page_size: int) -> tuple[list[dict], dict]`
  - 子查询取 `MAX(report_period) FROM fund_portfolio WHERE fund_ts_code = :fund_ts_code`（架构 §6.2 step 3）
  - 主查询 `WHERE fund_ts_code = :fund_ts_code AND report_period = (子查询)`
  - LEFT JOIN `stocks` 表 ON `stocks.symbol = fund_portfolio.stock_symbol`，取 `stocks.name AS stock_name`（架构 §6.2 step 5）
  - `ORDER BY stk_mkv_ratio DESC NULLS LAST`
  - 分页同上
  - **关键返回**：附带元信息 `{"is_portfolio_empty": <bool>, "has_portfolio": <bool>, "latest_report_period": <str | null>, "latest_ann_date": <str | null>}`，供前端区分"Tushare 未收录（场景 A）"与"最新期未披露（场景 B）"
    - `is_portfolio_empty = (total == 0)` — 当前查询（最新报告期）返回为空
    - `has_portfolio = EXISTS(SELECT 1 FROM fund_portfolio WHERE fund_ts_code = :fund_ts_code)` — 该基金是否有任何历史持仓记录
    - `latest_report_period = (SELECT MAX(report_period) FROM fund_portfolio WHERE fund_ts_code = :fund_ts_code) OR NULL` — 该基金最新已有报告期（供前端标题展示）
    - `latest_ann_date = (SELECT ann_date FROM fund_portfolio WHERE fund_ts_code = :fund_ts_code AND report_period = (SELECT MAX(report_period) FROM fund_portfolio WHERE fund_ts_code = :fund_ts_code) ORDER BY ann_date DESC NULLS LAST LIMIT 1) OR NULL` — 该基金最新已有报告期的公告日（按 ann_date DESC 取最新一次公告，NULL 时返回 null）
- `async def reverse_lookup(self, symbol: str, page: int, page_size: int) -> tuple[list[dict], int]`
  - 先查 `stocks` 表确认 symbol 存在，获取 `stock_name`（架构 §6.3 step 2）
  - 主查询：`WHERE fund_portfolio.stock_symbol = :symbol AND stk_mkv_ratio >= 1.0 AND report_period = (SELECT MAX(report_period) FROM fund_portfolio)`（架构 §6.3 step 3 + BR-07 阈值）
  - JOIN `funds` 表取 `funds.name AS fund_name / funds.fund_type / funds.management`（架构 §6.3 step 4）
  - `ORDER BY stk_mkv_ratio DESC NULLS LAST`
  - 分页同上
  - **symbol 格式处理**：接受纯数字（如 "600519"）或带后缀（如 "600519.SH"）；后端统一去除后缀后再拼接 `.SH/.SZ` 优先匹配（架构 §8.6 风险表"股票代码格式不一致"对策）
  - **关键返回**：附带元信息 `{"stock_name": <str | null>, "report_period": <str | null>}`，供前端反查页标题展示股票名称与最新报告期

#### 2. 业务路由（`server/src/api/v1/funds.py`）

- `router = APIRouter(prefix="/funds", tags=["Funds"])`
- 4 个 GET 端点：

| 端点 | 入参 | 出参 |
| --- | --- | --- |
| `GET /funds` | `search: str \| None`、`market: str \| None`、`fund_type: str \| None`、`page: int = 1`、`page_size: int = 20` | `ApiResponse[PaginatedResponse[FundOut]]` |
| `GET /funds/{ts_code}` | `ts_code: str` | `ApiResponse[FundOut]` |
| `GET /funds/{ts_code}/portfolio` | `ts_code: str`、`page: int = 1`、`page_size: int = 20` | `ApiResponse[PortfolioResponse]`（`PortfolioResponse = {data: list[FundPortfolioOut], total, page, pageSize, isPortfolioEmpty, hasPortfolio, latestReportPeriod, latestAnnDate}`） |
| `GET /funds/reverse-lookup` | `symbol: str`、`page: int = 1`、`page_size: int = 20` | `ApiResponse[ReverseLookupResponse]`（`ReverseLookupResponse = {data: list[ReverseLookupItem], total, page, pageSize, stockName, reportPeriod}`） |

- 字段命名：API 响应采用 **camelCase**（架构 §7.6 明确）；通过 Pydantic `model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)` 或自定义序列化实现
- 字段数据来源标注（架构 §7.3 末段）：
  - `search` / `symbol`：user_input
  - `market` / `fundType` / `period`：frontend_computed
  - `page` / `pageSize`：frontend_computed
- 列表默认 `page_size=20`（架构 §2.3 成功标准）
- 性能：所有端点走索引（`funds.ts_code` 唯一、`fund_portfolio(fund_ts_code, report_period)` 与 `(stock_symbol, report_period)` 联合索引）

#### 3. 注册路由（`server/src/api/v1/router.py`）

- 在现有 v1 router 中追加：`from src.api.v1.funds import router as funds_router` + `router.include_router(funds_router)`

#### 4. 安全要求（架构 §8.3 传播）

- 业务 API 走 `_user = Depends(get_current_user)` 强制登录（架构 §8.3 "前端业务 API 需登录后访问"）
- 所有查询走 SQLAlchemy 参数化（无字符串拼接）

#### 5. 可观测性（架构 §8.5 传播）

- 业务 API 不写 AsyncTask（无后台任务），无需 progress callback
- 失败时使用项目统一错误处理（参考 `server/src/api/error_handlers.py`），返回稳定 `ApiResponse.error` 结构

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | 创建 `FundRepository` | backend | done | `server/src/repositories/fund_repository.py`，4 个方法 |
| 2 | 实现列表端点 `GET /funds` | backend | done | 含 search/market/fundType/page/pageSize 5 个参数 |
| 3 | 实现详情端点 `GET /funds/{ts_code}` | backend | done | 单条 Fund 查询 |
| 4 | 实现持仓端点 `GET /funds/{ts_code}/portfolio` | backend | done | 含 `isPortfolioEmpty / hasPortfolio / latestReportPeriod` 元信息（与 §1 元信息结构对齐） |
| 5 | 实现反查端点 `GET /funds/reverse-lookup` | backend | done | 阈值 1% 在 SQL 过滤；symbol 格式归一化 |
| 6 | 注册 funds router | backend | done | `server/src/api/v1/__init__.py` 追加 include_router |

## 验收标准

### 后端验收

- [ ] AC-01 `GET /api/v1/funds?search=沪深300&page=1&pageSize=20` 返回 200，分页结构正确；search 命中（不区分大小写）；列表项含 `tsCode / name / fundType / benchmark / management / foundDate`
- [ ] AC-02 `GET /api/v1/funds?market=E&fundType=股票型&page=1&pageSize=20` 返回 200，仅含市场=E 且 fundType=股票型；与 search 同时生效
- [ ] AC-03 `GET /api/v1/funds/510300.SH/portfolio` 返回 200，data 数组按 `stkMkvRatio` DESC 排序；分页正确；元信息 `isPortfolioEmpty` / `hasPortfolio` / `latestReportPeriod` / `latestAnnDate` 字段存在
- [ ] AC-03（场景 A）某基金在 `fund_portfolio` 表中无任何记录时，`isPortfolioEmpty=true, hasPortfolio=false, latestReportPeriod=null, latestAnnDate=null`
- [ ] AC-03（场景 B）某基金有旧期记录但最新期未披露时，`isPortfolioEmpty=true, hasPortfolio=true, latestReportPeriod="YYYY-MM-DD", latestAnnDate="YYYY-MM-DD"`（为该基金最新已有报告期及其公告日）
- [ ] AC-04 `GET /api/v1/funds/reverse-lookup?symbol=600519&page=1&pageSize=20` 返回 200，data 数组仅含 `stkMkvRatio >= 1.0` 的记录，按 `stkMkvRatio` DESC 排序
- [ ] AC-04（symbol 格式）`symbol=600519` 与 `symbol=600519.SH` 都能命中同一只股票
- [ ] AC-04（空结果）股票无任何 ≥1% 重仓基金时，data 为空数组，total=0
- [ ] **E2E 不适用说明**：本功能为内部 API 端点，无 UI 触达点；由 plan-04 / plan-05 在前端 E2E 中覆盖。API 验收通过 curl / Postman / Swagger UI 人工或自动化验证

### 性能验收（架构 §8.1）

- [ ] `GET /funds`（分页 pageSize=20）响应时间 < 2s（DevTools / curl 计时确认）
- [ ] `GET /funds/{ts_code}/portfolio`（前 20 条持仓）响应时间 < 3s
- [ ] `GET /funds/reverse-lookup`（分页 pageSize=20）响应时间 < 3s

## 验证命令

```bash
# 启动后端
cd server
uvicorn server.main:app --port 8000 --reload

# 列表 + 搜索 + 过滤
curl -s "http://localhost:8000/api/v1/funds?search=%E6%B2%AA%E6%B7%80300&page=1&pageSize=20" | jq
curl -s "http://localhost:8000/api/v1/funds?market=E&fundType=%E8%82%A1%E7%A5%A8%E5%9E%8B&page=1&pageSize=20" | jq

# 详情 + 持仓
curl -s "http://localhost:8000/api/v1/funds/510300.SH" | jq
curl -s "http://localhost:8000/api/v1/funds/510300.SH/portfolio?page=1&pageSize=20" | jq

# 反查
curl -s "http://localhost:8000/api/v1/funds/reverse-lookup?symbol=600519&page=1&pageSize=20" | jq
curl -s "http://localhost:8000/api/v1/funds/reverse-lookup?symbol=600519.SH&page=1&pageSize=20" | jq

# 边界：无持仓基金
curl -s "http://localhost:8000/api/v1/funds/000000.OF/portfolio" | jq '.data.isPortfolioEmpty'

# Swagger UI 验证
open http://localhost:8000/docs

# 性能（粗略）
time curl -s "http://localhost:8000/api/v1/funds?page=1&pageSize=20" > /dev/null
```

## 交接上下文

- **架构章节**: §4.2 模块职责（FundAPI、FundRepository）、§6.1 列表加载、§6.2 详情页、§6.3 反查流程、§7.3 API 边界、§7.6 命名映射
- **相关代码**:
  - `server/src/repositories/base.py`（`BaseRepository` 父类）
  - `server/src/api/v1/stocks.py` 或 `sectors.py`（参考类似业务 router 写法）
  - `server/src/api/schemas/response.py`（`ApiResponse[T]` 包装）
  - `server/src/api/deps.py`（`get_session`、`get_current_user`）
  - `server/src/models/stock.py`（反查 JOIN 的 `stocks` 表模型）
- **契约 / 数据对象**:
  - API 出参字段严格遵循架构 §7.2 + §7.6 命名映射（camelCase）
  - `PortfolioResponse` 是新结构（包含元信息 `isPortfolioEmpty` / `hasPortfolio` / `latestReportPeriod` / `latestAnnDate`），见实现规格 §1
  - `ReverseLookupResponse` 包含元信息 `stockName` / `reportPeriod`，见实现规格 §1
- **下游消费方**:
  - plan-04（列表页）依赖 `GET /funds` 与过滤参数
  - plan-05（详情页 / 反查页）依赖 `GET /funds/{ts_code}`、`GET /funds/{ts_code}/portfolio`、`GET /funds/reverse-lookup`

## 风险与边界

- **执行顺序**: 按 Task 列表 1→6 顺序执行；Repository 完成后才能写端点
- **验证失败排查方向**:
  - 列表返回空：检查 `funds` 表是否有数据（plan-01 同步是否执行）；检查 search/market/fundType 参数是否被正确解析
  - 持仓接口 500：检查 `stocks` 表是否有对应 `symbol`（架构 §4.2 复用声明验证项 — 依赖项目 03 的 stock_basic 同步）
  - 反查无结果：检查 `fund_portfolio.stock_symbol` 格式是否与 `stocks.symbol` 一致（symbol 格式归一化是否正确）
  - 性能不达标：检查 `funds.ts_code` 唯一索引与 `fund_portfolio` 联合索引是否生效（`EXPLAIN ANALYZE`）
- **允许修改的额外文件**: 无
- **暂停条件**:
  - 实际表结构（`fund_portfolio` 列名等）与架构 §7.2 命名不一致时（需调整 ORM 模型或在 Repository 做映射）
  - `stocks.symbol` 与 `fund_portfolio.stock_symbol` 格式长期不一致（需新增归一化逻辑）
- **风险备注**:
  - 反查 `symbol` 格式归一化策略需在 PR 中明确（推荐：去除后缀后纯数字 + 优先尝试 `.SH`）
  - `latest_portfolio` 子查询对每只基金独立执行，已有 `(fund_ts_code, report_period)` 联合索引，性能可控
- **E2E 不适用说明**: 本功能为 API 端点，无 UI 触达点；由 plan-04 / plan-05 在前端 E2E 中覆盖

### 后端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| 列表搜索无结果 | data=[], total=0，200 OK（不返回 404） | done |
| 详情 ts_code 不存在 | 返回 404，`error.message = "Fund not found"` | done |
| 持仓基金无任何记录 | data=[], isPortfolioEmpty=true, hasPortfolio=false, latestReportPeriod=null（200 OK） | done |
| 持仓基金有旧期无最新期 | data=[], isPortfolioEmpty=true, hasPortfolio=true, latestReportPeriod="YYYY-MM-DD"（为该基金最新已有报告期；200 OK） | done |
| 反查 symbol 不存在于 stocks 表 | 返回 404，`error.message = "Stock not found"` | done |
| 反查结果为空 | data=[], total=0，200 OK | done |
| 列表 page 超出范围 | data=[], total=<真实总数>，200 OK | done |
| 入参类型错误（如 page=abc） | FastAPI 自动 422 验证错误 | done |
