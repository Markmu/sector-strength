# 开发计划检查报告

## 一、检查对象

- 架构文档：`docs/04-A股基金持仓分析/04-1-架构文档-A股基金持仓分析.md`
- 实现计划：`docs/04-A股基金持仓分析/04-2-实现计划-A股基金持仓分析/`
- 功能数：5（plan-01 ~ plan-05）

## 二、总评

- 结论：**有阻塞问题**（已全部修复）
- 阻塞问题数：3（已修复）
- 建议项数：6（已修复）

实现计划整体结构完整，5 个 FEAT 功能拆分合理、依赖 DAG 无循环、必备章节齐全、AC 追踪矩阵全覆盖。初始检查发现 3 处阻塞问题，已全部修复：

1. ✅ plan-02 `is_portfolio_empty` SQL 定义与验收标准矛盾 → 简化为 `(total == 0)`
2. ✅ `latestPeriodExists` 语义三方不一致 → 重命名为 `hasPortfolio`，新增 `latestReportPeriod`
3. ✅ README execution_order 与 depends_on 矛盾 → 拆分为 4 组

6 个建议项也已同步修复（字段计数、API 元数据、L1 降级说明、L4 验收、计划层新增标注）。

## 三、Contract 预检

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| README frontmatter `workflow_type: create-dev-plan` | ✅ 通过 | |
| README frontmatter `org_mode: feature` | ✅ 通过 | |
| README `status: review_ready` 合法 | ✅ 通过 | 属于 `plan.readme_frontmatter_status` |
| README `execution_order` 引用真实 plan-XX | ✅ 通过 | 5 个均存在 |
| README `total_tasks` 与 plan-*.md 数量一致 | ✅ 通过 | 均为 5 |
| README 必备章节完整性 | ✅ 通过 | 10 个 required section 全部存在 |
| README 验收标准追踪矩阵表头 | ✅ 通过 | AC-ID / 需求原文 / 架构承接 / 计划承接 / 验证方式 / 当前状态 |
| FEAT frontmatter feat_id 与文件名一致 | ✅ 通过 | plan-01~05 全部匹配 |
| FEAT status 合法 | ✅ 通过 | 全部为 `draft`，属于 `plan.task_file_status` |
| FEAT 必备章节完整性 | ✅ 通过 | 5 个 FEAT 均包含全部 8 个 required section |
| Task/边界状态仅使用 todo/done/waived | ✅ 通过 | 全部为 `todo` |
| FEAT depends_on 引用真实存在功能 | ✅ 通过 | |
| **README execution_order 与 depends_on 一致性** | **❌ 不通过** | plan-04 depends_on plan-02，但两者被放在同一并行组。详见阻塞问题 #3 |

## 四、验收标准追踪

| AC-ID | 架构要求 | README 承接 | FEAT 承接 | 结论 |
| --- | --- | --- | --- | --- |
| AC-01 | 基金列表展示与搜索 | plan-02, plan-04 | plan-02 §5 AC-01 + plan-04 §5 AC-01 | ✅ 映射完整 |
| AC-02 | 基金过滤（市场+类型） | plan-02, plan-04 | plan-02 §5 AC-02 + plan-04 §5 AC-02 | ✅ 映射完整 |
| AC-03 | 基金详情页展示最新持仓 | plan-02, plan-05 | plan-02 §5 AC-03 + plan-05 §5 AC-03 | ⚠️ 映射存在但空态元信息定义有矛盾（阻塞问题 #1/#2） |
| AC-04 | 股票反查 | plan-02, plan-05 | plan-02 §5 AC-04 + plan-05 §5 AC-04 | ⚠️ 缺少报告期与股票名称元数据（建议项 #5/#6） |
| AC-05 | 数据缺失的透明呈现 | plan-05 | plan-05 §5 AC-05 场景 A/B | ⚠️ 依赖 plan-02 元信息定义修复（阻塞问题 #1/#2） |
| AC-06 | 管理员手动同步基金数据 | plan-01, plan-03 | plan-01 §5 AC-06 + plan-03 §5 AC-06 | ✅ 映射完整 |
| AC-07 | 同步失败的可见提示 | plan-01, plan-03 | plan-01 §5 AC-07 + plan-03 §5 AC-07 | ✅ 映射完整 |

## 五、维度检查结果

| 维度 | 结论 | 问题数 | 摘要 |
| --- | --- | --- | --- |
| 1. 核心闭环与系统目标 | ✅ 继承良好 | 0 | 核心闭环 Fund→Portfolio→Query 在 README 输入摘要明确引用 |
| 2. 范围与非目标 | ✅ 继承良好 | 0 | P0 全部有 FEAT 承接；§2.2 非目标均未引入 |
| 3. 成功标准 | ✅ 继承良好 | 0 | 7 项定量标准散布在对应 FEAT 性能验收中 |
| 4. 验收标准防漂移 | ⚠️ 有矛盾 | 2 | AC-03/AC-05 空态元信息内部不一致（阻塞 #1/#2） |
| 5. ADR 约束 | ✅ 继承良好 | 0 | 6 条 ADR 全部在 README 护栏和 FEAT 实现规格中体现 |
| 6. 用户流程与状态机 | ⚠️ 有遗漏 | 1 | L1 列表行标注"暂无数据"与列表不 JOIN fund_portfolio 的实现矛盾未说明（建议 #2） |
| 7. 模块职责与系统上下文 | ✅ 继承良好 | 0 | 6 个架构模块均有对应 FEAT 承接，depends_on 正确体现上下游 |
| 8. 运行链路 | ✅ 继承良好 | 0 | 4 条运行链路步骤在 FEAT 实现规格中一一落地 |
| 9. 数据模型与契约 | ⚠️ 有遗漏 | 2 | 反查/详情响应缺少 reportPeriod 和 stockName（建议 #5/#6）；字段计数有误（建议 #1） |
| 10. 非功能需求 | ✅ 基本覆盖 | 1 | L4 降级无验收项（建议 #4），其余 NFR 均有传播 |
| 11. 实施建议与技术选型 | ✅ 继承良好 | 0 | 技术栈一致，阶段划分合理 |
| 12. 风险与未决策项 | ✅ 继承良好 | 0 | 架构 5 项风险均有缓解，open_questions 同步为空 |
| 13. 功能拆分质量 | ✅ 继承良好 | 0 | 单 FEAT ≤ 8 task，依赖 DAG 无环 |
| 14. 可执行性 | ✅ 继承良好 | 0 | 文件路径具体，验证命令可运行，E2E-TDD 覆盖到位 |
| 15. 状态与报告契约 | ❌ 有矛盾 | 1 | execution_order 与 depends_on 矛盾（阻塞 #3） |
| 16. 复用声明链路验证 | ✅ 继承良好 | 0 | 3 项复用声明在 FEAT 中均有正确调用描述 |

## 六、问题清单

### 阻塞问题

| # | 严重级别 | 位置 | 问题 | 修补建议 |
| --- | --- | --- | --- | --- |
| 1 | 🔴 blocker | plan-02 §1 `get_latest_portfolio` 元信息 SQL 定义 vs plan-02 §5 验收标准 AC-03 场景 B | **`is_portfolio_empty` 定义与验收标准矛盾**。SQL 定义为 `(total == 0) AND NOT EXISTS(SELECT 1 FROM fund_portfolio WHERE fund_ts_code = :fund_ts_code)`，Scenario B（有旧期但最新期未披露）下 total=0、EXISTS=true → `is_portfolio_empty=false`；但 plan-02 §5 AC-03 场景 B 期望 `isPortfolioEmpty=true` | 修改 SQL 定义为 `is_portfolio_empty = (total == 0)`（仅判断当前查询结果为空即可），或修改验收标准中 Scenario B 的期望值为 `isPortfolioEmpty=false`（表示"并非完全无数据，只是最新期没有"）。前者语义更直观，推荐采纳 |
| 2 | 🔴 blocker | 架构 §6.2 场景 B vs plan-02 §5 AC-03 场景 B vs plan-05 §5 AC-03 场景 B | **`latestPeriodExists` 语义三方不一致**。架构 §6.2 场景 B 写明 `latestPeriodExists: false`（最新期未披露 → false）；plan-02 验收标准期望 `latestPeriodExists=true`；plan-05 验收标准也期望 `latestPeriodExists=true`。plan-02 SQL 定义为 `EXISTS(SELECT 1 FROM fund_portfolio WHERE fund_ts_code = :fund_ts_code)`，Scenario B 下 EXISTS=true，与 plan 验收一致但与架构矛盾。根本原因：架构中 `latestPeriodExists` 指"最新全局报告期是否有数据"（false=没有），plan 中指"该基金是否有任何历史数据"（true=有）。语义完全不同 | 需统一语义后修改。推荐方案：①保留两个布尔字段但重命名为 `hasAnyPortfolio`（是否有任何历史数据）和 `isLatestPeriodEmpty`（最新期是否为空）；②或保持字段名但修改 SQL 使之对齐架构语义：`latest_period_exists = EXISTS(SELECT 1 FROM fund_portfolio WHERE fund_ts_code = :fund_ts_code AND report_period = (SELECT MAX(report_period) FROM fund_portfolio))`。修改后需同步更新 plan-02 §5 和 plan-05 §5 的验收标准期望值 |
| 3 | 🔴 blocker | README frontmatter `execution_order` | **execution_order 与 depends_on 矛盾**。frontmatter 写 `[["plan-01"], ["plan-02", "plan-03", "plan-04"], ["plan-05"]]`，将 plan-02、03、04 放在同一并行组。但 plan-04 `depends_on: ["plan-02"]`，不可与 plan-02 同组并行执行。阶段摘要 §6 正确描述了 Phase 1 = plan-01 → plan-02（顺序），但 frontmatter 未体现 | 修改 execution_order 为 `[["plan-01"], ["plan-02", "plan-03"], ["plan-04"], ["plan-05"]]`（plan-02 完成后 plan-04 才能启动，plan-03 仅依赖 plan-01 可与 plan-02 并行或紧随其后）。同步更新 `total_phases` 和 §6 阶段摘要 |

### 建议项

| # | 严重级别 | 位置 | 问题 | 修补建议 |
| --- | --- | --- | --- | --- |
| 4 | 🟡 suggest | plan-01 §1 实现规格 + Task 列表 | **Fund 模型字段计数错误**。实现规格称 Fund 有"11 个字段"，Task 列表 Task 1 称"含 12 字段"。按架构 §7.2 Fund interface 实际有 13 个字段（含 id）或 12 个业务字段（不含 id） | 统一为"13 个字段（含 id 自增主键）"或"12 个业务字段 + id 自增主键" |
| 5 | 🟡 suggest | plan-02 §1 PortfolioResponse + plan-05 反查页标题 | **反查 API 响应缺少前端标题所需的元数据**。plan-05 反查页标题需展示"股票名称 + 最新报告期"，但 plan-02 `reverse_lookup` 返回的 `PaginatedResponse[ReverseLookupItem]` 不含顶层 `stockName` 和 `reportPeriod` | 在反查 API 响应中增加元信息结构，如 `meta: { stockName: string, reportPeriod: string }`，与持仓端点的 `isPortfolioEmpty/latestPeriodExists` 元信息风格保持一致 |
| 6 | 🟡 suggest | plan-02 §1 PortfolioResponse + plan-05 详情页标题 | **持仓 API 响应缺少报告期字段**。plan-05 详情页标题展示"最新报告期：YYYY-MM-DD"，但 plan-02 `PortfolioResponse` 结构（`{data, total, page, pageSize, isPortfolioEmpty, latestPeriodExists}`）不含 `reportPeriod` | 在 `PortfolioResponse` 中增加 `latestReportPeriod: string \| null` 字段 |
| 7 | 🟡 suggest | plan-04 §5 L1 降级验收 vs 架构 §6.1 | **列表行标注"暂无数据"与列表不 JOIN fund_portfolio 的实现矛盾未说明**。架构 §6.1 明确"列表不 JOIN fund_portfolio 表"，§6.2 step 7 要求"无持仓基金列表页行内标注'暂无数据'"。plan-04 验收 L1 要求列表行标注"暂无数据"，但未说明如何在不 JOIN fund_portfolio 的前提下获取此信息 | 在 plan-02 列表端点实现规格中增加方案说明：①在 funds 表增加 denormalized `has_portfolio` 布尔字段（由同步任务更新）；②或在列表查询中增加轻量子查询 `EXISTS(SELECT 1 FROM fund_portfolio WHERE fund_ts_code = funds.ts_code)`。方案②有索引保障性能可控 |
| 8 | 🟡 suggest | plan-03 §5 实现规格 "同步今日新披露" 按钮 | **新增 UI 功能未在架构中提及**。plan-03 实现规格第 5 节增加了"同步今日新披露"按钮，架构 §3.1 流程 C 仅描述"手动同步"和"同步指定报告期"两个入口 | 属合理扩展（用户体验优化）。建议在 plan-03 功能概要的"不在范围"之前或实现规格中标注"本计划新增，架构未提及" |
| 9 | 🟡 suggest | 架构 §8.2 L4 降级 | **L4 降级（Tushare 完全不可用）无验收覆盖**。架构定义了 L1~L4 四级降级策略，但 L4（"无法触发新同步，已有数据正常查询"）在任何 FEAT 中均无对应验收项 | 可标注"部署阶段落实"，或在 plan-03 管理端增加验收项：Tushare 不可用时管理端同步面板展示"数据源暂时不可用"提示 |

## 七、合理扩展

| 位置 | 扩展内容 | 为什么合理 |
| --- | --- | --- |
| plan-03 实现规格 §5 | 报告期下拉展示最近 8 个季度（前端硬编码或后端查询） | 架构未指定报告期选择器的具体数据源；前端硬编码或简单后端查询均符合 MVP 精神，不引入额外复杂度 |
| plan-03 实现规格 §5 | "同步今日新披露"快捷按钮 | 用户操作效率优化，复用现有同步逻辑，不增加后端复杂度。建议标注为计划层新增（见建议 #8） |
| plan-04 文件清单 | 新增 `Pagination.tsx` 通用分页组件 | 计划标注"或复用现有"，视项目现有分页组件情况灵活处理，不构成过度设计 |
| plan-05 实现规格 §5 | "全部持仓"展开按钮（加载完整列表） | 架构 §7.3 持仓端点默认 pageSize=20，展开功能提升用户体验，不违背架构约束 |
| plan-05 新增文件 | `EmptyPortfolioState.tsx` 独立空态组件 | 架构 §6.2 修复项要求区分两种空态场景，独立组件使复用和测试更清晰 |

## 八、建议补丁计划

按优先级排列应修改的 README 或 FEAT 章节：

### 必须修改（阻塞项）

1. **plan-02 §1 `get_latest_portfolio` 元信息 SQL 定义**（阻塞 #1 + #2）
   - 修改 `is_portfolio_empty` SQL 定义，同步修改 plan-02 §5 AC-03 场景 A/B 验收标准期望值
   - 统一 `latestPeriodExists` 语义：对齐架构（检查最新全局报告期）或明确重新定义并同步更新架构文档
   - 同步修改 plan-05 §5 AC-03/AC-05 中对应的期望值

2. **README frontmatter `execution_order`**（阻塞 #3）
   - 修改为 `[["plan-01"], ["plan-02", "plan-03"], ["plan-04"], ["plan-05"]]`（或 `[["plan-01"], ["plan-02"], ["plan-03", "plan-04"], ["plan-05"]]`，取决于 plan-03 是否可与 plan-02 并行）
   - 同步更新 `total_phases` 和 §6 阶段摘要描述

### 建议修改（非阻塞）

3. **plan-02 §1 PortfolioResponse 结构**（建议 #5 + #6）
   - 增加 `latestReportPeriod: string | null` 字段
   - 在反查端点响应中增加 `meta: { stockName, reportPeriod }` 结构

4. **plan-01 实现规格 §1 字段计数**（建议 #4）
   - 将"11 个字段"统一为"13 个字段（含 id 自增主键）"

5. **plan-02 §1 或 plan-04 §5 列表 L1 降级实现说明**（建议 #7）
   - 明确列表页如何在不 JOIN fund_portfolio 的前提下展示"暂无数据"标注

6. **plan-03 实现规格 §5 "同步今日新披露"标注**（建议 #8）
   - 标注为"计划层新增，架构未提及"
