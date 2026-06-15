# 开发计划检查报告

## 一、检查对象

- 架构文档：`docs/07-股东分组匹配明细/07-1-架构文档-股东分组匹配明细.md`（status: done）
- 需求基线：`docs/07-股东分组匹配明细/07-0-需求设计-股东分组匹配明细.md`
- 实现计划：`docs/07-股东分组匹配明细/07-2-实现计划-股东分组匹配明细/`
- 功能数：2（plan-01 后端 + plan-02 前端）

代码级核查范围（MEMORY 重点项）：
- 后端路由：`server/src/api/admin/shareholder_groups.py`、`server/src/api/admin/__init__.py`、`server/src/api/router.py`、`server/main.py`
- 后端服务：`server/src/services/shareholder_group_service.py`、`server/src/services/shareholder_analysis_service.py:292-344`
- 后端测试：`server/tests/test_shareholder_group_admin_api.py`、`server/tests/conftest.py`
- 前端 API：`web/src/lib/api.ts`
- 前端 E2E：`web/tests/e2e/shareholder-groups.spec.ts`、`web/tests/e2e/helpers/mock-shareholder-api.ts`

## 二、总评

- **结论：有阻塞问题（需要修改）**
- 阻塞问题数：**5**
- 建议项数：**4**

主要问题集中在 plan-02 §3 #9（Playwright 场景代码示例），大量调用了**不存在的 mock helper 与测试数据工厂**，以及前端 page 路径前缀缺失。这些会让 implementer 在 red 阶段直接踩坑：red 测试不是因为组件未实现而失败，而是因为 helper import 失败/路由 404 而失败，违背 plan-01 自己在 §3 #8 末尾强调的 "red 阶段失败原因不能是测试代码本身的语法/逻辑错误（如有则先修测试代码）" 原则。

架构基线对路径前缀、复用声明、AC 追溯、ADR 等的承接**整体良好**；前后端 API 契约的"四件套校验"在 plan 内部已经做了一轮（路径/方法/query/响应字段），核对真实代码后**完全正确**。最大风险是 plan-02 的 E2E 示例代码与现实 helpers/路由不匹配。

## 三、Contract 预检

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| README frontmatter `workflow_type: create-dev-plan` | ✓ | line 2 |
| README frontmatter `org_mode: feature` | ✓ | line 6 |
| README frontmatter `status: review_ready` | ✓ | line 3，属合法枚举 |
| README `execution_order` 引用真实 plan | ✓ | `[plan-01, plan-02]`，两个 plan 文件均存在 |
| README `total_tasks: 2` 与 plan 文件数一致 | ✓ | 2 个 plan-*.md |
| README 必备章节齐全（10 项） | ✓ | 概览/输入摘要/追踪矩阵/模块地图/依赖图/阶段摘要/任务总览/未决策项/执行前置/变更记录 |
| 验收标准追踪矩阵表头格式正确 | ✓ | `AC-ID / 需求原文 / 架构承接 / 计划承接 / 验证方式 / 当前状态` |
| plan-01 frontmatter `feat_id=plan-01`，与文件名一致 | ✓ | line 2 |
| plan-02 frontmatter `feat_id=plan-02`，与文件名一致 | ✓ | line 2 |
| plan-01/02 `status: ready-to-dev` 合法 | ✓ | 均在合法枚举内 |
| plan-01/02 必备 8 章节齐全 | ✓ | 功能概要/文件清单/实现规格/Task 列表/验收标准/验证命令/交接上下文/风险与边界 |
| Task 状态全部 `todo` | ✓ | plan-01 9 项 / plan-02 11 项 |
| `waived` 用法 | n/a | 无 waived |
| `depends_on` 引用真实存在功能 | ✓ | plan-01=[]、plan-02=[plan-01] |

## 四、验收标准追踪

| AC-ID | 架构要求 | README 承接 | FEAT 承接 | 结论 |
| --- | --- | --- | --- | --- |
| AC-01 | 逐关键词匹配的去重股票数 | ✓（plan-01+plan-02） | plan-01 §5 pytest + plan-02 §5 场景 1 | ✓ |
| AC-02 | 保留所有关键词合并匹配总数 | ✓（plan-02） | plan-01 §5 现有 preview 回归 + plan-02 §5 场景 1 | ✓ |
| AC-03 | 点击查看明细展示该关键词明细列表 | ✓（plan-01+plan-02） | plan-01 §5 pytest + plan-02 §5 场景 2 | ✓ |
| AC-04 | 同股票多股东按股东分行 | ✓（plan-01+plan-02） | plan-01 §5 pytest + plan-02 §5 场景 2 | ✓ |
| AC-05 | 明细按股票代码升序、同股票多股东相邻 | ✓（plan-01+plan-02） | plan-01 §5 pytest + plan-02 §5 场景 2 | ✓ |
| AC-06 | 修改关键词后股数与明细实时刷新 | ✓（plan-02） | plan-02 §5 场景 3 | ✓ |
| AC-07 | 失败均降级不阻塞编辑与保存 | ✓（plan-01+plan-02） | plan-01 §5 pytest + plan-02 §5 场景 4 | ✓ |
| AC-08 | 空关键词不显示股数与明细入口 | ✓（plan-02） | plan-02 §5 场景 5 | ✓ |
| AC-09 | 关键词匹配数为 0 时查看明细入口置灰 | ✓（plan-02） | plan-02 §5 场景 5 | ✓ |

架构 §2.4 全部 9 条 AC 在 README 追踪矩阵 + 至少一个 plan 中可追溯到具体验证方式。**承接完整性合格**。

## 五、维度检查结果

| 维度 | 结论 | 问题数 | 摘要 |
| --- | --- | --- | --- |
| 1. 核心闭环与系统目标 | ✓ | 0 | Keyword→Match→Detail 闭环在 README §2.1 复述完整 |
| 2. 范围与非目标 | ✓ | 0 | P0 全部承接；非目标（列表行级、导出、用户侧改造）在 plan-01/02 §1 不在范围呼应 |
| 3. 成功标准 | ⚠ | 1 | 性能目标（≤200ms/≤1s）在 plan-01 §5 验收中提到，但用 `time.perf_counter()` 在 pytest 内做性能断言不合理（CI 抖动+fixture 数据量小不可信），属建议项 |
| 4. 验收标准防漂移 | ✓ | 0 | 9 条 AC 全部映射 |
| 5. ADR 约束 | ✓ | 0 | ADR-1~5 均在 README §2.2 与对应 plan §3/§8 体现 |
| 6. 用户流程与状态机 | ✓ | 0 | 状态机在 plan-02 §1 概述 + 风险与边界体现 |
| 7. 模块职责与系统上下文 | ✓ | 0 | README §4 模块地图与架构 §4.2 对齐 |
| 8. 运行链路 | ✓ | 0 | 6.1~6.4 链路在 plan-01/02 §3 分步实现 |
| 9. 数据模型与契约 | ✓ | 0 | Pydantic 模型与 TS interface 完整 |
| 10. 非功能需求 | ⚠ | 1 | 性能目标验证方式略不合理（建议项） |
| 11. 实施建议与技术选型 | ✓ | 0 | 与架构一致 |
| 12. 风险与未决策项 | ✓ | 0 | open_questions 为空 |
| 13. 功能拆分质量 | ✓ | 0 | plan-01（后端 9 task）/ plan-02（前端 11 task）合理 |
| 14. 可执行性 | **✗** | **5** | plan-02 §3 #9 大量调用不存在的 helper + 路径前缀错（阻塞） |
| 15. 状态与报告契约 | ✓ | 0 | 状态合法 |
| 16. 复用声明链路验证 | ✓ | 0 | 代码级核对全部可复用，import 路径准确 |
| 17. 前后端 API 契约一致性（代码级） | ✓ | 0 | 路径前缀/方法/query/response 字段全部对齐，**无重复前缀** |

## 六、问题清单

### 阻塞问题（5 项 — 全部集中在 plan-02 §3 #9）

| # | 严重级别 | 位置 | 问题 | 修补建议 |
| --- | --- | --- | --- | --- |
| B-1 | blocker | plan-02 §3 #9 场景 1/2/3/4/5（line 500/534/578/613/643 五处） `await page.goto('/admin/shareholder-groups')` | **前端页面路径缺少 `/dashboard` 前缀**。现有 `web/tests/e2e/shareholder-groups.spec.ts:14` 定义 `ADMIN_GROUPS_PAGE = '/dashboard/admin/shareholder-groups'`，所有现有 spec 都用此路径。Next.js App Router 实际页面位于 `web/src/app/dashboard/admin/shareholder-groups/page.tsx`。plan 中写 `/admin/shareholder-groups` 会触发 next middleware 路由守卫重定向或 404 | 五处统一改为 `await page.goto('/dashboard/admin/shareholder-groups')` 或在文件顶部定义 `ADMIN_GROUPS_PAGE` 常量复用 |
| B-2 | blocker | plan-02 §3 #9 五个场景共 5 处 `createTestGroup({ id, name, keywords })`（line 492/518/561/599/636） | **测试数据工厂 `createTestGroup` 不存在**。现有 `helpers/mock-shareholder-api.ts` 只导出 `createTestShareholderGroups(): ShareholderGroupItem[]`（返回 5 个预定义组）和 `createQFiiGroup(): ShareholderGroupItem`（创建单个 QFII 组）。implementer 照抄会 import 失败 | 二选一：(a) 在 §3 #8 mock helper 列表里**显式新增** `createTestGroup(partial: Partial<ShareholderGroupItem>): ShareholderGroupItem` 的 factory 函数说明，且补到 Task 列表 #2；(b) 改用 `createQFiiGroup()` 风格写 `createSocialGroup()` 等专用 factory |
| B-3 | blocker | plan-02 §3 #9 场景 1/2/3/4/5 共 5 处 `mockShareholderGroupsSuccess(page, [...])`（line 491/517/561/599/635） | **mock helper 命名错误**。现有 helper 实际叫 `mockShareholderGroupsList(page, listResponses: ShareholderGroupItem[][])`（参数是数组的数组，支持多次调用返回不同结果）。plan 写的 `mockShareholderGroupsSuccess` 不存在 | 改为 `mockShareholderGroupsList`，参数包成 `[groups]`（嵌套数组） |
| B-4 | blocker | plan-02 §3 #9 场景 1 line 498 `mockPreviewMatchSuccess(page, { matchedStockCount: 3 })` + 场景 4 line 602 `mockPreviewMatchError(page, 500)` | **mock helper 命名错误 + 参数签名错误**。现有 helper 实际叫 `mockShareholderGroupPreview(page, matchedStockCount: number = 3)`（参数是数字）。且无对应 Error 变体。plan 调用的两个 helper 均不存在 | (a) `mockPreviewMatchSuccess(page, { matchedStockCount: 3 })` → `mockShareholderGroupPreview(page, 3)`；(b) 在 §3 #8 mock helper 列表显式新增 `mockShareholderGroupPreviewError(page, status)` 并补到 Task 列表 #2 |
| B-5 | blocker | plan-02 §3 #9 line 412 "参照现有 `mockShareholderGroupsSuccess` 风格" + 整个 §3 #9 | **现有 helper 命名约定不一致已扩散到新增 helper 的注释**。plan-02 §3 #8 把新 helper 命名为 `mockPreviewBreakdownSuccess` 等（带 `Success` 后缀），与现有 `mockShareholderGroupsList / mockShareholderGroupPreview / mockShareholderGroupCreate`（业务动词风格）不一致。这会令 implementer 困惑是否要重命名现有 helper | 二选一：(a) 新 helper 改成与现有风格一致（`mockShareholderGroupPreviewBreakdown(page, items)` / `mockShareholderGroupKeywordMatches(page, data)` 等），并在 §3 #8 注释里说明沿用现有命名；(b) 明确写出"新增 helper 采用 Success/Error 后缀风格，与现有 mockShareholderGroup* 系列不同，是新增约定"，并要求 Task #2 同步重命名现有的 5 个 helper（不推荐，影响现有 spec） |

### 建议项（4 项）

| # | 严重级别 | 位置 | 问题 | 修补建议 |
| --- | --- | --- | --- | --- |
| S-1 | suggestion | plan-01 §5 性能验收"单关键词股数查询 ≤ 200ms（pytest 中用 `time.perf_counter()` 套查询断言可接受）" | 在 pytest 内用 wall time 断言性能不可靠。fixture 数据量小（5 行）几乎任何查询都 < 1ms，断言通过无意义；CI runner 抖动会让原本 200ms 的查询偶尔 400ms，断言不稳定。架构 §8.1 给的是预期目标，不是回归测试硬约束 | 把性能验收降级为"实现完成后手动 curl 验证 ≤ 200ms（用日志中的 INFO 耗时字段判断），不写 wall time 断言"；或改为"若超 1s（10× 目标）才标记 fail"作为兜底 |
| S-2 | suggestion | plan-01 §3 #8 用例 #5 fixture（`000001` 改 `600001`）与用例 #6（`000001` 测 stockName=null）共享同一个 `sample_holders` fixture | 同一 fixture 在两个用例间数据语义冲突。implementer 要么复制两份 fixture，要么用例 #6 改 mock service 或改断言。属实现细节，可在 implementer 阶段调整，但 plan 应注明"两个用例需独立 fixture" | 在 §3 #8 用例 #5 注释加"用例 #5 与 #6 因 symbol 排序要求不同，请拆为两个 fixture（`sample_holders_sorted` / `sample_holders_with_missing`），或 #6 改用 service 单元测试不依赖 HTTP" |
| S-3 | suggestion | plan-02 §3 #8 line 412 mock helper 注释 / 场景代码 line 562-576 | 场景 3 用 `page.route('**/api/v1/admin/shareholder-groups/preview-breakdown', ...)` 内联 mock，与 §3 #8 自定义 helper `mockPreviewBreakdownSuccess` 用 `matchApiPath` 精确匹配风格不一致。同一 plan 内 mock 写法两种风格 | 场景 3 统一改用 `mockPreviewBreakdownSuccess` 的多次返回值版本（参考 `mockShareholderGroupsList` 的 `listResponses` 数组按 callIndex 返回），与现有 spec 风格一致 |
| S-4 | suggestion | plan-01 §3 #8 line 339 `sample_holders` fixture 用 `test_session.add_all(rows)` + `await test_session.commit()` 后立即 return rows；同时插 stocks 表又 commit | 两次 commit 之间没有事务边界保护。若第一段 commit 成功但第二段失败，holder 数据已落库污染后续测试。现有 `conftest.py:107 test_session` fixture 通常配置了 function-scoped rollback，但 plan 中未显式说明依赖该机制 | 加注释 "依赖 conftest.py `test_session` 的 function-scope 回滚；fixture 结束后自动清理"。或改为单次 commit |

## 七、合理扩展

| 位置 | 扩展内容 | 为什么合理 |
| --- | --- | --- |
| plan-01 §3 #8 | pytest 用例从架构 §9 验证目标里隐含的"最小集成测试"扩展到 13 个（含边界 + 权限 + 注入回归） | 后端 FEAT 的 E2E-TDD 必须有 red/green 证据，13 个用例完整覆盖 AC + 边界 + 安全（LIKE 转义回归），不超出范围 |
| plan-01 §3 #1 | `_count_matched_stocks_single` 不再调用 `_get_latest_report_period`（由调用方传入 period） | 避免 N 个关键词 N 次查 MAX(report_period)，性能优化合理，与架构 §10 演进方向"未来批量化 SQL"思路一致 |
| plan-01 §3 #2 | `DISTINCT ON` 在 SQLAlchemy 用 `.distinct(*cols)` API + 备选子查询方案 | 架构 §6.2 给的 SQL 模板，ORM 表达有版本差异，提供备选方案合理 |
| plan-02 §3 #4 | debounce 回调内并行调 preview + preview-breakdown | AC-02 + AC-01 并存展示需求 |
| plan-02 §3 #5 | `handleViewDetail` 切换关键词时先 reset `detailState` 再请求 | 与架构 §3.3 状态机 DetailCollapsed → DetailLoading 一致 |
| plan-02 §3 #6 | data-testid 命名约定（`keyword-count-${idx}` / `view-detail-${idx}` / `keyword-detail-panel`） | 遵循 `.claude/rules/e2e-playwright-best-practices.md` 规则 5（避免多元素匹配）+ 规则 7（依赖稳定选择器而非文案） |
| plan-01 §3 #6 #7 + plan-02 §3 #1 #2 | 在每个端点/adminApi 方法下显式列"前后端契约校验（四件套）"：路径/方法/query/response | 对应 MEMORY 中"路径前缀验证"经验，且经代码级核对全部正确 |

## 八、建议补丁计划

按优先级排序：

1. **[阻塞]** 修补 plan-02 §3 #9 所有 5 个 Playwright 场景代码示例：
   - 全局把 `page.goto('/admin/shareholder-groups')` 改为 `page.goto('/dashboard/admin/shareholder-groups')`（5 处）
   - `createTestGroup(...)` → 决定方案：要么补 factory 到 Task #2，要么改用 `createQFiiGroup()` 风格的专用 factory
   - `mockShareholderGroupsSuccess` → `mockShareholderGroupsList`，参数改为嵌套数组（5 处）
   - `mockPreviewMatchSuccess` → `mockShareholderGroupPreview`，参数从对象改为数字（1 处）
   - `mockPreviewMatchError` → 补到 Task #2 新增 helper（1 处）

2. **[阻塞]** 修补 plan-02 §3 #8 mock helper 命名（5 个新 helper）：
   - 决定方案 A：与现有 `mockShareholderGroup*` 风格统一（推荐）
   - 或方案 B：明确"Success/Error 后缀是新约定"，并在 §3 #8 顶部说明
   - 在 Task 列表 #2 补充 `createTestGroup` factory 与 `mockShareholderGroupPreviewError` 的实现要求

3. **[建议]** plan-01 §5 性能验收降级（删掉 `time.perf_counter()` 断言，改为手动验证或 10× 兜底）

4. **[建议]** plan-01 §3 #8 用例 #5/#6 的 fixture 拆分提示

5. **[建议]** plan-02 §3 #9 场景 3 内联 mock 改用 helper（统一风格）

---

**复核结论**：**需要修改（5 个阻塞 + 4 个建议项）**。所有阻塞问题集中在 plan-02 §3 #9 的 E2E 示例代码与真实代码库的不匹配。架构承接、复用声明、路径前缀、AC 追溯全部合格；E2E 示例需要按现有 `shareholder-groups.spec.ts` 与 `mock-shareholder-api.ts` 的实际命名重新校准。
