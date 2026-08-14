# 开发计划检查报告（第 2 轮复审）

- 检查日期：2026-08-14
- 架构文档：`docs/16-A股全市场量价指标/16-1-架构文档-A股全市场量价指标.md`
- 实现计划：`docs/16-A股全市场量价指标/16-2-实现计划-A股全市场量价指标/`（README + plan-01~plan-08，共 9 文件）
- 检查依据：`.zcode/skills/dev-plan-check/SKILL.md`
- 代码核对方式：读取真实后端/前端代码逐项验证（路由挂载链 main.py→router.py→v1/__init__.py→admin/__init__.py；ApiClient/AdminApiClient 泛型与解包层级；indexMonitorApi/etfMonitorApi/adminApi/tasksApi 范式；task_manager/task_executor 方法名与行号；data_init/collector/task_handlers 锚点；alembic head；pytest/jest/playwright 配置；async_task.to_dict 与 task 详情序列化路径）
- 复审范围：第 1 轮 4 项修复的彻底性 + 新引入不一致排查 + 全维度复查

## 一、总结论：PASS

第 1 轮 3 个 major 全部修复彻底、未引入新问题；全维度复查未发现 blocker 或 major。仅余 4 处不影响可执行性的 trivial 锚点/措辞偏差（均 ≤ minor，且其中 3 处在第 1 轮已归类为可接受的锚点漂移类）。

| 严重度 | 数量 |
| --- | --- |
| blocker | 0 |
| major | 0 |
| minor | 4（均为 trivial，不阻断执行） |

按 dev-plan-check 通过标准（无 blocker、AC 全映射、必备章节完整、E2E-TDD 覆盖用户可见功能、状态/依赖合法、维度 17 四件套代码级核对通过）——**判定 PASS**。

## 二、第 1 轮修复彻底性核查（grep 全量验证）

| # | 第 1 轮声称修复 | 复审 grep 核查 | 结论 |
| --- | --- | --- | --- |
| 1 | README `critical_path` 改为 6 节点最长链 + §1 文字同步 | frontmatter `critical_path: ["plan-01","plan-02","plan-03","plan-06","plan-07","plan-08"]`（README:12）；§1「关键路径: plan-01 → plan-02 → plan-03 → plan-06 → plan-07 → plan-08（6 节点最长链）」（README:29）。全文搜索无残留 5 节点链或"plan-05 在关键路径"措辞；grep 命中的 `plan-05` 均为 AC 矩阵/execution_order 的合法出现 | 彻底 ✓ |
| 2 | plan-07 API 泛型改为完整业务包 + `as unknown as` cast | plan-07:55 `apiClient.get<{ success: boolean; data: MarketMetricsTrendData }>`；plan-07:67 `.then(res => res.data as unknown as { success: boolean; data: MarketMetricsTrendData })`。全文无残留旧泛型 `apiClient.get<MarketMetricsTrendData>`（裸业务对象） | 彻底 ✓ |
| 3 | result 键风格统一 camelCase（plan-05 产出/plan-04 透传/plan-08 直消费） | plan-05:65 显式「result JSON 键全部 camelCase」+ dateResults 逐项 camelCase（plan-05:64）；plan-04:43 to_dict「原样透传 dict \| None」；plan-08:44「result 键全 camelCase…前端直消费、无二次键转换」+ plan-08:130 三方契约一致声明。grep 搜索「须转换/若以 snake_case 存储/须在消费层做一次键转换」等对冲措辞在 plan-04/05/08/README **零命中** | 彻底 ✓ |
| 4 | plan-03 锚点校准、plan-06 Query regex→pattern、plan-08 RECORDS_SWR_KEY 行号 | plan-03:137「`_cleanup_disappeared_stocks` 调用 L578-581 / 定义 L616」（实测 data_init.py 调用 L578、定义 L616 ✓）；plan-06:44 `pattern="^(30\|90\|250)$"`（注释「regex= 已弃用」）；plan-08:129「RECORDS_SWR_KEY L65」（实测 IndexSyncPanel.tsx:65 ✓） | 彻底 ✓ |

**新不一致排查**：4 项修复均未引入新的契约不一致。plan-07 泛型/cast 与 api.ts:1370-1371 文档化约定、indexMonitorApi/etfMonitorApi 范式（api.ts:1529、1419）完全对齐；result camelCase 经 task 详情端点序列化路径复核为「必需且正确」（见 §六 e）。

## 三、Contract 预检

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| README frontmatter `workflow_type`/`status`/`org_mode` | ✓ | create-dev-plan / review_ready / feature |
| `execution_order` 引用真实 plan-XX | ✓ | 6 组全覆盖 plan-01~08 |
| `total_tasks` = plan 文件数 | ✓ | 8 = 8 |
| README 必备章节（10 项）齐全 | ✓ | 概览/输入摘要/AC 矩阵/模块地图/依赖图/阶段摘要/任务总览/未决策项/执行前置/变更记录 |
| AC 矩阵表头固定 | ✓ | `AC-ID \| 需求原文 \| 架构承接 \| 计划承接 \| 验证方式 \| 当前状态` |
| 8 plan frontmatter `feat_id`/`dimension`/`phase`/`status`/`depends_on` | ✓ | 文件名与 feat_id 一致；dimension ∈ {backend/frontend/mixed}；status=ready-to-dev |
| 每 plan 8 章节齐全 | ✓ | 功能概要/文件清单/实现规格/Task 列表/验收标准/验证命令/交接上下文/风险与边界 |
| 功能概要 7 必填字段 | ✓ | 目标/可观察结果/依赖/关联 AC/架构模块/前置条件/不在范围 |
| 无 `{{placeholder}}` 空缺 | ✓ | `<rev12>` 为已声明自生成 revision（非模板空缺） |
| Task/边界状态仅 todo/done/waived | ✓ | 全部 todo；无 waived |

## 四、验收标准追踪（双向一致）

架构 §2.5 AC-01~AC-13（13 条）在 README 矩阵全部出现，无遗漏；逐条核验 README「计划承接」↔ 各 plan「关联验收标准」两方向闭合，无孤立 AC、无 plan 侧自造 AC：

| AC-ID | README 计划承接 | plan 侧关联 AC（核对） | 结论 |
| --- | --- | --- | --- |
| AC-01 | plan-02, plan-03 | plan-02 ✓ plan-03 ✓ | ✓ |
| AC-02 | plan-04, plan-05, plan-08 | plan-04 ✓ plan-05 ✓ plan-08 ✓ | ✓ |
| AC-03 | plan-03 | plan-03 ✓ | ✓ |
| AC-04 | plan-07 | plan-07 ✓ | ✓ |
| AC-05 | plan-06, plan-07 | plan-06 ✓ plan-07 ✓ | ✓ |
| AC-06 | plan-06, plan-07 | plan-06 ✓ plan-07 ✓ | ✓ |
| AC-07 | plan-02, plan-03, plan-04, plan-05, plan-08 | 五 plan 均列 ✓ | ✓ |
| AC-08 | plan-05 | plan-05 ✓ | ✓ |
| AC-09 | plan-01, plan-03, plan-05 | plan-01 ✓ plan-03 ✓ plan-05 ✓ | ✓ |
| AC-10 | plan-05, plan-08 | plan-05 ✓ plan-08 ✓ | ✓ |
| AC-11 | plan-04, plan-05, plan-08 | 三 plan 均列 ✓ | ✓ |
| AC-12 | plan-07 | plan-07 ✓ | ✓ |
| AC-13 | plan-02, plan-03 | plan-02 ✓ plan-03 ✓ | ✓ |

用户可见功能（plan-07/08）均要求 E2E-TDD red/green 双阶段证据（存 `docs/e2e/evidence/plan-0X-e2e-{red|green}-{date}.md`）；`docs/e2e/` 与 `docs/e2e/evidence/` 目录均已存在 ✓。

## 五、维度检查结果

| 维度 | 结论 | 问题数 | 摘要 |
| --- | --- | --- | --- |
| 1 核心闭环 | ✓ | 0 | 拉取→核验→汇总→展示闭环在 README §2.1 + 各 plan 完整承接 |
| 2 范围/非目标 | ✓ | 0 | P0 全覆盖；§2.3「明确不做」在 plan-02/03/06 显式遵守 |
| 3 成功标准 | ✓ | 0 | §2.4 定量标准（P95≤500ms、单日可复算、幂等覆盖）落到对应 plan 验收/性能段 |
| 4 AC 防漂移 | ✓ | 0 | 见 §四 |
| 5 ADR | ✓ | 0 | ADR-1~6 护栏在 README §2.2 表 + plan 实现规格呼应 |
| 6 流程/状态机 | ✓ | 0 | §3.3 状态机（pending/running/completed/failed/cancelled）在 plan-04 全分支覆盖 |
| 7 模块职责 | ✓ | 0 | §4.2 六模块 ↔ plan-01~08 一一对应（README §4 模块地图） |
| 8 运行链路 | ✓ | 0 | §6.1~6.4 链路在 plan-03/05/06 逐步落地 |
| 9 数据模型/契约 | ✓ | 0 | §7.2 对象/TS 契约逐字段对齐；result camelCase 三方自洽 |
| 10 非功能 | ✓ | 0 | §8.1 性能/§8.2 降级/§8.5 可观测性注入对应 plan |
| 11 技术选型 | ✓ | 0 | 技术栈与 §9 三阶段一致 |
| 12 风险 | ✓ | 0 | §8.6 风险在 plan 风险与边界有缓解 |
| 13 功能拆分 | ✓ | 0 | 单 FEAT 连贯；Task 列表均 ≤9 步；DAG 无环 |
| 14 可执行性 | ✓ | 0 | 文件清单具体；验证命令可运行（见 §六 g） |
| 15 状态/报告 | ✓ | 0 | 状态合法；本报告写入 contract 路径 |
| 16 复用声明 | ✓ | 0 | init_stocks_lifecycle/MarketMetricsService 调用链清晰 |
| 17 前后端契约（代码级） | ✓ | 0 | 四件套 + 解包层级 + snake/camel 全部代码级核对通过（见 §六 e） |

## 六、重点核查逐项结论（a–i）

### a. 第 1 轮 4 项修复的彻底性 — PASS

见 §二，4 项修复 grep 全量核查全部彻底，无残留、无误伤、无对冲措辞。

### b. 结构/frontmatter/8 章节/7 必填字段/无占位符 — PASS

见 §三 Contract 预检，全部满足。

### c. AC 追踪矩阵双向一致 — PASS

见 §四，13 条 AC 双向闭合。

### d. DAG/execution_order/phase/critical_path 一致性（图论最长链复核）— PASS

按 `depends_on` 计算各节点最长深度：
- plan-01=1, plan-02=2, plan-03=3, plan-04=2, plan-05=4, plan-06=4, plan-07=5, plan-08=6
- 最长链终点 plan-08（深度 6），回溯路径 plan-08←plan-07←plan-06←plan-03←plan-02←plan-01 = `plan-01→02→03→06→07→08`（6 节点）。
- 与 README `critical_path` 完全一致 ✓；`execution_order` 6 组与 `depends_on` 不矛盾 ✓；组内并行声明（plan-03/04、plan-05/06）经核文件不相交，成立 ✓。

### e. 前后端契约四件套正确性（重点：plan-07 修复后的泛型与 cast）— PASS

**路径前缀**：
- plan-06/07 GET `/market-metrics/trend?range=30` × `apiClient.baseURL=${API_BASE_URL}/api/v1`（api.ts:9）= `/api/v1/market-metrics/trend`（无双前缀）✓
- plan-08 POST `/admin/init/market-metrics` × AdminApiClient baseURL 同 = `/api/v1/admin/init/market-metrics`；后端实测挂载链 main.py:111 `prefix="/api"` + router.py:29 `prefix="/v1/admin"` + admin/__init__.py 无统一前缀 + 子路由 `prefix="/init"`（init_index_basic.py:39 范式）= `/api/v1/admin/init/market-metrics` ✓
- plan-08 记录区 `fetcher('/api/v1/admin/tasks?task_types=...')`：fetcher `API_BASE=NEXT_PUBLIC_API_URL`（不含 /api，fetcher.ts:8），不双前缀 ✓

**HTTP 方法存在性与鉴权**：GET 在 `ApiClient`（api.ts:119）经 `getAuthHeaders()`（api.ts:45-57）携带 Authorization ✓；POST 在 `AdminApiClient`（api.ts:530），`AdminApiClient` 覆盖了 request/get/post/patch/delete 全部方法（api.ts:453/525/530/535/540），均走带鉴权的 `request`，无「继承未覆盖不带鉴权」风险 ✓；后端 `@router.get("/trend")`/`POST /market-metrics` 三方一致 ✓。

**query 命名**：`range` 单词无 snake/camel 歧义；`task_types/page/page_size` 保持 snake_case（与 IndexSyncPanel.tsx:65 `RECORDS_SWR_KEY` 同款）✓；body `{start_date,end_date}` snake_case（与 Pydantic payload 一致）✓。

**响应字段命名 + 解包层级**：
- plan-07：`apiClient.get<{ success: boolean; data: MarketMetricsTrendData }>`（plan-07:55）——泛型 T 写完整业务包，与 api.ts:1370-1371 文档化约定、indexMonitorApi（api.ts:1529）/etfMonitorApi（api.ts:1419）完全一致；`ApiClient.request` 返回 `{ data: 完整响应体 }`（api.ts:111），故 `res.data`={success,data}，组件再取 `.data`。SWR cast `res.data as unknown as { success, data }`（plan-07:67）与锚点 IndexMonitorPage.tsx:46-49 完全一致 ✓。
- **ApiResponse\<T\> z.infer 交叠问题**：`ApiResponse<T> = z.infer<ApiResponseSchema> & { data?: T }`（api.ts:20-22），schema 仅含 `error?`。修复前泛型 `<MarketMetricsTrendData>` 使 `res.data` 类型为 `MarketMetricsTrendData`，cast 到 `{success,data}` 无结构交叠 → tsc 报 neither sufficiently overlaps。修复后泛型为 `<{success,data}>`，`res.data` 类型即 `{success,data} | undefined`，`as unknown as {success,data}` 合法通过 tsc（IndexMonitorPage 同款）。**类型撒谎问题已根除** ✓。
- plan-08：`adminApiClient.post<{ task_id: string }>`（plan-08:52）——AdminApiClient.request 返回 `{ data: json.data }`（api.ts:517，已解一层），故 `res.data`={task_id}，与既有 `initEtfHistory`（api.ts:618-619）/`initIndexHistory`（api.ts:625-626）范式逐字一致 ✓。

### f. 验证命令可执行性 — PASS

- pytest：`cd server && source .venv/bin/activate`（`server/.venv` 真实存在 ✓）；单文件命令均带 `--no-cov`（pytest.ini 全局 `--cov-fail-under=80`/`--cov=src`，单跑需规避 ✓）；README §9.3 全量 `pytest tests/ -v` 不带 `--no-cov`（有意启用 80% 门槛 ✓）；`testpaths=tests`+`python_files=test_*.py`+`--import-mode=importlib` 递归收集，新建 `tests/api/admin/test_init_market_metrics.py` 自动被收集 ✓。
- 迁移链：实测 `alembic heads` 单一 head `7e3309ce89da`（文件 `2026_08_13_2234-7e3309ce89da_add_index_basic_sort_order.py`，down_revision=`f92bfffc49c3`）；plan-01 `down_revision='7e3309ce89da'` 正确 ✓；plan-04 迁移 down_revision 相对指向 plan-01 迁移（depends_on plan-01，时序成立）✓。
- pnpm 脚本：`web/package.json` `test=jest`/`build=next build`/`test:e2e=playwright test` 真实存在；无 `type-check` 脚本，plan-07/08 用 `pnpm exec tsc --noEmit`（未误用）✓；Playwright `testDir='./tests/e2e'`、`baseURL=http://localhost:3100`（playwright.config.ts:9/23）与计划一致 ✓。
- **`pnpm test -- tests/...` 写法可行性**：jest.config.ts testMatch 收 `<rootDir>/tests/**/*.{test,spec}.{js,jsx,ts,tsx}`（L23-25），testPathIgnorePatterns 排除 `tests/e2e/`（L31）；`pnpm test -- tests/market-metrics/X.test.tsx` = `jest tests/market-metrics/X.test.tsx`，jest 接受位置参数作路径过滤，目标文件命中 testMatch，可行 ✓；`pnpm test:e2e -- tests/e2e/X.spec.ts` = `playwright test tests/e2e/X.spec.ts`，Playwright 接受位置参数作文件过滤（相对 testDir），可行 ✓。

### g. 跨文件契约自洽 — PASS

- **TaskFenceContext 时序**：plan-03 用 `from __future__ import annotations` + `TYPE_CHECKING` 前向引用（plan-03:138），运行时不导入 `task_fence`；真正构造/fence 在 plan-04（task_fence.py）落地、plan-05 传入真实实例。plan-03 depends_on=[plan-01,plan-02] 虽不含 plan-04，但运行时不导入且 `task_context` 仅由 plan-05（depends_on plan-04）传入，依赖传递满足 ✓。
- **迁移链衔接**：plan-04 depends_on=[plan-01]，其迁移 down_revision 指向 plan-01 迁移 revision，时序成立 ✓。
- **result camelCase 三方**：plan-05 handler 构造即 camelCase → plan-04 to_dict 原样透传 → plan-08 前端直消费。**深度复核 task 详情端点序列化路径**（`GET /{task_id}`）：端点用 `ApiResponse[TaskDetailResponse]`（tasks.py:255 response_model）+ `TaskDetailResponse(**task.to_dict())`（tasks.py:292），**未对响应体施加 `_dict_to_camel`**（与 index_monitor 手动包裹 `_dict_to_camel` 不同）；AsyncTask.to_dict 本身产出 camelCase 顶层键（async_task.py:57-58 `"taskId"`）。因此 result 子树没有任何 snake→camel 转换层——plan-05 写 camelCase 是「必需且正确」的（若写 snake_case 前端将直接收到 snake_case 而取到 undefined）。plan-04 §5 显式为 TaskDetailResponse/TaskResponse 增加 `result: Optional[dict]`，确保 `**task_dict` 不被 Pydantic 默认 `extra='ignore'` 丢弃。三方契约自洽且与序列化路径强制一致 ✓。
- **并行性**：plan-03/04 文件不相交（plan-03: market_metrics_service/data_init；plan-04: task_fence/task_manager/task_executor/async_task）✓；plan-05/06 文件不相交（plan-05: task_handlers/init_market_metrics/admin.__init__/collector/job_manager；plan-06: api/v1/market_metrics/v1.__init__）✓。

### h. plan-05 执行验证用例可操作性 — PASS

plan-05 验证命令 #2（plan-05:127-137）直接调 `TaskManager.create_exclusive_task(task_type='sync_market_metrics', ...)`。该方法是 plan-04 新增（plan-04 §3），plan-05 depends_on=[plan-01,02,03,04]，故 plan-05 执行时方法已存在 ✓。脚本 import 路径正确：`AsyncSessionLocal`（src.db.database，task_executor.py:17 已证实可导入）、`TaskManager`（src.services.task_manager）、`MarketDailyMetric`（plan-01 创建于 src/models/market_daily_metric.py）✓。方法签名一致（plan-04 `create_exclusive_task(task_type, params, created_by, timeout_seconds)`，脚本传 `task_type/params/created_by`，timeout_seconds 缺省）✓。

### i. plan-05 执行验证用例可操作性（补充：collector/conftest）— PASS

- plan-05 collector 锚点实测：`run_daily_update` L72（plan-05:71 ✓）、`results` dict L85（plan-05:77 ✓）、`_update_market_data` L263（plan-05:75 ✓）；新增 `_update_market_metrics` 在 `_update_market_data` 成功后调用，results 增加 `market_metrics_updated` 键，符合现有 results 结构 ✓。
- plan-05 `tests/api/admin/` 新建子目录：pytest `--import-mode=importlib` 不需 `__init__.py`；`tests/api/conftest.py` autouse `api_auth_override`（conftest.py:8-24 覆盖 `get_current_user` 为 admin）对子目录自动生效，plan-05:162 声明正确 ✓。

## 七、问题清单（仅 trivial，均不阻断）

| # | 严重度 | 所在文件 | 问题 | 建议修复 |
| --- | --- | --- | --- | --- |
| 1 | minor | plan-08:55（§2 注释）、plan-08:129（交接上下文） | 引用「与既有 `initLimit`/`initIndexHistory` 同款」作为锚点，但 `web/src/lib/api.ts` 中**不存在 `initLimit` 方法**（实际同类锚点为 `initEtfHistory` L618-619 / `initIndexHistory` L625-626，两者范式与 plan-08 `initMarketMetrics` 逐字一致）。仅措辞引用失准，实质代码范式与锚点正确。 | 将「initLimit」改为「initEtfHistory」或直接引用 initIndexHistory。非阻断。 |
| 2 | minor | plan-08:59（§3 IndexSyncPanel 范式锚点） | 「互斥 L44-52」指向的实为 `IndexSyncPanel.tsx` 的 `SyncRecord` interface 定义（L44-52），而非互斥按钮逻辑；互斥 isRunning 逻辑在更下方。概念锚点（IndexSyncPanel 为同步面板范式）成立，仅行号指向偏移。 | 锚点改为「IndexSyncPanel useTaskStatus + isRunning 互斥范式（方法名为主）」。非阻断。 |
| 3 | minor | plan-07:79（§4 IndexMonitorPage 插入点） | 引用 `<IndexOverviewCards .../>（L153）`，实测 IndexOverviewCards 渲染在 `IndexMonitorPage.tsx:154`（±1 行）。 | 刷新为 L154 或以组件名为主。非阻断。 |
| 4 | minor | plan-03:137、plan-01:158（data_init/tushare 锚点） | `_safe_nested_tx` 引用 L29，实测 `data_init.py:30`（±1 行）。 | 刷新为 L30 或以方法名为主。非阻断（第 1 轮已归类同类锚点漂移）。 |

> 说明：以上 4 项均为锚点行号 ±1 或方法名引用失准，不影响「实现者照抄代码范式」的可执行性，且第 1 轮已将此类锚点漂移定为可接受。本轮未发现新增 major/blocker。

## 八、合理扩展（无需修改）

| 位置 | 扩展 | 为何合理 |
| --- | --- | --- |
| plan-01 | TradingCalendarRepository 只读查询方法（get_record/get_trading_days/get_recent_open_days/has_any_open_day） | 服务 AC-09/06 服务端交易日轴；架构 §4.2 已指 repository 为日历唯一入口 |
| plan-03 | `close_cache` 跨日缓存参数、`MAX_CLOSE_LOOKBACK_REQUESTS` 预算常量 | 落地 ADR-3 有界回溯与 §8.4 预算 |
| plan-04 | `TaskFenceRegistry` 进程级注册表 | 让 handler 不改三参签名即取 fence context，服务 AC-02/07 |
| plan-07 | `MetricKey` 类型 | 服务 AC-04 指标切换 UI 状态 |
| README §2.5 | 测试目录/迁移路径相对架构 §9 的偏差修正 | 以代码约定（jest testMatch、flat test_data_init.py）为准，正确 brownfield 修正 |
| plan-04 §5 | TaskDetailResponse/TaskResponse 增加 `result: Optional[dict]` | 必需——task 详情端点 `TaskDetailResponse(**task_dict)` 依赖该字段，否则 result 键被 Pydantic 丢弃 |

## 九、复审方法说明

本轮为独立上下文第 2 轮复审。除常规 17 维度外，按 dev-plan-check SKILL「修复彻底性验证」要求，对第 1 轮 4 项修复涉及的所有标识符（`critical_path` 6 节点链、`apiClient.get` 泛型写法、`as unknown as` cast、`tradeDate/successCount/dateResults/unprocessedDates` 等 result 键、`pattern=`、`RECORDS_SWR_KEY` 行号）在 README + 全部 plan + 交接上下文做了 grep 全量核查，确认「应改处全改、应留处未误伤」。并对修复是否引入新不一致做了专项排查（plan-07 泛型与 ApiResponse\<T\> z.infer 交叠、result 序列化路径、三方契约措辞），均无新问题。
