# 开发计划检查报告

## 一、检查对象

- 架构文档：`docs/11-板块成分股列表/11-1-架构文档-板块成分股列表.md`
- 实现计划：`docs/11-板块成分股列表/11-2-实现计划-板块成分股列表/`（README + plan-01~04）
- 功能数：4

## 二、总评

- 结论：**有阻塞问题**
- 阻塞问题数：1
- 建议项数：6

整体计划结构完整、AC 全覆盖、ADR/状态机/数据契约继承到位，且 plan-01 的"四件套契约校验"与后端真实代码（`sectors.py:254-324`、`__init__.py`、`api.ts`）逐项核对一致，质量较高。主要风险集中在 **plan-02 对 `Pagination` 组件 props 的描述与真实代码不符**（会导致按计划描述直接实现时 TS 编译失败），以及若干可执行性细节（sectorId 可空类型、mock factory 类型来源、实施方式二选一未定）。

## 三、Contract 预检

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| README frontmatter `workflow_type=create-dev-plan` | ✅ | README frontmatter line 2 |
| README `org_mode=feature` | ✅ | line 6 |
| README `status=review_ready`（合法） | ✅ | line 3，属 `plan.readme_frontmatter_status` 合法值 |
| README `execution_order` 引用真实 plan | ✅ | `[["plan-01"], ["plan-02","plan-03"], ["plan-04"]]`，全部存在 |
| `total_tasks=4` 与 plan-*.md 数量一致 | ✅ | line 9，目录下 4 个 plan 文件 |
| 含全部 `feature_readme_required_sections` | ✅ | 概览(§1)/输入摘要(§2)/验收标准追踪矩阵(§3)/模块地图(§4)/依赖图(§5)/阶段摘要(§6)/任务总览(§7)/未决策项(§8)/执行前置(§9)/变更记录(§10) 全部齐备 |
| 验收标准追踪矩阵表头正确 | ✅ | AC-ID/需求原文/架构承接/计划承接/验证方式/当前状态 六列 |
| plan-01 文件名↔feat_id 一致 | ✅ | `plan-01-...` ↔ `feat_id: "plan-01"` |
| plan-02 文件名↔feat_id 一致 | ✅ | 同上 |
| plan-03 文件名↔feat_id 一致 | ✅ | 同上 |
| plan-04 文件名↔feat_id 一致 | ✅ | 同上 |
| 各 FEAT `status` 合法 | ✅ | 均为 `draft`，属 `plan.task_file_status` 合法值 |
| 各 FEAT 含全部 `feature_task_required_sections` | ✅ | 功能概要/文件清单/实现规格/Task 列表/验收标准/验证命令/交接上下文/风险与边界 八节齐备（逐文件核对） |
| Task 与边界场景状态仅用 todo/done/waived | ✅ | 全部为 `todo`，无非法状态 |
| waived 有原因 | N/A | 无 waived 项 |
| `depends_on` 引用真实功能 | ✅ | plan-01→[]；plan-02/03→[plan-01]；plan-04→[plan-02,plan-03]，均真实存在 |

## 四、验收标准追踪

| AC-ID | 架构要求 | README 承接 | FEAT 承接 | 结论 |
| --- | --- | --- | --- | --- |
| AC-01 | 图表下方成分股区块，强度分降序，六列+总数 | README §3 行 70（plan-02 + e2e TC） | plan-02 §验收 AC-01；plan-04 TC-1.1/TC-2.1 | ✅ 双层承接，E2E 覆盖 |
| AC-02 | 点击强度分表头切换升降序 | README §3 行 71 | plan-02 §验收 AC-02；plan-04 TC-1.2/TC-2.2 | ✅ |
| AC-03 | 点击市值表头降序，不可排序列不响应 | README §3 行 72 | plan-02 §验收 AC-03；plan-04 TC-1.3/TC-2.3 | ✅ |
| AC-04 | 翻页+切每页条数，总页数更新，滚动顶部 | README §3 行 73 | plan-02 §验收 AC-04；plan-04 TC-1.4/TC-2.4 | ✅ |
| AC-05 | 加载失败重试，图表不受影响 | README §3 行 74 | plan-02 §验收 AC-05；plan-04 TC-1.5/TC-2.5 | ✅ |
| AC-06 | 无成分股空态文案 | README §3 行 75 | plan-02 §验收 AC-06；plan-04 TC-1.6/TC-2.6 | ✅ |
| AC-07 | 点击行跳个股页，落地页不空白 | README §3 行 76 | plan-03 §验收 AC-07；plan-04 TC-1.7/TC-3.1 | ✅ |

AC-01~07 全部映射到 README 追踪矩阵 + 至少一个 FEAT；用户可观察功能（plan-02/03/04）均有 E2E-TDD（red+green）验收项，并已落地 `docs/e2e/11-e2e-用例-板块成分股列表.md`。无孤立验收项，无弱化/改写。

## 五、维度检查结果

| 维度 | 结论 | 问题数 | 摘要 |
| --- | --- | --- | --- |
| 1 核心闭环与系统目标 | ✅ 通过 | 0 | README §2.1 完整复述 Sector→Stocks→Stock 闭环；首版目标被 plan-01~04 阶段验收覆盖 |
| 2 范围与非目标 | ✅ 通过 | 0 | P0 范围（列表/排序/分页/三态/下钻/落地页）均有 FEAT；非目标（深度功能/权重/二级筛选/导出）未被引入；架构 §4.3 过度设计清单未被违反 |
| 3 成功标准 | ✅ 通过 | 0 | 架构 §2.3/§8.1 的 ≤500ms 进入 plan-02 §性能验收、plan-03 §性能验收（DevTools 人工确认） |
| 4 验收标准防漂移 | ✅ 通过 | 0 | 7 个 AC 全映射；plan-02/03 checklist 未弱化 AC；E2E-TDD red/green 两阶段证据齐全（plan-04 + 已存在的 e2e 文档） |
| 5 ADR 约束 | ✅ 通过 | 0 | ADR-1~5 均在 README §2.2 护栏表 + 各 FEAT 实现规格体现（ADR-4 在 plan-01、ADR-5 在 plan-03）；禁止事项与"不在范围"呼应；演进余地未提前实施 |
| 6 用户流程与状态机 | ✅ 通过 | 0 | 主流程节点（加载/排序/分页/下钻）有 FEAT 覆盖；错误/空/降级路径有验收项；状态枚举 Loading/Success/Empty/Error 与架构 §3.3 一致（plan-02 三态呈现） |
| 7 模块职责与系统上下文 | ✅ 通过 | 0 | 架构 §4.2 五模块在 README §4 模块地图均有承接；上下游在 depends_on / 交接上下文体现；过度设计清单遵守 |
| 8 运行链路 | ✅ 通过 | 0 | 链路 L1（成分股加载 6 步）在 plan-02 实现规格 §1/§3 一一落地；链路 L2（下钻 4 步）在 plan-03 落地；错误处理/重试（mutate）无遗漏 |
| 9 数据模型与契约 | ✅ 通过 | 0 | SectorStockItem/SectorStocksData/SectorStocksResponse 与后端 `sectors.py:309-318` + `PaginatedData` 字段一致；状态枚举对齐；snake_case 标注；`.data.data` 解包显式（plan-02 §序列化与包裹） |
| 10 非功能需求 | ✅ 通过 | 0 | 性能/错误处理/降级/安全（鉴权复用 get_current_user、sort_by 白名单）/可观测性（console.error）均落 FEAT；成本无新增（架构 §8.4） |
| 11 实施建议与技术选型 | ✅ 通过 | 0 | Next.js+SWR / FastAPI 栈与架构一致；Phase 1→2→3 划分符合依赖 DAG；未超首版范围 |
| 12 风险与未决策项 | ✅ 通过 | 0 | 架构 §8.6 三风险（getStock 字段/SectorStock 误导/sort_by 穿透）在 FEAT 风险与边界有缓解；open_questions 继承（无）；README §8 未决策项=无 |
| 13 功能拆分质量 | ✅ 通过 | 0 | 每个 FEAT 连贯；文件清单 ≤4（plan-02 最大 4，远 < 15）；Task 步骤 ≤5（plan-04 最大 5，< 12）；依赖 DAG 无环 |
| 14 可执行性 | ⚠️ 有建议 | 3 | 文件路径具体；modify 文件（api.ts/page.tsx）真实存在；但 **Pagination props 描述与真实代码不符（见问题1）**、sectorId 可空类型未处理（问题3）、plan-04 mock factory 引用的 StockDetailItem 类型无处 import（问题4） |
| 15 状态与报告契约 | ✅ 通过 | 0 | README/FEAT frontmatter 状态合法；README 展示状态与 FEAT 一致；本报告写入 `reviews/dev-plan-check-2026-07-05.md` 符合命名 pattern |
| 16 复用声明链路验证 | ✅ 通过 | 0 | 架构"复用 Pagination/SimpleSelect/CrowdRankingTable/getSectorStocks/getStock"在 FEAT 有调用描述且与可行性结论一致；无架构未提及的新复用；Pagination 默认导出 + import 路径 + props 已核对（但 props 名称描述有误，见维度17/问题1） |
| 17 前后端 API 契约一致性（代码级） | ⚠️ 有阻塞 | 1+3 | 四件套逐项核对：路径无双前缀✅、GET+鉴权✅、query snake_case✅、响应 snake_case✅、`.data.data` 解包✅、`/stocks/{id}` isdigit 与 item.id 一致✅；但 **Pagination props 描述错误（阻塞）** + pageSizeOptions 默认值偏差（建议）+ sectorId 类型未对齐（建议） |

## 六、问题清单

| 严重级别 | 位置 | 问题 | 修补建议 |
| --- | --- | --- | --- |
| blocker | plan-02 §实现规格 §3「分页器」段（约行 124） | 描述传入 Pagination 的 props 为"`total`、`page`、`pageSize`、`onPageChange`、`onPageSizeChange`"。**真实 `Pagination` 组件（`web/src/components/ui/Pagination.tsx:8-23`）props 为 `currentPage`（非 `page`）、`totalPages`、`total`、`pageSize`、`onPageChange`、`onPageSizeChange`、`pageSizeOptions`、`showPageSizeSelector`、`showJumpToPage`。** 缺 `totalPages` 且 `page` 应为 `currentPage`。按计划字面实现会 TS 编译失败；计划自述的参考模板 CrowdRankingTable 实际是 `currentPage={page}` + 自算 `totalPages`（CrowdRankingTable.tsx:121,293），与计划描述自相矛盾。 | 改写 plan-02 §3 分页器段为："复用 `Pagination`（默认导出）。需先算 `totalPages = Math.ceil(total/pageSize)`，传入 `currentPage={page}`、`totalPages`、`total`、`pageSize`、`onPageChange`、`onPageSizeChange`、`showPageSizeSelector`、`pageSizeOptions={[20,50,100]}`（参照 CrowdRankingTable.tsx:292-301 写法）。" |
| 建议项 | plan-02 §3「分页器」+ plan-02 验收 AC-04 | 真实 Pagination `pageSizeOptions` 默认 `[10,20,50,100]`（Pagination.tsx:6）；架构 §7.2 与 AC-04 要求可选 20/50/100。计划只说"pageSize 可选项 20/50/100"未显式要求传 `pageSizeOptions={[20,50,100]}`，实现者若照抄 CrowdRankingTable（其未传该 prop，渲染出 10/20/50/100）会与 AC-04 偏差。 | plan-02 §3 显式补一句"必须传 `pageSizeOptions={[20,50,100]}`（默认含 10，需覆盖）"。 |
| 建议项 | plan-02 §实现规格 §4「详情页接入」+ 风险与边界 | 详情页 `sectorId` 真实类型为 `number \| null`（`page.tsx:36` `useState<number \| null>(null)`）。plan-02 组件 props `sectorId: number`，接入 `<SectorStocksTable sectorId={sectorId} />` 时 TS 会报 `number\|null` 不可赋 `number`。页面虽在 line 152 用 `!sectorId` 提前 return 错误态（运行时到挂载点已非空），但 TS 静态类型无法收窄。 | plan-02 §4 接入写为 `<SectorStocksTable sectorId={sectorId!} />`（与页面既有 `useSectorStrengthHistory({ sectorId: sectorId! })` line 74 风格一致），并在风险与边界补"sectorId 类型为 number\|null，接入用 `!` 断言"。 |
| 建议项 | plan-04 §实现规格 §1 mock helpers + §交接上下文 | `createTestStockDetail(): StockDetailItem` 引用的 `StockDetailItem` 类型由 plan-03 在落地页"就地定义"（plan-03 §1），**未从任何 types 文件 export**，plan-04 mock factory 无处 import，TS 编译会失败。 | 二选一：(a) plan-01 契约层顺带 export `StockDetailItem`（推荐，与 SectorStockItem 同源）；或 (b) plan-04 mock factory 内联定义同名 interface。建议在 plan-01/plan-04 各补一条交接说明。 |
| 建议项 | plan-03 §实现规格 §1「数据获取」 | 同一数据获取给出两种实现方式（"建议用 SWR…也可直接复用更简单的 useEffect 模式"），未定一，属实现规格含糊。项目内既有 SWR 范式（useSectorStrengthHistory）也有直接调用范式（详情页 fetchSectors），实现者会摇摆。 | plan-03 §1 明确选 SWR（query key `/stocks/${id}`，fetcher 解包 `.data.data`），与 plan-02 hook 风格统一；删除"useEffect 也可"的备选表述。 |
| 建议项 | plan-04 §文件清单 + Task 3 | 将 `docs/e2e/11-e2e-用例-板块成分股列表.md` 标为 `create`，但该文件**已存在**（2026-07-05 生成，含完整 FEAT-02/03 TC 表 + factory + red/green 说明）。"create"动作与现状不符。 | plan-04 文件清单将该行动作改为 `modify`（或 `ensure`），Task 3 改为"对齐/补全既有 e2e 用例文档"；同时核对文档 TC 编号（TC-2.x/TC-3.x）与 plan-04 §2 场景表 TC-1.x 编号统一。 |

## 七、合理扩展

| 位置 | 扩展内容 | 为什么合理 |
| --- | --- | --- |
| plan-02 新增 `web/src/components/sector-analysis/helpers.ts`（架构未显式列出独立文件） | 把市值量级/趋势/价格/分数格式化抽成 helpers | 架构 §7.6 已要求"市值量级简写""趋势数值→箭头颜色"等 UI 格式化；plan-03 个股落地页也需复用同一格式化（plan-03 §3 显式 import）。抽独立文件避免两处重复，属合理重构，未引入新功能或新依赖。 |
| plan-04 §实现规格 §2 提到"板块详情页本身会请求 strength-history 与 ma-history 图表数据，需安装最小 mock" | E2E 进入 `/dashboard/sector-analysis/{id}` 会触发既有图表 hook 请求 | 这是落测试的必要前置（避免 401 重定向使 fixture 失效），属测试基础设施而非功能扩张；plan-04 风险与边界已声明"允许补充图表 mock 到 helpers"。 |
| plan-03 落地页新增"返回按钮"（架构 §6.2 未列） | `router.back()` 返回板块详情页 | 架构 §6.2 只要求"渲染基础信息"，但 AC-07 要求"不空白"+ 闭环可走通；返回按钮提升闭环可用性，不触及非目标（深度功能），属合理 UX 补充。 |

## 八、建议补丁计划

按优先级：

1. **[blocker] plan-02 §实现规格 §3「分页器」段**：改写 Pagination props 描述为真实签名（`currentPage`/`totalPages` + 自算 totalPages，参照 CrowdRankingTable.tsx:121,292-301），并显式加 `pageSizeOptions={[20,50,100]}`（覆盖默认 `[10,20,50,100]`）。
2. **[建议] plan-02 §4 接入 + 风险与边界**：sectorId 接入用 `sectorId!` 断言，补 number|null 类型说明。
3. **[建议] plan-01 契约层 / plan-04 mock helpers**：统一 `StockDetailItem` 类型的归属（推荐 plan-01 export，plan-04 import），消除 mock factory 编译风险。
4. **[建议] plan-03 §1 数据获取**：定一 SWR 方案，删除 useEffect 备选表述。
5. **[建议] plan-04 文件清单/Task 3**：将 e2e 用例文档动作由 `create` 改为 `modify`，并统一 TC 编号体系（TC-1.x vs TC-2.x/TC-3.x）。
6. **[建议] plan-02 AC-04**：在验收项显式写"pageSize 选择器仅显示 20/50/100（不含 10）"，与修补 1 呼应。

> 修补 1 为阻塞项，须在 plan-02 进入 ready-to-dev 前完成；其余为可执行性建议，建议一并修订以降低实现期返工。维度 1~13、15、16 全部通过，维度 17 四件套代码级核对（路径/方法/query/响应/解包/isdigit）均通过。
