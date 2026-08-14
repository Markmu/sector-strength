---
feat_id: "plan-06"
title: "市场量价查询 API"
dimension: backend
phase: 2
status: done
depends_on: ["plan-01", "plan-03"]
---

# plan-06: 市场量价查询 API

## 功能概要

- **目标**: 新增登录态 `GET /api/v1/market-metrics/trend?range=30`：从本地 `trading_calendar_days` 取最近 N 个开市日左连接 `market_daily_metrics`，输出 latest + 带缺口的 points（缺失日三项为 null，不补 0/前值）；GET 路径零 Provider 调用。
- **完成后可观察结果**: 登录用户请求该端点可得到 `{success, data}` camelCase 响应：`latest` 为最近有结果日的三指标与参与数，`points` 恰好 N 个交易日点且缺失日为 null、`hasMissingDates` 如实标记；切 `range=90/250` 返回对应数量的交易日点。本地日历无任何开市日时返回明确"未初始化"错误而非猜测日期；服务端只返回所需交易日数。
- **依赖**: plan-01（trading_calendar_days 表与索引）、plan-03（market_daily_metrics 表有数据）
- **关联验收标准**: [AC-05]（30/90/250 服务端裁剪）、[AC-06]（缺口 null 不伪造）
- **涉及架构模块**: 市场量价查询 API（架构 §4.2 模块 4）
- **前置条件**: plan-01/03 已合并；本地 PostgreSQL。
- **不在范围**: 前端组件（plan-07）；管理端任务接口（plan-04/05 已交付）。

## 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| create | `server/src/api/v1/market_metrics.py` | trend 端点 + helper |
| modify | `server/src/api/v1/__init__.py` | 挂载 router |
| create | `server/tests/api/test_market_metrics.py` | 契约/缺口/空态/权限测试 |

## 实现规格

### 后端部分

#### 1. 路由与契约（架构 §6.4.2、§7.3）

- `router = APIRouter(prefix="/market-metrics", tags=["MarketMetrics"])`；挂载链：v1 主路由 `/v1`（api/v1/__init__.py:30）→ main.py `/api` → **最终路径 `/api/v1/market-metrics/trend`**
- 签名（照抄 index_monitor.py 锚点范式）：

```python
@router.get("/trend")
async def get_trend(
    range: int = Query(30, description="趋势交易日数", pattern="^(30|90|250)$"),  # Pydantic v2 用 pattern=（regex= 已弃用）
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
```

- **query 参数命名**：`range` 单词无 snake/camel 歧义；非法值由 Query 校验拒绝（422）
- **响应包裹**：`{"success": True, "data": _dict_to_camel({...})}`；helper `_serialize_value`（Decimal→float、date→isoformat）与 `_dict_to_camel` 从 index_monitor.py:55-80 复制（与 etf_monitor 同源惯例）
- Decimal 经 `_serialize_value` 输出为有限 `float`（**不得输出字符串**，§7.3）

#### 2. 查询逻辑（架构 §6.4.2、ADR-6）

1. `SELECT cal_date FROM trading_calendar_days WHERE is_open=true ORDER BY cal_date DESC LIMIT {range}` → 反转为升序 dates（≤250 点，走 `idx_trading_calendar_days_cal_date_is_open`）
2. dates 为空 → `{"success": False, "data": None, "message": "交易日历未初始化，请先执行市场量价同步"}`（HTTP 200；**不得用自然日/工作日伪造**）
3. `SELECT cal_date, m.* FROM unnest/IN dates LEFT JOIN market_daily_metrics m ON m.trade_date = t.cal_date ORDER BY cal_date ASC`（SQLAlchemy `select(TradingCalendarDay.cal_date, MarketDailyMetric).outerjoin(...)`；参数化 IN）
4. points 逐日构造：缺结果日 `volumeShares/amountYuan/averagePrice/finalStockCount/suspendedStockCount` 全 null；有结果日取数值列（snake_case dict → `_dict_to_camel` 转 camelCase）
5. `latest`：points 自尾向头的第一个有值点（**展示最近成功结果及其日期**，不伪装今天，§8.2-1）；全空 → null
6. `hasMissingDates`：任一点 `volumeShares is None`
7. 返回 `{latest, points, range, has_missing_dates}` → camelCase 后 `{latest, points, range, hasMissingDates}`
8. **GET 路径禁止**：实例化 `TradingCalendar`（缓存未命中会实时访问 Provider）、调用 DataSourceFactory/Tushare（§4.2 模块 4 验证）

**可观测性（架构 §8.5）**：日志记录 `range/points/missing_count/db_duration_ms`；**禁止记录任何 Provider 调用**（天然满足——不调用）。

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | 创建 market_metrics.py：helper + trend 端点 | backend | done | 左连接 + null 点 |
| 2 | v1/__init__.py 挂载 router | backend | done | /api/v1/market-metrics/* |
| 3 | 编写 test_market_metrics.py | backend | done | 契约/缺口/空态/鉴权/性能 |

## 验收标准

### 后端验收

- [x] AC-05 `range=30/90/250` 分别返回 30/90/250 个交易日点（不足时返回全部已有）；`range=50` 被 422 拒绝
- [x] AC-06 造 5 日轴 + 3 日数据 → 5 点、缺失 2 点三项为 null、`hasMissingDates=true`、latest 为最后一个有值日；**无 0/前值填充**
- [x] `latest` 取最近有结果日（当日无数据时不是今天）；全部有数时 `hasMissingDates=false`
- [x] 本地日历空表 → success=False + 明确 message，data=null
- [x] 响应字段 camelCase、Decimal 为 float number（断言 `isinstance(volumeShares, float)`）、日期 ISO 字符串
- [x] 未登录（无 token）→ 401；普通登录用户可读（AC-11 查询权限侧）
- [x] mock DataSourceFactory 断言 GET 路径零 Provider 调用
- [x] E2E 不适用：纯 API 功能，浏览器可见行为由 plan-07 的 E2E（mock 本端点）覆盖；本功能以 pytest 契约测试为质量门

### 性能验收（架构 §8.1）

- [x] 250 日查询 P95 ≤ 500ms（测试内计时断言单次查询 < 500ms，种子 250 行数据；只走索引，0 次 Provider 调用）

## 验证命令

```bash
cd server && source .venv/bin/activate

# 1. API 契约测试
pytest tests/api/test_market_metrics.py -v --no-cov

# 2. 回归
pytest tests/test_api tests/api -q --no-cov
```

## 交接上下文

- **架构章节**: §4.2 模块 4、§5 ADR-6、§6.4.1-2、§7.2（TS 契约）、§7.3、§8.1/8.5
- **相关代码**: `server/src/api/v1/index_monitor.py`（helper L55-80、路由范式 L86-114）、`server/src/api/v1/__init__.py`（挂载 L29-48）
- **契约 / 数据对象**: `MarketMetricsTrendData` / `MarketMetricPoint`（架构 §7.2 TS 定义即本端点输出契约，plan-07 前端类型与之逐字段一致）
- **下游消费方**: plan-07（MarketMetricsPanel 消费）
- **四件套校验结论**: 前端 endpoint `/market-metrics/trend?range=30` × baseURL `${API_BASE_URL}/api/v1` = `/api/v1/market-metrics/trend`（无双前缀）；方法 GET 在 ApiClient 存在且带鉴权（getAuthHeaders L45-57）；query 名 `range` 单词无风格歧义；响应 data 字段经 `_dict_to_camel` 输出 camelCase、Decimal→float，与前端类型一致

## 风险与边界

- **执行顺序**: 按 Task 列表顺序执行
- **验证失败排查方向**: 缺口测试先经 Repository 种子日历；P95 超标先查是否 seq scan（索引名见 plan-01）
- **允许修改的额外文件**: 无
- **暂停条件**: 无
- **风险备注**: `range` 是 Python 内建名，端点内变量改名 `range_days` 避免遮蔽

### 后端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| 日历有开市日但指标全空 | points 全 null、latest=null、hasMissingDates=true | done |
| 日历空表 | success=False + 未初始化 message | done |
| range > 已有开市日数 | 返回全部已有交易日点 | done |
| 非法 range | Query 校验 422 | done |
