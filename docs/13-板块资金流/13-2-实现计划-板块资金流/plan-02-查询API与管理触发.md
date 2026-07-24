---
feat_id: "plan-02"
title: "查询API与管理触发"
dimension: backend
phase: 2
status: done
depends_on: ["plan-01"]
---

# plan-02 查询API与管理触发

## 1. 功能概要

- **目标**: 实现资金流排行查询、盘中变化曲线查询、最新日期查询三个业务 API，以及管理员手动触发采集的 admin 端点。提供前端消费所需的全部后端接口。
- **完成后可观察结果**: 三个业务 GET 端点（/rankings、/timeseries、/latest-date）返回符合架构 §7.2 Schema 的 camelCase 响应；排行返回最新采样点数据并按净额降序；曲线按板块名分组返回时间序列；admin POST 端点创建 AsyncTask 并返回 task_id。用 curl 或 FastAPI /docs 调用各端点均返回正确结构。
- **依赖**: plan-01（sector_fund_flow 表 + 采集器 + TaskType）
- **关联验收标准**: [AC-01, AC-02, AC-03, AC-04, AC-06, AC-08, AC-10, AC-11, AC-12]
- **涉及架构模块**: 资金流服务 SectorFundFlowService、排行 API sector_fund_flow.py、admin 触发端点
- **前置条件**: plan-01 完成，sector_fund_flow 表有数据
- **不在范围**: 前端页面（plan-03）

## 2. 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| create | `server/src/services/sector_fund_flow_service.py` | SectorFundFlowService（排行/曲线/最新日期） |
| create | `server/src/api/v1/sector_fund_flow.py` | 业务 GET 路由（3 端点） |
| modify | `server/src/api/v1/__init__.py` | 注册 sector_fund_flow_router |
| create | `server/src/api/admin/init_sector_fund_flow.py` | admin 触发端点 |
| modify | `server/src/api/admin/__init__.py` | 注册 init_sector_fund_flow_router |

## 3. 实现规格

### 后端部分

#### 1. SectorFundFlowService（sector_fund_flow_service.py）

构造：`__init__(self, session: AsyncSession)`（仿 FundCrowdAnalysisService，fund_crowd_analysis_service.py:44）。

**get_rankings(sector_type, trade_date, sort_by, order, page, page_size) -> dict**：
- 取该 trade_date + sector_type 下每个 sector_name 的最新采样点：子查询 `WHERE (trade_date, sector_type, sector_name, sample_time) IN (SELECT trade_date, sector_type, sector_name, MAX(sample_time) FROM sector_fund_flow WHERE trade_date=:d AND sector_type=:t GROUP BY sector_name)`
- LEFT JOIN sectors ON sector_fund_flow.sector_name = sectors.name，取 sectors.id 为 sector_id（匹配不上为 null）
- 按 sort_by（net_inflow/inflow/outflow，默认 net_inflow）+ order（desc/asc，默认 desc）排序
- 分页 LIMIT/OFFSET（page 默认 1，page_size 默认 20）
- 返回 `{has_data, trade_date, items:[{rank, sector_name, sector_id, change_percent, inflow, outflow, net_inflow, company_count, leading_stock, leading_stock_change, current_price}], total, page, page_size}`
- rank 按当前排序结果顺序编号

**get_timeseries(sector_names: list[str], sector_type, trade_date) -> dict**：
- 取该 trade_date + sector_type + sector_names（IN）下所有采样点，按 sample_time 升序
- 按 sector_name 分组，每组 `[{sample_time, net_inflow}]`
- 返回 `{has_data, trade_date, series:[{sector_name, data:[{sample_time, net_inflow}]}]}`
- 无数据返回 has_data=false + 空 series

**get_latest_date(sector_type) -> dict**：
- `SELECT MAX(trade_date) FROM sector_fund_flow WHERE sector_type=:t`
- 返回 `{latest_date: 'YYYY-MM-DD' or null}`

#### 2. 业务路由（sector_fund_flow.py）

仿 fund_crowd_analysis.py 范式（router = APIRouter(prefix="/sector-fund-flow", tags=[...])，_dict_to_camel + _serialize_value helper，{success, data} 包裹，Depends(get_current_user)）。

| 端点 | 方法 | query 参数（snake_case） | 说明 |
| --- | --- | --- | --- |
| /rankings | GET | sector_type(默认industry), trade_date(可选), sort_by(默认net_inflow), order(默认desc), page(默认1), page_size(默认20) | 排行 |
| /timeseries | GET | sector_names(逗号分隔→split), sector_type, trade_date(可选) | 曲线 |
| /latest-date | GET | sector_type(默认industry) | 最新日期 |

**响应序列化**：经 `_dict_to_camel`（snake→camel）+ `_serialize_value`（Decimal→float, date→ISO）。复用 fund_crowd_analysis.py:104-129 的两个 helper（import 或复制）。

**路径拼接四件套校验**：
- 路径：router prefix `/sector-fund-flow` + v1 主路由 prefix `/v1` = `/api/v1/sector-fund-flow/rankings`
- 前端 endpoint 将写 `/sector-fund-flow/rankings`（baseURL 已含 /api/v1）
- query 参数 snake_case 与后端定义一致
- 响应 camelCase（经 _dict_to_camel）

**可观测性（架构 §8.5）**：异常时 logger.exception 记录请求参数。

#### 3. v1/__init__.py 注册

仿现有：`from .sector_fund_flow import router as sector_fund_flow_router` + `router.include_router(sector_fund_flow_router)`。

#### 4. admin 触发端点（init_sector_fund_flow.py）

仿 init_funds.py（src/api/admin/init_funds.py）：
- `router = APIRouter(prefix="/init", tags=["Admin - Sector Fund Flow"])`
- POST `/sector-fund-flow`，`response_model=ApiResponse[dict]`
- `Depends(require_admin)` + 并发保护（查 SYNC_SECTOR_FUND_FLOW 的 pending/running 任务）
- 创建 AsyncTask（TaskType.SYNC_SECTOR_FUND_FLOW，params={}）
- 返回 `{task_id}`
- **复用调用细节**：`from src.services.task_manager import TaskManager`（延迟导入避免循环依赖），`from src.models.async_task import AsyncTask`，`from src.api.schemas.response import ApiResponse`

#### 5. admin/__init__.py 注册

仿 init_funds 注册（src/api/admin/__init__.py:31）：`from .init_sector_fund_flow import router as init_sector_fund_flow_router` + `router.include_router(init_sector_fund_flow_router)`。

**路径**：admin 路由在 router.py:29 以 `include_router(admin_router, prefix="/v1/admin")` 挂载（admin/__init__.py:27 的 APIRouter 本身无 prefix），init 子路由 prefix=/init + /sector-fund-flow = `/api/v1/admin/init/sector-fund-flow`

## 4. Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | 实现 SectorFundFlowService（3 方法） | backend | done | 最新采样点子查询+LEFT JOIN |
| 2 | 创建业务路由 sector_fund_flow.py（3 端点） | backend | done | _dict_tocamel+_serialize_value |
| 3 | v1/__init__.py 注册路由 | backend | done | |
| 4 | 创建 admin 触发端点 init_sector_fund_flow.py | backend | done | AsyncTask+并发保护 |
| 5 | admin/__init__.py 注册路由 | backend | done | |
| 6 | curl/docs 验证 4 个端点 | backend | done | 返回结构正确 |

## 5. 验收标准

### API 功能验收
- [ ] AC-01 GET /rankings 默认返回行业维度净额降序排行，含 sector_id（匹配上）/null（未匹配）
- [ ] AC-02 GET /rankings?sector_type=concept 返回概念维度数据
- [ ] AC-03 GET /rankings?sort_by=inflow&order=asc 排序正确，不可排序参数忽略
- [ ] AC-04 GET /rankings?trade_date=历史日期 返回该日数据；无数据日期 has_data=false
- [ ] AC-06 GET /timeseries?sector_names=A,B 返回按板块名分组的时间序列
- [ ] AC-08 GET /timeseries 无数据时 has_data=false + 空 series
- [ ] AC-10 排行响应 sector_id：名称匹配 sectors 表的有值，不匹配的 null
- [ ] AC-11 POST /api/v1/admin/init/sector-fund-flow 创建 AsyncTask 返回 task_id，并发时拒绝
- [ ] AC-12 GET /rankings?page=2&page_size=50 分页正确，total 随之变化
- [ ] 响应字段 camelCase（netInflow/sectorName/sampleTime 等）
- [ ] Decimal 正确序列化为 float，date 序列化为 ISO 字符串

### 执行验证验收（task handler 联动）
- [ ] admin POST 创建的 AsyncTask 能被 plan-01 的 handler 消费执行，status=completed

## 6. 验证命令

```bash
cd server
# 启动服务后用 curl 或 /docs 验证
.venv/bin/uvicorn src.main:app --reload &
# 排行
curl -s localhost:8000/api/v1/sector-fund-flow/rankings?sector_type=industry | python -m json.tool
# 曲线
curl -s localhost:8000/api/v1/sector-fund-flow/timeseries?sector_names=电网设备,半导体&sector_type=industry | python -m json.tool
# 最新日期
curl -s localhost:8000/api/v1/sector-fund-flow/latest-date | python -m json.tool
# 单元测试
.venv/bin/python -m pytest tests/ -k "fund_flow" -v
```

## 7. 交接上下文

- **架构章节**: §6.2 排行链路、§6.3 曲线链路、§7.2 Schema、§7.3 API 边界
- **相关代码**: fund_crowd_analysis.py（路由范式+helper）、init_funds.py（admin 范式）、sector.py:12（sectors.name JOIN）
- **契约/数据对象**: FundFlowRankingItem、FundFlowTimeseriesData（架构 §7.2 响应视角）
- **下游消费方**: plan-03 前端消费这 4 个端点

## 8. 风险与边界

- **执行顺序**: service→业务路由→注册→admin 端点→注册→验证
- **验证失败排查方向**: 排行无数据检查 trade_date 默认值；sector_id 全 null 检查 sectors 表是否有数据；404 检查路由注册
- **允许修改的额外文件**: 无
- **暂停条件**: 无
- **E2E 不适用说明**: 纯后端 API，用 curl/docs 验证；前端 E2E 在 plan-03
- **风险备注**: 最新采样点子查询要确保性能（走 idx_sff_date_type_name_time 索引）

### 后端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| trade_date 未传 | 默认取 latest_date | done |
| sector_names 为空 | timeseries 返回空 series | done |
| 该日期无数据 | rankings/timeseries 返回 has_data=false | done |
| sort_by 非法值 | 容错为默认 net_inflow | done |
| admin 重复触发 | 并发保护拒绝，返回提示 | done |
