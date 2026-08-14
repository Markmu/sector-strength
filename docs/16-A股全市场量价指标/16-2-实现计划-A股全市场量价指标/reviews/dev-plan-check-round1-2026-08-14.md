# 开发计划检查报告（第 1 轮）

- 检查日期：2026-08-14
- 架构文档：`docs/16-A股全市场量价指标/16-1-架构文档-A股全市场量价指标.md`
- 实现计划：`docs/16-A股全市场量价指标/16-2-实现计划-A股全市场量价指标/`（README + plan-01~plan-08，共 9 文件）
- 检查依据：`.zcode/skills/dev-plan-check/SKILL.md` + `.claude/contracts/workflow-schema.json`
- 代码核对方式：读取真实后端/前端代码逐项验证（路由挂载链、API 客户端解包层级、模型/迁移 head、测试基建）

## 一、总结论：FAIL

存在 **0 个 blocker** 与 **3 个 major** 问题。按 dev-plan-check 通过标准（无 blocker 且维度 17 四件套代码级核对通过），3 个 major 中含前后端契约/类型撒谎（维度 17）与跨功能 result 契约不自洽，判定为 **FAIL**，需修复后复审。

| 严重度 | 数量 |
| --- | --- |
| blocker | 0 |
| major | 3 |
| minor | 3 |

## 二、问题清单

| # | 严重度 | 所在文件 | 问题描述 | 建议修复 |
| --- | --- | --- | --- | --- |
| 1 | major | README.md（frontmatter `critical_path`、§1 概览、§5 依赖图说明） | `critical_path: ["plan-01","plan-02","plan-03","plan-05","plan-08"]`（5 节点）**不是真实最长链**。按 DAG 计算：plan-07 依赖 plan-06，plan-08 依赖 plan-05 与 plan-07；最长路径为 `plan-01→02→03→06→07→08`（6 节点，经 plan-06/plan-07）。当前声明的链虽然边都存在，但被一条更长的链超越，违反「critical_path 为真实最长链」。注：`execution_order`（真正驱动执行序）正确，故不阻断执行，仅调度元数据错误。 | 将 `critical_path` 改为 `["plan-01","plan-02","plan-03","plan-06","plan-07","plan-08"]`；同步更新 §1 概览与 §5 依赖图说明中的「关键路径」文字。 |
| 2 | major | plan-07-首页市场量价面板.md（§2 API 客户端代码、§3 SWR 范式） | `marketMetricsApi.getTrend` 写成 `apiClient.get<MarketMetricsTrendData>(...)`，**违反仓库已文档化的 ApiClient+SWR 解包约定**（`web/src/lib/api.ts` L1106-1109 明示「泛型 T 必须写 `{ success: boolean; data: 业务对象 }`，否则 res.data 取值类型撒谎 + 运行时 undefined」；README §2.3 自己也写了同一约定）。ApiClient.request 返回 `{ data: 完整响应体 }`，故 `res.data` 实际是 `{success,data}` 而非业务对象——当前泛型把业务对象类型直接套到 `res.data` 上，类型撒谎。继而 §3 的 `.then(res => res.data as { success: boolean; data: MarketMetricsTrendData })`：从 `MarketMetricsTrendData` 到 `{success,data}` 二者无结构重叠，TS `as` 会报「neither sufficiently overlaps」，**照抄将无法通过 `pnpm exec tsc --noEmit`**（plan-07 自己列为质量门）。同仓锚点 `IndexMonitorPage.tsx:42` 用的是 `res.data as unknown as {...}`。 | (a) §2 改为 `apiClient.get<{ success: boolean; data: MarketMetricsTrendData }>(...)`（与 indexMonitorApi/etfMonitorApi/sectorFundFlowApi 一致）；(b) §3 cast 改为 `as unknown as { success: boolean; data: MarketMetricsTrendData }`（对齐 IndexMonitorPage:42）。§交接上下文描述已正确，仅需让代码样本与描述一致。 |
| 3 | major | plan-08-数据管理市场量价同步面板.md（§1 类型与 Hook、交接上下文）↔ plan-05（§2 Task 列表 step 5/6）↔ plan-04（§1 to_dict） | 跨功能 `AsyncTask.result` 键风格契约**不自洽**：plan-05 §2 step5 明确写入 `{tradeDate,status,expected,daily,suspended,final,reason?}`（camelCase），plan-04 §1 `to_dict()` 对 result「原样透传 dict（不经 _dict_to_camel）」，因此前端应直接按 camelCase 消费、**无需转换**；但 plan-08 §1 写「后端 result JSON 以 snake_case 写入时**须在消费层做一次键转换**」，交接上下文又对冲「若以 snake_case 存储…以 plan-05 实际写入格式为准」。三方口径冲突，把决策推迟到实现期，存在真实风险：若 plan-08 按「须转换」实现而 plan-05 写 camelCase，或 plan-05 按自然 Python 写 snake_case，均会导致 `tradeDate`/`dateResults` 等键取到 undefined。 | 统一锁定为单一口径（推荐 camelCase，与架构 §7.2 TS 接口、plan-05 §2 描述一致）：plan-08 删除「须做键转换」与对冲措辞，明确「result 为 camelCase、直接消费、无转换」；并在 plan-05 §2 显式声明 handler 写入 result 的键全部 camelCase（与 to_dict 透传一致）。 |
| 4 | minor | plan-03 §交接上下文 / plan-08 §交接上下文（行号锚点） | 个别行号锚点轻微漂移：plan-03 引用 `_cleanup_disappeared_stocks L576-581`（实际 def 在 `data_init.py:616`、调用在 `:578`）；plan-08 引用 `RECORDS_SWR_KEY L53`（实际 `IndexSyncPanel.tsx:65`）；plan-06/README 引用 `index_monitor.py:55-80` 的 helper（实际 `_serialize_value/_dict_to_camel` 在 ~`:80-110`）。函数/常量均存在，仅行号偏移。 | 锚点改为「方法/常量名」为主、行号为辅，或按实测刷新行号。非阻断。 |
| 5 | minor | plan-06 §1 Query 签名 | `Query(30, description=..., regex="^(30|90|250)$")` 使用已弃用的 `regex` 形参（Pydantic v2 / 新版 FastAPI 推荐 `pattern`）；现仓 `src/api/v1/*` 路由未使用 regex/pattern，属新引入模式。 | 改用 `pattern="^(30|90|250)$"`（或 `Annotated[Literal[30,90,250], Query(30)]`），与新版栈一致。非阻断。 |
| 6 | minor | plan-01/plan-04 文件清单迁移文件名 | 迁移文件名含 `<rev12>` 占位（如 `2026_08_14_0001-<rev12>_add_market_metrics_and_calendar.py`）。非 `{{placeholder}}` 模板空缺，且文中已注明「revision 自生成 12 位 hex」，可接受；仅为提示。 | 保持现状即可；实现时以 `alembic revision`/手写生成的真实 revision 替换。 |

## 三、逐项核查结论（a–i）

### a. 结构与字段合法性 — 通过

- README frontmatter：`workflow_type: create-dev-plan` ✓、`status: review_ready`（属 `readme_frontmatter_status`）✓、`org_mode: feature` ✓、`source_architecture` ✓、`project_type: brownfield` ✓、`total_tasks: 8` = 8 个 plan 文件 ✓；`execution_order` 引用均为真实 plan-XX ✓。
- README 必备章节（contract `feature_readme_required_sections` 10 项：概览/输入摘要/验收标准追踪矩阵/模块地图/依赖图/阶段摘要/任务总览/未决策项/执行前置/变更记录）全部齐全 ✓。
- 验收标准追踪矩阵表头固定为 `AC-ID | 需求原文 | 架构承接 | 计划承接 | 验证方式 | 当前状态` ✓。
- 8 个 plan 文件 frontmatter：`feat_id` 与文件名一致 ✓；`dimension` ∈ {backend, frontend, mixed} ✓；`phase` ∈ {1,2,3} ✓；`status: ready-to-dev` ∈ `task_file_status` ✓；`depends_on` 引用真实 ✓。
- 每个 plan 8 章节（功能概要/文件清单/实现规格/Task 列表/验收标准/验证命令/交接上下文/风险与边界）齐全 ✓。
- 功能概要 7 必填字段（目标/完成后可观察结果/依赖/关联验收标准/涉及架构模块/前置条件/不在范围）逐文件齐全 ✓。
- 无 `{{placeholder}}` 模板空缺（`<rev12>` 为已声明的自生成 revision，见 minor #6）✓。

### b. AC 追踪 — 通过

- 架构 §2.5 的 AC-01~AC-13（共 13 条）在 README 追踪矩阵**全部出现，无遗漏** ✓。
- README「计划承接」与各 plan「关联验收标准」**双向一致**（逐条核验 AC-01~13 两方向闭合，无孤立 AC、无 plan 侧自造 AC）✓。
- 「验证方式」均指向具体 FEAT 章节（如「plan-05 §5 执行验证」），可追溯 ✓。

### c. DAG — 部分不通过（major #1）

- `depends_on` 引用全部存在 ✓；无循环 ✓；`phase` 与依赖深度相容 ✓；`execution_order` 分组与 `depends_on` 不矛盾 ✓。
- 组内并行声明经核为真：plan-03/04 文件不相交（plan-03: market_metrics_service/data_init；plan-04: task_fence/task_manager/task_executor）✓；plan-05/06 文件不相交（plan-05: task_handlers/init_market_metrics/admin.__init__/collector/job_manager；plan-06: api/v1/market_metrics/v1.__init__）✓。
- **critical_path 非真实最长链**（major #1）：声明 5 节点链，实际最长为 6 节点链 `plan-01→02→03→06→07→08`。

### d. 文件清单 — 通过

- 所有 `modify` 路径真实存在（已逐一核验：`models/__init__.py`、`data_acquisition/{models,base,tushare_client}.py`、`data_init.py`、`tests/test_data_init.py`、`async_task.py`、`task_manager.py`、`task_executor.py`、`api/admin/{__init__,tasks}.py`、`task_handlers.py`、`collector.py`、`scheduler/job_manager.py`、`tests/test_data_updater.py`、`api/v1/__init__.py`、`web/src/lib/api.ts`、`IndexMonitorPage.tsx`、`app/dashboard/page.tsx`、`useTaskStatus.ts`、`app/dashboard/admin/data/page.tsx`）✓。
- `create` 路径无重复声明；plan-07 创建 `marketMetricsTypes.ts`、plan-08 modify 同文件——因 plan-08 depends_on plan-07 且 README 标注「同文件顺序编辑，串行」，无冲突 ✓。
- 测试路径符合收集规则：pytest `testpaths=tests`、`python_files=test_*.py`（递归收集，`tests/services/`、`tests/api/`、新建 `tests/api/admin/` 均被收集）✓；jest `testMatch` 只收 `<rootDir>/tests/**`（故计划把组件测试放 `web/tests/market-metrics/`、E2E spec 放 `web/tests/e2e/` 正确，且 jest `testPathIgnorePatterns` 排除 `tests/e2e/`，Playwright `testDir='./tests/e2e'`、baseURL 3100）✓。README §2.5 对架构 §9 测试目录偏差的修正（`__tests__/`→`tests/market-metrics/`）正确 ✓。

### e. 前后端契约（四件套 + 解包层级 + snake/camel） — 部分不通过（major #2）

代码级核对结论：

- **路径拼接**：plan-06/07 GET `/market-metrics/trend?range=30` × `apiClient.baseURL=${API_BASE_URL}/api/v1` = `/api/v1/market-metrics/trend?range=30`（无双前缀）✓；plan-08 POST `/admin/init/market-metrics` × `adminApiClient.baseURL=${API_BASE_URL}/api/v1` = `/api/v1/admin/init/market-metrics`（与后端 `admin_router prefix=/v1/admin` + 子路由 `prefix=/init` + main.py `prefix=/api` 一致）✓；plan-08 记录区 `fetcher('/api/v1/admin/tasks?task_types=...')`（fetcher 的 `API_BASE=NEXT_PUBLIC_API_URL` 不含 /api，故不双前缀，与 IndexSyncPanel 的 `RECORDS_SWR_KEY` 同款）✓。
- **HTTP 方法存在性与鉴权**：GET 在 `ApiClient` 有定义且经 `getAuthHeaders()`（api.ts:45-57）带 Authorization ✓；POST 在 `AdminApiClient` 有定义且带鉴权（并对 `/admin/` 无 token 告警）✓；后端 `@router.get("/trend")`/`POST /market-metrics` 三方一致 ✓。
- **query 命名**：`range` 单词无 snake/camel 歧义；`task_types/page/page_size` 保持 snake_case（与既有 `listTasks` 一致）✓；body `{start_date,end_date}` snake_case（与 Pydantic payload 一致）✓。
- **响应字段命名**：plan-06 经 `_dict_to_camel` 输出 camelCase、Decimal→float、date→ISO，与 plan-07 前端类型逐字段一致 ✓；plan-08 `initMarketMetrics` 取 `{task_id}` snake_case（与 `initIndexHistory` 等同款）✓。
- **解包层级**：ApiClient 返回 `{data:完整响应体}`（需 `res.data`={success,data} 再取 `.data`），AdminApiClient 返回 `{data:json.data}`（解一层）。plan-07 §交接上下文与 §3 的**文字描述正确**（res.data={success,data} 再 .data），但 §2 代码泛型写错（major #2）；plan-08 adminApi 解一层正确 ✓。
- **snake/camel 口径**：query/body snake_case、响应业务字段 camelCase，与架构 §7.3/§7.6 一致 ✓。

### f. 验证命令可执行性 — 通过

- pytest：`cd server && source .venv/bin/activate`（`server/.venv` 真实存在 ✓）；单文件命令均带 `--no-cov`（规避 `pytest.ini` 全局 `--cov-fail-under=80`）✓；README §9.3 全量 `pytest tests/ -v` 不带 `--no-cov` 故 80% 门槛生效（有意）✓。
- 迁移链：实测 `alembic heads` 返回**单一 head `7e3309ce89da`**（文件 `2026_08_13_2234-7e3309ce89da_add_index_basic_sort_order.py`，down_revision=`f92bfffc49c3`）。plan-01 `down_revision='7e3309ce89da'` 正确 ✓；plan-04 迁移 down_revision 指向 plan-01 迁移 revision（相对引用，时序成立）✓。
- pnpm：`web/package.json` 无 `type-check` 脚本——计划**未**误用 `pnpm type-check`，而是直接 `pnpm exec tsc --noEmit`（tsc 经 typescript 依赖可用）、`pnpm build`、`pnpm test`(=jest)、`pnpm test:e2e`(=playwright test)，脚本名均真实存在 ✓。
- Playwright `testDir='./tests/e2e'`、baseURL 3100 与计划 E2E 命令一致 ✓。

### g. 内容质量 — 通过

- **task handler 执行验证**：plan-05 §验收「AC-02（执行验证，task handler 不豁免）触发任务 → 等待 completed → 查询 market_daily_metrics」+ §验证命令 #2 提供触发脚本与查库脚本（触发→等待→查库闭环）✓。
- **E2E-TDD red/green**：plan-07 Task7「先 red 后实现」、§验收「red 证据与 green 证据齐备，存 docs/e2e/evidence/plan-07-e2e-{red|green}-{date}.md」；plan-08 Task8 与 §验收同款 red/green 路径 ✓；`docs/e2e/` 目录存在 ✓。
- **NFR 注入**：§8.1 性能 → plan-02（0.3s 节流/2 页）、plan-05（逐日提交/进度单调）、plan-06（P95≤500ms/零 Provider）、plan-07（单 ECharts 实例）各有「性能验收」段并标注来源 ✓；§8.2 降级 → plan-07「降级回归验收」、plan-06 latest 取最近成功日 ✓；§8.5 可观测性 → plan-03/05/06 结构化日志字段、plan-04 owner lock 获取/丢失/fencing 拒绝日志，均带「可观测性注」✓。
- **边界场景状态合法**：所有 plan 的边界场景表状态均用 `todo`，无非法枚举 ✓；无 `waived` 滥用 ✓。

### h. 跨文件一致性 — 部分不通过（major #3，其余通过）

- **plan-03 TaskFenceContext 前向引用 ↔ plan-04 task_fence.py 交付时序**：成立。plan-03 用 `from __future__ import annotations` + `TYPE_CHECKING` 前向引用，运行时不导入 `task_fence`；真正构造/fence 在 plan-05（depends_on plan-04）落地。plan-03 depends_on=[plan-01,plan-02] 虽不含 plan-04，但因运行时不导入、且 sync_date 的 task_context 仅由 plan-05 传入真实实例，依赖被传递满足 ✓。
- **plan-04 迁移 down_revision ↔ plan-01 迁移衔接**：plan-04 depends_on=[plan-01]，其迁移 down_revision 显式指向 plan-01 迁移 revision，时序成立 ✓。
- **plan-05 ↔ plan-06 文件不相交（README 声称可并行）**：经核两功能 modify/create 文件集无交集，并行安全 ✓。
- **plan-08 消费 plan-05 result 键风格约定**：**不自洽**（major #3）。

### i. 与架构一致性 — 通过

- **无自造 AC**：各 plan 验收标准均回溯架构 AC-XX；新增的 Repository 只读方法、`MetricKey`、`close_cache`、`TaskFenceRegistry` 等均以「实现级补充项，非新造 AC」显式标注 ✓。
- **无遗漏架构模块**：架构 §4.2 六模块（采集与日历 / 汇总服务 / 任务入口与编排 / 查询 API / 首页面板 / 同步面板）分别由 plan-01~08 全覆盖，模块地图（README §4）一一对应 ✓。
- **未违背「明确不做」清单**：架构 §2.3 明确不做项（盘中/分钟、分交易所对比、加权均价、行业聚合、信号告警、原始快照表、改写 qfq `stock_daily_market_data`、Redis/MQ/worker、`ah_vol/amount` 叠加）在各 plan 中均被遵守——plan-02/03 显式禁用逐股 qfq `get_daily_data`、禁止 N+1、停牌补价只读未复权 daily、GET 零 Provider、无新中间件 ✓。

## 四、合理扩展（无需修改）

| 位置 | 扩展 | 为何合理 |
| --- | --- | --- |
| plan-01 | TradingCalendarRepository 只读查询方法（get_record/get_trading_days/get_recent_open_days/has_any_open_day） | 服务于 AC-09/AC-06 的服务端交易日轴，非新能力；架构 §4.2 已指 repository 为日历唯一入口 |
| plan-03 | `close_cache` 跨日缓存参数、`MAX_CLOSE_LOOKBACK_REQUESTS` 预算常量 | 落地 ADR-3 有界回溯与 §8.4 预算，非新增需求 |
| plan-04 | `TaskFenceRegistry` 进程级注册表 | 让 handler 不改三参签名即可取 executor 构造好的 fence context，服务于 AC-02/07 |
| plan-07 | `MetricKey` 类型 | 服务于 AC-04 指标切换 UI 状态 |
| README §2.5 | 测试目录与迁移文件路径相对架构 §9 的偏差修正 | 以代码约定（jest testMatch、flat test_data_init.py）为准，属正确 brownfield 修正 |

## 五、修复优先级建议

1. **major #3（result 键风格）**：跨功能契约歧义，运行时风险最高，优先统一为 camelCase 直消费。
2. **major #2（plan-07 类型撒谎）**：影响自身 `pnpm exec tsc --noEmit` 质量门，按 indexMonitorApi 范式对齐泛型与 cast。
3. **major #1（critical_path）**：调度元数据失真，更新为 6 节点最长链。
4. minor #4/#5/#6：复审时顺手修正。

修复后建议派独立上下文 subagent 复审一轮（dev-plan-check SKILL「同质化盲区」提示），重点 grep 验证 `tradeDate`/`successCount`/`dateResults` 在 plan-04/05/08 与 README 的全部出现口径一致，以及 plan-07 `apiClient.get` 泛型写法是否全仓对齐。
