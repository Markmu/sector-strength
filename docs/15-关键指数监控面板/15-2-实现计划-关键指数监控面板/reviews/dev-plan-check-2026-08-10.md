# 开发计划检查报告

> 检查日期：2026-08-10
> 检查依据：`dev-plan-check` skill + `workflow-schema.json` contract
> 检查者：dev-plan-check subagent

## 一、检查对象

- **架构文档**：`/Users/muchao/code/sector-strength/docs/15-关键指数监控面板/15-1-架构文档-关键指数监控面板.md`（workflow_type=arch-gen, status=review_ready）
- **实现计划**：`/Users/muchao/code/sector-strength/docs/15-关键指数监控面板/15-2-实现计划-关键指数监控面板/`
- **功能数**：4（plan-01 ~ plan-04）
- **项目类型**：Brownfield（在已有板块强度分析平台上扩展指数监控能力）

## 二、总评

- **结论**：**需补充**（有 1 个 blocker + 多个建议项；无重大架构漂移，但 plan-02 任务执行机制描述与现有代码范式偏差较大，实现者照抄会踩坑）
- **阻塞问题数**：1
- **建议项数**：9
- **核心判断**：实现计划在功能拆分、AC 追踪、依赖 DAG、前后端契约上整体对齐架构文档；主要问题集中在 plan-02 对异步任务执行机制的描述与现有 `TaskManager + TaskRegistry + @TaskRegistry.register` 范式不一致，以及部分复用细节缺失。

## 三、Contract 预检

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| README frontmatter `workflow_type: create-dev-plan` | ✅ 通过 | 第 2 行 |
| README frontmatter `org_mode: feature` | ✅ 通过 | 第 6 行 |
| README frontmatter `status` 合法 | ✅ 通过 | `review_ready`（在 `plan.readme_frontmatter_status` 白名单） |
| README `execution_order` 引用真实存在 | ✅ 通过 | `[["plan-01", "plan-02"], ["plan-03", "plan-04"]]`，与 plan-01~04 文件一一对应 |
| README `total_tasks` 与 plan-*.md 数量一致 | ✅ 通过 | `total_tasks: 4` / `total_task_files: 4`，目录有 4 个 plan-*.md |
| README 包含 `feature_readme_required_sections` 全部 10 项 | ✅ 通过 | 概览/输入摘要/验收标准追踪矩阵/模块地图/依赖图/阶段摘要/任务总览/未决策项/执行前置/变更记录 齐全 |
| README 追踪矩阵表头固定 | ✅ 通过 | `AC-ID / 需求原文 / 架构承接 / 计划承接 / 验证方式 / 当前状态` |
| FEAT 文件名 `plan-XX` 与 `feat_id` 一致 | ✅ 通过 | 4 个文件均通过 |
| FEAT `status` 合法 | ✅ 通过 | 全部 `draft`（在 `plan.task_file_status`） |
| FEAT 正文包含 `feature_task_required_sections` 全部 8 项 | ✅ 通过 | 功能概要/文件清单/实现规格/Task 列表/验收标准/验证命令/交接上下文/风险与边界 4 个文件均齐 |
| Task 与边界场景状态合法 | ✅ 通过 | 全部 `todo`（合法值） |
| `depends_on` 引用真实存在的功能 | ✅ 通过 | plan-02→[plan-01]、plan-03→[plan-02]、plan-04→[plan-03]、plan-04 前置条件还含 plan-02（一致） |

## 四、验收标准追踪

架构文档 §2.4 共 16 条 AC（AC-01~AC-13，含 AC-08a/b/c/d）。

| AC-ID | 架构要求 | README 承接 | FEAT 承接 | 结论 |
| --- | --- | --- | --- | --- |
| AC-01 | 主页指数总览展示 | plan-03, plan-04 | plan-03 §验收(AC-01)、plan-04 §总览验收 | ✅ 双向覆盖 |
| AC-02 | 多指数走势对比 | plan-03, plan-04 | plan-03 §走势验收、plan-04 §走势验收 | ✅ 双向覆盖 |
| AC-03 | 估值水位与分位 | plan-03, plan-04 | plan-03 §估值验收、plan-04 §估值验收 | ✅ 双向覆盖（含 hasData=false 异常分支） |
| AC-04 | 成分权重展示 | plan-03, plan-04 | plan-03 §权重验收、plan-04 §权重验收 | ✅ 双向覆盖 |
| AC-05 | ETF 资金跳转 | plan-04 | plan-04 §ETF 跳转验收 + Task #7/#15 | ✅ 覆盖（含 useSearchParams 改造） |
| AC-06 | 成分股跳转个股 | plan-04 | plan-04 §权重验收（AC-06 行）+ Task #10 | ✅ 覆盖 |
| AC-07 | 关注指数管理 | plan-03, plan-04 | plan-03 §关注清单验收、plan-04 §关注管理验收 | ✅ 双向覆盖 |
| AC-08 | 数据空状态 | plan-04 | plan-04 §总览验收(AC-08) | ✅ 覆盖 |
| AC-08a | 指数清单同步 | plan-02 | plan-02 §清单同步验收（AC-08a）5 条 | ✅ 覆盖（含 is_watched 不被覆盖校验） |
| AC-08b | 历史数据回填 | plan-02 | plan-02 §回填验收（AC-08b）5 条 | ✅ 覆盖 |
| AC-08c | 同步互斥与进度 | plan-02, plan-04 | plan-02（task_type 注册）、plan-04 §同步验收(AC-08c) | ✅ 覆盖 |
| AC-08d | 同步失败与恢复 | plan-02, plan-04 | plan-04 §同步验收(AC-08d) | ⚠️ plan-02 未显式列 AC-08d 验收项（重试链路依赖 AsyncTask，plan-02 主要承接 task 创建侧） |
| AC-09 | 真实数据验证 | plan-02, plan-04 | plan-01 §AC-09、plan-02 §数据真实性、plan-04 §全流程 | ✅ 三段覆盖 |
| AC-10 | 每日自动更新 | plan-04 | plan-04 §日更验收(AC-10) + Task #1 | ✅ 覆盖（含 `index_daily_updated` 计数键） |
| AC-11 | 非管理员不可见 | plan-04 | plan-04 §权限验收(AC-11) + Task #12 | ✅ 覆盖 |
| AC-12 | 当日未更新降级 | plan-03, plan-04 | plan-03 §总览验收(AC-12)、plan-04 §降级验收 | ✅ 双向覆盖 |
| AC-13 | 个别指数失败隔离 | plan-04 | plan-04 §总览验收(AC-13) | ✅ 覆盖 |

**追踪矩阵完整性：16/16 AC 全部映射**，FEAT 关联验收标准与 README 一致，无孤立验收项。

## 五、维度检查结果

| 维度 | 结论 | 问题数 | 摘要 |
| --- | --- | --- | --- |
| 1 核心闭环与系统目标 | ✅ 通过 | 0 | 核心闭环"采集→入库→查询→展示"出现在 README §2.1；首版目标被 FEAT 验收覆盖 |
| 2 范围与非目标 | ✅ 通过 | 0 | P0 七项范围被 plan-01~04 全部承接；ADR 非目标（独立路由页/watchlist 表/Redis）在实现规格中未引入 |
| 3 成功标准 | ✅ 通过 | 0 | 性能目标（/overview≤2s 等）在 plan-01/03 性能验收逐条映射；估值覆盖 6/14 在 AC-03 验收项体现 |
| 4 验收标准防漂移 | ✅ 通过 | 0 | 16 条 AC 全覆盖；AC-08d 在 plan-02 未列项为轻微 gap（见问题清单 #5） |
| 5 ADR 约束 | ✅ 通过 | 0 | 5 条 ADR 在 README §2.2 护栏表 + 各 FEAT 实现规格呼应；ADR-2 is_watched 字段在 plan-02 边界场景明确"upsert 不覆盖 is_watched" |
| 6 用户流程与状态机 | ✅ 通过 | 0 | 主流程 §3.1 节点均被 FEAT 覆盖；6 个关键分支（数据未初始化/当日未更新/个别失败/无估值/同步中/同步失败）在 FEAT 边界场景表覆盖 |
| 7 模块职责与系统上下文 | ✅ 通过 | 0 | 7 个模块在 README §4 模块地图对应功能承接；上下游关系在 depends_on + 交接上下文体现；过度设计避免项未引入 |
| 8 运行链路 | ⚠️ 需补充 | 1 | §6.1~6.4 链路步骤在 FEAT 落地，但 plan-02 §6.1 描述"BackgroundTasks 异步执行 IndexDataInitService.sync_index_basic()"与现有 TaskRegistry 范式不一致（见问题 #1） |
| 9 数据模型与契约 | ✅ 通过 | 0 | 4 张表 Schema 在 plan-01 实现规格逐字段列出；6 类 API 响应 camelCase 输出在 plan-03/plan-04 一致；成交额÷10000 转亿元在 plan-03 Task 2 + plan-04 helpers 标注；序列化（Decimal→float、date→isoformat）在 plan-03 §响应格式验收显式 |
| 10 非功能需求 | ✅ 通过 | 0 | 性能 §8.1 在 plan-01/03 验收；降级 §8.2 L1~L5 在 plan-04 边界场景覆盖；安全 §8.3（require_admin/get_current_user 双重校验）在 plan-02/03 实现规格；可观测性 §8.5（logger.info/warning）在 plan-01/02/03 均有 |
| 11 实施建议与技术选型 | ✅ 通过 | 0 | Phase A/B/C 划分与 plan 阶段一致；技术栈与架构 §9 一致 |
| 12 风险与未决策项 | ✅ 通过 | 0 | 架构 §8.6 风险在 plan-02 边界场景（upsert 覆盖 is_watched / 历史回填失败 / 权重月度缓存）有缓解；open_questions 为空，README §8 一致 |
| 13 功能拆分质量 | ✅ 通过 | 0 | 4 个 FEAT 均为连贯能力；plan-04 Task 16 步略超 12 步建议但属集成功能合理；DAG 无循环（链式） |
| 14 可执行性 | ⚠️ 需补充 | 2 | 文件清单路径具体；但 plan-02 task 执行机制描述误导（#1）；plan-04 响应解包层级确认在风险区有提示但实现规格未统一（#6） |
| 15 状态与报告契约 | ✅ 通过 | 0 | README/FEAT 状态合法；本报告按 contract 写入 `reviews/dev-plan-check-{date}.md` |
| 16 复用声明链路验证 | ⚠️ 需补充 | 2 | DataSourceFactory.create() / EtfDataInitService 范式 / etf_monitor.py helper / useTaskStatus 在 plan-02/03/04 有调用描述；但 `useTaskStatus` Hook 的具体 import 路径和返回结构在 plan-04 §12 有代码示例（OK）；TaskType 枚举注册位置（task_handlers.py）和 @TaskRegistry.register 装饰器范式在 plan-02 未写清（见 #1、#2） |
| 17 前后端 API 契约一致性（代码级） | ✅ 通过 | 0 | 4 类盲区逐项核对：(1) 路径前缀：endpoint `/index-monitor/overview` × baseURL `${API}/api/v1` = `/api/v1/index-monitor/overview` ✓（api.ts:9,37 + router.py:29 + v1/__init__.py:29）；(2) HTTP 方法：apiClient 有 get/post/put/delete（api.ts:119-136），后端 6 个 GET + 1 PUT + 3 POST 一致；(3) query 参数：前端 `ts_codes`/`start_date`/`ts_code`/`index_code`/`top_n` snake_case 与后端 Query 定义一致 ✓；(4) response 字段：camelCase 经 `_dict_to_camel` 转换，前端 IndexOverviewItem.ts 类型 `tsCode/pctChg/peTtm` 与后端输出一致 ✓。响应包裹 `{success,data}` 与前端解包层级（apiClient.request 返回 `{data: body}`，组件读 `res.data.data`）在 plan-04 §风险与边界"响应解包确认"有显式提示 ✓ |

## 六、问题清单

| 严重级别 | 位置 | 问题 | 修补建议 |
| --- | --- | --- | --- |
| 🔴 Blocker | plan-02 §实现规格 #2「Admin 同步路由」+ §复用声明调用细节 | **任务执行机制描述与现有代码范式不一致**。plan-02 写「创建 AsyncTask（task_type=...），BackgroundTasks 异步执行 IndexDataInitService.sync_index_basic()」。但现有 ETF admin 路由（`init_etf_daily.py:65-75`、`init_etf_history.py:113`、`init_etf_basic.py:65`）使用 `TaskManager(session).create_task(task_type=TaskType.X.value, params=...)` 创建任务，实际执行由任务 worker 拾取并通过 `@TaskRegistry.register(TaskType.X)` 装饰器（`task_handlers.py:1257`）注册的 handler 函数执行，handler 签名是 `(task_id, params, manager)`，在 handler 内部才调用 `IndexDataInitService`。plan-02 描述的「BackgroundTasks 直接执行 service」会让实现者写错执行入口。 | 在 plan-02 §实现规格 #2 改写为：① 在 `task_handlers.py` 的 `TaskType` 枚举加 `SYNC_INDEX_BASIC="sync_index_basic"` / `BACKFILL_INDEX_HISTORY="backfill_index_history"` / `SYNC_INDEX_DAILY="sync_index_daily"` 三个成员（与现有 `SYNC_ETF_DAILY="sync_etf_daily"` 同格式，**注意值是小写 snake_case，不是大写**）；② 在 `task_handlers.py` 新增 3 个 `@TaskRegistry.register(TaskType.X)` 装饰的 handler 函数，签名 `(task_id, params, manager)`，内部 `from src.services.data_init_index import IndexDataInitService` 后调用对应方法；③ admin 路由用 `TaskManager(session).create_task(task_type=TaskType.X.value, params={}, max_retries=3, timeout_seconds=3600, created_by=admin.id)` 创建任务（照抄 `init_etf_daily.py:64-75`）；④ 删除「BackgroundTasks 异步执行」措辞。同时 plan-04 §IndexSyncPanel 的 useTaskStatus 调用细节是 OK 的，但需确认轮询的 task 状态字段（status/progress/errorMessage）与 AsyncTask 模型一致。 |
| 🟡 建议 | plan-02 §实现规格 #2「task_type 后端注册」 | 描述「确认后端 AsyncTask 的 TaskType 枚举注册了...」不够精确。TaskType 枚举在 `server/src/services/task_handlers.py:27`（不在 AsyncTask 模型中）；handler 注册用 `@TaskRegistry.register` 装饰器（`task_handlers.py:105+`）。建议写清两个具体位置。 | 改写为：「在 `server/src/services/task_handlers.py` 的 `TaskType` 枚举（L27-69 范围）加三个成员；在文件末尾新增三个 `@TaskRegistry.register(TaskType.X)` 装饰的 async handler 函数，参考 `sync_etf_daily_task`（L1257-1294）范式」。 |
| 🟡 建议 | plan-02 §实现规格 #1「IndexDataInitService」+ §复用声明 | **构造函数与 handler 集成方式未写清**。plan-02 给出 `__init__(self, session)` + `set_session/set_progress_callback/set_cancel_check`，但未说明 handler 内如何把 manager 的进度回调桥接到 service 的 `_progress_callback`。现有 `sync_etf_daily_task` 是通过 `manager.update_progress(task_id, cur, total)` 上报，而 service 期望 `set_progress_callback(cb)`。 | 在 plan-02 §实现规格 #1 补充 handler 内的桥接代码示例：`service.set_progress_callback(lambda cur, total, msg: await manager.update_progress(task_id, cur, total))`（或参照 `sync_etf_daily_task` 的 `manager.log_message` + `manager.update_progress` 调用范式）。 |
| 🟡 建议 | plan-02 §实现规格 #2「Admin 同步路由」 | **并发保护（互斥）未在后端实现规格体现**。AC-08c 要求"互斥在前端 + 后端 max_instances=1 双重保障"。现有 `init_etf_daily.py:48-62` 有并发保护（查询同 task_type 的 pending/running 任务，存在则返回 success=false）。plan-02 未写此后端互斥逻辑。 | 在 plan-02 §实现规格 #2 的 3 个 POST 端点描述中加：「并发保护：照抄 `init_etf_daily.py:48-62`，查询同 task_type 的 pending/running AsyncTask，存在则返回 `{success: false, message: "已有任务运行中"}`」。 |
| 🟡 建议 | plan-02 §验收标准 | **AC-08d（同步失败与恢复）在 plan-02 未列验收项**。架构 AC-08d 的后端侧（AsyncTask 重试 + 已成功保留 + 重试从失败点继续）依赖 plan-02 的 task 机制，但 plan-02 验收清单只列了 AC-08a/08b/09。 | 在 plan-02 §验收标准新增「AC-08d 失败恢复验收」小节：任务失败后 status=failed、已 upsert 的数据保留（幂等）、重试创建新 task 从失败点继续。 |
| 🟡 建议 | plan-04 §实现规格 #5「helpers.ts」+ §风险与边界 | **成交额单位换算在 helpers 与后端输出关系描述有矛盾风险**。helpers.ts 的 `formatAmount` 写 `amount / 10000`（千元→亿元），但 plan-03 §实现规格 #2 明确「amount 后端 ÷10000 转亿元再输出」。plan-04 §5 末尾「序列化确认」注释了"后端已转亿元，helpers 不需再除"——但 helpers 代码仍写了 `/ 10000`。二者矛盾。 | 二选一：(a) 后端输出亿元（plan-03 现状），helpers 的 `formatAmount` 改为 `(amount).toFixed(2) + ' 亿'`（不再除）；(b) 后端输出千元，helpers 除 10000。建议选 (a) 与架构 §7.6「成交额：API 输出转亿元（÷10000）」一致。务必在 plan-03 和 plan-04 两处同步修正。 |
| 🟡 建议 | plan-04 §实现规格 #4「api.ts」+ §风险与边界「响应解包确认」 | **响应解包层级实现规格未统一**。plan-04 §风险区提示「apiClient.get 返回 response，外层 {success,data} 由 AdminApiClient 自动剥壳（adminApi），但 indexMonitorApi 走 apiClient 需确认解包层级」。经核实 `api.ts:111` 的 `ApiClient.request` 返回 `{ data: body }`（body 是后端 `{success,data}`），所以组件消费是 `res.data.data.indices`（两层 .data）。plan-04 实现规格 #7~#11 的 SWR 调用未写清解包层级，实现者易写错。 | 在 plan-04 §实现规格 #4 末尾或 §7 IndexMonitorPage 增加解包范式说明：「SWR fetcher 调 `indexMonitorApi.getOverview().then(res => res.data)`（解一层得到 `{success,data}`），组件再读 `data.data.indices`（解第二层）」。参照现有 `useEtfMonitor.ts` 的 `.then(res => res.data as ...)` 范式。建议为指数监控也新建 `web/src/hooks/useIndexMonitor.ts`（与 useEtfMonitor 对齐），而非在组件内直接 SWR。 |
| 🟡 建议 | plan-04 §实现规格 #6「主页改造」+ §风险与边界 | **is_admin 获取方式实现规格不够具体**。plan-04 §6 写 `import { useAuth } from '...'`（省略号），风险区写"暂停条件：is_admin 获取方式不明确时暂停确认"。经核实 `web/src/contexts/AuthContext.tsx:32` 导出 `useAuth()`，`AuthContext.tsx:27,252` 提供 `isAdmin: boolean`（基于 `user.role === 'admin'`）。 | 在 plan-04 §实现规格 #6 把 import 路径写清：`import { useAuth } from '@/contexts/AuthContext'` + `const { isAdmin } = useAuth()`。删除"暂停确认"措辞（已可确认）。 |
| 🟡 建议 | plan-04 §Task 列表 #14「补 TaskMonitorPanel 中文映射」 | **行号引用 L197-202 可能过时且不完整**。plan-04 §实现规格 #14 引用「TaskRow 的 JSX `&&` 链（L197-202）」。经核实 `TaskMonitorPanel.tsx:197-202` 确实存在该链，但当前链只有 init_sectors/init_stocks/init_historical_data/init_sector_stocks/backfill_by_date/backfill_by_range 6 项，**缺少 ETF 相关 task_type 的中文映射**（sync_etf_daily/sync_etf_basic/backfill_etf_history 均未映射）。这意味着 plan-04 补 3 个指数映射时，应顺便确认是否需要一并补 ETF 映射（或指数映射紧跟现有链末尾即可）。 | 在 plan-04 §实现规格 #14 补一句：「现有链未含 ETF task_type 映射（sync_etf_daily 等也未映射中文），本任务只在链末尾追加 3 个指数 task_type 映射，不动 ETF 部分；如需统一补齐 ETF 映射请单独立项」。避免实现者误以为现有链已含 ETF。 |
| 🟡 建议 | plan-01 §实现规格 #3「Alembic 迁移」+ 预置 SQL | **预置 14 只关注指数的执行时机描述分散**。plan-01 §3 末尾写「此 SQL 在 plan-02 的 sync_index_basic 完成后执行」，plan-02 §实现规格 #1「sync_index_basic」也写了「upsert 完成后执行预置 14 只 UPDATE」。两处重复且 plan-01 的 SQL 块（含具体 14 个 ts_code 列表）与 plan-02 的描述（「WHERE ts_code IN 预置清单」）不完全一致。建议以 plan-02 为唯一 SoT。 | 在 plan-01 §3 删除预置 SQL 块（或改为「详见 plan-02 §sync_index_basic 实现原则」），把 14 只 ts_code 列表移到 plan-02 §实现规格 #1 的 sync_index_basic 描述中作为唯一来源。 |

## 七、合理扩展

| 位置 | 扩展内容 | 为什么合理 |
| --- | --- | --- |
| plan-04 §验收标准「全流程验收（US 覆盖矩阵）」 | 引用 PRD 用户故事 US-01~US-08 并映射到 Task # + AC | 架构文档未显式列 US 矩阵，plan-04 补充有助于 E2E 场景设计；未违背架构 |
| plan-04 §实现规格 #13「data/page.tsx Tab 枚举」 | Tab 加 `'index-data'` 并加 `data-testid="tab-index-data"` | 架构 §9 步骤 23 只说「新增指数数据 Tab」，plan-04 补 testid 利于 E2E 选择器；合理扩展 |
| plan-02 §边界场景「权重月度缓存」 | 集合记录已拉取月份，同月不重复 | 架构 §6.2 实现原则已提及，plan-02 在边界场景显式列出，强化实现注意 |
| plan-03 §实现规格 #5「weights JOIN stocks」 | 明确 `IndexWeight.con_code == Stock.ts_code` 直接 JOIN（con_code 格式 600519.SH 与 stocks.ts_code 一致） | 架构 §7.2 只说「JOIN stock_basic 取 name」，plan-03 核实 Stock 模型有 ts_code（stock.py:20）和 name（stock.py:13）字段后写清 JOIN 条件；合理 |

## 八、建议补丁计划

按优先级列出应修改的 README 或 FEAT 章节：

### P0（Blocker，必须修复才能进入执行）

1. **plan-02 §实现规格 #2「Admin 同步路由」+ §复用声明调用细节**
   - 改写任务执行机制描述：删除「BackgroundTasks 异步执行 service」，改为「TaskManager.create_task + task_handlers.py 注册 @TaskRegistry.register handler」范式（照抄 init_etf_daily.py + sync_etf_daily_task）。
   - 同步更新 plan-02 §Task 列表 #5「注册 task_type 到后端枚举」说明：枚举在 `task_handlers.py:27`，值是小写 snake_case；handler 用装饰器注册。
   - 补 handler 内 service 进度回调桥接代码示例。

### P1（建议项，影响实现顺畅度）

2. **plan-02 §实现规格 #2**：补后端并发保护逻辑（照抄 init_etf_daily.py:48-62）。
3. **plan-02 §验收标准**：补 AC-08d 失败恢复验收小节。
4. **plan-03 §实现规格 #2 + plan-04 §实现规格 #5 helpers.ts**：统一成交额单位换算（建议后端输出亿元，helpers 不再除），两处同步修正。
5. **plan-04 §实现规格 #4 或 #7**：补响应解包层级范式（建议新建 useIndexMonitor.ts，对齐 useEtfMonitor）。
6. **plan-04 §实现规格 #6**：把 useAuth import 路径写清，删除"暂停确认"。

### P2（建议项，文档清晰度）

7. **plan-02 §实现规格 #2 task_type 注册描述**：写清 TaskType 枚举和 @TaskRegistry.register 两个具体位置。
8. **plan-04 §实现规格 #14 TaskMonitorPanel**：补说明现有链未含 ETF 映射。
9. **plan-01 §实现规格 #3 + plan-02 §实现规格 #1**：预置 14 只 SQL 以 plan-02 为唯一 SoT。

---

## 附：检查方法说明

- 架构文档与实现计划逐章节对照（维度 1-16）
- 代码级契约核对（维度 17）：读取了 `web/src/lib/api.ts`（ApiClient/AdminApiClient/baseURL/解包层级）、`server/src/api/v1/etf_monitor.py`（路由范式/helper/鉴权）、`server/src/api/admin/init_etf_daily.py`（TaskManager.create_task 范式）、`server/src/services/task_handlers.py`（TaskType 枚举 + @TaskRegistry.register）、`server/src/services/data_init_etf.py`（service 范式）、`server/src/services/data_acquisition/tushare_client.py`（get_sw_index_classify 锚点）、`server/src/services/data_updater/collector.py`（步骤 8 ETF + results 结构）、`server/src/api/router.py`（admin 挂载 /v1/admin）、`server/src/api/v1/__init__.py` + `admin/__init__.py`（路由注册）、`server/src/models/__init__.py`（模型注册位置）、`server/src/models/stock.py`（JOIN 可行性）、`web/src/contexts/AuthContext.tsx`（isAdmin 来源）、`web/src/hooks/useEtfMonitor.ts`（SWR 解包范式）、`web/src/components/admin/TaskMonitorPanel.tsx`（中文映射链）、`web/src/app/dashboard/admin/data/page.tsx`（Tab 结构）、`web/src/app/dashboard/page.tsx`（主页现状）
- 占位符扫描：仅 plan-01 文件名含 `<hex>`（alembic autogenerate 标准约定，可接受），无其他 TODO/TBD/待补充残留
