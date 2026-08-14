---
title: '融资融券数据同步与首页曲线图'
type: 'feature'
created: '2026-08-14'
status: 'done'
context:
  - docs/16-A股全市场量价指标/16-1-架构文档-A股全市场量价指标.md
  - docs/16-A股全市场量价指标/16-2-实现计划-A股全市场量价指标/README.md
---

<!-- 参照第 16 期 market-metrics 全链路范式（单表日期级 upsert + 异步任务 fencing + 缺口 null），新增一套同构的融资融券数据闭环。 -->

<frozen-after-approval reason="人工意图 — 除非人类重新协商，否则不可修改">

## 意图

**问题：** 首页缺少反映市场两融杠杆与多空力量对比的指标，用户无法直观判断市场融资（做多）/融券（做空）情绪。

**方案：** 照搬 market-metrics 范式，用 tushare `margin` 汇总接口按交易日拉取全市场（沪/深/北）两融数据并聚合为全市场单行存储；首页新增融资融券曲线图面板（双 Y 轴展示 4 指标），数据管理页新增同步触发面板。

## 边界

**必须：**
- 复用 market-metrics 的单表日期级原子 upsert（`on_conflict_do_update(trade_date)`）、异步任务专属锁 + fencing + 互斥 + 恢复、查询端 `trading_calendar_days` LEFT JOIN 缺口输出 null 三大范式。
- 数据源固定为 `margin`（融资融券交易汇总，doc_id=58）；全市场合计口径（对接口返回的全部交易所行聚合为 1 行，实测为沪 SSE/深 SZSE/北 BSE 三行），不拆分交易所。
- 复用现有 ECharts + echarts-for-react，前端展示层统一 ÷1e8 转亿。
- `rzye` / `rqye` / `rzmre` / `rzche` / `rqmcl` 五字段对全部交易所行求和（行数以接口实际返回为准）；`rzrqye = sum(rzye) + sum(rqye)` 服务层重算（不直接 sum tushare 每行 rzrqye）。

**先问：** 无（数据粒度=全市场合计、历史范围=近1年、曲线指标=4个全选 已在前置澄清中确认）。

**禁止：**
- 不引入 `margin_detail` 个股明细同步（数据量大、不在本期范围）。
- 不改动 market-metrics 现有代码逻辑（仅复用范式、以新增文件为主）。
- 不引入新图表库或新状态管理库。

## 需求变更

### 新增

- **REQ-1（采集）**：系统 SHALL 在 tushare 客户端提供 `get_margin(trade_date)` 方法，调用 `pro.margin(trade_date=)` 返回当日全部交易所行（实测 SSE/SZSE/BSE 三行）原始数据，复用 `_execute_with_retry` + `_df_to_rows` + `_decimal_field` 范式，字段经 `Decimal(str())` 强约束。
- **REQ-2（存储）**：系统 SHALL 新建 `market_margin_daily` 表，每交易日唯一一行（`trade_date` 唯一约束），存储 rzye/rqye/rzmre/rzche/rqmcl（Numeric(20,2)）与 rzrqye（Numeric(20,2)）及 created_at/updated_at。
- **REQ-3（汇总服务）**：系统 SHALL 提供 `MarginService.sync_date(trade_date)`：拉取全部交易所行 → 五字段求和 → rzrqye 重算 → Decimal 原子 upsert（`on_conflict_do_update(trade_date)`），成功立即 commit、失败回滚当日。
- **REQ-4（异步任务）**：系统 SHALL 新增保留任务类型 `sync_market_margin`（`TaskType.SYNC_MARKET_MARGIN`），注册专属 handler，逐交易日串行调用 sync_date，结果含成功/跳过/失败计数与逐日明细（camelCase）。该任务 SHALL 具备专属 advisory lock + owner lock + fencing token + stale 恢复（照搬 plan-04 fencing 范式），并加入 `RESERVED_TASK_TYPES`（通用 `/admin/tasks` 入口封堵）。
- **REQ-5（同步端点）**：管理员 SHALL 通过 `POST /api/v1/admin/init/margin`（`require_admin` + 日期范围校验：起止倒置/end>today/跨度≤3650天/日历刷新/零交易日，任一失败不建任务）触发互斥同步任务。
- **REQ-6（查询端点）**：系统 SHALL 提供 `GET /api/v1/margin/trend?range=30|90|250`（零 Provider 调用，`trading_calendar_days` LEFT JOIN `market_margin_daily`，缺口输出 null），响应 `{success, data:{latest, points, range, hasMissingDates}}`，经 `_dict_to_camel` + Decimal→float。
- **REQ-7（首页面板）**：首页（dashboard 非管理员视图）SHALL 在 MarketMetricsPanel 旁新增融资融券曲线图面板，含最新值卡片（4 指标：融资余额/融券余额/两融合计余额/融资买入额）+ 双 Y 轴曲线（左轴万亿级 rzye+rzrqye，右轴千亿级 rqye+rzmre，含 legend）+ 30/90/250 范围切换。
- **REQ-8（同步面板）**：数据管理页 SHALL 新增"融资融券"tab，挂载同步触发面板（日期范围输入 + 触发 + useTaskStatus 轮询 + 成功/跳过/失败计数 + 逐日明细展开 + 历史任务记录列表）。

</frozen-after-approval>

## 代码地图

**后端 — 新增：**
- `server/src/models/market_margin_daily.py` — NEW，表模型（仿 `market_daily_metric.py`）
- `server/alembic/versions/2026_08_14_XXXX-xxxx_add_market_margin_daily.py` — NEW，建表迁移
- `server/src/services/margin_service.py` — NEW，`MarginService.sync_date` + 聚合 + `_atomic_upsert`
- `server/src/api/v1/margin.py` — NEW，查询路由 `GET /margin/trend`
- `server/src/api/admin/init_margin.py` — NEW，同步触发路由 `POST /init/margin`
- `server/src/repositories/margin_repository.py` — NEW（若 market-metrics 有仓储层；否则 service 内直查）

**后端 — 改动（小改）：**
- `server/src/services/data_acquisition/tushare_client.py:1750~1923` — 加 `get_margin(trade_date)`，仿 `get_market_daily_quotes` 的分页/重试范式（margin 单日仅数行，无需分页）
- `server/src/models/__init__.py` — 注册 `MarketMarginDaily`
- `server/src/services/task_handlers.py:92` — `TaskType` 加 `SYNC_MARKET_MARGIN = "sync_market_margin"`；新增 `@TaskRegistry.register(SYNC_MARKET_MARGIN)` handler（仿 `:1876` sync_market_metrics_task）
- `server/src/services/task_manager.py:28` — `RESERVED_TASK_TYPES` 加 `"sync_market_margin"`；`:38-39` 旁加 `MARGIN_LOCK_KEY`/`MARGIN_OWNER_LOCK_KEY` 常量；扩展 `create_exclusive_task` 与 stale 恢复以支持新 task_type
- `server/src/api/admin/__init__.py:46` — 挂载 `init_margin.router`
- `server/src/api/v1/__init__.py:49` — 挂载 `margin.router`

**前端 — 新增：**
- `web/src/types/marginTypes.ts` — NEW，契约类型（`MarginPoint` / `MarginTrendData` / `MarginRange` / `MarginTaskResult`）
- `web/src/components/market-margin/MarginPanel.tsx` — NEW，首页面板（最新值卡片 + 双 Y 轴曲线 + 范围切换）
- `web/src/components/market-margin/MarginSyncPanel.tsx` — NEW，数据管理同步面板

**前端 — 改动（小改）：**
- `web/src/lib/api.ts:649` — `adminApi.initMargin(start_date, end_date)` → `POST /admin/init/margin`；`:1627` 旁加 `marginApi.getTrend(range)` → `GET /margin/trend?range=`
- `web/src/app/dashboard/page.tsx:69` — MarketMetricsPanel 旁挂载 `<MarginPanel />`
- `web/src/app/dashboard/admin/data/page.tsx:15` — `DataTab` 加 `'market-margin'`；`:106` 加 tab 按钮；`:127` 加挂载 `&&`

## 任务清单

- [ ] **T1 数据模型 + 迁移**：新建 `server/src/models/market_margin_daily.py`（字段见 REQ-2，`trade_date` 唯一约束 + 索引，Numeric(20,2)）；`server/src/models/__init__.py` 注册；新建 Alembic 迁移建表（仿 `2026_08_14_0001-c4b9e2a7f813_*.py` 的 create_table+create_index 范式）。
- [ ] **T2 采集适配器**：在 `server/src/services/data_acquisition/tushare_client.py` 加 `get_margin(trade_date) -> list[dict]`，调 `pro.margin(trade_date=)`，复用 `_execute_with_retry`+`_df_to_rows`，字段经 `_decimal_field` 转 Decimal；单日仅数行（实测 3 行）无需分页。
- [ ] **T3 汇总服务**：新建 `server/src/services/margin_service.py`，`MarginService.sync_date(trade_date)`：日历守卫 → `get_margin` → 五字段求和 → rzrqye 重算 → `_atomic_upsert`（on_conflict_do_update(trade_date)，仿 `market_metrics_service.py:805`）；成功 commit / 失败回滚。
- [ ] **T4 异步任务 + fencing**：`task_handlers.py:92` 加 `SYNC_MARKET_MARGIN`；新增 handler（仿 `:1876`，逐日串行调 sync_date，构造 camelCase result 含成功/跳过/失败 + 逐日明细）；`task_manager.py` 加锁 key 常量、扩 `create_exclusive_task` 与 stale 恢复支持 sync_market_margin、`RESERVED_TASK_TYPES` 加成员。
- [ ] **T5 admin 同步端点**：新建 `server/src/api/admin/init_margin.py`（仿 `init_market_metrics.py`，`POST /init/margin`，require_admin + 五项日期校验 + `create_exclusive_task(task_type="sync_market_margin")`）；`api/admin/__init__.py` 挂载。
- [ ] **T6 查询端点**：新建 `server/src/api/v1/margin.py`（仿 `market_metrics.py:103`，`GET /margin/trend?range=30|90|250`，零 Provider，trading_calendar_days LEFT JOIN market_margin_daily，缺口 null，`_dict_to_camel`+Decimal→float）；`api/v1/__init__.py` 挂载。
- [ ] **T7 首页面板**：新建 `web/src/types/marginTypes.ts`；新建 `web/src/components/market-margin/MarginPanel.tsx`（仿 MarketMetricsPanel：SWR key `['marginTrend', range]`、RANGE_OPTIONS [30,90,250]、最新值卡片 4 指标 ÷1e8 转亿、双 Y 轴 echarts option 左轴 rzye+rzrqye 右轴 rqye+rzmre 含 legend、dynamic import ssr:false）；`dashboard/page.tsx:69` 旁挂载；`api.ts` 加 `marginApi.getTrend` + `adminApi.initMargin`。
- [ ] **T8 同步面板 + admin tab**：新建 `web/src/components/market-margin/MarginSyncPanel.tsx`（仿 MarketMetricsSyncPanel：日期范围输入 + `adminApi.initMargin` + `useTaskStatus` 轮询 + 成功/跳过/失败计数 + 逐日 dateResults 展开 + SWR 拉 `/admin/tasks?task_types=sync_market_margin`）；`dashboard/admin/data/page.tsx` 加 `'market-margin'` tab + 按钮 + 挂载。

## 验收标准

- **AC-1（聚合正确）**：Given 某 trade_date tushare margin 返回 SSE 行 {rzye:1.0e12, rqye:5.0e10, rzmre:7.0e10}、SZSE 行 {rzye:8.0e11, rqye:3.0e10, rzmre:4.0e10} 与 BSE 行 {rzye:2.0e10, rqye:1.0e10, rzmre:1.0e10}，when 执行 `MarginService.sync_date(t)`，then `market_margin_daily` 该日 rzye=1.82e12、rqye=9.0e10、rzmre=1.2e11、rzrqye=1.91e12。
- **AC-2（幂等 upsert）**：Given 表中已存在 trade_date D 的记录，when 同日再次 sync_date(D) 成功，then 该行被更新而非新增（行数不变，updated_at 刷新）。
- **AC-3（同步任务互斥）**：Given 一个 sync_market_margin 任务正在运行，when 管理员再次触发同区间同步，then 第二次请求被拒绝（409 或 success=false 互斥错误），不产生重复任务。
- **AC-4（同步端点校验）**：Given 请求 body end_date 晚于今天，when POST /api/v1/admin/init/margin，then 返回错误且不创建任务。
- **AC-5（查询缺口）**：Given range=30 且期间有若干交易日 market_margin_daily 无数据，when GET /api/v1/margin/trend?range=30，then 这些日期对应 point 字段为 null，hasMissingDates=true，points 长度=区间交易日数。
- **AC-6（首页面板渲染）**：Given 已同步数据且非管理员登录，when 打开 /dashboard，then 融资融券面板渲染 4 张最新值卡片（单位亿）+ 双 Y 轴曲线（左轴 rzye/rzrqye、右轴 rqye/rzmcl）+ legend + 30/90/250 切换可切换范围并重新请求。
- **AC-7（同步面板）**：Given 管理员打开数据管理页，when 点击"融资融券"tab 并输入日期范围触发同步，then 面板显示任务进度、逐日成功/跳过/失败明细，完成后历史记录列表出现该条任务。
- **AC-8（通用入口封堵）**：Given sync_market_margin 为保留任务类型，when 通过通用 POST /api/v1/admin/tasks 创建该类型，then 被拒绝。
