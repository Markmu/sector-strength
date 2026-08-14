# 开发计划检查报告（第 3 轮终检）

- 检查日期：2026-08-14
- 架构文档：`docs/16-A股全市场量价指标/16-1-架构文档-A股全市场量价指标.md`
- 实现计划：`docs/16-A股全市场量价指标/16-2-实现计划-A股全市场量价指标/`（README + plan-01~plan-08，共 9 文件）
- 检查依据：`.zcode/skills/dev-plan-check/SKILL.md` + `.claude/contracts/workflow-schema.json`
- 前序报告：`reviews/dev-plan-check-round1-2026-08-14.md`（FAIL：3 major + 3 minor）、`reviews/dev-plan-check-round2-2026-08-14.md`（PASS：4 trivial minor，其中 2 项已修复、2 项裁定为 checker 误报）
- 本轮性质：独立上下文第 3 轮终检（fresh-eyes 复核），目标为确认前两轮修复全部落位、误报裁定属实、且不再存在 blocker/major/minor
- 代码核对方式：本轮**独立重读**真实代码核验全部关键锚点（data_init.py / IndexSyncPanel.tsx / api.ts / IndexMonitorPage.tsx / main.py / router.py / v1\_\_init\_\_.py / index_monitor.py / task_executor.py / task_manager.py / tasks.py / collector.py / task_handlers.py / fetcher.ts / useTaskStatus.ts / data-page.tsx / pytest.ini / jest.config.ts / playwright.config.ts / package.json / alembic versions），未沿用前两轮结论

## 一、总结论：PASS（终检通过，未发现问题）

| 严重度 | 数量 |
| --- | --- |
| blocker | 0 |
| major | 0 |
| minor | 0 |

第 1 轮 3 个 major 与第 2 轮判定的 2 处 trivial 修复全部落位且彻底；第 2 轮另 2 处「问题」经本轮独立代码复核**确认为 checker 误报**（详见 §二.a）；全部 9 个计划文件按 17 维度 + 代码级契约复核无任何 blocker/major/minor 遗留。实现计划可进入执行。

## 二、终检清单逐项结论（a–j 全 PASS）

### a. 第 2 轮修复落位核验 + 两个"误报"裁定独立复核 — PASS

**修复落位（4 处锚点逐一实测）**：

| 修复项 | 计划文本 | 代码实测 | 结论 |
| --- | --- | --- | --- |
| plan-03 `_safe_nested_tx` L29→L30 | plan-03:137「`_safe_nested_tx` L30」 | `data_init.py:30` `async def _safe_nested_tx(...)` | ✓ 精确 |
| plan-08 互斥锚点 | plan-08:129「互斥 isAnySyncRunning L488/L535」 | `IndexSyncPanel.tsx:488` 定义、`:535` `disabled={isAnySyncRunning}`（首处禁用用法） | ✓ 精确 |
| plan-08 initIndexHistory 锚点 | plan-08:129「initIndexHistory L626」 | `api.ts:625` 方法签名、`:626` `adminApiClient.post<{task_id: string}>('/admin/init/index-history', ...)` 范式行 | ✓（锚点指向 post 范式行，方法块 625-626 内） |
| plan-08 initLimit 锚点 | plan-08:129「initLimit L631」 | `api.ts:631` `initLimit: (start_date?, end_date?) => adminApiClient.post...` | ✓ 精确 |

**两个"误报"裁定的独立复核（本轮亲自 grep 实测）**：

1. **`initLimit` 存在性**：`web/src/lib/api.ts:631` 确实存在 `initLimit` 方法（涨停专题三表同步，`adminApiClient.post<{task_id: string}>('/admin/init/limit', ...)`）。第 2 轮 minor #1 声称「不存在 initLimit 方法」**确系 checker 误报**；plan-08:55「与既有 `initLimit`/`initIndexHistory` 同款」的引用事实正确。裁定维持 ✓。
2. **`IndexOverviewCards` 行号**：`web/src/components/index-monitor/IndexMonitorPage.tsx:153` 确实是 `<IndexOverviewCards overview={overview} />` 渲染行。plan-07:79 写「L153」**正确**；第 2 轮 minor #3 声称实测为 L154 **确系误报**（本轮 sed 输出逐行确认 153 行）。裁定维持 ✓。

结论：第 2 轮的 4 项 minor 中，2 项修复落位正确、2 项误报裁定正确——即第 2 轮遗留问题实际为 0，本轮复核无新增问题。

### b. 结构完整性 — PASS

- README frontmatter：`workflow_type: create-dev-plan` ✓、`status: review_ready`（∈ `readme_frontmatter_status`）✓、`org_mode: feature` ✓、`total_tasks: 8` = 8 个 plan 文件 ✓、`execution_order` 6 组引用全部真实 ✓
- README 10 必备章节齐全（概览/输入摘要/验收标准追踪矩阵/模块地图/依赖图/阶段摘要/任务总览/未决策项/执行前置/变更记录）✓；AC 矩阵表头固定六列 ✓
- 8 个 plan：`feat_id` 与文件名一致 ✓；`dimension` ∈ {backend, frontend, mixed} ✓；`phase` ∈ {1,2,3} ✓；`status: ready-to-dev`（∈ `task_file_status`）✓；`depends_on` 引用真实 ✓
- 每个 plan 恰好 8 个必备 H2 章节（功能概要/文件清单/实现规格/Task 列表/验收标准/验证命令/交接上下文/风险与边界，grep 逐文件确认）✓
- 功能概要 7 必填字段（目标/完成后可观察结果/依赖/关联验收标准/涉及架构模块/前置条件/不在范围）逐文件齐全 ✓
- 无 `{{placeholder}}`（grep 全文零命中；`<rev12>` 为已声明自生成 revision，非模板空缺）✓
- Task 状态与边界场景状态全部 `todo`，无非法枚举、无 waived ✓

### c. AC-01~13 追踪矩阵双向一致、无自造 AC — PASS

- 架构 §2.5 的 13 条 AC 在 README 矩阵全部出现，无遗漏 ✓；矩阵「验证方式」均指向真实 plan 章节（`plan-XX §5` 即第 5 章节「验收标准」，指针有效）✓
- **README → FEAT**：每条 AC 的「计划承接」所列 plan 均在文件内引用该 AC 且验收标准有对应实质条目。特别核验 AC-07↔plan-03：plan-03 关联验收标准行列 [AC-01/03/09/13]，但 §4 失败错误结构显式标注「（AC-07）」、§5 含「任一关键值非法、集合不平衡、预期外代码、重复 → 整日不落库」验收条目——README 验证方式「plan-03 §5 整日失败」可追溯成立，无弱化 ✓
- **FEAT → README**：8 个 plan 的关联验收标准声明的每个 AC 均出现在 README 对应行的「计划承接」中（逐 plan grep 比对，完全闭合）✓
- 文件内辅助性 AC 引用（plan-01 交接上下文 AC-06、plan-03 close_cache 注 AC-02、plan-06 验收「AC-11 查询权限侧」）均标注为支撑/补充用途且不与 README 主承接冲突，非漂移 ✓
- 无孤立/自造 AC：所有扩展项（Repository 只读方法、close_cache、TaskFenceRegistry、MetricKey、unprocessedDates 展示）均显式标注「实现级补充项，非新造 AC」✓

### d. DAG / critical_path / execution_order / phase 一致性 — PASS

- 按 `depends_on` 重算深度：plan-01=1、02=2、03=3、04=2、05=4、06=4、07=5、08=6；最长链 `plan-01→02→03→06→07→08`（6 节点）
- frontmatter `critical_path`（README:12）与 §1 概览文字（README:29，含「plan-05 分支在 plan-08 前汇入」）均与图论最长链一致 ✓
- `execution_order` 6 组拓扑有效（每组依赖均在前序组出现）✓；`phase` 分组（1:01/02，2:03/04/05/06，3:07/08）与 §6 阶段摘要、§7 任务总览一致 ✓
- 组内并行声明核验：plan-03/04 文件集不相交（market_metrics_service/data_init vs task_fence/task_manager/task_executor/async_task/admin tasks）✓；plan-05/06 文件集不相交（task_handlers/init_market_metrics/collector/job_manager vs api/v1/market_metrics）✓

### e. 文件清单 modify 存在 / create 无重复 / 测试路径规则 — PASS

- 全部 `modify` 路径逐一实测存在：后端 17 项（models/\_\_init\_\_.py、data_acquisition 三件、data_init.py、tests/test_data_init.py、async_task.py、task_manager.py、task_executor.py、admin/tasks.py、task_handlers.py、admin/\_\_init\_\_.py、collector.py、job_manager.py、tests/test_data_updater.py、v1/\_\_init\_\_.py、init_index_basic.py 仅作锚点）+ 前端 9 项（api.ts、fetcher.ts 相关、IndexMonitorPage.tsx、IndexSyncPanel.tsx 仅锚点、IndexTrendChart.tsx 仅锚点、dashboard/page.tsx、useTaskStatus.ts、admin/data/page.tsx）全 OK ✓
- `create` 路径跨 plan 无重复；plan-08 modify 的 `marketMetricsTypes.ts`/`api.ts` 由 plan-07 先 create/modify 且 depends_on + README「同文件顺序编辑」声明串行，无冲突 ✓
- 测试路径规则：pytest `testpaths=tests` + `python_files=test_*.py` + `--import-mode=importlib`（tests/services/、tests/api/、新建 tests/api/admin/ 均自动递归收集，无需 \_\_init\_\_.py）✓；jest `testMatch` 收 `<rootDir>/tests/**` 且 `testPathIgnorePatterns` 排除 tests/e2e（组件测试放 web/tests/market-metrics/ 正确）✓；Playwright `testDir='./tests/e2e'`、baseURL 3100 ✓

### f. 四件套契约 + 解包层级（plan-05/06/07/08）— PASS（本轮代码级独立复核）

1. **路径前缀**：后端挂载链实测 `main.py:111 app.include_router(api_router, prefix="/api")` × `src/api/v1/__init__.py:30 APIRouter(prefix="/v1")` × 业务路由 `prefix="/market-metrics"` = `/api/v1/market-metrics/trend`；admin 侧 `src/api/router.py:29 prefix="/v1/admin"` × `init_index_basic.py:39 prefix="/init"` 范式 = `/api/v1/admin/init/market-metrics`。前端 `api.ts:9 API_BASE_WITH_PREFIX = ${API_BASE_URL}/api/v1`，endpoint 不带 `/api/v1` → 无双前缀 ✓；plan-08 记录区 `fetcher('/api/v1/admin/tasks?...')`，fetcher `API_BASE=NEXT_PUBLIC_API_URL`（不含 /api）不双前缀 ✓
2. **HTTP 方法存在性与鉴权**：`ApiClient.get`（api.ts:119）经 `getAuthHeaders()`（api.ts:45）携带 Authorization；`AdminApiClient extends ApiClient`（api.ts:448）且覆盖 get/post（api.ts:525/530）均走鉴权 request ✓；后端 `@router.get("/trend")` / 专用 POST 三方一致 ✓
3. **query 参数命名**：`range` 单词无 snake/camel 歧义且后端 `Query(30, pattern="^(30|90|250)$")`（plan-06:44，regex→pattern 修复落位，全文无 `regex=` 用法残留——唯一命中为「regex= 已弃用」注释）✓；`task_types/page/page_size` snake_case（与 IndexSyncPanel.tsx:65 `RECORDS_SWR_KEY` 同款）✓；body `{start_date,end_date}` snake_case 与 Pydantic payload 一致 ✓
4. **响应字段命名 + 解包层级**：plan-06 helper 实测在 `index_monitor.py:55 _serialize_value` / `:66 _dict_to_camel`（落在计划标注的 55-80 区间内；第 1 轮 minor #4 对此的质疑不成立），Decimal→float、date→ISO ✓；plan-07 泛型 `apiClient.get<{ success, data: MarketMetricsTrendData }>` + `res.data as unknown as {...}`（与 IndexMonitorPage.tsx:42-49 锚点实测一致），`res.data`={success,data} 再取 `.data` 不多解不少解 ✓；plan-08 `adminApiClient.post<{task_id}>`，`AdminApiClient.request` 实测 `return { data: json.data }`（解一层）✓；fetcher 实测 `return result.data || result` ✓
5. **result 契约序列化路径**：`AsyncTask.to_dict()` 顶层 camelCase（`taskId/taskType/...`，async_task.py:57-58 实测）；任务详情端点 `tasks.py:294 TaskDetailResponse(**task_dict)` 无 `_dict_to_camel`——result 子树无任何键转换层，plan-05 写 camelCase 为**必需且正确**；plan-04 §5 已为 TaskResponse/TaskDetailResponse 增加 `result: Optional[dict]` 防 Pydantic extra 丢弃 ✓

### g. 验证命令逐条可执行 — PASS

- `server/.venv` 真实存在；所有单文件 pytest 命令均带 `--no-cov`（pytest.ini 实测 `--cov=src` + `--cov-fail-under=80`，规避正确）；README §9.3 全量 `pytest tests/ -v` 不带 `--no-cov` 属有意启用门槛 ✓
- 迁移链实测：`alembic/versions` 最末端 `2026_08_13_2234-7e3309ce89da`（rev=7e3309ce89da，down=f92bfffc49c3），且无任何迁移 down 指向 7e3309ce89da → **单一 head 成立**；plan-01 `down_revision='7e3309ce89da'` 正确、plan-04 迁移链到 plan-01 之上时序成立 ✓
- pnpm 脚本实测存在：`test=jest`、`build=next build`、`test:e2e=playwright test`、`dev=next dev -p 3100`；计划用 `pnpm exec tsc --noEmit`（未误用不存在的 type-check 脚本）✓；`pnpm test -- tests/...`、`pnpm test:e2e -- tests/e2e/...` 位置参数过滤写法可行（jest/playwright 均接受）✓
- Playwright 配置与 3100 baseURL 一致 ✓；`docs/e2e/` 与既有用例文件存在，evidence 目录契约路径合法 ✓

### h. 跨文件契约 — PASS

- **TaskFenceContext 时序**：plan-03 用 `from __future__ import annotations` + TYPE_CHECKING 前向引用（运行时不导入 task_fence）；实现于 plan-04、真实实例仅由 plan-05（depends_on 含 plan-04）传入；plan-03 直接依赖不含 plan-04 但传递满足 ✓
- **迁移链**：plan-01（down=7e3309ce89da）→ plan-04（down=plan-01 迁移 revision），两条迁移分属两功能且 execution_order 保序 ✓
- **result camelCase 三方**：plan-05:65 显式「result JSON 键全部 camelCase…原样透传不经 _dict_to_camel，plan-08 前端直消费、无二次键转换」→ plan-04:43「原样透传 dict | None」+ TaskResponse/TaskDetailResponse 增 result 字段 → plan-08:44/130「直消费、无二次键转换」。grep 全文无「须在消费层做键转换」「若以 snake_case 存储」等对冲措辞残留（唯一命中即上述「无二次键转换」正向声明）✓
- **并行组文件不相交**：见 d ✓

### i. E2E-TDD 与 plan-05 执行验证 — PASS

- plan-07：Task 7「E2E 用例文档 + mock helper + spec（red 证据）｜先 red 后实现」；§5「red 证据与 green 证据齐备，存 docs/e2e/evidence/plan-07-e2e-{red|green}-{date}.md」；风险与边界明确「Task 7 的 red 证据必须先于 Task 3 实现」✓
- plan-08：Task 8 + §5 同款 red/green 双阶段证据要求 ✓
- plan-05 执行验证（task handler 不豁免）：§5「触发任务 → 等待 completed → 查询 market_daily_metrics」+ 验证命令 #2 提供 `create_exclusive_task` 触发脚本与查库脚本；脚本 import 实测有效（`AsyncSessionLocal` 在 src/db/database.py:42、`TaskManager`/`create_exclusive_task` 签名与 plan-04 §3 一致、timeout_seconds 可缺省）、`MarketDailyMetric` 由 plan-01 创建 ✓

### j. README 变更记录与 reviews 产物 — PASS

- 变更记录两条：①初始生成（8 功能/3 阶段，与实际 8 个 plan 文件一致）；②质检修复 R1——其声明的五类修复本轮逐一实证：critical_path 6 节最长链（README:12/29）✓、plan-07 泛型+`as unknown as`（plan-07:55/67）✓、result camelCase 三方（见 h）✓、Query pattern（plan-06:44）✓、锚点行号校准（含第 2 轮补校的 plan-03 L30、plan-08 L488/L535/L626/L631，同属「锚点行号校准」范畴）✓
- `reviews/` 下存在两轮报告：`dev-plan-check-round1-2026-08-14.md`、`dev-plan-check-round2-2026-08-14.md`；本报告为第三轮，写入同目录 ✓

## 三、Contract 预检

| 检查项 | 结果 |
| --- | --- |
| README frontmatter 枚举合法 | ✓ |
| README 10 必备章节 + AC 矩阵表头 | ✓ |
| 8 plan frontmatter（feat_id/dimension/phase/status/depends_on） | ✓ |
| 8 plan 8 章节 + 功能概要 7 字段 | ✓ |
| 无占位符 / Task 状态枚举合法 | ✓ |
| 报告写入 `reviews/dev-plan-check-{date}.md` | ✓（本文件） |

## 四、维度检查结果

| 维度 | 结论 | 摘要 |
| --- | --- | --- |
| 1 核心闭环 | ✓ | 拉取→核验→汇总→展示在 README §2.1 与 plan-01~08 完整承接 |
| 2 范围/非目标 | ✓ | P0 全覆盖；§2.3 不做清单在 plan-02/03/06 显式遵守 |
| 3 成功标准 | ✓ | P95≤500ms、单日可复算、幂等覆盖等落到对应 plan 验收/性能段 |
| 4 AC 防漂移 | ✓ | 13 条 AC 双向闭合（见 §二.c） |
| 5 ADR | ✓ | ADR-1~6 护栏在 README §2.2 + 各 plan 实现规格呼应 |
| 6 流程/状态机 | ✓ | pending/running/completed/failed/cancelled 全分支在 plan-04 |
| 7 模块职责 | ✓ | 架构六模块 ↔ plan-01~08 一一对应 |
| 8 运行链路 | ✓ | §6.1~6.4 在 plan-03/05/06 逐步落地 |
| 9 数据模型/契约 | ✓ | §7.2 对象/TS 契约逐字段对齐；result camelCase 三方自洽且与序列化路径强制一致 |
| 10 非功能 | ✓ | §8.1/8.2/8.5 分别注入 plan-02/05/06/07/04 性能/降级/可观测段 |
| 11 技术选型 | ✓ | 技术栈与 §9 三阶段一致；无超首版范围 |
| 12 风险 | ✓ | §8.6 风险在 plan 风险与边界均有缓解 |
| 13 功能拆分 | ✓ | Task 列表 ≤9 步；DAG 无环；文件清单不膨胀 |
| 14 可执行性 | ✓ | 文件清单/验证命令/前置条件全部可执行（见 §二.e/g/i） |
| 15 状态/报告 | ✓ | 状态合法且一致；报告路径符合 contract |
| 16 复用声明 | ✓ | 复用点（savepoint 范式、ApiResponse、useTaskStatus、fetcher 等）均写明调用细节且与代码实证一致 |
| 17 前后端契约（代码级） | ✓ | 四件套 + 解包层级 + snake/camel 全部独立复核通过（见 §二.f） |

## 五、问题清单

无。blocker / major / minor 均为 0。

## 六、备注（非问题，仅记录核验痕迹）

1. plan-03 关联验收标准行列 [AC-01/03/09/13]、未列 AC-07，而 README AC-07 计划承接含 plan-03——经核 plan-03 §4 显式标注（AC-07）且 §5 含「整日不落库」验收条目，README 验证方式指针可追溯，实质覆盖无弱化，判非缺陷（第 1/2 轮同判）。
2. plan-08:129「initIndexHistory L626」：方法签名在 api.ts:625、post 范式行在 :626——锚点指向范式行，属方法块内 ±1，精确性满足「照抄范式」用途，判非缺陷。
3. 第 1 轮 minor #4 中「index_monitor helper 实际在 ~80-110」的质疑经本轮实测不成立（`_serialize_value` L55 / `_dict_to_camel` L66，计划标注 55-80 正确）；第 2 轮已不再列入，与本轮结论一致。

## 七、终检结论

三轮检查闭环：第 1 轮 3 major → 已修复并经第 2 轮 grep 全量验证彻底；第 2 轮 4 trivial minor → 2 项修复落位、2 项确认误报；本轮独立上下文对 a–j 十类检查项与 17 维度全部复核，**未发现任何 blocker/major/minor 问题**。

**终检通过。实现计划（README + plan-01~plan-08）可进入执行阶段。**
