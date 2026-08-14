---
feat_id: "plan-06"
title: "融资融券查询API"
dimension: backend
phase: 2
status: done
depends_on: ["plan-01", "plan-03"]
---

# plan-06: 融资融券查询API

## 功能概要

- **目标**: 新建 `server/src/api/v1/margin.py`（逐行对照仿 `market_metrics.py`），提供登录态 `GET /api/v1/margin/trend?range=30|90|250`：从本地 `trading_calendar_days` 取最近 N 个开市日（`is_open=True`，DESC LIMIT N 后反转为升序）LEFT JOIN `market_margin_daily`（`trade_date == cal_date`），输出 `latest` + 带缺口的 points（缺失日六指标全 null，不补 0/前值）；**GET 路径零 Provider 调用**；响应经 `_dict_to_camel` + Decimal→float。
- **完成后可观察结果**: 登录用户请求该端点得到 `{success, data:{latest, points, range, hasMissingDates}}` camelCase 响应：point 含 `tradeDate/rzye/rqye/rzmre/rzche/rqmcl/rzrqye`（元口径 float），`points` 恰好 N 个交易日点且缺失日六指标为 null、`hasMissingDates` 如实标记；切 `range=90/250` 返回对应数量交易日点；本地日历无任何开市日时返回明确"未初始化"错误而非猜测日期；`range=50` 等非法值 422。
- **依赖**: plan-01（`market_margin_daily` 表与 `MarketMarginDaily` 模型、trading_calendar_days 复用）、plan-03（表内有真实数据可供执行验证）
- **关联验收标准**: [AC-5]（查询缺口：缺失日 null、hasMissingDates、points 长度=区间交易日数）
- **涉及架构模块**: 融资融券查询 API（spec REQ-6，对应 16 期 plan-06 的 market_metrics.py）
- **前置条件**: plan-01/03 已合并；本地 PostgreSQL。
- **不在范围**: 前端面板（plan-07）；admin 触发端点（plan-05）；任何写路径。

## 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| create | `server/src/api/v1/margin.py` | trend 端点 + helper，逐行对照 market_metrics.py |
| modify | `server/src/api/v1/__init__.py` | L27 旁 import + L49 旁 include_router 挂载 |
| create | `server/tests/api/test_margin.py` | 契约 / 缺口 / 空态 / 鉴权 / 零 Provider 测试 |

## 实现规格

### 后端部分

#### 1. 路由与契约（spec REQ-6）

- `router = APIRouter(prefix="/margin", tags=["Margin"])`；挂载链：v1 主路由 `/v1`（`api/v1/__init__.py`）→ main.py `/api` = **最终路径 `/api/v1/margin/trend`**
- 签名（照抄 market_metrics.py:103-113 范式，含 **16 期 Query pattern 实测教训**——Pydantic 2.12 禁止对 int schema 应用 pattern，声明为 pattern 约束的 `str` 后端点内 `int()`，线上契约不变）：

```python
@router.get("/trend")
async def get_trend(
    range: str = Query("30", description="趋势交易日数（30/90/250）", pattern="^(30|90|250)$"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
```

- **query 参数命名**：`range` 单词无 snake/camel 歧义；非法值由 Query pattern 校验拒绝（422）
- **响应包裹**：`{"success": True, "data": _dict_to_camel({...})}`；helper `_serialize_value`（Decimal→float、date→isoformat）与 `_dict_to_camel` 从 index_monitor.py:55-80 复制（与 market_metrics.py / etf_monitor 同源惯例）
- Decimal 经 `_serialize_value` 输出为有限 `float`（**不得输出字符串**）；单位口径锁定：**存储元、API 输出元原始值 float**，÷1e8 转亿只在 plan-07 前端显示层

#### 2. 查询逻辑（照抄 market_metrics.py:129-208 结构）

1. `range_days = int(range)`（`range` 为 Python 内建名，端点内改名避免遮蔽，16 期风险备注照搬）
2. `SELECT cal_date FROM trading_calendar_days WHERE is_open=true ORDER BY cal_date DESC LIMIT {range_days}` → 反转为升序 dates（≤250 点，走 `idx_trading_calendar_days_cal_date_is_open`）
3. dates 为空 → `{"success": False, "data": None, "message": "交易日历未初始化，请先执行融资融券同步"}`（HTTP 200；**不得用自然日/工作日伪造**）
4. `select(TradingCalendarDay.cal_date, MarketMarginDaily).outerjoin(MarketMarginDaily, MarketMarginDaily.trade_date == TradingCalendarDay.cal_date).where(cal_date.in_(dates), is_open=True).order_by(cal_date.asc())`（参数化 IN）；`metric_map = {cal: m for cal, m in rows if m is not None}`
5. points 逐日构造（`_to_point(cal, metric)` helper，对照 market_metrics.py:76-97）：缺结果日 `rzye/rqye/rzmre/rzche/rqmcl/rzrqye` 全 **null**（不补 0/前值）；有结果日取六指标列（snake_case dict → `_dict_to_camel` 转 camelCase）——point 字段契约 `tradeDate/rzye/rqye/rzmre/rzche/rqmcl/rzrqye`（rqyl 不落库不输出，spec D1/plan-01 口径）
6. `latest`：points 自尾向头的第一个 `rzye` 非 null 点（**展示最近成功结果及其日期**，不伪装今天）；全空 → null
7. `hasMissingDates`：任一点 `rzye is None`
8. 返回 `{latest, points, range, has_missing_dates}` → camelCase 后 `{latest, points, range, hasMissingDates}`
9. **GET 路径禁止**：实例化 `TradingCalendar`（缓存未命中会实时访问 Provider）、调用 DataSourceFactory/Tushare——本文件不 import 任何 Provider 侧模块

**可观测性**: 日志记录 `range/points/missing_count/db_duration_ms`（前缀 `margin trend`）；禁止记录任何 Provider 调用（天然满足——不调用）。

#### 3. 路由挂载

`server/src/api/v1/__init__.py` 两处对称扩展（不动 16 期行）：

- import 区 L27 旁：`from .margin import router as margin_router  # 融资融券查询 API（第 17 期 plan-06）`
- 注册区 L49 旁：`router.include_router(margin_router)  # /api/v1/margin/*（第 17 期 plan-06）`

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | 创建 margin.py：helper（_serialize_value/_dict_to_camel）+ _to_point | backend | done | 六指标 null 点契约 |
| 2 | trend 端点：日历取轴 + LEFT JOIN + latest/hasMissingDates | backend | done | 零 Provider |
| 3 | v1/__init__.py 挂载 router | backend | done | /api/v1/margin/* |
| 4 | 编写 test_margin.py | backend | done | 契约/缺口/空态/鉴权/性能 |

## 验收标准

### 后端验收

- [x] AC-5 `range=30/90/250` 分别返回 30/90/250 个交易日点（不足时返回全部已有）；`range=50` 被 422 拒绝
- [x] AC-5 造 5 日轴 + 3 日 `market_margin_daily` 数据 → 5 点、缺失 2 点**六指标全 null**、`hasMissingDates=true`、`latest` 为最后一个有值日；**无 0/前值填充**；`points` 长度=区间交易日数
- [x] `latest` 取最近有结果日（当日无数据时不是今天）；全部有数时 `hasMissingDates=false`
- [x] 响应字段 camelCase、Decimal 为 float number（断言 `isinstance(rzye, float)`）、日期 ISO 字符串；point 字段恰为 `tradeDate/rzye/rqye/rzmre/rzche/rqmcl/rzrqye` 七键
- [x] 本地日历空表 → `success=False` + 明确 message，`data=null`
- [x] 未登录（无 token）→ 401；普通登录用户可读
- [x] mock DataSourceFactory 断言 GET 路径零 Provider 调用（文件级断言不 import Provider 模块 + 运行时调用计数）
- [x] E2E 不适用：纯 API 功能，浏览器可见行为由 plan-07 的 E2E（mock 本端点）覆盖；本功能以 pytest 契约测试为质量门

### 性能验收

- [x] 250 日查询 P95 ≤ 500ms（测试内计时断言单次查询 < 500ms，种子 250 行数据；只走索引，0 次 Provider 调用）

## 验证命令

```bash
cd server && source .venv/bin/activate

# 1. API 契约测试（种子日历 + market_margin_daily 部分数据，
#    参照 tests/api/test_market_metrics.py 惯例）
pytest tests/api/test_margin.py -v --no-cov

# 2. 回归（确认 v1/__init__.py 挂载未破坏既有路由）
pytest tests/api -q --no-cov

# 3. 全量回归
pytest tests/ -q --no-cov
```

## 交接上下文

- **spec 章节**: REQ-6（查询端点）、边界（必须：trading_calendar_days LEFT JOIN 缺口 null 三大范式之一）、任务清单 T6
- **相关代码**: `server/src/api/v1/market_metrics.py`（L1-212 全量对照母本：helper L48-73、_to_point L76-97、Query pattern 教训 L103-113、查询主体 L129-208）、`server/src/api/v1/index_monitor.py`（helper 同源 L55-80）、`server/src/api/v1/__init__.py`（import L27、挂载 L49）、`server/src/models/market_margin_daily.py`（plan-01 交付）
- **契约 / 数据对象**: `MarginTrendData` / `MarginPoint`（本端点输出契约，plan-07 前端类型与之逐字段一致；六指标元口径 float）
- **下游消费方**: plan-07（MarginPanel 消费）
- **四件套校验结论**: 前端 endpoint `/margin/trend?range=30` × baseURL `${API_BASE_URL}/api/v1` = `/api/v1/margin/trend`（无双前缀）；方法 GET 在 ApiClient 存在且带鉴权；query 名 `range` 单词无风格歧义；响应 data 字段经 `_dict_to_camel` 输出 camelCase、Decimal→float，与前端类型一致
- **实现级补充项**: `latest`/`hasMissingDates` 判据取 `rzye`（16 期取 volume_shares 的同位裁定），服务于 AC-5，非新造 AC

## 风险与边界

- **执行顺序**: 按 Task 列表顺序执行
- **验证失败排查方向**: 缺口测试先经 TradingCalendarRepository 种子日历；P95 超标先查是否 seq scan（索引名见 plan-01）；422 不生效先查 pattern 是否误写在 int 类型上
- **允许修改的额外文件**: 无
- **暂停条件**: 无
- **风险备注**: 数值量级（rzye ~1.8e12 元）在 float64 精确整数范围（<2^53≈9.0e15）内，Decimal→float 无精度损失；前端 ÷1e8 后展示层处理（plan-07）

### 后端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| 日历有开市日但两融全空 | points 六指标全 null、latest=null、hasMissingDates=true | done |
| 日历空表 | success=False + 未初始化 message | done |
| range > 已有开市日数 | 返回全部已有交易日点 | done |
| 非法 range（50/abc） | Query pattern 校验 422 | done |
| 未登录 | 401（get_current_user） | done |
