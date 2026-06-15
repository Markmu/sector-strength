---
feat_id: "plan-01"
title: "后端逐关键词股数与明细查询API"
dimension: backend
phase: 1
status: done
depends_on: []
---

# plan-01: 后端逐关键词股数与明细查询API

## 1. 功能概要

- **目标**: 在 `ShareholderGroupService` 增加 2 个公开方法（`preview_match_breakdown` + `list_keyword_matches`）和 2 个私有辅助方法（`_count_matched_stocks_single` + `_get_keyword_matches`），并在 admin 路由 `shareholder_groups.py` 新增 2 个 GET 端点（`/preview-breakdown` + `/keyword-matches`）及 4 个 Pydantic 响应模型，让前端能在编辑弹窗内逐关键词查询匹配股数并下钻查看明细。
- **完成后可观察结果**: 管理员在前端弹窗输入关键词后，前端能调到 `/api/v1/admin/shareholder-groups/preview-breakdown?keywords=kw1,kw2` 拿到每个关键词单独匹配的去重股票数；点击「查看明细」能调到 `/api/v1/admin/shareholder-groups/keyword-matches?keyword=kw&page=1&page_size=20` 拿到三列（symbol + stockName + holderName）按股票代码升序排列、同股票多股东分行的明细列表，total 字段与列表行数（同股票多股东按分行）口径一致。当某个关键词查询失败时，返回的对应 item 中 `matchedStockCount` 为 null，前端据此渲染错误状态。普通用户访问返回 401/403，未认证访问返回 401（与现有 `preview` 端点的权限模型一致）。现有 `preview` 端点（合并总数）行为完全不变。
- **依赖**: 无（独立后端功能；测试需要的 fixture 自带）
- **关联验收标准**: [AC-01, AC-02, AC-03, AC-04, AC-05, AC-07]
- **涉及架构模块**: `ShareholderGroupService`（新增方法）、admin 路由 `shareholder_groups.py`（新增端点 + 模型）
- **前置条件**:
  - PostgreSQL 实例运行（开发库，与 05/06 共用）
  - `top10_float_holders` 表有 `ix_top10_symbol_period (symbol, report_period)` 和 `ix_top10_report_period (report_period)` 索引（05 已建）
  - `stocks` 表存在且 `stocks.symbol` 可与 `top10_float_holders.symbol` 关联
  - 后端依赖 `src.api.deps.require_admin`、`src.api.schemas.response.ApiResponse`、`pydantic.alias_generators.to_camel` 均已就位（06 已用）
- **不在范围**:
  - 前端任何改动（plan-02 负责）
  - 用户侧 `/api/v1/shareholder-analysis/*` 任何端点改动
  - 修改现有 `preview` 端点行为（保留下游 UI 与 E2E mock 不变）
  - 修改现有 `_count_matched_stocks`（OR 多关键词版）
  - 新增数据库表 / 字段 / 迁移
  - 引入缓存层 / 异步任务队列

## 2. 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| modify | `server/src/services/shareholder_group_service.py` | 新增 4 个方法：`preview_match_breakdown`、`list_keyword_matches`、`_count_matched_stocks_single`、`_get_keyword_matches` |
| modify | `server/src/api/admin/shareholder_groups.py` | 新增 2 个端点（`GET /preview-breakdown`、`GET /keyword-matches`）+ 4 个 Pydantic 响应模型（`KeywordCountItem`、`PreviewBreakdownData`、`KeywordMatchItem`、`KeywordMatchesData`） |
| modify | `server/tests/test_shareholder_group_admin_api.py` | 追加 6+ 个 pytest 用例覆盖新端点 + 现有 preview 回归 |

## 3. 实现规格

### 后端部分

#### 1. `ShareholderGroupService._count_matched_stocks_single(keyword: str, period: Any) -> int`

**位置**：紧邻现有 `_count_matched_stocks` 方法之后（约 line 155 后）。

**复用声明**：
- `_escape_like_keyword`：模块级私有函数（line 86-95），`return keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")`
- `Top10FloatHolder`：从 `src.models` import（已在文件顶部 import，无需重复）
- `func.count` / `func.distinct` / `select` / `and_`：已在文件顶部 import

**实现要点**：
- 单关键词版本的 `_count_matched_stocks`，**不再调用** `_get_latest_report_period`（period 由调用方传入，避免 N 个关键词时 N 次查 MAX）
- SQL 形态（参数绑定，禁止拼接）：
  ```python
  stmt = (
      select(func.count(func.distinct(Top10FloatHolder.symbol)))
      .where(
          and_(
              Top10FloatHolder.report_period == period,
              Top10FloatHolder.holder_name.like(
                  f"%{_escape_like_keyword(keyword)}%", escape="\\"
              ),
          )
      )
  )
  ```
- 调用方负责保证 `keyword` 已 `.strip()` 且非空、`period` 已校验非 None
- 返回 `int(result.scalar() or 0)`，与现有 `_count_matched_stocks` 一致

**安全要求**（架构 §8.3）：
- 关键词长度 sanity check：调用方 `preview_match_breakdown` 在循环前过滤 `len(kw) > 200` 的关键词直接返回 null（不发起查询，避免超大 pattern 拖垮 DB），参照 `ShareholderGroupRule.keyword` 字段 `String(200)` 上限

#### 2. `ShareholderGroupService._get_keyword_matches(keyword: str, period: Any) -> list[tuple]`

**位置**：紧邻 `_count_matched_stocks_single` 之后。

**复用声明**：
- `Stock` 模型：从 `src.models` import（若文件未 import 需新增 `from src.models import Stock`，参照 `shareholder_analysis_service.py:292-344` 的 import 方式）
- `_escape_like_keyword`：模块级私有函数（line 86-95）

**实现要点**（ADR-3：一次性完成匹配 + JOIN stocks + 排序）：
- 使用 SQLAlchemy 显式构造 SQL（不使用 raw text，但功能等价于架构 §6.2 SQL）：
  ```python
  from sqlalchemy import literal_column
  from sqlalchemy.dialects.postgresql import aggregate_order_by  # 仅参考，DISTINCT ON 用 func

  stmt = (
      select(
          Top10FloatHolder.symbol,
          Stock.name.label("stock_name"),
          Top10FloatHolder.holder_name,
      )
      .select_from(Top10FloatHolder)
      .outerjoin(Stock, Stock.symbol == Top10FloatHolder.symbol)
      .where(
          and_(
              Top10FloatHolder.report_period == period,
              Top10FloatHolder.holder_name.like(
                  f"%{_escape_like_keyword(keyword)}%", escape="\\"
              ),
          )
      )
      # DISTINCT ON 必须配合 ORDER BY 前缀匹配（PG 要求）
      .distinct(
          Top10FloatHolder.symbol,
          Top10FloatHolder.holder_name,
      )
      .order_by(
          Top10FloatHolder.symbol.asc(),
          Top10FloatHolder.holder_name.asc(),
          Top10FloatHolder.ann_date.desc().nullslast(),
      )
  )
  ```
- 若 SQLAlchemy `.distinct(*columns)` API 不可用或不直观，可改用 `.prefix_with("DISTINCT ON (h.symbol, h.holder_name)")` 写在 select_from 之前；最终以 pytest 验证为准
- 返回 `result.all()`，每行是 `Row(symbol, stock_name, holder_name)`；`stock_name` 可能为 None（stocks 表缺失该 symbol）
- 不在本方法内做分页（分页由 `list_keyword_matches` 在 Python 层做，参照 `ShareholderAnalysisService.get_holdings` 风格）

**实现备选（若 .distinct(*cols) 在当前 SQLAlchemy 版本不可用）**：
- 用子查询：先 select `DISTINCT ON (symbol, holder_name) ... ORDER BY symbol, holder_name, ann_date DESC`，外层再 `ORDER BY symbol, holder_name`
- 推荐先尝试 `.distinct(*cols)`，pytest red 失败再切换

#### 3. `ShareholderGroupService.preview_match_breakdown(keywords: list[str], exclude_group_id: Optional[int] = None) -> dict`

**位置**：紧邻现有 `preview_match` 方法之后。

**复用声明**：
- `_get_latest_report_period`（line 107-111）：取 MAX(report_period)
- `_count_matched_stocks_single`：本 plan 新增的私有方法

**实现要点**（架构 §6.1 + ADR-5 降级）：
- 入参 `keywords` 为前端传入的 list[str]（由路由层把逗号字符串 split 后传入）
- 调用前过滤空关键词（`kw.strip()` 为空的不进入结果）
- 报告期取一次：`period = await self._get_latest_report_period()`；为 None 时每个关键词返回 0
- 对每个关键词用 `try/except Exception` 单独包裹（重要：单个关键词失败不抛错到整体）：
  ```python
  items = []
  period = await self._get_latest_report_period()
  for kw in keywords:
      clean = kw.strip()
      if not clean:
          continue  # 空 kw 不返回 item（前端按索引映射会跳过空行）
      if len(clean) > 200:
          items.append({"keyword": kw, "matched_stock_count": None})
          logger.error("keyword too long, skip: %s", clean[:50])
          continue
      if period is None:
          items.append({"keyword": kw, "matched_stock_count": 0})
          continue
      try:
          cnt = await self._count_matched_stocks_single(clean, period)
          items.append({"keyword": kw, "matched_stock_count": cnt})
      except Exception as e:
          logger.exception("preview_match_breakdown single kw failed: %s", e)
          items.append({"keyword": kw, "matched_stock_count": None})
  return {"items": items}
  ```
- 注意：返回字典的 key 用 snake_case（`matched_stock_count`），由路由层 `_dict_to_camel` 转 camelCase
- `exclude_group_id` 参数本期后端实现时可忽略（与现有 `_count_matched_stocks` 一致的占位行为），但保留入参以保持 API 一致性

**可观测性（架构 §8.5）**：
- 方法入口记录 `logger.info("preview_match_breakdown called, keywords=%d, period=%s", len(keywords), period)`
- 单关键词失败 catch 内记录 `logger.exception(...)`（已含堆栈）
- 复用文件顶部现有 `logger = logging.getLogger(__name__)`

#### 4. `ShareholderGroupService.list_keyword_matches(keyword: str, page: int, page_size: int, exclude_group_id: Optional[int] = None) -> dict`

**位置**：紧邻 `preview_match_breakdown` 之后。

**复用声明**：
- `_get_latest_report_period`（line 107-111）
- `_get_keyword_matches`：本 plan 新增的私有方法

**实现要点**（架构 §6.2）：
- 入参 `keyword` 为单值（已 `.strip()` 非空，由路由层校验）；`page` ≥ 1（默认 1）；`page_size` 默认 20
- 报告期为 None → 返回空列表 + total=0
- 全量查询：`rows = await self._get_keyword_matches(keyword, period)`
- Python 层分页：
  ```python
  total = len(rows)
  offset = (page - 1) * page_size
  page_rows = rows[offset : offset + page_size]
  items = [
      {
          "symbol": r.symbol,
          "stock_name": r.stock_name,  # 可能为 None
          "holder_name": r.holder_name,
      }
      for r in page_rows
  ]
  return {
      "items": items,
      "total": total,
      "page": page,
      "page_size": page_size,
  }
  ```
- `total` 用 `len(rows)`（与列表行数口径一致，即同股票多股东按分行计入）—— 与架构 §6.2 的 `COUNT(DISTINCT (h.symbol, h.holder_name))` 等价
- `exclude_group_id` 入参同 `preview_match_breakdown`，本期后端实现时可忽略

**性能优化（架构 §10 演进方向）**：
- 若上线后发现单关键词匹配 > 1000 行导致内存压力，再改为 SQL 层 `LIMIT/OFFSET` + `COUNT(*) OVER()`（不在本期范围）

#### 5. Pydantic 响应模型（4 个）

**位置**：`server/src/api/admin/shareholder_groups.py` 现有 `PreviewMatchResponse` 模型之后（约 line 67 后）。

```python
class KeywordCountItem(BaseModel):
    """逐关键词股数项"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    keyword: str = Field(..., description="前端传入的草稿关键词原值")
    matched_stock_count: Optional[int] = Field(
        ..., description="该关键词单独匹配的去重股数；null 表示查询失败"
    )


class PreviewBreakdownData(BaseModel):
    """股数细分响应 data"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    items: List[KeywordCountItem] = Field(..., description="逐关键词股数列表")


class KeywordMatchItem(BaseModel):
    """单条明细项"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    symbol: str = Field(..., description="股票代码")
    stock_name: Optional[str] = Field(
        None, description="股票名称；stocks 表缺失该 symbol 时为 null"
    )
    holder_name: str = Field(..., description="股东名称")


class KeywordMatchesData(BaseModel):
    """明细列表响应 data"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    items: List[KeywordMatchItem] = Field(..., description="明细列表")
    total: int = Field(..., description="符合条件的总明细行数")
    page: int = Field(..., description="当前页码（1-based）")
    page_size: int = Field(..., description="每页条数")
```

- 字段经 `to_camel` 转 camelCase 输出（`matchedStockCount`、`stockName`、`holderName`、`pageSize`）—— 与架构 §7.2 一致
- `KeywordCountItem.matched_stock_count` 类型为 `Optional[int]`，对应 AC-07 单关键词失败降级

#### 6. 路由层端点 `GET /preview-breakdown`

**位置**：现有 `preview_match` 端点（line 81-98）之后，`GET ""` 列表端点（line 101）之前。**顺序关键**：必须在 `/{group_id}` 动态路径之前声明，避免被吞掉（与现有 `preview` 的位置约定一致，参照 line 78 注释）。

```python
@router.get("/preview-breakdown", response_model=ApiResponse[PreviewBreakdownData])
async def preview_match_breakdown(
    keywords: str = Query(..., description="逗号分隔的关键词列表"),
    exclude_group_id: Optional[int] = Query(
        None, description="预览时排除的分组ID（可选，本期占位）"
    ),
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    """逐关键词查询匹配的去重股票数（AC-01）。"""
    keyword_list = [kw.strip() for kw in keywords.split(",") if kw.strip()]
    service = ShareholderGroupService(session)
    result = await service.preview_match_breakdown(keyword_list, exclude_group_id)
    return ApiResponse(
        success=True,
        data=PreviewBreakdownData(
            items=[
                KeywordCountItem(**_dict_to_camel(item)) for item in result["items"]
            ]
        ),
        message=f"共 {len(result['items'])} 个关键词",
    )
```

**前后端契约校验（四件套）**：
- 路径拼接：前端 endpoint `/admin/shareholder-groups/preview-breakdown?...` × apiClient.baseURL `${API_BASE_URL}/api/v1` = 后端实际路径 `/api/v1/admin/shareholder-groups/preview-breakdown`（admin_router 在 `/v1/admin`，子 router 在 `/shareholder-groups`，无重复前缀）
- HTTP 方法：GET；后端 `@router.get` 与前端 `adminApiClient.get` 一致
- query 参数命名：`keywords`（逗号分隔字符串）、`exclude_group_id`（snake_case，与现有 `preview` 一致）；FastAPI 接收 snake_case，前端 `URLSearchParams` 写 `exclude_group_id` —— 一致
- 响应字段命名：外层 `ApiResponse{ success, data, message }`（与现有 admin 端点一致）；`data` 内 `items[].matchedStockCount`（camelCase，由 Pydantic alias 转换）；前端类型定义必须用 `matchedStockCount` —— 一致

#### 7. 路由层端点 `GET /keyword-matches`

**位置**：紧邻 `preview-breakdown` 之后。

```python
@router.get("/keyword-matches", response_model=ApiResponse[KeywordMatchesData])
async def get_keyword_matches(
    keyword: str = Query(..., min_length=1, description="单个关键词"),
    page: int = Query(1, ge=1, description="页码（1-based）"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    exclude_group_id: Optional[int] = Query(
        None, description="排除的分组ID（可选，本期占位）"
    ),
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    """查询单个关键词匹配的明细列表（AC-03 ~ AC-05）。"""
    service = ShareholderGroupService(session)
    result = await service.list_keyword_matches(
        keyword=keyword.strip(),
        page=page,
        page_size=page_size,
        exclude_group_id=exclude_group_id,
    )
    return ApiResponse(
        success=True,
        data=KeywordMatchesData(**_dict_to_camel(result)),
        message=f"共 {result['total']} 条明细",
    )
```

**前后端契约校验（四件套）**：
- 路径拼接：前端 endpoint `/admin/shareholder-groups/keyword-matches?...` × baseURL `/api/v1` = `/api/v1/admin/shareholder-groups/keyword-matches`（无重复前缀）
- HTTP 方法：GET
- query 参数命名：`keyword`、`page`、`page_size`（snake_case，FastAPI 自动转 snake_case 收参数）；前端必须传 `page_size`（不是 `pageSize`）—— query 参数不经 Pydantic alias 转换，**响应体字段才转**
- 响应字段命名：`data.items[].stockName / holderName`（camelCase）；`data.pageSize`（camelCase）；前端类型定义必须用 `pageSize`、`stockName`、`holderName`

**安全要求（架构 §8.3）**：
- `keyword` 用 `min_length=1` 防止空串
- `page_size` 用 `le=100` 限制最大值，防止恶意大页请求拖垮 DB
- 单关键词长度限制由 service 层 `_get_keyword_matches` 调用 `_escape_like_keyword` 时天然保护（虽不报错但匹配效率受影响；架构 §8.3 提到对超 200 字符的 keyword 在 `preview_match_breakdown` 层级直接返回 null，明细场景由 `Query(min_length=1)` 起步保护；如需更严可在路由加 `max_length=200`）

#### 8. pytest 测试用例（追加到 `server/tests/test_shareholder_group_admin_api.py`）

**位置**：现有文件末尾追加，复用现有 `admin_client` / `normal_client` / `client`（未认证）fixtures。

**测试数据准备 fixture**：
```python
@pytest_asyncio.fixture
async def sample_holders(test_session):
    """插入测试 top10_float_holders 数据：覆盖单关键词多股、同股票多股东、跨报告期"""
    from src.models.top10_float_holder import Top10FloatHolder
    from datetime import date

    rows = [
        # 报告期 2024-06-30
        Top10FloatHolder(symbol="600000", report_period=date(2024, 6, 30),
                          holder_name="全国社保基金一一六组合", ann_date=date(2024, 7, 1)),
        Top10FloatHolder(symbol="600000", report_period=date(2024, 6, 30),
                          holder_name="全国社保基金一零四组合", ann_date=date(2024, 7, 1)),
        Top10FloatHolder(symbol="600036", report_period=date(2024, 6, 30),
                          holder_name="全国社保基金一零八组合", ann_date=date(2024, 7, 1)),
        Top10FloatHolder(symbol="000001", report_period=date(2024, 6, 30),
                          holder_name="社保基金理事会", ann_date=date(2024, 7, 1)),
        # 旧报告期 2024-03-31（验证只取最新期）
        Top10FloatHolder(symbol="600000", report_period=date(2024, 3, 31),
                          holder_name="全国社保基金一二三组合（旧期）", ann_date=date(2024, 4, 1)),
    ]
    test_session.add_all(rows)
    await test_session.commit()

    # stocks 表插入股票名称
    from src.models.stock import Stock
    stocks = [
        Stock(symbol="600000", name="浦发银行"),
        Stock(symbol="600036", name="招商银行"),
        # 000001 故意不插入，测试 stockName=null 兜底
    ]
    test_session.add_all(stocks)
    await test_session.commit()
    return rows
```

**测试用例（6+ 个，覆盖 AC-01/03/04/05/07 + 回归）**：
1. `test_preview_breakdown_returns_per_keyword_count`（AC-01）：调 `?keywords=全国社保,社保基金`，断言返回 2 个 item，每个 matchedStockCount 正确（全国社保 → 2 只：600000 + 600036；社保基金 → 3 只：600000 + 600036 + 000001）
2. `test_preview_breakdown_empty_keywords_returns_empty`（AC-01 边界）：调 `?keywords=,,,`，断言 items 为空
3. `test_keyword_matches_returns_three_columns`（AC-03）：调 `?keyword=全国社保&page=1&page_size=20`，断言每个 item 含 symbol + stockName + holderName 三字段；total=3
4. `test_keyword_matches_same_stock_multi_holders_split_rows`（AC-04）：调 `?keyword=全国社保`，断言 600000 出现 2 行（一一六组合 + 一零四组合），symbol 相同但 holderName 不同
5. `test_keyword_matches_ordered_by_symbol_then_holder`（AC-05）：调 `?keyword=社保基金`，断言返回的 symbol 序列单调不降序（600000 < 600000 < 000001 不成立 → 实际应是 000001 < 600000 < 600000，因 0 < 6 字符串比较）—— 注意调整 fixture 让 symbol 升序有意义（如改 000001 为 600001）
6. `test_keyword_matches_stock_name_null_when_stocks_table_missing`（AC-03 边界）：调 `?keyword=社保基金`，断言 000001 行的 stockName 为 null
7. `test_keyword_matches_pagination`（AC-03 边界）：调 `?keyword=社保基金&page=1&page_size=2` 断言 items 长度为 2 + total=3；调 `?page=2` 断言剩 1 条
8. `test_preview_breakdown_partial_failure_returns_null_for_failed_keyword`（AC-07 后端语义）：mock service 在某个关键词查询时抛 Exception，断言该 item 的 matchedStockCount 为 null，其他 item 正常
9. `test_keyword_matches_only_latest_report_period`（隐含约束）：断言旧报告期（2024-03-31）的 holder 不在结果中
10. `test_preview_breakdown_requires_admin`（权限回归）：normal_client → 403；client（无 token）→ 401
11. `test_keyword_matches_requires_admin`（权限回归）：同上
12. `test_existing_preview_endpoint_still_works`（AC-02 回归）：现有 `?keywords=全国社保,社保基金` 调 `/preview` 仍返回合并总数（去重 3 只），与改造前一致

**SQL 注入回归测试**（AC 隐含，架构 §8.3）：
13. `test_keyword_matches_escapes_like_wildcards`：调 `?keyword=%`，断言结果为空或仅匹配字面 `%`，不会匹配全表

**red 阶段原则**：
- 测试只通过 HTTP client 调 API 端点，不 import 尚未实现的业务模块
- red 阶段失败原因应为「端点尚未实现 → 404」（参照现有 test 文件 line 14-15 注释），而非 ImportError / 测试代码错误
- 失败原因不能是测试代码本身的语法/逻辑错误（如有则先修测试代码）

## 4. Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | red：追加 6+ pytest 用例到 `test_shareholder_group_admin_api.py` | backend | done | 覆盖 §3 #8 的 13 个测试用例（最小 6 个核心 + 4 个边界 + 3 个回归）；运行预期失败（端点 404） |
| 2 | 实现 `_count_matched_stocks_single` 私有方法 | backend | done | 紧邻现有 `_count_matched_stocks` 之后；复用 `_escape_like_keyword` + period 入参 |
| 3 | 实现 `_get_keyword_matches` 私有方法 | backend | done | SQLAlchemy `.distinct(*cols)` + outerjoin Stock；优先尝试该 API，失败再改子查询 |
| 4 | 实现 `preview_match_breakdown` 公开方法 | backend | done | 单关键词 try/except 降级；logger.info/exception |
| 5 | 实现 `list_keyword_matches` 公开方法 | backend | done | Python 层分页；total = len(rows) |
| 6 | 新增 4 个 Pydantic 响应模型 | backend | done | `KeywordCountItem` / `PreviewBreakdownData` / `KeywordMatchItem` / `KeywordMatchesData` |
| 7 | 新增 `GET /preview-breakdown` 端点 | backend | done | 紧邻 `preview` 之后、列表端点之前；`Depends(require_admin)` |
| 8 | 新增 `GET /keyword-matches` 端点 | backend | done | 紧邻 `/preview-breakdown` 之后；query 参数 `page_size`、`page`（snake_case） |
| 9 | green：运行 pytest 全套通过 | backend | done | 33/33 用例通过（含 15 新增 + 18 现有），证据由 test-e2e 阶段写入 `docs/e2e/evidence/plan-01-07-e2e-green-{date}.md` |

## 5. 验收标准

### 后端核心功能验收

- [ ] AC-01 `GET /preview-breakdown?keywords=全国社保,社保基金` 返回 2 个 item，每个 matchedStockCount 单独计算（互不影响、互不依赖）
- [ ] AC-02 `GET /preview?keywords=...` 行为完全不变（回归测试通过）
- [ ] AC-03 `GET /keyword-matches?keyword=全国社保` 返回 items 每行含 symbol + stockName + holderName 三字段；total 与列表行数口径一致
- [ ] AC-04 同股票多股东 → 多行（如 600000 × 2 不同 holderName）
- [ ] AC-05 返回 items 按 symbol 升序；同 symbol 的多行相邻
- [ ] AC-07 单关键词查询失败时该 item `matchedStockCount: null`，其他 item 正常返回

### 性能验收（架构 §8.1 目标）

- [ ] 单关键词股数查询（COUNT DISTINCT）≤ 200ms（pytest 中用 `time.perf_counter()` 套查询断言可接受；本地 PostgreSQL）
- [ ] 单关键词明细查询（含 JOIN + 分页）≤ 1s（典型 < 200 条数据量）

### 安全验收（架构 §8.3）

- [ ] `_escape_like_keyword` 转义 `%` 和 `_`，查询参数绑定 holder_name，不拼接 SQL
- [ ] `keyword` 用 `Query(min_length=1)` 防空串；`page_size` 用 `le=100` 限制
- [ ] 关键词超 200 字符的 preview 项返回 `matchedStockCount: null`
- [ ] normal_user 访问 `/preview-breakdown` 返回 403；无 token 返回 401
- [ ] normal_user 访问 `/keyword-matches` 返回 403；无 token 返回 401

### pytest 集成验收（E2E-TDD）

- [ ] **red 阶段**：在 `server/tests/test_shareholder_group_admin_api.py` 追加 6+ 个 pytest 用例（§3 #8 详列），实现前运行预期失败（端点 404），证据存 `docs/e2e/evidence/plan-01-pytest-red-{date}.md`
- [ ] **green 阶段**：实现完成后运行 `pytest tests/test_shareholder_group_admin_api.py -v` 全部通过（含新增用例 + 现有 5 个端点测试不破坏），证据存 `docs/e2e/evidence/plan-01-pytest-green-{date}.md`

### 全流程/集成验收（US 覆盖矩阵）

> 架构文档 §2.3 成功标准 + PRD §2.2 用户故事承接：US-01（逐关键词定位）/ US-02（保存前下钻）/ US-04（同股票多股东相邻）/ US-05（失败降级不阻塞）。

| US 编号 | 用户故事简述 | 承接功能 | 验证方式 |
| --- | --- | --- | --- |
| US-01 | 编辑时看到每个关键词分别匹配多少股 | plan-01, plan-02 | plan-01 §5 AC-01 pytest + plan-02 §5 Playwright 场景 1 |
| US-02 | 保存前下钻查看具体匹配股票与股东 | plan-01, plan-02 | plan-01 §5 AC-03/04/05 pytest + plan-02 §5 Playwright 场景 2 |
| US-03 | 修改关键词后股数与明细实时刷新 | plan-02 | plan-02 §5 Playwright 场景 3 |
| US-04 | 明细按股票代码升序，同股票多股东相邻 | plan-01, plan-02 | plan-01 §5 AC-04/05 pytest + plan-02 §5 Playwright 场景 2 |
| US-05 | 明细加载失败不阻塞编辑和保存 | plan-01, plan-02 | plan-01 §5 AC-07 pytest + plan-02 §5 Playwright 场景 4 |

- [ ] US-01/02/04/05 的后端语义在 plan-01 pytest 用例中可独立验证（US-03/05 的前端行为由 plan-02 验证）

## 6. 验证命令

```bash
# red 阶段：预期失败（端点 404 / 测试 assertion error）
cd server && source .venv/bin/activate && pytest tests/test_shareholder_group_admin_api.py -v -k "preview_breakdown or keyword_matches"

# green 阶段：全部通过
cd server && source .venv/bin/activate && pytest tests/test_shareholder_group_admin_api.py -v

# 仅跑新端点的测试
cd server && source .venv/bin/activate && pytest tests/test_shareholder_group_admin_api.py -v -k "preview_breakdown or keyword_matches"

# 现有 preview 端点回归
cd server && source .venv/bin/activate && pytest tests/test_shareholder_group_admin_api.py -v -k "preview_match"

# 手动验证（启动后端 + curl）
cd server && uvicorn main:app --reload --port 8000
# 另一个终端（先生成管理员 token）
curl -X GET "http://localhost:8000/api/v1/admin/shareholder-groups/preview-breakdown?keywords=全国社保,社保基金" \
  -H "Authorization: Bearer <admin_token>"
curl -X GET "http://localhost:8000/api/v1/admin/shareholder-groups/keyword-matches?keyword=全国社保&page=1&page_size=20" \
  -H "Authorization: Bearer <admin_token>"
```

E2E（pytest API 集成测试）是后端功能的主质量门。开发必须先运行 red pytest 看到预期失败（端点 404），再实现到 green 全部通过。

## 7. 交接上下文

- **架构章节**: §1 系统摘要、§4.2 模块职责（后端 4 个新方法 + 2 端点）、§5 ADR-1/2/3/5、§6.1/6.2 运行链路、§7.2 Schema、§7.3 API 边界、§8.1 性能、§8.3 安全、§8.5 可观测性
- **相关代码**:
  - 现有 service：`server/src/services/shareholder_group_service.py:86-154`（复用工具）
  - 现有路由：`server/src/api/admin/shareholder_groups.py:22, 81-98`（路由前缀 + preview 端点参考）
  - JOIN 参考：`server/src/services/shareholder_analysis_service.py:292-344`（`_get_industry_for_stocks` 的 JOIN Stock 模式）
  - 测试参考：`server/tests/test_shareholder_group_admin_api.py`（fixtures + httpx 风格）
- **契约 / 数据对象**:
  - `KeywordCountItem`、`PreviewBreakdownData`、`KeywordMatchItem`、`KeywordMatchesData`（本 plan §3 #5 详列）
  - `ApiResponse[T]` 外层包裹（`src.api.schemas.response`）
- **下游消费方**: plan-02（前端 `adminApi.previewShareholderGroupMatchBreakdown` + `adminApi.listShareholderGroupKeywordMatches` 直接消费这两个端点的契约）

## 8. 风险与边界

- **执行顺序**: 按 Task 列表顺序执行。Task 1（red 测试）必须先于 Task 2-8（实现）。
- **验证失败排查方向**:
  - pytest 报 ImportError / 测试代码错误 → 先修测试代码（不是被测代码问题）
  - pytest 报 404 → 正常的 red 阶段失败，进入实现
  - pytest 报 500 / SQL 错误 → 检查 `_get_keyword_matches` 的 SQLAlchemy 写法（特别是 `.distinct(*cols)` API 在当前 SQLAlchemy 版本是否可用，不可用则改子查询）
  - 权限测试 403/401 不符合预期 → 检查 `require_admin` 是否正确依赖
- **允许修改的额外文件**:
  - 若 SQLAlchemy 版本不直接支持 `.distinct(*cols)`，可在 `shareholder_group_service.py` 引入子查询写法（不修改现有方法）
  - 若测试发现现有 fixture 不充分，可在 `test_shareholder_group_admin_api.py` 文件顶部新增 fixture（不影响现有用例）
- **暂停条件**:
  - SQLAlchemy `.distinct(*cols)` API 报错且子查询方案也不可行 → 暂停，向用户确认是否引入 raw SQL text
  - 测试 fixture 与现有 conftest 冲突 → 暂停，确认 fixture 命名空间
- **E2E 不适用说明**: 后端 FEAT 的 red/green 用 pytest API 集成测试，不写 Playwright（参照 MEMORY `后端 FEAT E2E 适配 pytest`）。这是后端测试的既定方案，不是豁免
- **风险备注**:
  - **SQLAlchemy DISTINCT ON 写法**：PostgreSQL `DISTINCT ON (cols)` 在 SQLAlchemy 中用 `.distinct(*cols)` 表达；不同版本支持度不同。red 阶段写测试时不依赖该 API（只断言结果），green 阶段如 API 不可用再切换子查询方案
  - **stocks 表缺失 symbol 兜底**：测试用例 `test_keyword_matches_stock_name_null_when_stocks_table_missing` 显式覆盖该场景；前端 plan-02 也会兜底显示「-」
  - **重复关键词**：后端按入参顺序返回相同 keyword 的多个 item；前端按索引映射渲染（详见 plan-02）

### 后端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| `keywords` query 参数为空字符串或全 `,` | 路由 split + filter 后 `keyword_list` 为空 → service 返回 `items=[]` | done |
| 单个关键词超 200 字符 | service 层 `len(clean) > 200` 判断 → 该 item 返回 `matchedStockCount: null` + 日志 ERROR | done |
| `top10_float_holders` 表最新报告期为 None | service 返回每个 item `matchedStockCount: 0`（preview）/ total=0 items=[]（keyword-matches） | done |
| 单关键词查询抛 DB 异常 | service 层 try/except 包裹 → 该 item 返回 `matchedStockCount: null`；其他 item 不受影响 | done |
| `stocks` 表缺失某 symbol | `LEFT JOIN` 后 stock_name 为 None → KeywordMatchItem.stock_name=None 输出 null | done |
| LIKE 通配符 `%` / `_` 在 keyword 中 | `_escape_like_keyword` 转义 → 安全 LIKE 查询 | done |
| `page=0` 或 `page=-1` | FastAPI `Query(ge=1)` 校验 → 422 | done |
| `page_size=200` 超过 100 | FastAPI `Query(le=100)` 校验 → 422 | done |
| normal_user 访问两个新端点 | `Depends(require_admin)` 拒绝 → 403 | done |
| 无 token 访问两个新端点 | `Depends(require_admin)` 拒绝 → 401 | done |
| 同股票多股东匹配（PG DISTINCT ON 行为） | `DISTINCT ON (symbol, holder_name)` + `ORDER BY symbol, holder_name, ann_date DESC NULLS LAST` → 每个 (symbol, holder_name) 取最新 ann_date 一行 | done |
| 报告期跨期（最新期 vs 旧期） | service 仅查 `MAX(report_period)` → 旧期数据不出现 | done |
