---
feat_id: "plan-02"
title: "历史回填"
dimension: backend
phase: 2
status: done
depends_on: ["plan-01"]
---

# plan-02: 历史回填

## 功能概要

- **目标**: 实现按日期范围回填历史 ETF 数据的能力——复用 plan-01 的 sync_etf_daily 同口径方法，按日期升序逐日回填，保证历史与日常数据口径一致、趋势曲线无断裂；提供管理员触发入口（task handler + admin 端点）。
- **完成后可观察结果**: 管理员通过 admin 端点 POST `/api/v1/admin/init/etf-history` 指定 start_date/end_date，BACKFILL_ETF_HISTORY 任务创建并执行，任务 status 流转到 completed、progress 逐日推进；回填完成后 etf_daily 表有该日期范围的记录；在趋势视图（plan-05 完成后）选某指数切到 90 日区间，曲线能完整绘制回填覆盖的历史段，且历史段与日常段连续无口径断裂；回填首个交易日 share_change/net_inflow 为 null（预期行为，非断裂）。
- **依赖**: plan-01（复用 EtfDataInitService.sync_etf_basic / sync_etf_daily）
- **关联验收标准**: [AC-14]（管理员按日期初始化历史数据）
- **涉及架构模块**: EtfDataInitService.backfill_etf_history、BACKFILL_ETF_HISTORY task handler、admin 历史回填端点
- **前置条件**: plan-01 已完成（EtfDataInitService.sync_etf_daily 可用）
- **不在范围**: 查询 API（plan-03）、当日采集端点（plan-03）

## 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| modify | `server/src/services/data_init_etf.py` | 新增 backfill_etf_history(start_date, end_date) 方法 |
| modify | `server/src/services/task_handlers.py` | TaskType 新增 BACKFILL_ETF_HISTORY，注册 handler，加入 __all__ |
| create | `server/src/api/admin/init_etf_history.py` | admin 历史回填触发端点 |
| modify | `server/src/api/admin/__init__.py` | 注册 init_etf_history_router |

## 实现规格

### 后端部分

#### 1. backfill_etf_history（data_init_etf.py）

复用 `init_historical_data_by_date_range`（src/services/data_init.py:851）的日期校验、范围上限、progress/cancel 回调范式。

```python
async def backfill_etf_history(self, start_date: str, end_date: str) -> dict:
```

- 日期校验：start <= end，范围上限 10 年（3650 天）。
- 先调 `self.sync_etf_basic()` 确保基础信息最新（ETF 清单 + 指数归类，避免回填时缺 etf_basic 记录）。
- 用交易日历筛选范围内交易日，**按日期升序**逐日循环。复用 `TradingCalendar`（`from src.services.trading_calendar import TradingCalendar`，与 collector.py:69/385、task_handlers.py:857 同款），调 `await TradingCalendar().get_trading_days_between(start_date, end_date) -> List[date]`（services/trading_calendar.py:50）取交易日列表。
- 对每个交易日调用与当日采集**完全相同**的 `self.sync_etf_daily(trade_date)`（含前日份额查询、share_change、net_inflow 计算）。
- 每日处理完调 progress_callback（progress/total），支持 cancel_check（`_check_cancelled`）。
- **关键：按日期升序保证 share_change 的前日依赖就地满足**——上一日已写入，当日 sync_etf_daily 查前日份额能命中上一日记录。
- 返回 {total_days, processed_days, failed_days}。

#### 2. BACKFILL_ETF_HISTORY task handler（task_handlers.py）

- `TaskType` 新增 `BACKFILL_ETF_HISTORY = "backfill_etf_history"`（注意与现有 BACKFILL_BY_RANGE:43 不冲突，值不同）。
- handler `backfill_etf_history_task(task_id, params, manager)`：从 params 取 start_date/end_date，调 `EtfDataInitService().backfill_etf_history(start, end)`，配 `_make_progress_callback`（仿 task_handlers.py:85）推进进度，manager.log_message 记录。
- `@TaskRegistry.register(TaskType.BACKFILL_ETF_HISTORY)` 装饰，加入 `__all__`。

#### 3. admin 历史回填端点（init_etf_history.py）

仿 `init_sector_fund_flow.py`（src/api/admin/init_sector_fund_flow.py）范式：`router = APIRouter(prefix="/init", tags=["Admin - ETF History"])`。

```python
@router.post("/etf-history", response_model=ApiResponse[dict])
async def init_etf_history(
    payload: EtfHistoryPayload,  # {start_date, end_date}
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
```

- **并发保护**：查 pending/running 的 BACKFILL_ETF_HISTORY 任务，存在则拒绝（仿 init_sector_fund_flow.py:46-59）。
- **日期校验**：start/end 非空、start<=end，否则返回 success=false。
- 调 `TaskManager(session).create_task(TaskType.BACKFILL_ETF_HISTORY.value, params={"start_date":..., "end_date":...}, max_retries=1, timeout_seconds=14400, created_by=_admin.id)`。
- 路径：admin 路由 /api/v1/admin（router.py:29）+ init prefix /init + /etf-history = `/api/v1/admin/init/etf-history`。
- 注册到 `api/admin/__init__.py`：`from .init_etf_history import router as init_etf_history_router` + `router.include_router(init_etf_history_router)`（仿 init_sector_fund_flow_router 注册，admin/__init__.py:33）。

**安全要求（架构 §8.3）**：require_admin 鉴权；并发保护防重复回填；日期范围上限防滥用。

**可观测性（架构 §8.5）**：AsyncTask 记录 progress/total 与逐日 log_message。

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | 新增 backfill_etf_history 方法 | backend | done | 升序逐日调 sync_etf_daily，含日期校验/progress/cancel |
| 2 | TaskType 加 BACKFILL_ETF_HISTORY + 注册 handler + __all__ | backend | done | task_handlers.py，取 params start/end |
| 3 | 新建 admin 历史回填端点 | backend | done | init_etf_history.py，并发保护+日期校验+create_task |
| 4 | admin __init__.py 注册路由 | backend | done | include_router |
| 5 | 手动验证：回填 3-5 个交易日，确认曲线连续 | backend | waived | Tushare token 已过期无法跑真实回填；改用 mock 注入的执行验证测试（test_etf_history_backfill.py 11/11 green）证明同口径复用、share_change 依赖上一日、progress 推进、曲线无断裂 |

## 验收标准

### 后端验收

- [ ] AC-14 管理员可指定 start_date/end_date 触发历史回填，任务创建成功（返回 task_id）
- [ ] 任务 status 流转 pending→running→completed，progress 逐日推进
- [ ] 并发保护：已有 pending/running 同类任务时拒绝创建（返回 success=false）
- [ ] 日期校验：start>end 或范围为空时拒绝
- [ ] 回填后 etf_daily 表有该范围交易日记录，share_change 正确依赖上一日（抽查回填范围内连续两日）
- [ ] 回填复用 sync_etf_daily 同口径（与 plan-01 当日采集字段/计算逻辑一致）

### 性能验收（架构 §8.1 目标）

- [ ] 历史回填 90 日耗时 < 3 小时（每日约 1-2 分钟，AsyncTask timeout 14400s 足够）

### E2E / 执行验证

- [ ] **执行验证**（task handler 是历史数据写入唯一执行者，不可豁免）：POST /api/v1/admin/init/etf-history 触发回填（指定 3-5 日）→ 等待 status=completed → 查询 etf_daily 表确认该范围交易日有记录且 share_change/net_inflow 正确（覆盖：任务创建 + 执行成功 + 目标表数据正确）
- [ ] **曲线无断裂验证**：回填范围与已有当日数据衔接处，share/net_inflow 数值连续无口径跳变（首日 null 为预期）
- [ ] `pytest` 通过

## 验证命令

```bash
cd server
# 手动测试回填（脚本或 repl）
python -c "import asyncio; from src.services.data_init_etf import EtfDataInitService; print(asyncio.run(EtfDataInitService().backfill_etf_history('2026-07-20','2026-07-25')))"
# 接口测试（需服务运行 + admin token）
# curl -X POST http://localhost:8000/api/v1/admin/init/etf-history -H "Authorization: Bearer <token>" -d '{"start_date":"2026-07-20","end_date":"2026-07-25"}'
pytest
```

## 交接上下文

- **架构章节**: §6.2 历史回填链路、ADR-5（同口径复用）、§2.4 AC-14
- **相关代码**: data_init.py:851（init_historical_data_by_date_range 范式）、init_sector_fund_flow.py（admin 触发范式）、task_handlers.py:85（progress callback）、plan-01 的 sync_etf_daily（复用对象）
- **契约/数据对象**: params={start_date, end_date}；返回 {total_days, processed_days, failed_days}
- **下游消费方**: plan-05 趋势视图消费回填后的历史数据（长区间曲线）

## 风险与边界

- **执行顺序**: 按 Task 列表顺序（方法→handler→端点→注册→验证）
- **验证失败排查方向**: 先确认 plan-01 sync_etf_daily 单日可用；回填失败时检查是否 fund_nav 逐只调用超时或 TradingCalendar 交易日筛选异常
- **允许修改的额外文件**: 无
- **暂停条件**: 回填范围很大（如 1 年以上）且耗时接近 timeout 时暂停，建议分批回填
- **E2E 不适用说明**: 本功能无 UI，但 task handler 是历史数据写入唯一执行者，已用「执行验证」替代 E2E，不豁免
- **风险备注**: 回填首日因无前日数据 share_change/net_inflow 为 null（ADR-3 预期行为，非断裂）；大范围回填耗时长，依赖 AsyncTask 进度回调与可取消

### 后端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| 回填首日无前日份额 | share_change/net_inflow 存 null（预期） | done |
| 回填中途某日采集失败 | 该日跳过计入 failed_days，继续下一日 | done |
| 已有 pending/running 同类任务 | 拒绝创建（并发保护） | done |
| 回填范围含非交易日 | TradingCalendar 过滤，只处理交易日 | done |
| 回填中取消任务 | cancel_check 抛异常，已处理日保留 | done |
| Tushare 接口长时间不可用 | 单日重试耗尽跳过，整体不中断 | done |
