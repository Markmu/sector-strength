---
feat_id: "plan-01"
title: "后端基金扎堆度聚合查询API"
dimension: backend
phase: 1
status: done
depends_on: []
---

# plan-01: 后端基金扎堆度聚合查询API

## 1. 功能概要

- **目标**: 新建 `FundCrowdRepository`（扎堆度聚合查询封装）+ `FundCrowdAnalysisService`（聚合服务：排行榜、环比、行业分布）+ 2 个用户侧 API 端点（`GET /api/v1/fund-crowd-analysis/rankings` + `GET /api/v1/fund-crowd-analysis/industry-distribution`）+ 7 个 Pydantic 响应模型，零存储新增，完全复用 04 期 `fund_portfolio` + `funds` 表和现有 `sectors` / `sector_stocks` / `stocks` 行业体系。同时完成 1 项非阻塞索引优化（聚合查询索引前缀 `(report_period, stock_symbol)`）。
- **完成后可观察结果**: 登录用户调 `GET /api/v1/fund-crowd-analysis/rankings?scope=active&page=1&page_size=20` 返回最新报告期（`MAX(report_period)`）扎堆度排行榜，按 `fund_count`（COUNT DISTINCT fund_ts_code）降序、`total_float_ratio`（SUM stk_float_ratio）次降序，每条 item 含 `stockSymbol/stockName/industries/fundCount/totalFloatRatio/fundCountChange/totalFloatRatioChange/isNew`；当 `scope=all` 时无 `invest_type` 过滤，当 `scope=active` 时过滤掉被动指数型/增强指数型基金（含 `invest_type IS NULL` 显式处理）；上一报告期（次大值）存在时环比字段按 `stock_symbol` 内存对比（含"新进"判定），上期缺失时 `hasPrevPeriod=false` 且环比字段统一 `null`。调 `GET /api/v1/fund-crowd-analysis/industry-distribution?scope=active` 返回按行业聚合的扎堆股数量占比 + 合计占流通比参考值。`fund_portfolio` 表无数据时 rankings 返回 `hasData=false`、industry-distribution 返回空 distribution。响应统一 `{ success: true, data: {...} }` 包裹，输出字段 camelCase（Pydantic `to_camel` alias），数值字段为 number（Decimal→float）。
- **依赖**: 无（独立后端功能；测试所需 fixture 自带）
- **关联验收标准**: [AC-01, AC-02, AC-03, AC-04, AC-06, AC-07, AC-08]
- **涉及架构模块**: `FundCrowdRepository`（新建）、`FundCrowdAnalysisService`（新建）、用户侧路由 `fund_crowd_analysis.py`（新建）+ v1 路由注册
- **前置条件**:
  - PostgreSQL 实例运行（开发库，与 04/06 共用）
  - `fund_portfolio` 表已有数据（含 `ix_fund_portfolio_symbol_period (stock_symbol, report_period)` 和 `ix_fund_portfolio_fund_period (fund_ts_code, report_period)` 索引，见 §3 #10 非阻塞优化）
  - `funds.invest_type` 字段已通过 04 期同步填值（被动型枚举经 DB 查询确认为 `'被动指数型'` 和 `'增强指数型'`，ADR-1）
  - `sectors`（含 `type='industry'` 板块）+ `sector_stocks` + `stocks` 表数据存在
  - 后端依赖 `src.api.deps.get_current_user`（普通用户 JWT 认证）、`src.api.schemas.response.ApiResponse`、`pydantic.alias_generators.to_camel` 均已就位（06 已用）
- **不在范围**:
  - 前端任何改动（plan-02 / plan-03 负责）
  - 04 `/funds/reverse-lookup` 端点任何改动（plan-03 仅前端复用，后端不动）
  - 新增数据表 / 字段 / 迁移（除 §3 #10 的索引优化为可选 alembic 迁移）
  - 引入缓存层 / 预计算表 / 物化视图（ADR-6）
  - 修改现有 `FundRepository`（不复用，新建独立 `FundCrowdRepository`）

## 2. 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| create | `server/src/repositories/fund_crowd_repository.py` | 新建 `FundCrowdRepository(BaseRepository[FundPortfolio])`，含 4 个方法：`get_report_periods`、`get_crowd_aggregation`、`get_industry_for_stocks`、`get_stock_names` |
| create | `server/src/services/fund_crowd_analysis_service.py` | 新建 `FundCrowdAnalysisService`，常量 `PASSIVE_INVEST_TYPES` + 方法 `get_rankings` / `get_industry_distribution` / `_compute_changes` |
| create | `server/src/api/v1/fund_crowd_analysis.py` | 新建路由（`prefix="/fund-crowd-analysis"`）+ 2 个端点 + 7 个 Pydantic 响应模型 |
| modify | `server/src/api/v1/__init__.py` | 注册 `fund_crowd_analysis` 子路由（紧邻 line 36 `funds_router` 之后，line 37 `shareholder_analysis_router` 之前） |
| modify | `server/tests/test_fund_crowd_api.py` | 新建测试文件，10+ 个 pytest 用例覆盖 AC-01/02/03/04/06/07/08 后端语义（参照 `server/tests/test_fund_api.py` 既有风格） |
| create（可选） | `server/alembic/versions/{rev}_add_fund_portfolio_period_symbol_index.py` | 非阻塞优化：新增 `ix_fund_portfolio_period_symbol (report_period, stock_symbol)` 索引前缀（arch-check 标注，详见 §3 #10） |

## 3. 实现规格

### 后端部分

#### 1. `FundCrowdRepository` 类（新建）

**位置**：`server/src/repositories/fund_crowd_repository.py`。

**复用声明**：
- `BaseRepository`：`server/src/repositories/base.py:18`，泛型基类，构造函数 `__init__(self, model: Type[ModelType], session: AsyncSession)`（line 29）；本类继承时调用 `super().__init__(FundPortfolio, session)`（参照 `FundRepository.__init__` line 38-39）
- `FundPortfolio` 模型：`server/src/models/fund_portfolio.py`，字段 `fund_ts_code/report_period/stock_symbol/market_value/amount/stk_mkv_ratio/stk_float_ratio`（line 14-21，已确认满足扎堆度聚合）
- `Fund` 模型：`server/src/models/fund.py`，字段 `ts_code/invest_type`（用于 JOIN 过滤）
- `Sector` / `SectorStock` / `Stock` 模型：JOIN 范式参照 `shareholder_analysis_service.py:304-352`（`_get_industry_for_stocks`）

#### 1.1 `get_report_periods(limit: int = 4) -> list[date]`

```python
stmt = (
    select(FundPortfolio.report_period)
    .distinct()
    .order_by(FundPortfolio.report_period.desc())
    .limit(limit)
)
result = await self.session.execute(stmt)
return [row[0] for row in result.all()]
```

- 返回最近 N 个报告期降序；空表返回 `[]`

#### 1.2 `get_crowd_aggregation(report_period: date, scope: str) -> dict[str, dict]`

**核心聚合方法**（ADR-2 + ADR-1）。返回 `{ stock_symbol: { "fund_count": int, "total_float_ratio": float | None } }`。

```python
from sqlalchemy import func, or_

# JOIN funds 取 invest_type（仅 scope=active 时过滤被动型）
stmt = (
    select(
        FundPortfolio.stock_symbol,
        func.count(FundPortfolio.fund_ts_code.distinct()).label("fund_count"),
        func.sum(FundPortfolio.stk_float_ratio).label("total_float_ratio"),
    )
    .select_from(FundPortfolio)
    .join(Fund, Fund.ts_code == FundPortfolio.fund_ts_code)  # inner join：持仓记录必然对应基金
    .where(FundPortfolio.report_period == report_period)
)
if scope == "active":
    # ADR-1：被动判定 = invest_type IN ('被动指数型', '增强指数型')；
    # 主动判定 = NOT IN (...) OR invest_type IS NULL（NULL 必须显式包含）
    stmt = stmt.where(
        or_(
            Fund.invest_type.notin_(PASSIVE_INVEST_TYPES),
            Fund.invest_type.is_(None),
        )
    )
# scope == "all"：无 invest_type 过滤
stmt = stmt.group_by(FundPortfolio.stock_symbol)
# ORDER BY 在 Service 层做（聚合后再 JOIN stocks/sector_stocks 后排序）

result = await self.session.execute(stmt)
agg: dict = {}
for symbol, fund_count, total_float_ratio in result.all():
    agg[symbol] = {
        "fund_count": int(fund_count or 0),
        # Decimal → float（避免序列化为字符串破坏前端图表）
        "total_float_ratio": float(total_float_ratio) if total_float_ratio is not None else None,
    }
return agg
```

**JOIN 类型**：`join(Fund, Fund.ts_code == FundPortfolio.fund_ts_code)`（INNER JOIN）—— 04 期同步保证持仓记录必然对应基金主表记录，inner join 性能更优。

**NULL 处理**（ADR-1）：`stk_float_ratio` 为 NULL（港股/境外标的）时数据库 SUM 自动忽略 NULL；`fund_count` 仍计入该基金。`invest_type` 为 NULL 时用 `Fund.invest_type.is_(None)` 显式包含到主动型，避免 `NOT IN` 漏掉 NULL。

#### 1.3 `get_industry_for_stocks(symbols: list[str]) -> dict`

**复用声明**：直接借鉴 `shareholder_analysis_service.py:304-352` 的 `_get_industry_for_stocks` SQL 范式（JOIN `SectorStock.stock_code == Stock.symbol AND Sector.code == SectorStock.sector_code AND Sector.type == 'industry'`）。本 plan 在 Repository 层实现（Service 不再重复 JOIN 逻辑），返回 `{ symbol: list[str] }`。

```python
from sqlalchemy import and_

stmt = (
    select(
        Stock.symbol,
        Sector.name,
    )
    .select_from(Stock)
    .outerjoin(SectorStock, SectorStock.stock_code == Stock.symbol)
    .outerjoin(
        Sector,
        and_(Sector.code == SectorStock.sector_code, Sector.type == "industry"),
    )
    .where(Stock.symbol.in_(symbols))
)
result = await self.session.execute(stmt)
mapping: dict = {sym: [] for sym in symbols}
for symbol, industry_name in result.all():
    if industry_name and industry_name not in mapping.get(symbol, []):
        mapping.setdefault(symbol, []).append(industry_name)
return mapping
```

**边界**：stocks 表缺失该 symbol 时该 symbol 在结果中不存在，Service 层兜底为 `industries=[]`（与 06 行为一致）。一股多行业全部展示（ADR-5）。

#### 1.4 `get_stock_names(symbols: list[str]) -> dict[str, str | None]`

```python
stmt = select(Stock.symbol, Stock.name).where(Stock.symbol.in_(symbols))
result = await self.session.execute(stmt)
return {symbol: name for symbol, name in result.all()}
```

- 用于 JOIN stocks 表取股票名（L2 降级：缺失显示"—"，对应 stockName=null）

#### 2. `FundCrowdAnalysisService` 类（新建）

**位置**：`server/src/services/fund_crowd_analysis_service.py`。

**复用声明**：
- `_compute_change_directions` 范式：`shareholder_analysis_service.py:264-302`（Python 内存 dict 对比，按 symbol 维度计算 cur-prev 变化 + "new" 判定）；本 plan 的 `_compute_changes` 是该范式的 08 版（按 `fund_count` 和 `total_float_ratio` 两字段对比，输出 `fund_count_change/total_float_ratio_change/is_new`）

```python
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.fund_crowd_repository import FundCrowdRepository

logger = logging.getLogger(__name__)

# ADR-1：被动型 invest_type 枚举（后端定义为常量便于调整，ADR-6 风险对策）
PASSIVE_INVEST_TYPES = ("被动指数型", "增强指数型")


class FundCrowdAnalysisService:
    """基金扎堆度聚合查询服务（实时聚合，无缓存）"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = FundCrowdRepository(session)
```

#### 2.1 `get_rankings(scope: str, search: Optional[str], page: int, page_size: int) -> dict`

**实现要点**（架构 §6.1）：

```python
async def get_rankings(self, scope: str, search: Optional[str], page: int, page_size: int) -> dict:
    # 1. 确定报告期（最新期 + 上期）
    periods = await self.repo.get_report_periods(limit=4)
    if not periods:
        return {"has_data": False, "current_period": None, "prev_period": None,
                "has_prev_period": False, "items": [], "total": 0, "page": page, "page_size": page_size}
    current_period = periods[0]
    prev_period = periods[1] if len(periods) >= 2 else None
    has_prev_period = prev_period is not None

    # 2. current 期聚合
    current_agg = await self.repo.get_crowd_aggregation(current_period, scope)

    # 3. prev 期聚合（仅 has_prev_period 时）
    prev_agg = await self.repo.get_crowd_aggregation(prev_period, scope) if has_prev_period else {}

    # 4. 环比对比（ADR-3，Python 内存，复用 06 _compute_change_directions 范式）
    changes = self._compute_changes(current_agg, prev_agg, has_prev_period)

    # 5. JOIN stocks 取 stock_name + JOIN sectors 取 industries
    all_symbols = list(current_agg.keys())
    stock_names = await self.repo.get_stock_names(all_symbols) if all_symbols else {}
    industry_map = await self.repo.get_industry_for_stocks(all_symbols) if all_symbols else {}

    # 6. 组装 item（含 search 在 SQL 后 Python 层应用？— 否，search 必须在 SQL WHERE 层保证分页 total 正确）
    # 注意：search 需在聚合 SQL 层过滤，本实现调整为：将 search 作为参数传给 get_crowd_aggregation，
    #       在 SQL WHERE 加 (stock_symbol LIKE 'x%' OR stock_name ILIKE '%x%')
    # （详见 §3 #2.4 search 过滤策略）

    # 7. 排序（fund_count DESC, total_float_ratio DESC，数据库 ORDER BY 双字段保证稳定）
    items = []
    for symbol, agg in current_agg.items():
        # search 过滤（若 search 未在 SQL 层处理则在此 Python 层兜底；推荐 SQL 层）
        ch = changes.get(symbol, {})
        items.append({
            "stock_symbol": symbol,
            "stock_name": stock_names.get(symbol),  # None 兜底
            "industries": industry_map.get(symbol, []),
            "fund_count": agg["fund_count"],
            "total_float_ratio": agg["total_float_ratio"],
            "fund_count_change": ch.get("fund_count_change"),
            "total_float_ratio_change": ch.get("total_float_ratio_change"),
            "is_new": ch.get("is_new"),
        })

    # 应用 search 过滤（如果未在 SQL 层做）
    # items = self._apply_search_filter(items, search)

    # 排序：fund_count DESC, total_float_ratio DESC（None 视为最小）
    items.sort(key=lambda x: (-x["fund_count"], -(x["total_float_ratio"] or 0)))

    # 8. 分页
    total = len(items)
    offset = (page - 1) * page_size
    page_items = items[offset: offset + page_size]

    return {
        "has_data": True,
        "current_period": current_period.isoformat(),  # date → ISO 字符串
        "prev_period": prev_period.isoformat() if prev_period else None,
        "has_prev_period": has_prev_period,
        "items": page_items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
```

#### 2.2 search 过滤策略（§3 #2.4）

架构 §6.1 step g + step h 实现原则："search 在 SQL WHERE 层过滤（stock_symbol LIKE 'xxx%' OR stock_name ILIKE '%xxx%'），分页后再返回；不前端过滤（保证分页 total 正确）"。

**两种实现路径（agent 任选其一，pytest 验证为准）**：

- **路径 A（推荐）**：将 `search` 参数传入 `get_crowd_aggregation`，在聚合 SQL 的 WHERE 加：
  ```python
  if search:
      # LEFT JOIN stocks 提前到聚合 SQL 中以支持 stock_name ILIKE
      stmt = stmt.outerjoin(Stock, Stock.symbol == FundPortfolio.stock_symbol)
      escaped = _escape_like_keyword(search)
      stmt = stmt.where(or_(
          FundPortfolio.stock_symbol.like(f"{escaped}%", escape="\\"),
          Stock.name.ilike(f"%{escaped}%", escape="\\"),
      ))
  ```
  这样 `current_agg` 只含命中 search 的 symbol，`total` 即 `len(current_agg)`，分页正确。
- **路径 B**：在 Python 层过滤 `items`（不推荐，性能稍差但实现简单；单期 ~15 万行聚合后 Python 过滤 1 万个扎堆股可接受）。若选 B，需在文档/注释说明"分页 total 是过滤后的数"。

**推荐路径 A**。无论哪种，必须 `_escape_like_keyword` 转义 `%` 和 `_`（架构 §8.3，参照 `shareholder_group_service.py:86-95` 的实现）。

#### 2.3 `_compute_changes(current_agg, prev_agg, has_prev_period) -> dict`

```python
def _compute_changes(self, current_agg, prev_agg, has_prev_period):
    """复用 06 _compute_change_directions 范式，按 stock_symbol 对比 fund_count / total_float_ratio。

    - has_prev_period=False：所有股票 fund_count_change/total_float_ratio_change/is_new 均为 None
    - symbol not in prev_agg → is_new=True（新进），fund_count_change=None
    - symbol in prev_agg → 计算 cur - prev（int / float 差值），is_new=False
    """
    changes: dict = {}
    if not has_prev_period:
        for symbol in current_agg:
            changes[symbol] = {
                "fund_count_change": None,
                "total_float_ratio_change": None,
                "is_new": None,  # ADR-3：has_prev_period=false 时 is_new=null
            }
        return changes

    for symbol, cur in current_agg.items():
        prev = prev_agg.get(symbol)
        if prev is None:
            changes[symbol] = {
                "fund_count_change": None,  # 新进无变化数值
                "total_float_ratio_change": None,
                "is_new": True,
            }
        else:
            cur_ratio = cur["total_float_ratio"]
            prev_ratio = prev["total_float_ratio"]
            ratio_change = None
            if cur_ratio is not None and prev_ratio is not None:
                ratio_change = round(cur_ratio - prev_ratio, 4)
            changes[symbol] = {
                "fund_count_change": cur["fund_count"] - prev["fund_count"],
                "total_float_ratio_change": ratio_change,  # 任一为 None → None
                "is_new": False,
            }
    return changes
```

**边界**：`total_float_ratio` 任一为 None 时 ratio_change=None（前端显示"—"），不影响 `fund_count_change`（始终为整数差值）。

#### 2.4 `get_industry_distribution(scope: str) -> dict`

**实现要点**（架构 §6.2 + ADR-5）：

```python
async def get_industry_distribution(self, scope: str) -> dict:
    periods = await self.repo.get_report_periods(limit=2)
    if not periods:
        return {"has_data": False, "current_period": None, "distribution": []}
    current_period = periods[0]

    # 复用 get_crowd_aggregation 拿到扎堆股集合 + total_float_ratio
    current_agg = await self.repo.get_crowd_aggregation(current_period, scope)
    all_symbols = list(current_agg.keys())
    if not all_symbols:
        return {"has_data": True, "current_period": current_period.isoformat(), "distribution": []}

    industry_map = await self.repo.get_industry_for_stocks(all_symbols)
    total_stock_count = len(all_symbols)

    # 按行业分组（一股多行业独立计数，与 06 一致）
    industry_stats: dict = {}  # { industry: { stock_count: set, total_float_ratio: float } }
    for symbol in all_symbols:
        industries = industry_map.get(symbol, [])
        if not industries:
            industries = ["未分类"]
        for ind in industries:
            if ind not in industry_stats:
                industry_stats[ind] = {"stock_count": set(), "total_float_ratio": 0.0}
            industry_stats[ind]["stock_count"].add(symbol)
            ratio = current_agg[symbol]["total_float_ratio"]
            if ratio is not None:
                industry_stats[ind]["total_float_ratio"] += ratio

    distribution = [
        {
            "industry": ind,
            "stock_count": len(stats["stock_count"]),  # COUNT DISTINCT stock_symbol
            "percentage": round(len(stats["stock_count"]) / total_stock_count * 100, 4),
            "total_float_ratio": round(stats["total_float_ratio"], 4),
        }
        for ind, stats in industry_stats.items()
    ]
    # 按 stock_count 降序（前端再 Top N 截断）
    distribution.sort(key=lambda x: -x["stock_count"])

    return {
        "has_data": True,
        "current_period": current_period.isoformat(),
        "distribution": distribution,
    }
```

**可观测性（架构 §8.5）**：方法入口记录 `logger.info("get_rankings called, scope=%s, search=%s, page=%d", scope, search, page)`；查询失败时 `logger.exception(...)`。

#### 3. Pydantic 响应模型（7 个，新建于 `fund_crowd_analysis.py`）

参照 `server/src/api/v1/funds.py:30-80` 的 `FundOut` / `FundPortfolioOut` 范式（`ConfigDict(alias_generator=to_camel, populate_by_name=True)`，snake_case 字段经 alias 转 camelCase 输出）。

```python
class RankingItem(BaseModel):
    """扎堆排行榜单项（API 输出视角 camelCase）"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    stock_symbol: str
    stock_name: Optional[str] = None
    industries: List[str] = Field(default_factory=list)
    fund_count: int
    total_float_ratio: Optional[float] = None
    fund_count_change: Optional[int] = None
    total_float_ratio_change: Optional[float] = None
    is_new: Optional[bool] = None


class RankingsData(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    has_data: bool
    current_period: Optional[str] = None
    prev_period: Optional[str] = None
    has_prev_period: bool
    items: List[RankingItem]
    total: int
    page: int
    page_size: int


class IndustryItem(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    industry: str
    stock_count: int
    percentage: float
    total_float_ratio: float


class IndustryDistributionData(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    has_data: bool
    current_period: Optional[str] = None
    distribution: List[IndustryItem]
```

- 字段经 `to_camel` 输出 camelCase（`stockSymbol / stockName / fundCount / totalFloatRatio / fundCountChange / totalFloatRatioChange / isNew / currentPeriod / prevPeriod / hasPrevPeriod / hasData / pageSize / stockCount / totalFloatRatio`）
- `Optional[bool]` 用于 `is_new`（ADR-3：has_prev_period=false 时为 null）

#### 4. 路由层端点（新建于 `fund_crowd_analysis.py`）

参照 `funds.py:24` 的 `router = APIRouter(prefix="/funds", tags=["Funds"])` 范式。

```python
from fastapi import APIRouter, Depends, Query
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_session, get_current_user
from src.api.schemas.response import ApiResponse
from src.models.user import User
from src.services.fund_crowd_analysis_service import FundCrowdAnalysisService

router = APIRouter(prefix="/fund-crowd-analysis", tags=["FundCrowdAnalysis"])


@router.get("/rankings")
async def get_rankings(
    scope: str = Query("active", description="基金口径：active=仅主动基金（默认），all=全部基金"),
    search: Optional[str] = Query(None, description="股票代码前缀或名称包含（不区分大小写）"),
    page: int = Query(1, ge=1, description="页码（1-based）"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """扎堆度排行榜（AC-01/02/03/06/07/08）"""
    if scope not in ("active", "all"):
        scope = "active"  # 容错
    service = FundCrowdAnalysisService(session)
    result = await service.get_rankings(scope=scope, search=search, page=page, page_size=page_size)
    return {"success": True, "data": result}  # result 字段已是 snake_case dict，前端消费 camelCase 由 _dict_to_camel 在路由层补一次转换或前端直接读 snake_case？
```

**响应字段命名边界（重要）**：与 `funds.py:228-234` 的 `reverse_lookup` 一致做法 —— 路由层用 helper `_dict_to_camel` 把 service 返回的 snake_case dict 转 camelCase 后再返回。参照 `funds.py` 的 `_dict_to_camel` helper（搜索文件内定义）。本 plan 在 `fund_crowd_analysis.py` 同样定义一个 `_dict_to_camel`（或复用 `src/api/v1/_helpers.py` 若已存在），递归转 dict/list 的 key 为 camelCase。

**最终返回**：`{"success": True, "data": _dict_to_camel(result)}`，确保 `data.items[0].stockSymbol` 等 camelCase 字段。

#### 5. 路由层端点 `GET /industry-distribution`

```python
@router.get("/industry-distribution")
async def get_industry_distribution(
    scope: str = Query("active", description="基金口径：active=仅主动基金（默认），all=全部基金"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """行业分布（AC-04）"""
    if scope not in ("active", "all"):
        scope = "active"
    service = FundCrowdAnalysisService(session)
    result = await service.get_industry_distribution(scope=scope)
    return {"success": True, "data": _dict_to_camel(result)}
```

**前后端契约校验（四件套）**：

- **路径拼接**：前端 endpoint `/fund-crowd-analysis/rankings?scope=...` × `apiClient.baseURL` `${API_BASE_URL}/api/v1`（`web/src/lib/api.ts:8`）= 后端实际路径 `/api/v1/fund-crowd-analysis/rankings`。v1_router 在 `/v1`（`__init__.py:25`），子 router 在 `/fund-crowd-analysis`（本 plan），最终经 `router.include_router(router, prefix="/api")` 拼出 `/api/v1/fund-crowd-analysis/rankings`，**无重复前缀**
- **HTTP 方法**：后端 `@router.get` → GET；前端 `apiClient.get` → GET；一致
- **query 参数命名**：`scope`（小写字符串）、`search`、`page`、`page_size`（snake_case）。**FastAPI Query 参数不经 Pydantic alias 转换**，前端必须传 `page_size`（不是 `pageSize`）—— query 风格与 04 `funds.py:202-203` 的 `page` / `page_size` 一致；响应体字段才经 `to_camel` 转 camelCase
- **响应字段命名**：外层 `{ success, data }`；`data.items[].stockSymbol/fundCount/totalFloatRatio/fundCountChange/totalFloatRatioChange/isNew`（camelCase）；`data.currentPeriod/prevPeriod/hasPrevPeriod/hasData/pageSize`（camelCase）；前端类型定义必须用这些 camelCase 名

**序列化约定**（架构 §7.3）：
- `current_period` 是 `date` 对象 → service 层 `.isoformat()` 转 ISO 字符串（如 `"2026-03-31"`）
- `total_float_ratio` 是 `Decimal` → service 层 `float(...)` 转 float（避免 Pydantic 把 Decimal 序列化为字符串破坏前端数值运算）
- `fund_count_change` 是 `int`，`total_float_ratio_change` 是 `float`，`is_new` 是 `bool | None`

#### 6. v1 路由注册（`server/src/api/v1/__init__.py`）

```python
# line 20 之后新增 import
from .fund_crowd_analysis import router as fund_crowd_analysis_router

# line 36 (funds_router) 之后新增
router.include_router(fund_crowd_analysis_router)  # /api/v1/fund-crowd-analysis/*
```

顺序无强约束（动态路径 `/{ts_code}` 在 `funds.py` 内，不影响本 router），但建议紧邻 funds 之后便于阅读。

#### 7. pytest 测试用例（新建 `server/tests/test_fund_crowd_api.py`）

**复用声明**：参照 `server/tests/test_fund_api.py` 既有风格 —— `from main import app` 入口、`_fastapi_app = app.app if hasattr(app, "app") else app`、`@pytest_asyncio.fixture` 的 `normal_user` + `auth_client`（注入 `get_current_user` dependency override + `get_session` override）、`httpx.AsyncClient` 调真实 API 端点。

**测试数据 fixture**（参照 `test_fund_api.py` 的 FundPortfolio 插入范式）：
```python
@pytest_asyncio.fixture
async def sample_portfolio(test_session):
    """插入测试数据：覆盖主动/被动、跨期、多股东、搜索命中"""
    from src.models.fund import Fund
    from src.models.fund_portfolio import FundPortfolio
    from src.models.stock import Stock
    from datetime import date

    funds = [
        Fund(ts_code="001001.OF", name="华夏成长", invest_type="普通股票型"),       # 主动
        Fund(ts_code="001002.OF", name="华夏大盘", invest_type="被动指数型"),       # 被动
        Fund(ts_code="001003.OF", name="易方达蓝筹", invest_type="增强指数型"),     # 被动
        Fund(ts_code="001004.OF", name="兴全新发", invest_type=None),              # 主动（NULL → 主动）
    ]
    portfolios = [
        # 最新期 2024-12-31
        FundPortfolio(fund_ts_code="001001.OF", report_period=date(2024,12,31), stock_symbol="600519", stk_float_ratio=Decimal("2.5")),
        FundPortfolio(fund_ts_code="001002.OF", report_period=date(2024,12,31), stock_symbol="600519", stk_float_ratio=Decimal("1.5")),
        FundPortfolio(fund_ts_code="001003.OF", report_period=date(2024,12,31), stock_symbol="600519", stk_float_ratio=Decimal("0.8")),
        FundPortfolio(fund_ts_code="001004.OF", report_period=date(2024,12,31), stock_symbol="600519"),  # stk_float_ratio=None
        FundPortfolio(fund_ts_code="001001.OF", report_period=date(2024,12,31), stock_symbol="000001", stk_float_ratio=Decimal("0.5")),
        FundPortfolio(fund_ts_code="001002.OF", report_period=date(2024,12,31), stock_symbol="000001", stk_float_ratio=Decimal("0.3")),
        # 上一期 2024-09-30（用于环比 + 新进）
        FundPortfolio(fund_ts_code="001001.OF", report_period=date(2024,9,30), stock_symbol="600519", stk_float_ratio=Decimal("2.0")),
        FundPortfolio(fund_ts_code="001004.OF", report_period=date(2024,9,30), stock_symbol="600519"),  # 600519 上期 2 只主动
        # 000001 上期无任何记录 → 新进
    ]
    stocks = [
        Stock(symbol="600519", name="贵州茅台"),
        Stock(symbol="000001", name="平安银行"),
    ]
    test_session.add_all(funds + portfolios + stocks)
    await test_session.commit()
    return {"funds": funds, "portfolios": portfolios, "stocks": stocks}
```

**测试用例（10+ 个）**：

1. `test_rankings_returns_active_scope_only`（AC-01）：`scope=active` 调 `/rankings`，断言 600519 的 `fundCount=2`（仅 001001 主动 + 001004 NULL 主动），排除 001002/001003 被动
2. `test_rankings_all_scope_includes_passive`（AC-02）：`scope=all` 调 `/rankings`，断言 600519 的 `fundCount=4`（全部 4 只）
3. `test_rankings_order_by_fund_count_desc`（AC-01 排序）：断言 600519 在 000001 之前（600519 fundCount=4 > 000001 fundCount=2，scope=all）
4. `test_rankings_total_float_ratio_sum`（AC-01 辅指标）：`scope=all`，断言 600519 的 `totalFloatRatio≈4.8`（2.5+1.5+0.8+0=NULL 忽略）
5. `test_rankings_change_computation`（AC-03）：`scope=active`，断言 600519 的 `fundCountChange=0`（本期 2 只主动 - 上期 2 只主动），`totalFloatRatioChange≈0.5`（2.5 - 2.0）；000001 的 `isNew=true`、`fundCountChange=null`（上期无记录）
6. `test_rankings_no_prev_period_returns_null_changes`（AC-06）：fixture 只插一个报告期 → `hasPrevPeriod=false`，所有 item 的 `fundCountChange/totalFloatRatioChange/isNew` 均为 null
7. `test_rankings_empty_portfolio_returns_has_data_false`（AC-07）：空表 → `hasData=false`、`items=[]`
8. `test_rankings_search_by_code_prefix`（AC-08）：`search=600` → 仅命中 600519，total=1
9. `test_rankings_search_by_name_contains`（AC-08）：`search=茅台` → 仅命中 600519，total=1
10. `test_rankings_search_no_match`（AC-08 边界）：`search=不存在的股票` → `items=[]`、`total=0`
11. `test_rankings_pagination`：`page=1&page_size=1` → items 长度 1、total=2；`page=2` → 剩 1 条
12. `test_industry_distribution_active_scope`（AC-04）：插入 sector_stocks 关联 600519→食品饮料，断言返回 distribution 含食品饮料、percentage 正确（扎堆股数 / 总扎堆股数 × 100）
13. `test_industry_distribution_multi_industries_per_stock`（AC-04 一股多行业）：600519 关联 2 个行业，断言 2 个行业均计数
14. `test_industry_distribution_empty_when_no_industry_mapping`（AC-04 边界）：无 sector_stocks 关联 → 归入"未分类"桶
15. `test_rankings_requires_auth`（权限回归）：未注入 auth 的 client → 401
16. `test_rankings_stock_name_null_when_stocks_table_missing`（L2 降级）：stocks 表无该 symbol → `stockName=null`
17. `test_rankings_total_float_ratio_null_when_all_null`（L3 降级）：所有记录 stk_float_ratio=None → `totalFloatRatio=null`，`fundCount` 仍正常

**SQL 注入回归测试**（AC 隐含，架构 §8.3）：
18. `test_rankings_search_escapes_like_wildcards`：`search=%` → 不匹配全表

**red 阶段原则**：测试只通过 HTTP client 调 API 端点（`from main import app`），不 import 尚未实现的 service / repository；red 失败原因应为「端点 404」或「service 模块 ImportError」，而非测试代码本身的语法/逻辑错误。

#### 8. 性能保障（架构 §8.1）

- 单期扎堆度聚合（GROUP BY + JOIN funds）目标 < 1s（15 万行级别，依赖 `ix_fund_portfolio_symbol_period` 索引）
- 环比两期各一次聚合 + Python 内存对比，总目标 < 3s
- 行业分布 JOIN sectors 目标 < 500ms
- pytest 中可不强制断言耗时（开发库数据量小），但 green 阶段建议手动 curl 验证 < 3s

#### 9. 安全要求（架构 §8.3）

- `Depends(get_current_user)` 普通用户认证（与 04/06 一致；本端点非 admin，普通登录用户即可访问）
- search 参数用 `_escape_like_keyword` 转义 `%` / `_`（参照 `shareholder_group_service.py:86-95`），SQLAlchemy 参数绑定（`.like(pattern, escape="\\")`），不拼接 SQL
- `page_size` 用 `Query(le=100)` 限制最大值，防恶意大页请求拖垮 DB
- 全模块只读，无写入操作

#### 10. 非阻塞索引优化（arch-check 标注，纳入交付）

**背景**：架构 §8.6 风险表 + arch-check 标注 —— 现有 `ix_fund_portfolio_symbol_period (stock_symbol, report_period)` 索引前缀不利于 `WHERE report_period = :latest GROUP BY stock_symbol` 查询（先按 stock_symbol 排序，report_period 在第二位，过滤效率低）。

**优化**：新增索引 `ix_fund_portfolio_period_symbol (report_period, stock_symbol)`（前缀为 report_period），让扎堆度聚合 SQL（WHERE report_period + GROUP BY stock_symbol）走索引前缀扫描。

**交付物**：
- 新建 alembic 迁移 `server/alembic/versions/{rev}_add_fund_portfolio_period_symbol_index.py`：
  ```python
  def upgrade():
      op.create_index(
          "ix_fund_portfolio_period_symbol",
          "fund_portfolio",
          ["report_period", "stock_symbol"],
      )
  def downgrade():
      op.drop_index("ix_fund_portfolio_period_symbol", table_name="fund_portfolio")
  ```
- **非阻塞说明**：此优化不阻断 AC 验证（pytest 在小数据量下不依赖索引也能通过）；标记为 plan-01 的"性能改进项"，agent 完成 §3 #1-#9 主功能后追加。若 alembic 迁移生成有阻碍（如本地 alembic 配置问题），可在 review 时记录并降级为"运维阶段手动建索引"，不阻塞 plan-01 进入 done

## 4. Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | red：新建 `test_fund_crowd_api.py` 追加 10+ pytest 用例 | backend | done | 覆盖 §3 #7 的 18 个测试用例（red 阶段已就位 20 个用例，详见 red 证据）；red 阶段失败原因 = 端点 404 |
| 2 | 新建 `fund_crowd_repository.py` + 4 个方法 | backend | done | `get_report_periods` / `get_crowd_aggregation`（含 NULL + scope 过滤 + search SQL 层）/ `get_industry_for_stocks`（复用 06 JOIN 范式）/ `get_stock_names` |
| 3 | 新建 `fund_crowd_analysis_service.py` + 常量 `PASSIVE_INVEST_TYPES` | backend | done | `get_rankings`（报告期判定 + 环比 + 排序 + 分页） / `get_industry_distribution` / `_compute_changes`（复用 06 范式） |
| 4 | search 过滤策略实现（路径 A：SQL WHERE 层） | backend | done | `_escape_like_keyword` 转义 + `.like(prefix, escape='\\')` / `.ilike(contains, escape='\\')`；search 在 SQL WHERE 层，分页 total 正确 |
| 5 | 新建 4 个 Pydantic 响应模型 + `_dict_to_camel` helper | backend | done | `RankingItem` / `RankingsData` / `IndustryItem` / `IndustryDistributionData`（plan §3 #3 列出的 4 类，足够覆盖 7 个语义字段）；camelCase 输出（递归 dict/list） |
| 6 | 新建 `fund_crowd_analysis.py` 路由 + 2 个端点 | backend | done | `GET /rankings` + `GET /industry-distribution`；`Depends(get_current_user)`；query 参数 snake_case（scope/search/page/page_size） |
| 7 | 注册 v1 路由（`__init__.py`） | backend | done | 紧邻 funds_router 之后、shareholder_analysis_router 之前 |
| 8 | green：运行 pytest 全套通过 | backend | done | `pytest tests/test_fund_crowd_api.py --no-cov -v` 20/20 通过；`test_fund_api.py` 34/34 不破坏 |
| 9 | 非阻塞：新增 `ix_fund_portfolio_period_symbol` 索引迁移 | backend | done | alembic 迁移 `4b8668ae3d1d`，`alembic upgrade head` 已应用成功 |

## 5. 验收标准

### 后端核心功能验收

- [ ] AC-01 `GET /rankings?scope=active` 返回最新报告期扎堆度排行榜，按 `fundCount` 降序、`totalFloatRatio` 次降序；每条 item 含 7 个字段（stockSymbol/stockName/industries/fundCount/totalFloatRatio/fundCountChange/totalFloatRatioChange/isNew）
- [ ] AC-02 `GET /rankings?scope=all` 纳入被动型基金，相关股票 `fundCount` ≥ `scope=active`；切回 `scope=active` 恢复主动口径
- [ ] AC-03 上期存在时 `fundCountChange` 为整数差值、`totalFloatRatioChange` 为浮点差值；symbol 上期无记录时 `isNew=true`、`fundCountChange=null`
- [ ] AC-04 `GET /industry-distribution?scope=active` 返回按扎堆股数量占比聚合的行业分布，一股多行业独立计数，按 `stockCount` 降序
- [ ] AC-06 上期完全缺失时 `hasPrevPeriod=false`，所有 item 的 `fundCountChange/totalFloatRatioChange/isNew` 均为 null，当期排名正常
- [ ] AC-07 `fund_portfolio` 表无数据时 `hasData=false`、`items=[]`、`hasPrevPeriod=false`
- [ ] AC-08 `search` 按代码前缀（`stock_symbol LIKE 'x%'`）或名称包含（`stock_name ILIKE '%x%'`）匹配；无匹配 `total=0`；分页 total 是过滤后的数

### 性能验收（架构 §8.1 目标）

- [ ] `GET /rankings?scope=active` 排行榜加载（含环比二期聚合 + 分页）响应时间 < 3s（DevTools Network / 手动 curl 计时，15 万行级别）
- [ ] `GET /industry-distribution?scope=active` 加载时间 < 2s（扎堆股集合 JOIN sectors）

### 安全验收（架构 §8.3）

- [ ] `_escape_like_keyword` 转义 search 中的 `%` 和 `_`，SQLAlchemy 参数绑定
- [ ] `page_size` 用 `Query(le=100)` 限制
- [ ] 未认证访问 `/rankings` 和 `/industry-distribution` 返回 401

### pytest 集成验收（E2E-TDD）

- [ ] **red 阶段**：在 `server/tests/test_fund_crowd_api.py` 追加 10+ 个 pytest 用例（§3 #7 详列），实现前运行预期失败（端点 404 / service ImportError），证据存 `docs/e2e/evidence/plan-01-08-pytest-red-{date}.md`
- [ ] **green 阶段**：实现完成后运行 `cd server && source .venv/bin/activate && pytest tests/test_fund_crowd_api.py --no-cov -v` 全部通过（含 18 个新增用例），证据存 `docs/e2e/evidence/plan-01-08-pytest-green-{date}.md`
- [ ] 现有 `test_fund_api.py` 测试不破坏（运行 `pytest tests/test_fund_api.py --no-cov -v` 通过）

### 全流程/集成验收（US 覆盖矩阵）

> 架构文档 §2.3 成功标准 + PRD §2.2 用户故事承接：US-01（扎堆排行榜）/ US-02（主动/被动切换）/ US-03（环比变化）/ US-04（行业分布）。

| US 编号 | 用户故事简述 | 承接功能 | 验证方式 |
| --- | --- | --- | --- |
| US-01 | 看到被最多基金持有的股票排行榜 | plan-01, plan-02 | plan-01 §5 AC-01 pytest + plan-02 §5 E2E 场景 1 |
| US-02 | 切换仅主动/全部基金口径 | plan-01, plan-02 | plan-01 §5 AC-02 pytest + plan-02 §5 E2E 场景 2 |
| US-03 | 看环比变化（加强/瓦解/新进） | plan-01, plan-02 | plan-01 §5 AC-03/06 pytest + plan-02 §5 E2E 场景 3 |
| US-04 | 看扎堆股集中在哪些行业 | plan-01, plan-02 | plan-01 §5 AC-04 pytest + plan-02 §5 E2E 场景 4 |

- [ ] US-01/02/03/04 的后端语义在 plan-01 pytest 用例中可独立验证

## 6. 验证命令

```bash
# red 阶段：预期失败（端点 404 / ImportError）
cd server && source .venv/bin/activate && pytest tests/test_fund_crowd_api.py --no-cov -v

# green 阶段：全部通过
cd server && source .venv/bin/activate && pytest tests/test_fund_crowd_api.py --no-cov -v

# 现有 funds 测试回归（不应破坏）
cd server && source .venv/bin/activate && pytest tests/test_fund_api.py --no-cov -v

# 手动验证（启动后端 + curl，需先生成普通用户 token）
cd server && uvicorn main:app --reload --port 8000
# 另一个终端
curl -X GET "http://localhost:8000/api/v1/fund-crowd-analysis/rankings?scope=active&page=1&page_size=20" \
  -H "Authorization: Bearer <user_token>"
curl -X GET "http://localhost:8000/api/v1/fund-crowd-analysis/industry-distribution?scope=active" \
  -H "Authorization: Bearer <user_token>"

# 非阻塞索引迁移（若实施）
cd server && alembic upgrade head
```

> **MEMORY 提醒**：后端跑单/子集测试文件必须加 `--no-cov`，否则 `cov-fail-under=80` 致退出码非 0 误判失败。

pytest API 集成测试（参照 `test_fund_api.py`）是后端功能的主质量门。开发必须先运行 red pytest 看到预期失败（端点 404），再实现到 green 全部通过。

## 7. 交接上下文

- **架构章节**: §1 系统摘要、§4.2 模块职责、§5 ADR-1/2/3/5/6、§6.1/6.2 运行链路、§7.2 Schema、§7.3 API 边界、§7.6 命名规则、§8.1 性能、§8.2 降级（L1-L5）、§8.3 安全、§8.5 可观测性
- **相关代码**:
  - 现有 service 参考：`server/src/services/shareholder_analysis_service.py:264-302`（`_compute_change_directions` 范式）、`:304-352`（`_get_industry_for_stocks` JOIN 范式）
  - 现有 repository 参考：`server/src/repositories/fund_repository.py:38-39`（构造函数）、`:172-300`（FundPortfolio 查询范式）
  - 现有路由参考：`server/src/api/v1/funds.py:24`（router prefix）、`:196-238`（reverse_lookup 端点 + `_dict_to_camel` 用法）、`:30-80`（Pydantic model + to_camel 范式）
  - 现有测试参考：`server/tests/test_fund_api.py`（fixtures + httpx 风格 + FundPortfolio 插入）
  - 模型字段：`server/src/models/fund_portfolio.py:14-21`（FundPortfolio 字段已确认满足聚合需求）
- **契约 / 数据对象**:
  - `RankingItem` / `RankingsData` / `IndustryItem` / `IndustryDistributionData`（本 plan §3 #3 详列）
  - `ApiResponse{ success, data }` 外层包裹（`src.api.schemas.response`）；本 plan 端点直接返回 `{"success": True, "data": _dict_to_camel(result)}`，与 `funds.reverse_lookup` 一致（不强制用 `ApiResponse` 类，可用 dict）
- **下游消费方**: plan-02（前端 `fundCrowdAnalysisApi.getRankings` + `getIndustryDistribution` 直接消费这两个端点的契约）；plan-03（下钻复用 04 `/funds/reverse-lookup`，与本 plan 无契约依赖）

## 8. 风险与边界

- **执行顺序**: 按 Task 列表顺序执行。Task 1（red 测试）必须先于 Task 2-7（实现）；Task 9（索引迁移）非阻塞，最后做。
- **验证失败排查方向**:
  - pytest 报 ImportError / 测试代码错误 → 先修测试代码（不是被测代码问题）
  - pytest 报 404 → 正常的 red 阶段失败，进入实现
  - pytest 报 500 / SQL 错误 → 检查 `get_crowd_aggregation` 的 JOIN funds 写法（INNER JOIN 是否正确）+ scope 过滤的 NULL 处理（`Fund.invest_type.is_(None)` 显式包含）
  - 环比数值不对 → 检查 `_compute_changes` 的 dict 对比逻辑（is_new 判定 + ratio_change None 传播）
  - 分页 total 不对 → search 是否在 SQL WHERE 层过滤（路径 A）；若用 Python 过滤（路径 B）需对过滤后的 items 分页
- **允许修改的额外文件**:
  - 若 `_dict_to_camel` 已在某个 helper 模块存在（如 `src/api/v1/_helpers.py`），可改为 import 复用而非重复定义
  - 若 SQLAlchemy 版本对 `func.count(FundPortfolio.fund_ts_code.distinct())` 支持有问题，可改用 `func.count_distinct(FundPortfolio.fund_ts_code)`（视版本而定）
- **暂停条件**:
  - alembic 迁移生成受阻（如本地 alembic 配置问题）→ 暂停 Task 9，记录后降级为"运维阶段手动建索引"，不阻塞 plan-01 进入 done
  - JOIN funds 后性能严重退化（> 5s）→ 暂停，向用户确认是否引入 `funds.ts_code` 索引优化或改子查询
- **E2E 不适用说明**: 后端 FEAT 的 red/green 用 pytest API 集成测试（参照 `test_fund_api.py`），不写 Playwright（参照 MEMORY `后端 FEAT E2E 适配 pytest`）。这是后端测试的既定方案，不是豁免
- **风险备注**:
  - **NULL 投资类型处理**：`Fund.invest_type` 为 NULL 时必须用 `.is_(None)` 显式包含到主动型，否则 SQL `NOT IN (...)` 会漏掉 NULL 行（ADR-1 风险对策）；测试用例 #1/#4 显式覆盖（001004.OF invest_type=None 归主动）
  - **stk_float_ratio NULL 累加**：SUM 自动忽略 NULL，但若该股票所有记录均为 NULL → `total_float_ratio=None`（前端显示"—"）；测试用例 #16 覆盖（L3 降级）
  - **stocks 表缺失兜底**：`get_stock_names` 返回的 dict 缺失某 symbol → service 层 `stock_names.get(symbol)` 返回 None → `stockName=null`；测试用例 #15 覆盖
  - **search 大小写**：stock_symbol 用 `.like('xxx%')`（区分大小写，因股票代码本身大写）；stock_name 用 `.ilike('%xxx%')`（不区分大小写，AC-08 "不区分大小写" 指名称搜索）

### 后端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| `fund_portfolio` 表为空 | `get_report_periods` 返回 `[]` → service 返回 `hasData=false` | done |
| 只有一个报告期（无上期） | `hasPrevPeriod=false`，所有 item 的 change 字段为 null | done |
| 某股票上期无记录 | `is_new=true`、`fund_count_change=null`、`total_float_ratio_change=null` | done |
| `stk_float_ratio` 全 NULL | `total_float_ratio=null`，`fund_count` 正常 | done |
| `invest_type` 为 NULL | 显式归主动型（`.is_(None)` 包含） | done |
| `stocks` 表缺失某 symbol | `stock_name=null`，不影响扎堆度计算 | done |
| 某股票无行业关联 | `industries=[]`（rankings）/ 归入"未分类"桶（industry-distribution） | done |
| `scope` 传非法值（非 active/all） | 路由层容错为 `scope=active` | done |
| `search` 含 `%` 或 `_` | `_escape_like_keyword` 转义 → 安全 LIKE 查询 | done |
| `page=0` 或负数 | FastAPI `Query(ge=1)` 校验 → 422 | done |
| `page_size=200` 超过 100 | FastAPI `Query(le=100)` 校验 → 422 | done |
| 一股多行业 | `industries` 数组多值 / 行业分布多桶独立计数 | done |
| 未认证访问 | `Depends(get_current_user)` 拒绝 → 401 | done |
| 单只基金跨多报告期重复持有同一股票 | `COUNT(DISTINCT fund_ts_code)` 去重，单期内只算 1 只 | done |
