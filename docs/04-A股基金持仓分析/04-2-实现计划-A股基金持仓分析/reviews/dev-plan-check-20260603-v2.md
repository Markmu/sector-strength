# 开发计划检查报告

> 本次为 **2026-06-03 第二轮检查**。第一轮报告 `dev-plan-check-20260603.md`（同日 19:09）列出 3 项 blocker + 6 项建议，声称"已全部修复"。本轮回查发现：
>
> - 3 项 blocker 修复有效（execution_order 已拆 4 组；空态字段 `isPortfolioEmpty / hasPortfolio / latestReportPeriod` 在 plan-02 §1/§5、plan-05 §5 三方已对齐）。
> - 6 项建议中 #1（字段计数）、#2（L1 降级说明）、#4（L4 降级验收）、#5/6（API 元数据）已落到位。
> - 但发现 **2 项新 blocker** + **5 项新建议**（含 1 项原建议 #8 仅做了"标注"，未实际收敛范围）。

## 一、检查对象

- 架构文档：`docs/04-A股基金持仓分析/04-1-架构文档-A股基金持仓分析.md`
- 实现计划：`docs/04-A股基金持仓分析/04-2-实现计划-A股基金持仓分析/`
- 功能数：5（plan-01 ~ plan-05）

## 二、总评

- 结论：**有阻塞问题**（2 项 blocker 需修复后才能进入实现）
- 阻塞问题数：2
- 建议项数：5

总体而言：核心闭环、ADR 约束、模块职责映射、AC 追踪矩阵、性能验收、降级策略传播均已对齐架构；新增问题集中在 **跨 FEAT 的字段/文件命名一致性** 与 **E2E 证据可执行性**。

## 三、Contract 预检

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| README frontmatter `workflow_type: create-dev-plan` | ✅ 通过 | |
| README frontmatter `org_mode: feature` | ✅ 通过 | |
| README `status: review_ready` 合法 | ✅ 通过 | 属于 `plan.readme_frontmatter_status` |
| README `execution_order` 引用真实 plan-XX | ✅ 通过 | 4 组共 5 个 plan 全部存在 |
| README `execution_order` 与 FEAT `depends_on` 一致 | ✅ 通过 | 第一轮 blocker #3 已修复：plan-03 仅依赖 plan-01，可与 plan-02 并行；plan-04 依赖 plan-02，独立一组 |
| README `total_tasks / total_task_files` 与 plan-*.md 数量一致 | ✅ 通过 | 均为 5 |
| README `total_phases` 与 execution_order 组数一致 | ⚠️ 不一致 | `total_phases: 3` 但 execution_order 拆 4 组；阶段摘要 §6 也写 3 阶段。需统一 |
| README 必备章节完整性 | ✅ 通过 | 10 个 required section 全部存在 |
| README 验收标准追踪矩阵表头 | ✅ 通过 | AC-ID / 需求原文 / 架构承接 / 计划承接 / 验证方式 / 当前状态 |
| FEAT frontmatter feat_id 与文件名一致 | ✅ 通过 | plan-01~05 全部匹配 |
| FEAT status 合法 | ✅ 通过 | 全部为 `draft`，属于 `plan.task_file_status` |
| FEAT 必备章节完整性 | ✅ 通过 | 5 个 FEAT 均包含全部 8 个 required section |
| Task/边界状态仅使用 todo/done/waived | ✅ 通过 | 全部为 `todo` |
| FEAT depends_on 引用真实存在功能 | ✅ 通过 | plan-03→plan-01、plan-04→plan-02、plan-05→plan-02/04 均正确 |

## 四、验收标准追踪

| AC-ID | 架构要求 | README 承接 | FEAT 承接 | 结论 |
| --- | --- | --- | --- | --- |
| AC-01 | 基金列表展示与搜索 | plan-02, plan-04 | plan-02 §5 AC-01 + plan-04 §5 AC-01 | ✅ 映射完整 |
| AC-02 | 基金过滤（市场 + 类型） | plan-02, plan-04 | plan-02 §5 AC-02 + plan-04 §5 AC-02 | ✅ 映射完整 |
| AC-03 | 基金详情页展示最新持仓 | plan-02, plan-05 | plan-02 §5 AC-03 + plan-05 §5 AC-03 | ⚠️ plan-02 §1 字段名已对齐，但 §6 Task 4 描述与 §9 边界场景表残留旧术语 `latest_period_exists` |
| AC-04 | 股票反查 | plan-02, plan-05 | plan-02 §5 AC-04 + plan-05 §5 AC-04 | ✅ 映射完整（含 `stockName` / `reportPeriod` 元信息） |
| AC-05 | 数据缺失的透明呈现 | plan-05 | plan-05 §5 AC-05 场景 A/B | ✅ 映射完整（依赖 plan-02 元信息已修） |
| AC-06 | 管理员手动同步基金数据 | plan-01, plan-03 | plan-01 §5 AC-06 + plan-03 §5 AC-06 | ⚠️ 验收通过 mock 错误验证 Tushare 异常，但实际 E2E spec 路径不可执行（见 blocker #2） |
| AC-07 | 同步失败的可见提示 | plan-01, plan-03 | plan-01 §5 AC-07 + plan-03 §5 AC-07 | ⚠️ 同上，E2E 不可执行 |

## 五、维度检查结果

| 维度 | 结论 | 问题数 | 摘要 |
| --- | --- | --- | --- |
| 1. 核心闭环与系统目标 | ✅ 继承良好 | 0 | Fund→Portfolio→Query 在 README §2.1 明确引用 |
| 2. 范围与非目标 | ✅ 继承良好 | 0 | P0 全部有 FEAT 承接；§2.2 非目标均未引入 |
| 3. 成功标准 | ✅ 继承良好 | 0 | 7 项定量标准（6 性能 + 1 数据缺失）已在对应 FEAT 性能验收中体现 |
| 4. 验收标准防漂移 | ⚠️ 有残留 | 1 | plan-02 §6 Task 4 + §9 边界场景表仍出现 `latest_period_exists`（已废字段名） |
| 5. ADR 约束 | ✅ 继承良好 | 0 | 6 条 ADR 全部在 README 护栏和 FEAT 实现规格中体现 |
| 6. 用户流程与状态机 | ✅ 继承良好 | 0 | 流程 A/B/C 全部覆盖；状态机无新增 |
| 7. 模块职责与系统上下文 | ⚠️ 有重复 | 1 | `useFunds.ts` 在 plan-03（标注 create）、plan-04（create）、plan-05（modify）三处出现，需明确所有权 |
| 8. 运行链路 | ✅ 继承良好 | 0 | 4 条运行链路步骤在 FEAT 实现规格中一一落地 |
| 9. 数据模型与契约 | ⚠️ 有扩展 | 1 | plan-05 §6 详情页标题声明"（公告日 YYYY-MM-DD）"，但 plan-02 §1 PortfolioResponse 元信息不返回 `annDate` |
| 10. 非功能需求 | ✅ 基本覆盖 | 0 | L4 降级已在 plan-03 §5 验收；其余 NFR 均有传播 |
| 11. 实施建议与技术选型 | ✅ 继承良好 | 0 | 技术栈一致，阶段划分合理 |
| 12. 风险与未决策项 | ✅ 继承良好 | 0 | 架构 5 项风险均有缓解，open_questions 同步为空 |
| 13. 功能拆分质量 | ✅ 继承良好 | 0 | 单 FEAT ≤ 8 task，依赖 DAG 无环 |
| 14. 可执行性 | ❌ 有阻塞 | 2 | E2E 引用 `e2e/fund-list.spec.ts` 等路径在仓库中不存在；`funds.ts` admin 端点路径与现有 admin 路由可能冲突待验证 |
| 15. 状态与报告契约 | ⚠️ 有不一致 | 1 | `total_phases: 3` 与 execution_order 4 组 + §6 阶段摘要 3 阶段三者口径不一 |
| 16. 复用声明链路验证 | ✅ 继承良好 | 0 | 3 项复用声明（AsyncTask、TushareDataSource、BaseRepository）在 FEAT 中均有正确调用描述 |

## 六、问题清单

### 阻塞问题

| # | 严重级别 | 位置 | 问题 | 修补建议 |
| --- | --- | --- | --- | --- |
| 1 | 🔴 blocker | plan-02 §6 Task 4 描述 + §9 边界场景表 | **空态元信息字段名内部残留旧术语**。§6 Task 4 写"含 `is_portfolio_empty` / `latest_period_exists` 元信息"；§9 边界场景表两行使用 `latestPeriodExists=true/false`；但 §1 元信息实际是 `is_portfolio_empty / has_portfolio / latest_report_period` 三字段，§5 验收也是 `isPortfolioEmpty/hasPortfolio/latestReportPeriod`。实现者按 Task 4 / 边界表实现会出现字段名漂移 | (1) §6 Task 4 改写为"含 `isPortfolioEmpty / hasPortfolio / latestReportPeriod` 元信息"；(2) §9 边界场景表两行改用新字段（场景 A: `isPortfolioEmpty=true, hasPortfolio=false`；场景 B: `isPortfolioEmpty=true, hasPortfolio=true`） |
| 2 | 🔴 blocker | README §9.3 + plan-04 §6 验证命令 + plan-03 §6 + plan-05 §7 验证命令 | **E2E spec 路径不可执行**。4 处 E2E 命令引用 `e2e/fund-list.spec.ts`、`e2e/fund-detail.spec.ts`、`e2e/fund-reverse-lookup.spec.ts`、`e2e/admin-fund-sync.spec.ts`（仓库根或 `pnpm e2e` 默认目录），但 `find /` 验证这些文件均不存在；实际 e2e 目录是 `web/tests/e2e/`（已有 `data-status.spec.ts`）和 `web/e2e/`。按架构要求"用户可观察功能优先使用端到端测试作为主质量门"，但 E2E 文件位置未在 README 锚定 | (1) 在 README §9.3 明确 e2e 路径（推荐沿用 `web/tests/e2e/`，命名 `fund-*.spec.ts`）并修正 `pnpm e2e` 命令；(2) 在 §10 变更记录追加本次路径确认；(3) 各 FEAT 验证命令同步修正 |

### 建议项

| # | 严重级别 | 位置 | 问题 | 修补建议 |
| --- | --- | --- | --- | --- |
| 3 | 🟡 suggest | plan-03 §1 文件清单 + plan-03 §3 "不在范围" | **`useFunds.ts` 文件所有权歧义**。plan-03 文件清单 line 44 把 `web/src/hooks/useFunds.ts` 列为 "create"，但其"不在范围"未声明 useFunds 创建；plan-04 line 40 实际负责 create；plan-05 line 42 modify。三处不冲突但容易让实现者误以为 plan-03 阶段就动 useFunds | 修改 plan-03 文件清单：把 `create web/src/hooks/useFunds.ts` 改为 `（无新文件，useTaskStatus 复用现位于 web/src/hooks/useTaskStatus.ts）`；或在 plan-03 §1 显式说明"本 plan 不创建 useFunds.ts" |
| 4 | 🟡 suggest | README frontmatter + §6 阶段摘要 | **`total_phases: 3` 与 execution_order 4 组口径不一**。frontmatter 写 3 个阶段，execution_order 拆 4 组并行批（plan-01、plan-02、plan-03∥plan-04、plan-05），§6 阶段摘要又用 3 阶段表述 | 二选一：(a) `total_phases: 4` 并把 §6 阶段摘要改为 4 阶段；(b) 合并 execution_order 为 `[["plan-01", "plan-02"], ["plan-03", "plan-04"], ["plan-05"]]` 保留 3 阶段口径但忽略 plan-04 强依赖 plan-02（不推荐）。推荐 (a) |
| 5 | 🟡 suggest | plan-05 §6 详情页标题 vs plan-02 §1 PortfolioResponse | **详情页标题声明"公告日"但 API 元信息不返回 `annDate`**。plan-05 line 73 标题文案"最新报告期：YYYY-MM-DD（公告日 YYYY-MM-DD）"，但 plan-02 §1 PortfolioResponse 元信息只返回 `latestReportPeriod`（来自 `MAX(report_period)`），未返回该报告期的 `ann_date`。按架构 §7.2 注释 `stock_name` 是 JOIN 字段、annDate 是 `fund_portfolio` 表字段，理应能取到 | 在 plan-02 §1 PortfolioResponse 元信息增加 `latestAnnDate: string \| null`；或在 plan-05 标题去掉"（公告日 YYYY-MM-DD）"片段 |
| 6 | 🟡 suggest | plan-05 §11 风险备注 | **动态路由 `[ts_code]` 含 `.` 的 Next.js 路由约束未在 E2E 验证命令中覆盖**。风险备注已点出"建议在 `router.push` 时使用 `encodeURIComponent`"，但 §7 验证命令中只有 `open http://localhost:3000/dashboard/funds/510300.SH` 直接访问，未提示 shell escape 与 Next.js 路由解析差异 | 在 §7 验证命令加一句注释：使用 `open "http://localhost:3000/dashboard/funds/510300.SH"` 引号包裹，URL 含 `.` 在 zsh 下需转义；并在 E2E 验收中加一项"详情页 URL 含 `.` 能正常解析" |
| 7 | 🟡 suggest | plan-04 §5 L1 降级验收 | **列表行内"暂无数据"标注未指明基于 `hasPortfolio` 字段**。plan-04 line 141 + line 204 验收"某基金无持仓数据时，列表中该基金行内标注'暂无数据'"，但未明确该字段来源。plan-02 §1 L1 降级说明通过子查询返回 `has_portfolio` 是上游实现，plan-04 验收项需指明消费方 | 在 plan-04 §5 L1 降级验收项加一句"基于 API 返回的 `hasPortfolio=false` 字段" |

## 七、合理扩展

| 位置 | 扩展内容 | 为什么合理 |
| --- | --- | --- |
| plan-02 §1 L1 降级方案 | 列表查询用 EXISTS 子查询 `has_portfolio = EXISTS(SELECT 1 FROM fund_portfolio WHERE fund_ts_code = Fund.ts_code)` | 解决"列表不 JOIN fund_portfolio"和"行内标注'暂无数据'"的实现冲突，索引保障性能 |
| plan-02 §1 反查元信息 | 在 `reverse_lookup` 响应中增加 `meta: { stockName, reportPeriod }` | 原架构 §7.2 ReverseLookupItem 未含此字段，但 plan-05 反查页标题确需展示，属合理契约补全 |
| plan-03 §5 "同步今日新披露"按钮 | 复用现有 `initFundPortfolio(period)` 入口的快捷按钮 | 计划层已在 §5 标注"计划层新增，架构未提及"；用户体验优化，不增加后端复杂度 |
| plan-03 §5 报告期下拉 | 默认展示最近 8 个季度（前端硬编码或后端查询） | 架构未指定选择器数据源，MVP 内合理 |
| plan-04 文件清单 | 新增 `Pagination.tsx` 通用分页组件 | 计划标注"或复用现有"，灵活处理 |
| plan-05 §5 持仓表"全部持仓"展开按钮 | 加载完整列表（无分页） | 架构 §7.3 默认 pageSize=20，展开提升 UX，不违背架构 |
| plan-05 新增文件 | `EmptyPortfolioState.tsx` 独立空态组件 | 架构 §6.2 修复项要求区分两种空态，独立组件使复用和测试更清晰 |

## 八、建议补丁计划

按优先级排列应修改的章节：

### 必须修改（阻塞项）

1. **plan-02 §6 Task 4 描述 + §9 边界场景表**（阻塞 #1）
   - §6 Task 4 改写为"含 `isPortfolioEmpty / hasPortfolio / latestReportPeriod` 元信息"
   - §9 边界场景表 line 215/216 改用新字段

2. **E2E 路径锚定**（阻塞 #2）
   - README §9.3 明确 e2e 目录为 `web/tests/e2e/`，修正 4 处 `pnpm e2e` 命令
   - plan-03/04/05 §6/§7 验证命令同步修正
   - 在 §10 变更记录追加本次路径确认

### 建议修改（非阻塞）

3. **plan-03 §1 文件清单**（建议 #3）
   - 删除 `create web/src/hooks/useFunds.ts`，或显式声明"本 plan 不创建 useFunds.ts"

4. **README frontmatter + §6 阶段摘要**（建议 #4）
   - `total_phases: 3` → 4；§6 阶段摘要改为 4 阶段

5. **plan-02 §1 PortfolioResponse 元信息 + plan-05 §6 标题**（建议 #5）
   - 二选一：在 `PortfolioResponse` 增加 `latestAnnDate` 字段；或在 plan-05 标题文案删除"（公告日 YYYY-MM-DD）"片段

6. **plan-05 §7 验证命令 + §11 风险备注**（建议 #6）
   - 验证命令加引号包裹与 shell escape 提示；E2E 验收加"详情页 URL 含 `.` 能正常解析"项

7. **plan-04 §5 L1 降级验收**（建议 #7）
   - 验收项加注"基于 API 返回的 `hasPortfolio=false` 字段"
