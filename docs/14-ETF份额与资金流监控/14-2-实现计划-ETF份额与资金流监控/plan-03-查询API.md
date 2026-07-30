---
feat_id: "plan-03"
title: "查询 API"
dimension: backend
phase: 2
status: done
depends_on: ["plan-01"]
---

# plan-03: 查询 API

## 功能概要

- **目标**: 实现 ETF 监控的 4 个查询端点（指数排行、指数明细、历史趋势、最新日期）+ 1 个当日采集 admin 端点；查询服务按跟踪指数聚合（group by index_name + SUM），支持维度/排序/日期/分页/趋势对象×指标×区间。
- **完成后可观察结果**: GET `/api/v1/etf-monitor/index-rankings?category=broad` 返回按 index_name 聚合的指数列表，每项含 etfCount/totalShare/totalShareChange/totalNetInflow，按 netInflow 降序、分页；GET `/index-detail` 返回某指数下 ETF 明细；GET `/trend?target_type=index&target_code=沪深300&metric=share&days=30` 返回时间序列；GET `/latest-date` 返回最新交易日；POST `/api/v1/admin/init/etf-daily` 触发当日采集返回 task_id。所有响应 `{success, data}` 包裹、camelCase、Numeric→float。
- **依赖**: plan-01（etf_basic/etf_daily 表与 SYNC_ETF_DAILY task handler）
- **关联验收标准**: [AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-07, AC-08, AC-09, AC-10, AC-12, AC-13]（查询接口支撑，前端交互验证在 plan-05）
- **涉及架构模块**: EtfMonitorService、查询路由 etf_monitor.py、admin 当日采集端点
- **前置条件**: plan-01 已完成；etf_daily 表已有至少一日数据（可手动 sync_etf_daily 灌入测试数据）
- **不在范围**: 历史回填端点（plan-02）、前端（plan-04/05）

## 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| create | `server/src/services/etf_monitor_service.py` | EtfMonitorService（4 个查询方法） |
| create | `server/src/api/v1/etf_monitor.py` | 查询路由（4 个 GET） |
| modify | `server/src/api/v1/__init__.py` | 注册 etf_monitor_router |
| create | `server/src/api/admin/init_etf_daily.py` | admin 当日采集端点 |
| modify | `server/src/api/admin/__init__.py` | 注册 init_etf_daily_router |
| modify | `server/src/api/v1/sector_fund_flow.py` | （可选）提取 _dict_to_camel/_serialize_value 到公共 helper |

## 实现规格

### 后端部分

#### 1. EtfMonitorService（etf_monitor_service.py）

仿 `SectorFundFlowService`（src/services/sector_fund_flow_service.py，service 层直接用 SQLAlchemy Core，不走 Repository）。

- **get_index_rankings(category, trade_date, sort_by, order, page, page_size) -> dict**：
  - JOIN etf_daily + etf_basic（按 ts_code），筛 category + trade_date。
  - 按 etf_basic.index_name 分组：`COUNT(ts_code)` 得 etfCount，`SUM(share)` 得 totalShare，`SUM(share_change)` 得 totalShareChange，`SUM(net_inflow)` 得 totalNetInflow。
  - sort_by 映射：'netInflow'→totalNetInflow、'shareChange'→totalShareChange、'share'→totalShare（参数值 camelCase，见架构 §7.6），order desc/asc。
  - 分页 LIMIT/OFFSET（默认 page=1, page_size=20）。
  - 单位换算：聚合在万份口径 SUM 后，输出 totalShare/totalShareChange ÷10000 转亿份（架构 §7.6）。
  - 返回 {hasData, tradeDate, items:[{indexName, category, etfCount, totalShare, totalShareChange, totalNetInflow}], total, page, pageSize}。
- **get_index_detail(index_name, category, trade_date) -> dict**：JOIN 筛 index_name + category + trade_date，返回该指数 ETF 明细（tsCode/name/unitNav/share/shareChange/netInflow/changePercent），按 netInflow 降序。份额输出 ÷10000 亿份。返回 {hasData, items}。
- **get_trend(target_type, target_code, metric, days, end_date) -> dict**：
  - 取 etf_daily 中 trade_date <= end_date 的最近 days 个交易日（按实际有数据的交易日，非日历日）。
  - **target_type='index' 时的交易日筛选**：先 JOIN etf_basic 筛 index_name 得该指数的 ts_code 集合，再取该集合在 etf_daily 中 trade_date<=end_date 的最近 N 个 distinct 交易日（取该指数全量 ETF 交易日的并集，避免取成全表交易日导致 series 长度偏差），最后在该 N 日内按 index_name 聚合 SUM。
  - target_type='etf'：按 ts_code 取单只，取该 ts_code 的最近 N 个交易日。
  - metric='share'：取 share（输出亿份 ÷10000）；metric='netInflow'：取 net_inflow（亿元）。
  - 按 trade_date 升序返回 [{tradeDate, value}]。
  - 完全无数据点返回 hasData=false + 空 series（架构 §6.5）。
  - 返回 {hasData, metric, unit, series:[{tradeDate, value}]}。
- **get_latest_date(category) -> dict**：取该 category 下 etf_daily 最大 trade_date。返回 {hasData, tradeDate}。

#### 2. 查询路由（etf_monitor.py）

仿 `sector_fund_flow.py`（src/api/v1/sector_fund_flow.py）范式：`router = APIRouter(prefix="/etf-monitor", tags=["EtfMonitor"])`，复用 `_dict_to_camel` + `_serialize_value`（直接复制该 helper 到本文件，或从 sector_fund_flow 导入；可选提取公共 helper 见 #6），`{success, data}` 包裹，`Depends(get_current_user)`。

```python
@router.get("/index-rankings")
async def get_index_rankings(
    category: str = Query("broad"),  # broad/industry
    trade_date: Optional[str] = Query(None),
    sort_by: str = Query("netInflow"),  # 参数值 camelCase（架构 §7.6 特例）
    order: str = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session = Depends(get_session), _user = Depends(get_current_user),
): ...  # 返回 {"success": True, "data": _dict_to_camel(result)}
```

四个端点：`/index-rankings`、`/index-detail`、`/trend`、`/latest-date`。query 参数名全 snake_case，sort_by/metric 参数值 camelCase。响应经 _dict_to_camel 转 camelCase，_serialize_value 处理 Decimal→float/date→isoformat。

**契约四件套校验**（前端 plan-04 消费）：
- 路径拼接：router prefix /etf-monitor + v1 主路由 /v1 = /api/v1/etf-monitor/*；前端 apiClient baseURL 已含 /api/v1，endpoint 写 /etf-monitor/index-rankings（不带 /api/v1）。
- HTTP 方法：4 个 GET，apiClient.get 存在且带鉴权（src/lib/api.ts ApiClient.get 带 getAuthHeaders）。
- query 命名：后端 snake_case（category/trade_date/sort_by/target_type/target_code），前端传同款 snake_case（与 sectorFundFlowApi 一致）。
- 响应字段：_dict_to_camel 输出 camelCase（hasData/tradeDate/indexName/totalShare...），前端类型定义匹配。

#### 3. 路由注册（v1/__init__.py）

`from .etf_monitor import router as etf_monitor_router` + `router.include_router(etf_monitor_router)`（仿 sector_fund_flow 注册，src/api/v1/__init__.py）。

#### 4. admin 当日采集端点（init_etf_daily.py）

仿 `init_sector_fund_flow.py`（src/api/admin/init_sector_fund_flow.py）范式：`router = APIRouter(prefix="/init", tags=["Admin - ETF Daily"])`。

```python
@router.post("/etf-daily", response_model=ApiResponse[dict])
async def init_etf_daily(
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):  # 并发保护 + create_task(TaskType.SYNC_ETF_DAILY.value, ...)
```

- 并发保护查 pending/running SYNC_ETF_DAILY（plan-01 已注册），存在则拒绝。
- 路径：/api/v1/admin/init/etf-daily。
- 注册到 admin/__init__.py（仿 init_sector_fund_flow_router，:33）。

#### 5. （可选）提取公共 helper

`_dict_to_camel`/`_serialize_value` 在 sector_fund_flow.py:42-67 与 funds.py 各有一份重复。可提取到 `server/src/api/v1/_helpers.py`（或 api/schemas/），两个路由文件改为 import。**可选**，不提取则复制到 etf_monitor.py（与现状一致）。

**安全要求（架构 §8.3）**：业务 GET 用 get_current_user（普通登录用户）；admin POST 用 require_admin；index_name/target_code 等 query 参数做基本校验（非空、长度限制）防注入（SQLAlchemy 参数化查询已防注入，额外校验防异常输入）。

**可观测性（架构 §8.5）**：查询异常用 logger 记录；归集正确性自检（抽样 SUM 核对）已在 plan-01 采集侧落实。

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | 新建 EtfMonitorService（4 查询方法） | backend | done | 指数聚合+排序+分页、明细、趋势、最新日期 |
| 2 | 新建查询路由 etf_monitor.py（4 GET） | backend | done | _dict_to_camel+_serialize_value+{success,data}+get_current_user |
| 3 | v1/__init__.py 注册路由 | backend | done | include_router |
| 4 | 新建 admin 当日采集端点 init_etf_daily.py | backend | done | 并发保护+create_task SYNC_ETF_DAILY |
| 5 | admin/__init__.py 注册路由 | backend | done | include_router |
| 6 | （可选）提取 _dict_to_camel/_serialize_value 公共 helper | backend | done | 可选，不提取则复制到 etf_monitor.py（采用复制方案，与现状一致） |

## 验收标准

### 后端验收

- [ ] AC-01/02/03/05/13 GET /index-rankings 返回指数聚合列表，category 切换/排序切换/日期切换/分页均正常
- [ ] AC-04 GET /index-detail 返回某指数 ETF 明细，按 netInflow 降序
- [ ] AC-06/07/08/09 GET /trend 返回时间序列，target_type(index/etf)/metric(share/netInflow)/days(7/30/90) 切换正常；完全无数据返回 hasData=false
- [ ] 指数汇总值正确：totalShare/totalShareChange/totalNetInflow = 该指数各 ETF 之和（抽查核对）
- [ ] 单位正确：份额输出亿份（÷10000），净流入额亿元
- [ ] 响应 {success, data} 包裹、camelCase、Decimal→float
- [ ] AC-12（完整）POST /api/v1/admin/init/etf-daily 触发采集返回 task_id，并发保护生效
- [ ] AC-10 查询异常不崩溃，返回明确错误（支撑前端重试）

### 性能验收（架构 §8.1 目标）

- [ ] 排行查询响应 < 500ms（人工或脚本计时）
- [ ] 趋势查询响应（90 日）< 500ms

### E2E / 接口验收

- [ ] 用 curl/httpie 验证 4 个 GET + 1 个 admin POST 端点返回结构与架构 §7.2 输出视角 Schema 一致
- [ ] E2E-TDD：前端交互由 plan-05 承接（本功能提供接口契约，red/green 证据在 plan-05 的 E2E spec）
- [ ] `pytest` 通过

## 验证命令

```bash
cd server
# 启动服务后用 curl 验证（需登录 token）
# GET 指数排行
curl "http://localhost:8000/api/v1/etf-monitor/index-rankings?category=broad&sort_by=netInflow&page=1&page_size=20" -H "Authorization: Bearer <token>"
# GET 趋势
curl "http://localhost:8000/api/v1/etf-monitor/trend?target_type=index&target_code=沪深300&metric=share&days=30" -H "Authorization: Bearer <token>"
# admin 采集
# curl -X POST http://localhost:8000/api/v1/admin/init/etf-daily -H "Authorization: Bearer <admin_token>"
pytest
```

## 交接上下文

- **架构章节**: §6.3/6.4/6.5 查询链路、§7.2 输出视角 Schema、§7.3 API 边界、ADR-4
- **相关代码**: sector_fund_flow.py:42-67（_dict_to_camel/_serialize_value）、sector_fund_flow_service.py（service 范式）、init_sector_fund_flow.py（admin 范式）、v1/__init__.py（注册）
- **契约/数据对象**: EtfIndexRankingsData/EtfIndexDetailData/EtfTrendData（架构 §7.2 输出视角）；query snake_case/响应 camelCase/sort_by 值 camelCase
- **下游消费方**: plan-04（etfMonitorApi 调用这些端点）、plan-05（前端组件消费）

## 风险与边界

- **执行顺序**: 按 Task 列表顺序（service→路由→注册→admin 端点→注册→可选 helper）
- **验证失败排查方向**: 先确认 etf_daily 表有测试数据（plan-01 sync_etf_daily 灌入）；查询无数据时检查 trade_date 参数与表数据日期是否匹配；聚合错误检查 JOIN 条件与 group by
- **允许修改的额外文件**: 若提取公共 helper，可新建 server/src/api/v1/_helpers.py
- **暂停条件**: 指数聚合 SUM 结果与各 ETF 手算之和不一致时暂停，排查 JOIN/group by 逻辑
- **E2E 不适用说明**: 本功能是纯接口，前端交互 E2E 在 plan-05 承接；但必须用接口验证（curl）确认返回结构正确，并用 plan-05 的 E2E red/green 覆盖端到端
- **风险备注**: 趋势查询取"实际有数据的最近 N 个交易日"需用子查询 distinct trade_date order by desc limit N，避免非交易日空点；index_name 含中文，URL 编码由前端/框架处理

### 后端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| 所选日期无数据 | index-rankings 返回 hasData=false，前端走空态 | done |
| 趋势对象完全无数据点 | trend 返回 hasData=false + 空 series | done |
| 趋势对象历史不足区间 | 返回实际有数据点（少于 N） | done |
| index_name 含特殊字符 | SQLAlchemy 参数化查询防注入 | done |
| 排序字段非法 | sort_by 非法值回落默认 netInflow | done |
| 分页超出范围 | 返回空 items + 正确 total | done |
