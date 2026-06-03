# 开发计划检查报告

> 本次为 **2026-06-03 第三轮检查**（回查）。
>
> 第二轮报告 `dev-plan-check-20260603-v2.md` 列出 2 项 blocker + 5 项建议，声称已修复。本轮重点验证修复有效性并做全维度回查。
>
> **结论：2 项 blocker 修复有效，5 项建议均已落地（含 1 处残留瑕疵）。无新 blocker，发现 2 项轻微建议。**

## 一、检查对象

- 架构文档：`docs/04-A股基金持仓分析/04-1-架构文档-A股基金持仓分析.md`
- 实现计划：`docs/04-A股基金持仓分析/04-2-实现计划-A股基金持仓分析/`
- 功能数：5（plan-01 ~ plan-05）

## 二、总评

- 结论：**通过**
- 阻塞问题数：0
- 建议项数：2（均为轻微格式/一致性项，不影响实现）

核心闭环、ADR 约束、模块职责映射、AC 追踪矩阵、性能验收、降级策略（L1~L4）、安全策略、复用声明链路均已完整对齐架构。实现计划可进入执行阶段。

## 三、v2 修复验证

| v2 问题 | 修复状态 | 验证详情 |
| --- | --- | --- |
| 🔴 Blocker #1: plan-02 §6/§9 旧字段名 | ✅ 已修复 | §6 Task 4 现为 `isPortfolioEmpty / hasPortfolio / latestReportPeriod`；§9 边界场景表全部使用新字段名 |
| 🔴 Blocker #2: E2E 路径未锚定 | ✅ 已修复 | README §9.3 已锚定 `web/tests/e2e/`；plan-03/04/05 验证命令统一使用 `pnpm e2e -- tests/e2e/*.spec.ts` |
| 🟡 建议 #3: useFunds.ts 所有权 | ✅ 已修复（有残留） | plan-03 文件清单已加注"实际由 plan-04 创建"，但 action 列仍为 `create`（见建议 #1） |
| 🟡 建议 #4: total_phases 口径 | ✅ 已修复（有残留） | frontmatter 已改为 4，§6 阶段摘要已改 4 阶段，但 §1 概览"总阶段数"仍为 3（见建议 #2） |
| 🟡 建议 #5: latestAnnDate 字段 | ✅ 已修复 | plan-02 §1 元信息新增 `latestAnnDate`；plan-05 标题逻辑补充"为 NULL 则省略" |
| 🟡 建议 #6: 动态路由 E2E | ✅ 已修复 | plan-05 §5 新增 E2E 强化项"URL 含 `.` 正确解析"；§11 风险备注同步更新 |
| 🟡 建议 #7: L1 降级字段来源 | ✅ 已修复 | plan-04 §5 明确"基于 API 返回的 `hasPortfolio=false` 字段" |

## 四、Contract 预检

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| README frontmatter `workflow_type: create-dev-plan` | ✅ 通过 | |
| README frontmatter `org_mode: feature` | ✅ 通过 | |
| README `status: review_ready` 合法 | ✅ 通过 | 属于 `plan.readme_frontmatter_status` |
| README `execution_order` 引用真实 plan-XX | ✅ 通过 | 4 组共 5 个 plan 全部存在 |
| README `execution_order` 与 FEAT `depends_on` 一致 | ✅ 通过 | plan-03 仅依赖 plan-01 可与 plan-02 并行；plan-04 依赖 plan-02 |
| README `total_tasks / total_task_files` 与 plan-*.md 数量一致 | ✅ 通过 | 均为 5 |
| README `total_phases` 与 execution_order 组数一致 | ⚠️ 轻微不一致 | frontmatter 已为 4（匹配 4 组），但 §1 概览"总阶段数"仍写 3（见建议 #2） |
| README 必备章节完整性 | ✅ 通过 | 10 个 required section 全部存在 |
| README 验收标准追踪矩阵表头 | ✅ 通过 | AC-ID / 需求原文 / 架构承接 / 计划承接 / 验证方式 / 当前状态 |
| FEAT frontmatter feat_id 与文件名一致 | ✅ 通过 | plan-01~05 全部匹配 |
| FEAT status 合法 | ✅ 通过 | 全部为 `draft`，属于 `plan.task_file_status` |
| FEAT 必备章节完整性 | ✅ 通过 | 5 个 FEAT 均包含全部 8 个 required section |
| Task/边界状态仅使用 todo/done/waived | ✅ 通过 | 全部为 `todo` |
| FEAT depends_on 引用真实存在功能 | ✅ 通过 | 所有引用均有效 |

## 五、验收标准追踪

| AC-ID | 架构要求 | README 承接 | FEAT 承接 | 结论 |
| --- | --- | --- | --- | --- |
| AC-01 | 基金列表展示与搜索 | plan-02, plan-04 | plan-02 §5 AC-01 + plan-04 §5 AC-01 | ✅ 完整 |
| AC-02 | 基金过滤（市场 + 类型） | plan-02, plan-04 | plan-02 §5 AC-02 + plan-04 §5 AC-02 | ✅ 完整 |
| AC-03 | 基金详情页展示最新持仓 | plan-02, plan-05 | plan-02 §5 AC-03 + plan-05 §5 AC-03 | ✅ 完整 |
| AC-04 | 股票反查 | plan-02, plan-05 | plan-02 §5 AC-04 + plan-05 §5 AC-04 | ✅ 完整 |
| AC-05 | 数据缺失的透明呈现 | plan-05 | plan-05 §5 AC-05 场景 A/B | ✅ 完整 |
| AC-06 | 管理员手动同步基金数据 | plan-01, plan-03 | plan-01 §5 AC-06 + plan-03 §5 AC-06 | ✅ 完整 |
| AC-07 | 同步失败的可见提示 | plan-01, plan-03 | plan-01 §5 AC-07 + plan-03 §5 AC-07 | ✅ 完整 |

## 六、维度检查结果

| 维度 | 结论 | 问题数 | 摘要 |
| --- | --- | --- | --- |
| 1. 核心闭环与系统目标 | ✅ 继承良好 | 0 | Fund→Portfolio→Query 在 README §2.1 明确引用 |
| 2. 范围与非目标 | ✅ 继承良好 | 0 | P0 全部有 FEAT 承接；§2.2 非目标（8 项）均未引入 |
| 3. 成功标准 | ✅ 继承良好 | 0 | 7 项定量标准已在对应 FEAT 性能/功能验收中体现 |
| 4. 验收标准防漂移 | ✅ 继承良好 | 0 | 旧字段名已全部清理；E2E-TDD red/green 要求覆盖所有用户可观察功能 |
| 5. ADR 约束 | ✅ 继承良好 | 0 | 6 条 ADR 全部在 README 护栏和 FEAT 实现规格中体现；禁止项未提前实施 |
| 6. 用户流程与状态机 | ✅ 继承良好 | 0 | 流程 A/B/C 全部覆盖；5 个关键分支均有验收项 |
| 7. 模块职责与系统上下文 | ✅ 继承良好 | 0 | 6 个架构模块均有对应 FEAT；上下游依赖在 depends_on 和交接上下文中体现 |
| 8. 运行链路 | ✅ 继承良好 | 0 | 4 条运行链路（§6.1-6.4）在 FEAT 实现规格中一一落地；错误处理和重试无遗漏 |
| 9. 数据模型与契约 | ✅ 继承良好 | 0 | Fund/FundPortfolio Schema 对齐；API 边界 6 端点一致；状态枚举对齐；数据来源标注清楚 |
| 10. 非功能需求 | ✅ 继承良好 | 0 | 性能目标（5 项）、降级策略（L1~L4）、安全（4 项）、可观测性均有传播和验收项 |
| 11. 实施建议与技术选型 | ✅ 继承良好 | 0 | 技术栈一致；阶段划分合理；未超出首版范围 |
| 12. 风险与未决策项 | ✅ 继承良好 | 0 | 5 项架构风险均有缓解措施；open_questions 同步为空 |
| 13. 功能拆分质量 | ✅ 继承良好 | 0 | 单 FEAT ≤ 8 task；依赖 DAG 无环；mixed FEAT 前后端接口对齐 |
| 14. 可执行性 | ✅ 继承良好 | 0 | 文件路径具体；modify 文件可定位；验证命令可运行；E2E 路径已锚定 |
| 15. 状态与报告契约 | ✅ 继承良好 | 0 | 状态合法；报告路径符合 contract |
| 16. 复用声明链路验证 | ✅ 继承良好 | 0 | 3 项复用声明（AsyncTask、TushareDataSource、BaseRepository）在 FEAT 中均有正确调用描述；外部表依赖（stocks）已说明 |

## 七、问题清单

无阻塞问题。

### 建议项

| # | 严重级别 | 位置 | 问题 | 修补建议 |
| --- | --- | --- | --- | --- |
| 1 | 🟢 minor | plan-03 §1 文件清单 line 44 | **useFunds.ts action 列残留 `create`**。描述已加注"实际由 plan-04 创建"，但 action 列仍为 `create`，实现者可能误以为 plan-03 需创建该文件 | 将 action 改为 `—`（无动作）或整行删除，仅保留说明文字 |
| 2 | 🟢 minor | README §1 概览 line 29 | **"总阶段数: 3" 与 frontmatter `total_phases: 4` 不一致**。v2 修复了 frontmatter 和 §6 但遗漏了 §1 | 改为 `总阶段数: 4` |

## 八、合理扩展

（与 v2 一致，无新增）

| 位置 | 扩展内容 | 为什么合理 |
| --- | --- | --- |
| plan-02 §1 L1 降级方案 | 列表查询用 EXISTS 子查询 `has_portfolio` | 解决"列表不 JOIN fund_portfolio"和"行内标注暂无数据"的实现冲突，索引保障性能 |
| plan-02 §1 反查元信息 | `ReverseLookupResponse` 增加 `stockName / reportPeriod` | 原架构 ReverseLookupItem 未含此字段，但反查页标题需展示，属合理契约补全 |
| plan-02 §1 PortfolioResponse 元信息 | 增加 `latestAnnDate` | 原架构未显式要求，但 plan-05 详情页标题需展示公告日，属于链路补全 |
| plan-03 §5 "同步今日新披露"按钮 | 复用现有 `initFundPortfolio(period)` 的快捷入口 | 计划层已标注"计划层新增"；用户体验优化，不增加后端复杂度 |
| plan-04 新增 Pagination.tsx | 通用分页组件（标注"或复用现有"） | 灵活处理 |
| plan-05 §5 "全部持仓"展开按钮 | 加载完整列表（无分页） | 架构默认 pageSize=20，展开提升 UX |
| plan-05 EmptyPortfolioState.tsx | 独立空态组件 | 架构 §6.2 要求区分两种空态，独立组件便于复用和测试 |

## 九、建议补丁计划

均为非阻塞项，可在执行前或执行中顺手修复：

1. **plan-03 §1 line 44**（建议 #1）— 将 useFunds.ts 行的 action 改为 `—` 或删除该行
2. **README §1 line 29**（建议 #2）— "总阶段数: 3" → "总阶段数: 4"
