---
feat_id: "plan-05"
title: "市场量价范围同步与自动日更"
dimension: backend
phase: 2
status: done
depends_on: ["plan-01", "plan-02", "plan-03", "plan-04"]
---

# plan-05: 市场量价范围同步与自动日更

## 功能概要

- **目标**: 注册 `sync_market_metrics` 任务类型与 handler（逐日串行、dateResults 结构化结果、部分失败语义）；新增唯一合法创建入口 `POST /api/v1/admin/init/market-metrics`（校验→刷新日历→互斥建任务）；接入 collector 自动日更（日历守卫、一次生命周期 preflight、行情后汇总、失败不阻断）与 scheduler 18:00 北京时间日更 job。
- **完成后可观察结果**: 管理员 POST 合法起止日后获得 `task_id`，任务逐交易日串行执行：成功日立即提交、失败日回滚并继续，进度与当前日期可轮询；结束后 `result` 携带 success/skipped/failed 计数与逐日四类完整性计数，失败数 >0 时任务落 failed 但成功日保留。交易日收盘后自动日更生成当日指标，非交易日明确跳过；指标失败不影响指数/ETF 等后续任务。倒置/未来/超10年/零交易日的创建请求被明确拒绝且不建任务。
- **依赖**: plan-01（Repository + 日历方法）、plan-02（采集方法）、plan-03（MarketMetricsService + LifecycleSnapshot）、plan-04（fence/互斥/RESERVED）
- **关联验收标准**: [AC-02]（范围同步）、[AC-07]（失败与恢复执行路径）、[AC-08]（自动更新）、[AC-09]（collector 非交易日跳过）、[AC-10]（日期范围校验）、[AC-11]（require_admin + 互斥）
- **涉及架构模块**: 任务入口与编排（架构 §4.2 模块 3）
- **前置条件**: plan-01~04 已合并；本地 PostgreSQL；TUSHARE_TOKEN（真实执行验证）。
- **不在范围**: 查询 API（plan-06）；前端面板（plan-07/08）。

## 文件清单

### 后端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| modify | `server/src/services/task_handlers.py` | TaskType 枚举 + sync_market_metrics handler |
| create | `server/src/api/admin/init_market_metrics.py` | 专用创建路由（唯一合法入口） |
| modify | `server/src/api/admin/__init__.py` | 挂载新路由 |
| modify | `server/src/services/data_updater/collector.py` | 日历守卫改造 + `_update_market_metrics()` + 当日在市过滤 |
| modify | `server/src/services/scheduler/job_manager.py` | 日更 job（按现有停用惯例预留 18:00 Asia/Shanghai） |
| create | `server/tests/api/admin/test_init_market_metrics.py` | 路由校验/互斥/鉴权测试 |
| modify | `server/tests/test_data_updater.py` | collector 日更步骤测试 |

## 实现规格

### 后端部分

#### 1. 专用创建路由（架构 §6.2.1-2、§7.3）

`server/src/api/admin/init_market_metrics.py`，范式照抄 `init_index_basic.py`（router `prefix="/init"`、`require_admin`、`ApiResponse` 包裹；最终路径 `/api/v1/admin/init/market-metrics`）：

- Pydantic payload：`start_date: date`、`end_date: date`（body snake_case，来源 user_input）
- 校验链（任一失败 `ApiResponse(success=False, message=...)`，**不建任务**）：
  1. `start_date <= end_date <= today`（AC-10）
  2. 跨度 ≤ 10 年（`_MAX_BACKSPAN_DAYS=3650`，架构 §8.2）
  3. `TradingCalendarRepository.refresh_range(start, end)`（Provider 失败/响应不完整 → 失败提示，不降级旧批次）
  4. 本地日历拆分交易日；**零交易日 → 明确提示不建任务**（§3.2 分支表）
- 通过后延迟导入 `TaskManager(session)` → `create_exclusive_task(task_type='sync_market_metrics', params={start_date,end_date ISO}, created_by=_admin.id)`；互斥命中 → success=False 提示已有任务（HTTP 200，与锚点一致）
- 成功返回 `ApiResponse(success=True, data={"task_id": ...})`
- **安全（§8.3）**：`require_admin` 依赖；日期用 Pydantic `date` 类型天然防注入；不透传 max_retries

#### 2. handler 注册（架构 §6.2.4-8、§7.2）

`task_handlers.py`：

- `TaskType` 枚举新增 `SYNC_MARKET_METRICS = "sync_market_metrics"`
- `@TaskRegistry.register(TaskType.SYNC_MARKET_METRICS)`，签名保持 `(task_id, params, manager)`：
  1. `ctx = TaskFenceRegistry.get(task_id)`（plan-04 注册表；取不到 → 抛错，自动路径不走 handler）
  2. 解析 params 起止日；从本地日历取交易日升序列表（非交易日不进 handler 计算；`skippedCount = 自然日数 − 交易日数`，§6.2.7）
  3. **一次生命周期 preflight**：fence 事务内 `DataInitService.init_stocks_lifecycle()` + preflight 任务日志写 → 构建 `LifecycleSnapshot` 复用（§6.2.4）
  4. 逐交易日：`MarketMetricsService.sync_date(day, snapshot, task_context=ctx, close_cache=cache)`（升序处理，cache 跨日复用）；每参数化页请求前 fence 检查绑定 token 的 generation active（§6.1.1）
  5. 每日结束向统一 `dateResults` 追加 `{tradeDate,status,expected,daily,suspended,final,reason?}` 并 `manager.update_progress`（progress/total 只计交易日，§6.2.7）；进度日志含当前日期与累计数
  6. 全部结束持久化 `result = {successCount, skippedCount, failedCount, dateResults, unprocessedDates}`（完整处理范围为空数组）；**result JSON 键全部 camelCase**——handler 构造时即用 camelCase 键（dateResults 逐项 `{tradeDate,status,expected,daily,suspended,final,reason?}`），`AsyncTask.to_dict()` 原样透传不经 `_dict_to_camel`，plan-08 前端直消费、无二次键转换；失败日志只记 endpoint、错误类别、≤50 问题代码样本
  7. `failedCount > 0` → 抛一次摘要（`max_retries=0` 由执行器直接落 failed，成功日不回滚，AC-02/07）
  8. 协程被 cancel（停止消费）→ `finalize_cancel_with_result`/`finalize_timeout_with_result` 保存 partial result（已处理日保留，未处理日进 unprocessedDates）

#### 3. collector 自动日更（架构 §6.3）

`collector.py` `run_daily_update()`（L72-169，现有步骤顺序不动）：

1. **交易日检查替换**：步骤 1 改为先 `TradingCalendarRepository.refresh_range(today, today)`（本次响应校验失败 → 日更失败，不用旧行冒充、不按工作日猜测；旧日历保留供首页只读降级），再以本批记录执行守卫：休市 → skipped 日志返回（AC-09）
2. `_update_stocks()` 升级：改调 `DataInitService(session).init_stocks_lifecycle()`（一次 L/D/P/G 联合 preflight + upsert/set-diff），产出 `LifecycleSnapshot` 存于 run 级变量
3. `_update_market_data()`：逐股行情只遍历 snapshot 的**当日在市集合**（不遍历历史退市全表，§6.3.2）
4. 新增步骤 `_update_market_metrics()`（在 `_update_market_data()` 成功后调用，§6.3.3）：`MarketMetricsService(session).sync_date(today, snapshot, task_context=None, ...)`——自动日更不读写 AsyncTask、不传 fence；失败写 `results.errors` 与 `market_metrics_updated=0`，**不覆盖最近成功结果、不阻断**指数/ETF 等后续步骤（§6.3.4）；成功置 `market_metrics_updated=1`
5. `results` dict 增加 `market_metrics_updated` 键（L85-96 既有结构）

#### 4. scheduler job（架构 §6.3 实现原则）

`job_manager.py` 按文件现行惯例添加日更 job 注册（开发期 job 停用则以注释形式预留，同 L102-113 模板）：`CronTrigger(hour=18, minute=0, timezone='Asia/Shanghai')` + `max_instances=1` + `replace_existing=True`，注释注明"Tushare 日线通常入库后的缓冲时段"。**采集侧守卫不得依赖 cron 工作日表达式**（§6.3 实现原则）。

**可观测性（架构 §8.5）**：collector 结果含 `market_metrics_updated`；日更失败进 `results.errors`；日历日志记录刷新范围、开/休市行数、是否本地覆盖降级。

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | init_market_metrics.py 路由 + 校验链 + 互斥建任务 | backend | done | 零交易日不建任务 |
| 2 | admin/__init__.py 挂载 | backend | done | /api/v1/admin/init/market-metrics |
| 3 | TaskType 枚举 + handler 注册（dateResults/进度/摘要） | backend | done | fence + 一次 preflight |
| 4 | handler 停止分支：partial result + unprocessedDates | backend | done | cancel/timeout finalize |
| 5 | collector 日历守卫替换 + 生命周期 preflight 接线 | backend | done | 旧行为不降级 |
| 6 | collector `_update_market_metrics` + 当日在市过滤 | backend | done | 失败不阻断 |
| 7 | scheduler job 预留 | backend | done | 18:00 Asia/Shanghai |
| 8 | 编写 test_init_market_metrics.py + test_data_updater.py 增量 | backend | done | 含执行验证用例 |

## 验收标准

### 后端验收

- [ ] AC-10 起止倒置 / end>today / 跨度>10 年 / 零交易日四类请求均 success=False 且 **AsyncTask 表无新行**；合法请求返回 task_id
- [ ] AC-11 非管理员调用专用路由 → 403（require_admin）；已存在同类型 pending/running 时再创建 → 拒绝并提示
- [ ] AC-02（执行验证，task handler 不豁免）触发任务 → 等待 completed → 查询 `market_daily_metrics` 确认范围内每个交易日恰一行且 `volume_shares/amount_yuan/average_price` 非空（可用 2-3 个真实交易日的小范围执行）
- [ ] AC-02 范围含失败日：任务落 failed，`result.failedCount≥1`，成功日数据保留在库；同范围重跑为覆盖
- [ ] `skippedCount = 自然日数 − 交易日数`；`progress/total` 只计交易日；result 含逐日四类计数（expected/daily/suspended/final）
- [ ] 生命周期 preflight 每任务仅执行一次（mock 断言 `init_stocks_lifecycle` 调用次数=1）
- [ ] AC-08 collector：休市日 skipped 不调 Provider；交易日历刷新失败 → 日更失败且不写当日指标；指标步骤失败 → `results.errors` 有记录、`etf/index` 步骤仍执行
- [ ] AC-09（collector 侧）本地日历休市记录存在时 `_update_market_metrics` 不执行
- [ ] AC-07 恢复路径：失败日重跑后该日 status 变 success 且值更新
- [ ] `pytest` 全量回归通过
- [ ] E2E 不适用：后端任务功能无浏览器界面；以"执行验证"用例（上第 3 条）作为质量门，前端可见性由 plan-08 覆盖

### 性能验收（架构 §8.1）

- [ ] 范围回填逐日串行、每日日级提交；进度至少每处理一日更新（轮询断言 progress 单调递增）

## 验证命令

```bash
cd server && source .venv/bin/activate

# 1. 路由与 collector 单测
pytest tests/api/admin/test_init_market_metrics.py tests/test_data_updater.py -v --no-cov

# 2. 执行验证（需 TUSHARE_TOKEN + 本地 PG；小范围真实任务）
python -c "
import asyncio
from src.db.database import AsyncSessionLocal
from src.services.task_manager import TaskManager
async def main():
    async with AsyncSessionLocal() as s:
        m = TaskManager(s)
        t = await m.create_exclusive_task(task_type='sync_market_metrics',
            params={'start_date':'2026-08-11','end_date':'2026-08-12'}, created_by=None)
        print('created:', t.task_id if t else 'BLOCKED')
asyncio.run(main())
"
# 然后启动执行器（或现有服务入口）等待任务终态，检查：
python -c "
import asyncio
from sqlalchemy import select
from src.db.database import AsyncSessionLocal
from src.models.market_daily_metric import MarketDailyMetric
async def main():
    async with AsyncSessionLocal() as s:
        rows = (await s.execute(select(MarketDailyMetric).order_by(MarketDailyMetric.trade_date))).scalars().all()
        for r in rows: print(r.trade_date, r.volume_shares, r.amount_yuan, r.average_price, r.final_stock_count)
asyncio.run(main())
"

# 3. 全量回归
pytest tests/ -q --no-cov
```

## 交接上下文

- **架构章节**: §3.1-3.2、§4.2 模块 3、§6.2、§6.3、§7.2-7.3、§8.1/8.4/8.5
- **相关代码**: `server/src/api/admin/init_index_basic.py`（路由范式 L39/L60-72）、`server/src/services/task_handlers.py`（`backfill_index_history_task` L1638-1688 范围同步范式）、`server/src/services/data_updater/collector.py`（`run_daily_update` L72-169、`_update_market_data` L263-376、results L85-96）
- **契约 / 数据对象**: `MarketMetricsTaskResult`（§7.2，写入 `AsyncTask.result`，plan-08 前端消费）；params `{start_date, end_date}`（ISO 字符串，user_input）
- **下游消费方**: plan-06（读 `market_daily_metrics`/`trading_calendar_days`）；plan-08（读任务 result 与日志）
- **路径说明**: `server/tests/api/admin/` 为新建子目录，`server/tests/api/conftest.py` 的 autouse admin override 自动生效

## 风险与边界

- **执行顺序**: 按 Task 列表顺序执行；Task 3-4 依赖 plan-04 的 Registry/finalize 方法
- **验证失败排查方向**: 任务一直 pending → 检查执行器是否持专属 owner lock；任务秒失败 → 看 `MarketMetricsSyncError` 四类计数定位是采集还是平衡校验
- **允许修改的额外文件**: 无
- **暂停条件**: 真实执行验证若因 Tushare 积分不足无法拉全市场 daily，暂停并请用户提供可用账号或改用更长等待窗口
- **风险备注**: 18:00 job 遵循仓库"开发期停用"惯例以注释预留，生产启用由部署阶段落实（§NFR 部署层 gap 标注）

### 后端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| 范围全为非交易日 | 路由零交易日拒绝，不建任务 | done |
| 范围含非交易日 | skippedCount 计数，不进 handler 计算 | done |
| 单日失败 | 回滚该日、记录 dateResults、继续下一日 | done |
| 任务运行中被取消 | 保存 partial result + unprocessedDates 后 finalize cancelled | done |
| collector 指标失败 | errors 记录、market_metrics_updated=0、不阻断后续 | done |
| 日历刷新失败（日更） | 日更失败，不用旧批冒充，首页用旧本地日历降级 | done |
