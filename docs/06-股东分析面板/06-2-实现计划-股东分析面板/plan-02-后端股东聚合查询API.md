---
feat_id: "plan-02"
title: "后端股东聚合查询API"
dimension: backend
phase: 2
status: done
depends_on: ["plan-01"]
---

# plan-02: 后端股东聚合查询API

## 1. 功能概要

- **目标**: 实现股东聚合查询服务，通过关键词 LIKE 匹配将股东归类到监控组，按股票粒度聚合持仓数据，计算跨期变动方向（增持/减持/新进/退出），关联行业板块，提供 overview / summary / industry-distribution / holdings 四个用户侧 API 端点。
- **完成后可观察结果**: 用户可通过 curl 调用 overview API 看到所有监控组的持仓股票数和变动趋势统计。调用 summary API 可获取指定组的汇总统计（持仓股票数、总持股数、平均占流通比）和变动趋势（增持/减持/新进/退出数量）。调用 industry-distribution API 可获取行业分布数据。调用 holdings API 可获取分页的持仓股票列表（含股票名称、持股数、占流通比、变动方向、行业）。筛选参数（industry、change_direction）正确过滤结果。
- **依赖**: plan-01（shareholder_groups 和 shareholder_group_rules 表数据）
- **关联验收标准**: [AC-01, AC-02, AC-03, AC-04, AC-05, AC-09, AC-11]
- **涉及架构模块**: ShareholderAnalysisService, User API routes (shareholder_analysis.py)
- **前置条件**: plan-01 已完成（分组和规则数据已入库），top10_float_holders 至少有一个报告期的数据
- **不在范围**: Admin API（plan-01）、前端页面（plan-03/04）、数据同步

## 2. 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| create | `server/src/services/shareholder_analysis_service.py` | 股东聚合查询服务 |
| create | `server/src/api/v1/shareholder_analysis.py` | 用户侧 API 路由 |
| modify | `server/src/api/v1/__init__.py` | 注册新路由 |

## 3. 实现规格

### 后端部分

#### 1. ShareholderAnalysisService — 核心匹配与聚合方法

新建 `server/src/services/shareholder_analysis_service.py`。

**依赖注入**：通过 AsyncSession 访问数据库。

**内部方法 `_get_report_periods(report_period: str | None)`**：
- 查询 top10_float_holders 表的 DISTINCT report_period 列表（降序取最近 4 个）
- **类型转换**：`top10_float_holders.report_period` 在表中为 `Date` 类型，DISTINCT 结果为 `date` 对象，须经 `.isoformat()` 序列化为 `YYYY-MM-DD` 字符串后再放入返回值，并作为后续匹配查询的 report_period 参数（避免 date/str 混用）
- API 入参 `report_period` 校验为日期字符串（`YYYY-MM-DD`），内部按需转换为 `date` 用于 DB 查询
- 确定 current_period：使用传入值或最新报告期
- 确定 prev_period：从 DISTINCT 列表中找 current_period 的前一个
- 返回 `{ report_periods: list[str], current_period: str, prev_period: str | None, has_prev_period: bool }`
- 被 get_overview 和 get_summary 共用，避免报告期查询逻辑重复

**内部方法 `_get_groups_with_rules()`**：
- 查询 shareholder_groups + shareholder_group_rules（join），返回 {group_id: GroupWithRules} 映射

**内部方法 `_match_holdings(group_ids, report_period)`**：
1. 获取指定 group_ids 的所有规则关键词，合并为一个大列表（多组联合时关键词取并集）
2. 对 top10_float_holders 表查询：report_period = 参数值，AND (holder_name LIKE '%kw1%' OR holder_name LIKE '%kw2%' OR ...)
3. 匹配结果按 (symbol, holder_name) 去重（同一股东可能匹配多个组的关键词，去重避免重复计数）
4. 按 symbol 聚合：SUM(hold_amount) AS total_hold_amount, SUM(hold_float_ratio) AS total_hold_float_ratio
5. 返回 Dict[symbol, AggregatedHolding]

> **多组联合查询语义**：多组时先获取所有 group_ids 的关键词合并为一个大列表，一次性对 top10_float_holders 做 LIKE OR 匹配（而非逐组分别查询后合并），匹配结果按 (symbol, holder_name) 去重后聚合为按 symbol 维度的统计。

**内部方法 `_compute_change_directions(current_holdings, prev_holdings)`**：
- 对每只股票：
  - current 有 + prev 无 → "new"
  - current 有 + prev 有 + current > prev → "increase"
  - current 有 + prev 有 + current < prev → "decrease"
  - current 有 + prev 有 + current == prev → "unchanged"
- 返回 Dict[symbol, change_direction]
- 返回 exit_symbols: Set[str]（prev 有 + current 无）

**内部方法 `_get_industry_for_stocks(symbols)`**：
- 通过显式 SQLAlchemy JOIN 查询行业数据（SectorStock 与 Sector/Stock 之间无 ORM relationship）
- JOIN 条件：
  - `SectorStock.stock_code == Stock.symbol`（stock_code 字符串关联 stocks.symbol）
  - `SectorStock.sector_code == Sector.code`（sector_code 字符串关联 sectors.code）
  - `Sector.type == 'industry'`（仅行业板块）
- 返回 Dict[symbol, { stock_name: str, industries: List[str] }]

> **注意**：SectorStock 和 Sector 之间通过 `sector_code` 字符串字段关联（非外键），与 Stock 通过 `stock_code` 关联 `stocks.symbol`。实现时必须使用显式 SQLAlchemy core join 或 select().where() 条件，不能使用 ORM relationship 的 joinedload/selectinload。一只股票可能关联多个行业板块，全部返回。

**LIKE 通配符安全**：所有 keyword 在拼 LIKE 参数前转义 % 和 _（与 plan-01 相同）。

#### 2. get_overview — 监控组概览

**参数**：`report_period: str | None`（None 时默认最新期）

1. 调用 `_get_report_periods(report_period)` 获取 report_periods 列表、current_period 和 prev_period
2. 获取所有分组及规则
3. 对每个 group：
   a. 调用 `_match_holdings([group.id], current_period)` 获取当前期聚合持仓
   b. 若 prev_period 存在，获取上期聚合持仓，调用 `_compute_change_directions` 计算变动方向
   c. 统计：stock_count, increase_count, decrease_count, new_count, exit_count
4. 按 stock_count 降序排列 groups
5. 返回 `{ report_periods, current_period, has_prev_period, groups: GroupOverview[] }`

#### 3. get_summary — 汇总统计 + 变动趋势

**参数**：`group_ids: list[int]`, `report_period: str`, `industry: str | None`, `change_direction: str | None`

1. 调用 `_match_holdings(group_ids, report_period)` 获取当前期聚合持仓
2. 调用 `_get_report_periods(report_period)` 获取 prev_period 信息，若 prev_period 存在则获取上期聚合持仓并计算变动方向
3. 若 change_direction 含 "exit"，查询上期匹配但当前期不存在的退出股票
4. LEFT JOIN 行业数据
5. 应用 industry 筛选（若提供）
6. 应用 change_direction 筛选（含 exit）
7. 计算汇总统计：stock_count, total_hold_amount, avg_hold_float_ratio
8. 计算变动趋势（不受 change_direction 筛选影响）：increase/decrease/new/exit 计数
9. 返回 `{ summary: { stock_count, total_hold_amount, avg_hold_float_ratio }, trend: { increase_count, decrease_count, new_count, exit_count }, has_prev_period }`

> **avg_hold_float_ratio 聚合计算方式**：按股票粒度聚合后，`avg_hold_float_ratio = AVG(每只股票的 total_hold_float_ratio)`，其中每只股票的 `total_hold_float_ratio = SUM(该组内所有匹配持有者的 hold_float_ratio)`。即先按股票求和，再对股票集合求简单平均。

**注意**：变动趋势统计不受 change_direction 筛选影响（否则选中"增持"后增持数=总数无意义）。

#### 4. get_industry_distribution — 行业分布

**参数**：`group_ids: list[int]`, `report_period: str`, `change_direction: str | None`

1. 调用与 summary 相同的匹配和聚合逻辑
2. 若 change_direction 含 "exit"，额外查询退出股票
3. LEFT JOIN 行业数据
4. 应用 change_direction 筛选（industry 筛选不生效——行业分布本身是筛选 UI 的数据源）
5. 按行业分组统计股票数和占比
6. 前N个行业（占比 > 5%）独立展示，其余合并为"其他/未分类"
7. 返回 `{ distribution: IndustryItem[] }`

#### 5. get_holdings — 持仓股票列表（分页）

**参数**：`group_ids: list[int]`, `report_period: str`, `industry: str | None`, `change_direction: str | None`, `page: int = 1`, `page_size: int = 20`

1. 调用与 summary 相同的匹配和聚合逻辑
2. 若 change_direction 含 "exit"，额外查询退出股票（退出股票展示上期的 total_hold_amount 和 total_hold_float_ratio）
3. LEFT JOIN 行业数据 + stocks（获取 stock_name）
4. 应用 industry + change_direction 筛选
5. 按 symbol 排序，分页
6. 返回 `{ holdings: HoldingItem[], total: int }`

**退出股票处理**：
- 查询上期匹配的 symbol 集合 - 当前期匹配的 symbol 集合 = 退出股票
- 退出股票的 total_hold_amount / total_hold_float_ratio 取上期数值
- 退出股票的 stock_name 和 industries 通过 stocks / sector_stocks 表获取

**可观测性（架构 §8.5）**：Service 层通过 Python logging 记录 warning 级别日志（如查询耗时 > 2s、数据不完整等异常情况），使用项目现有 logging 模块。

#### 6. 用户侧 API 路由

新建 `server/src/api/v1/shareholder_analysis.py`，**文件内必须声明 prefix**：`router = APIRouter(prefix="/shareholder-analysis", tags=["Shareholder Analysis"])`（参照 `funds.py`，`v1/__init__.py` 注册时不再加前缀——这是前端 `/shareholder-analysis` 命中 `/api/v1/shareholder-analysis` 的前提）：

- `GET /api/v1/shareholder-analysis/overview`
  - Query params: report_period（可选，默认最新）
  - 返回 OverviewResponse
- `GET /api/v1/shareholder-analysis/summary`
  - Query params: group_ids（必填，逗号分隔）, report_period（必填）, industry（可选）, change_direction（可选）
  - 返回 SummaryResponse
- `GET /api/v1/shareholder-analysis/industry-distribution`
  - Query params: group_ids（必填，逗号分隔）, report_period（必填）, change_direction（可选）
  - 返回 IndustryDistributionResponse
- `GET /api/v1/shareholder-analysis/holdings`
  - Query params: group_ids（必填，逗号分隔）, report_period（必填）, industry（可选）, change_direction（可选）, page（默认 1）, page_size（默认 20）
  - 返回 HoldingsResponse

在 `server/src/api/v1/__init__.py` 中注册路由：`router.include_router(shareholder_analysis_router)`

**API 响应包裹与命名（参照现有 funds API）**：
- 4 个用户侧 API 统一返回 `ApiResponse[T]` 包裹结构（`{ success: true, data: T }`），与 `funds.py` 一致；`response_model=ApiResponse[OverviewResponse]` 等
- 字段命名：Pydantic response model 使用 `alias_generator=to_camel` + `populate_by_name=True`（参照 `funds.py` 的 `from pydantic.alias_generators import to_camel`），后端字段定义 snake_case，序列化输出 camelCase，前端直接消费 camelCase
- 前端 `shareholderAnalysisApi` 方法返回包裹对象，SWR hooks 中 `.then(res => res.data)` 解一层取业务数据（与 `useFunds.ts` 一致）
- **Decimal 序列化**：`total_hold_amount`/`total_hold_float_ratio`/`avg_hold_float_ratio` 经 SUM/AVG 聚合后为 `Decimal`，Pydantic v2 默认序列化为字符串会破坏前端数值比较与图表渲染。参照 `funds.py` 的 `_serialize_value`，这些字段显式 `float()` 转换后再放入响应（或在 Pydantic model 配 `model_config = ConfigDict(json_encoders={Decimal: float})`）

## 4. Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | 实现 _get_report_periods 内部方法 | backend | done | 报告期列表查询 + current/prev period 确定，被 overview 和 summary 共用 |
| 2 | 实现 _get_groups_with_rules 内部方法 | backend | done | 查询所有分组及规则 |
| 3 | 实现 _match_holdings 内部方法 | backend | done | 关键词 LIKE 匹配 + 按股票聚合（含多组去重） |
| 4 | 实现 _compute_change_directions 内部方法 | backend | done | 跨期变动方向计算 + 退出股票检测 |
| 5 | 实现 _get_industry_for_stocks 内部方法 | backend | done | 批量获取股票行业关联（显式 JOIN） |
| 6 | 实现 get_overview 方法 | backend | done | 监控组概览（含变动趋势统计） |
| 7 | 实现 get_summary 方法 | backend | done | 汇总统计 + 变动趋势（含筛选） |
| 8 | 实现 get_industry_distribution 方法 | backend | done | 行业分布（含变动方向筛选） |
| 9 | 实现 get_holdings 方法 | backend | done | 分页持仓列表（含退出股票处理） |
| 10 | 创建用户侧 API 路由 | backend | done | 4 个 GET 端点 |
| 11 | 注册路由到 v1/__init__.py | backend | done | include_router |

## 5. 验收标准

### AC-01 验收：监控组概览展示

- [x] AC-01 `GET /api/v1/shareholder-analysis/overview` 返回 200，包含 report_periods 列表、current_period、has_prev_period、groups 数组
- [x] 每个 group 包含 group_id, group_name, stock_count, increase_count, decrease_count, new_count, exit_count
- [x] groups 按 stock_count 降序排列
- [x] report_periods 最多返回最近 4 个报告期

### AC-02 验收：监控组持仓详情查询

- [x] AC-02 `GET /api/v1/shareholder-analysis/summary?group_ids=1&report_period={latest}` 返回 summary（stock_count, total_hold_amount, avg_hold_float_ratio）和 trend（increase/decrease/new/exit 计数）
- [x] `GET /api/v1/shareholder-analysis/industry-distribution?group_ids=1&report_period={latest}` 返回 distribution 数组（industry, stock_count, percentage）
- [x] `GET /api/v1/shareholder-analysis/holdings?group_ids=1&report_period={latest}&page=1&page_size=20` 返回 holdings 数组和 total

### AC-03 验收：多监控组联合查询

- [x] AC-03 `GET /api/v1/shareholder-analysis/summary?group_ids=1,2&report_period={latest}` 返回两个组的合并汇总（去重）
- [x] holdings 同样按 (symbol) 去重后展示

### AC-04 验收：行业筛选

- [x] AC-04 `GET /api/v1/shareholder-analysis/holdings?group_ids=1&report_period={latest}&industry=银行` 仅返回行业为"银行"的股票
- [x] summary 同步受 industry 筛选影响

### AC-05 验收：变动方向筛选

- [x] AC-05 `GET /api/v1/shareholder-analysis/holdings?group_ids=1&report_period={latest}&change_direction=increase` 仅返回增持股票
- [x] `change_direction=exit` 返回退出股票（上期有本期无），展示上期持股数据
- [x] industry-distribution 受 change_direction 筛选影响
- [x] summary 的 trend 计数不受 change_direction 筛选影响

### AC-09 验收：报告期切换

- [x] AC-09 overview 接口传不同 report_period，返回对应报告期的数据
- [x] 不传 report_period 时默认最新期

### AC-11 验收：报告期数据不完整降级

- [x] AC-11 当上期数据缺失时，overview 返回 `has_prev_period: false`
- [x] summary 返回 `has_prev_period: false`，trend 计数为 0
- [x] holdings 中无上期数据的股票 change_direction 为 null

### 性能验收（架构 §8.1 目标）

- [ ] overview API 响应时间 < 3s（curl -w "%{time_total}" 计时）
- [ ] holdings API（分页 page_size=20）响应时间 < 2s

### 构建验收

- [x] 后端启动无报错，新路由注册成功
- [x] 无 import 错误或循环依赖

## 6. 验证命令

```bash
# 启动后端
cd server && uvicorn server.main:app --reload --port 8000 &

# 概览（需登录 token）
curl -s "http://localhost:8000/api/v1/shareholder-analysis/overview" \
  -H "Authorization: Bearer {token}" | python3 -m json.tool

# 汇总
curl -s "http://localhost:8000/api/v1/shareholder-analysis/summary?group_ids=1&report_period={latest}" \
  -H "Authorization: Bearer {token}" | python3 -m json.tool

# 行业分布
curl -s "http://localhost:8000/api/v1/shareholder-analysis/industry-distribution?group_ids=1&report_period={latest}" \
  -H "Authorization: Bearer {token}" | python3 -m json.tool

# 持仓列表
curl -s "http://localhost:8000/api/v1/shareholder-analysis/holdings?group_ids=1&report_period={latest}&page=1&page_size=20" \
  -H "Authorization: Bearer {token}" | python3 -m json.tool

# 多组联合
curl -s "http://localhost:8000/api/v1/shareholder-analysis/summary?group_ids=1,2&report_period={latest}" \
  -H "Authorization: Bearer {token}" | python3 -m json.tool

# 行业筛选
curl -s "http://localhost:8000/api/v1/shareholder-analysis/holdings?group_ids=1&report_period={latest}&industry=银行" \
  -H "Authorization: Bearer {token}" | python3 -m json.tool

# 变动方向筛选（增持）
curl -s "http://localhost:8000/api/v1/shareholder-analysis/holdings?group_ids=1&report_period={latest}&change_direction=increase" \
  -H "Authorization: Bearer {token}" | python3 -m json.tool

# 变动方向筛选（退出）
curl -s "http://localhost:8000/api/v1/shareholder-analysis/holdings?group_ids=1&report_period={latest}&change_direction=exit" \
  -H "Authorization: Bearer {token}" | python3 -m json.tool

# 性能计时
curl -w "\nTime: %{time_total}s\n" -s "http://localhost:8000/api/v1/shareholder-analysis/overview" \
  -H "Authorization: Bearer {token}" -o /dev/null
```

## 7. 交接上下文

- **架构章节**: §6.1 监控组概览加载、§6.2 持仓详情查询、§6.3 报告期切换、§7.1-7.2 领域对象与 Schema、§7.3 API 边界（用户侧部分）
- **相关代码**:
  - `server/src/models/top10_float_holder.py` — 股东数据源（只读查询）
  - `server/src/models/sector.py` + `server/src/models/sector_stock.py` — 行业关联（只读 JOIN）
  - `server/src/models/stock.py` — 股票名称（name 字段）
  - plan-01 创建的 `server/src/models/shareholder_group.py` — 分组规则读取
- **契约 / 数据对象**（前端消费，camelCase；后端 Pydantic 用 to_camel alias 转换，见 §3.6 / 架构 §7.6）:
  - `OverviewResponse`: { reportPeriods: string[], currentPeriod: string, hasPrevPeriod: boolean, groups: GroupOverview[] }
  - `GroupOverview`: { groupId, groupName, description, stockCount, increaseCount, decreaseCount, newCount, exitCount }
  - `SummaryResponse`: { summary: { stockCount, totalHoldAmount, avgHoldFloatRatio }, trend: { increaseCount, decreaseCount, newCount, exitCount }, hasPrevPeriod }
  - `IndustryDistributionResponse`: { distribution: IndustryItem[] }
  - `IndustryItem`: { industry, stockCount, percentage }
  - `HoldingsResponse`: { holdings: HoldingItem[], total }
  - `HoldingItem`: { symbol, stockName, totalHoldAmount, totalHoldFloatRatio, changeDirection, industries }
- **下游消费方**: plan-04（前端调用这 4 个 API 渲染页面）

## 8. 风险与边界

- **执行顺序**: 先实现内部方法（Task 1-5），再实现公开方法（Task 6-9），最后创建 API 路由（Task 10-11）
- **验证失败排查方向**:
  1. overview 返回空 groups → 检查 shareholder_groups 是否有数据（plan-01 是否执行）
  2. holdings 返回空 → 检查 top10_float_holders 是否有匹配数据
  3. 变动方向全为 null → 检查是否有 prev_period 数据
  4. 行业全为空 → 检查 sector_stocks + sectors(type=industry) 关联数据
  5. API 404 → 检查 v1/__init__.py 路由注册
- **允许修改的额外文件**: 无
- **暂停条件**: 聚合查询性能显著超出预期（>5s）时暂停，需评估是否引入索引或优化查询
- **E2E 不适用说明**: 本功能为纯后端 API，无可直接观察的用户界面。通过 curl 命令验证 API 行为即可，E2E 测试由 plan-04 承接。

### 后端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| top10_float_holders 表无数据 | overview 返回空 groups + report_periods 为空 | done |
| 只有一个报告期（无 prev_period） | has_prev_period=false，变动方向为 null | done |
| 指定的 group_ids 不存在 | 返回空匹配结果（不报错） | done |
| 股票未关联行业板块 | industries 为空数组，行业分布中归入"未分类" | done |
| 同一股东匹配多个组 | 多组联合查询时按 (symbol) 去重 | done |
| 退出股票查询（上期有本期无） | 额外查询上期匹配 symbol 集合，取差集 | done |
| change_direction=exit 但无上期数据 | 返回空列表（无退出记录） | done |
| industry 筛选传入不存在的行业 | 返回空列表 | done |
| LIKE 关键词包含特殊字符 | Service 层自动转义 % 和 _ | done |

### 风险备注

- 多组联合查询 + LIKE 匹配可能在数据量大时较慢。首版接受实时计算，架构评估单期 5 万条 × 5 组可接受。若超 3s 需考虑 pg_trgm 索引优化。
- 行业分布中一只股票属于多个行业时按独立计数统计，需在实现中注意不去重。
- holdings 的"退出"股票需要额外查询上期数据，增加了查询复杂度。需确保 SQL 效率。
