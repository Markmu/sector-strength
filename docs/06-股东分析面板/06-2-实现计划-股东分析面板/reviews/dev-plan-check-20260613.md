# 开发计划检查报告

## 一、检查对象

- **架构文档**：`docs/06-股东分析面板/06-1-架构文档-股东分析面板.md`
- **实现计划**：`docs/06-股东分析面板/06-2-实现计划-股东分析面板/`
- **功能数**：4（plan-01 ~ plan-04）

## 二、总评

- **结论**：通过（有建议项）
- **阻塞问题数**：0
- **建议项数**：8

实现计划整体质量较高，架构文档的核心决策、数据契约、运行链路、验收标准均被完整继承和拆分到对应 FEAT。依赖关系正确，文件清单路径具体，验证命令可执行。以下建议项为改进精度和完整性，不影响执行。

## 三、Contract 预检

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| README frontmatter `workflow_type` | ✅ | `create-dev-plan` |
| README frontmatter `org_mode` | ✅ | `feature` |
| README `status` 合法 | ✅ | `review_ready` ∈ [`draft`, `review_ready`, `in_execution`, `in_review`, `accepted`, `released`] |
| `execution_order` 引用真实 plan-XX | ✅ | `[["plan-01"], ["plan-02", "plan-03"], ["plan-04"]]`，全部存在 |
| `total_tasks` 与 plan-*.md 数量一致 | ✅ | `total_tasks: 4`，目录下有 4 个 plan 文件 |
| README 必备章节完整 | ✅ | 概览、输入摘要、验收标准追踪矩阵、模块地图、依赖图、阶段摘要、任务总览、未决策项、执行前置、变更记录 — 10/10 |
| 验收标准追踪矩阵表头正确 | ✅ | AC-ID / 需求原文 / 架构承接 / 计划承接 / 验证方式 / 当前状态 |
| plan-01 frontmatter `feat_id` 与文件名一致 | ✅ | `plan-01` |
| plan-02 frontmatter `feat_id` 与文件名一致 | ✅ | `plan-02` |
| plan-03 frontmatter `feat_id` 与文件名一致 | ✅ | `plan-03` |
| plan-04 frontmatter `feat_id` 与文件名一致 | ✅ | `plan-04` |
| 各 FEAT `status` 合法 | ✅ | 全部 `draft` ∈ [`draft`, `ready-to-dev`, `in-progress`, `review`, `done`, `deprecated`] |
| 各 FEAT 必备章节完整 | ✅ | 功能概要、文件清单、实现规格、Task 列表、验收标准、验证命令、交接上下文、风险与边界 — 4 个文件 8/8 |
| Task 列表状态合法 | ✅ | 全部 `todo` |
| 边界场景状态合法 | ✅ | 全部 `todo`，无 `waived` |
| `depends_on` 引用真实功能 | ✅ | plan-02→plan-01, plan-03→plan-01, plan-04→plan-02 |

## 四、验收标准追踪

| AC-ID | 架构要求 | README 承接 | FEAT 承接 | 结论 |
| --- | --- | --- | --- | --- |
| AC-01 | 监控组概览展示 | plan-02, plan-04 | plan-02 §5 API 验证 + plan-04 §5 页面渲染 | ✅ 完整映射 |
| AC-02 | 监控组持仓详情查询 | plan-02, plan-04 | plan-02 §5 三个 API + plan-04 §5 详情区 | ✅ 完整映射 |
| AC-03 | 多监控组联合查询 | plan-02, plan-04 | plan-02 §5 多组 API + plan-04 §5 多选交互 | ✅ 完整映射 |
| AC-04 | 行业筛选 | plan-02, plan-04 | plan-02 §5 筛选 API + plan-04 §5 筛选交互 | ✅ 完整映射 |
| AC-05 | 变动方向筛选 | plan-02, plan-04 | plan-02 §5 变动 API + plan-04 §5 筛选交互 | ✅ 完整映射 |
| AC-06 | 管理员新增监控组 | plan-01, plan-03 | plan-01 §5 API + plan-03 §5 页面操作 | ✅ 完整映射 |
| AC-07 | 管理员编辑匹配规则 | plan-01, plan-03 | plan-01 §5 API + plan-03 §5 编辑操作 | ✅ 完整映射 |
| AC-08 | 数据未同步空状态 | plan-04 | plan-04 §5 空状态展示 | ✅ 完整映射 |
| AC-09 | 报告期切换 | plan-02, plan-04 | plan-02 §5 API + plan-04 §5 切换交互 | ✅ 完整映射 |
| AC-10 | 管理员删除监控组 | plan-01, plan-03 | plan-01 §5 API + plan-03 §5 删除操作 | ✅ 完整映射 |
| AC-11 | 报告期数据不完整降级 | plan-02, plan-04 | plan-02 §5 has_prev_period + plan-04 §5 降级提示 | ✅ 完整映射 |

**结论**：架构 AC-01 ~ AC-11 全部映射到 README 和至少一个 FEAT，无孤立验收项。

## 五、维度检查结果

| 维度 | 结论 | 问题数 | 摘要 |
| --- | --- | --- | --- |
| 1. 核心闭环与系统目标 | ✅ 继承良好 | 0 | README §2.1 完整复述核心闭环，首版目标被阶段目标和 FEAT 验收标准覆盖 |
| 2. 范围与非目标 | ✅ 继承良好 | 0 | P0 范围 4 个 FEAT 全部承接，非目标未引入。§2.2 明确列出"不引入"项 |
| 3. 成功标准 | ✅ 继承良好 | 0 | 性能目标出现在 plan-02 和 plan-04 验收标准中（<3s / <2s / <1s） |
| 4. 验收标准防漂移 | ✅ 继承良好 | 1 | AC 映射完整。建议项 S-01：E2E-TDD 验证项缺失 |
| 5. ADR 约束 | ✅ 继承良好 | 0 | 7 条 ADR 全部在 README §2.2 以"实施护栏"形式体现 |
| 6. 用户流程与状态机 | ✅ 继承良好 | 0 | 流程 A/B 关键节点均被 plan-02/plan-03/plan-04 覆盖，7 个关键分支均有对应场景 |
| 7. 模块职责与系统上下文 | ✅ 继承良好 | 0 | 模块地图、depends_on、交接上下文中均体现上下游关系 |
| 8. 运行链路 | ✅ 继承良好 | 1 | 链路步骤落地完整。建议项 S-02：overview 中报告期列表查询可独立为内部方法 |
| 9. 数据模型与契约 | ✅ 继承良好 | 2 | 契约完整对齐。建议项 S-03：SectorStock 关联方式需注意；S-04：avg_hold_float_ratio 计算方式 |
| 10. 非功能需求 | ✅ 继承良好 | 0 | 性能、错误处理、降级、安全策略均落到 FEAT。可观测性在 plan-02 中体现 |
| 11. 实施建议与技术选型 | ✅ 继承良好 | 0 | 技术栈与架构一致，阶段划分合理 |
| 12. 风险与未决策项 | ✅ 继承良好 | 0 | 架构风险在 FEAT 风险与边界中体现，open_questions 为空 |
| 13. 功能拆分质量 | ✅ 继承良好 | 0 | 每个 FEAT 连贯，Task 列表均 ≤11 步，依赖 DAG 无循环 |
| 14. 可执行性 | ✅ 继承良好 | 1 | 文件清单路径具体。建议项 S-05：modify 文件定位策略可更精确 |
| 15. 状态与报告契约 | ✅ 继承良好 | 0 | 状态合法，报告路径正确 |
| 16. 复用声明链路验证 | ✅ 继承良好 | 1 | 复用声明基本正确。建议项 S-06：require_admin import 路径精确化；S-07：BaseRepository 方法覆盖说明；S-08：SectorStock 无 ORM relationship 的查询方式 |

## 六、问题清单

| 严重级别 | 位置 | 问题 | 修补建议 |
| --- | --- | --- | --- |
| 💡 建议 | plan-04 §8 | **S-01：E2E-TDD 验证项缺失**。plan-03 和 plan-04 均声明"E2E 不适用"，通过手动验证覆盖。架构 §2.3 成功标准要求"功能正常完成"，按 contract 惯例用户可观察功能应有 E2E-TDD（red/green）验收。plan-04 是核心用户页面，包含完整交互流程 | 在 plan-04 §5 增加 E2E 验收项或在 §8 风险与边界中写明 E2E 不适用的理由（首版时间优先、后续补充 Playwright 测试）——当前已写明但可更具体。接受当前写法，标记为后续增强 |
| 💡 建议 | plan-02 §3.2 | **S-02：报告期列表查询逻辑重复**。`get_overview` 和 `get_summary` 都需要获取 DISTINCT report_period 列表和 prev_period。实现规格中分散描述，无独立内部方法 | 在 plan-02 §3 Task 1 中增加 `_get_report_periods()` 内部方法，被 get_overview 和 get_summary 共用。当前不影响执行，实现者可自行抽取 |
| 💡 建议 | plan-02 §3.4 | **S-03：SectorStock 无 ORM relationship 需显式 JOIN**。架构 §4.2 提到复用 sectors + sector_stocks，但实际代码中 SectorStock 与 Sector 之间无 ORM relationship（通过 `sector_code` 字符串关联，非 FK），也与 Stock 无 relationship（通过 `stock_code` 关联 `stocks.symbol`）。plan-02 的 `_get_industry_for_stocks` 描述为"LEFT JOIN"，实现时需使用显式 SQLAlchemy join 而非 relationship | 在 plan-02 §3.4 或交接上下文中补充说明：SectorStock 与 Sector 通过 `sector_code = sectors.code` JOIN，与 Stock 通过 `stock_code = stocks.symbol` JOIN，需使用显式 SQLAlchemy core join |
| 💡 建议 | plan-02 §3.3 | **S-04：avg_hold_float_ratio 聚合语义需明确**。架构 §7.2 SummaryResponse 中 `avg_hold_float_ratio` 描述为"平均占流通股比例"。按股票聚合后，是 AVG(每只股票的 SUM(hold_float_ratio))？还是 SUM(hold_amount) / SUM(总流通股)？由于一只股票可能被同一组内多个持有者持有，聚合方式影响结果 | 在 plan-02 实现规格 §3.3 get_summary 中明确：`avg_hold_float_ratio = AVG(每只股票的 total_hold_float_ratio)`，其中每只股票的 total_hold_float_ratio = SUM(该组内所有匹配持有者的 hold_float_ratio)。这是按股票粒度聚合后的简单平均 |
| 💡 建议 | plan-01 §2 | **S-05：modify 文件定位策略可更精确**。`server/src/models/__init__.py` 和 `server/src/repositories/__init__.py` 的修改描述为"追加到 __all__"和"追加导出"，实际还需检查是否有 import 语句需要补充 | 在 plan-01 §2 文件清单的 modify 行说明中补充："追加 import 和 __all__ 导出" |
| 💡 建议 | plan-01 §3.4 | **S-06：require_admin import 路径精确化**。实现规格中提到"Admin API 路由使用 `require_admin` 依赖注入"，实际 import 路径为 `from src.api.deps import require_admin`（非 rbac.py）。实现规格中未给出 import 路径 | 在 plan-01 §3.4 中补充 import 路径：`from src.api.deps import require_admin` |
| 💡 建议 | plan-01 §3.2 | **S-07：BaseRepository 方法覆盖说明**。plan-01 继承 BaseRepository，但 plan 的 Repository 方法（get_with_rules / get_by_id_with_rules / replace_rules）均为自定义扩展。BaseRepository 提供的 get/list/create/update/delete 基本方法在 Service 中可能直接使用（如 create_group 中 create ShareholderGroup） | 在 plan-01 §3.2 或 §3.3 中说明：ShareholderGroupService 的 create_group 直接使用 BaseRepository.create()，update 使用 BaseRepository.update()，delete 使用 BaseRepository.delete()，自定义 Repository 方法仅用于需要 join rules 的查询场景 |
| 💡 建议 | plan-02 §3 | **S-08：多组联合查询的聚合去重语义**。架构 §6.2 提到"先获取所有组的关键词，合并后一次性 LIKE 匹配，按 (symbol, holder_name) 去重后再聚合"。plan-02 §3.1 描述了 `_match_holdings(group_ids, report_period)`，但未明确说明多组时关键词合并和去重的具体实现 | 在 plan-02 §3.1 `_match_holdings` 方法描述中补充：多组时先获取所有 group_ids 的关键词合并为一个大列表，一次性对 top10_float_holders 做 LIKE OR 匹配，匹配结果按 (symbol, holder_name) 去重后聚合为按 symbol 维度的统计 |

## 七、合理扩展

| 位置 | 扩展内容 | 为什么合理 |
| --- | --- | --- |
| plan-04 §5 | 新增"全流程验收（US 覆盖矩阵）"，将架构 §2.3 成功标准中的 US-01~US-07 以用户故事形式映射到验证方式 | 架构文档未要求 US 编号映射，但 plan-04 作为最终用户页面，用 US 矩阵确保端到端覆盖是合理的质量增强 |
| plan-04 §5 | 新增"降级回归验收"，覆盖架构 §8.2 的 L1~L3 降级策略 | 架构文档的降级策略在 §8.2 中定义，plan-04 将其细化为可验证的前端场景，属于合理的前端质量关注 |
| plan-03 §3 | 管理端编辑表单使用 debounce 500ms 调用 preview API | 架构 §6.4 未规定 debounce 间隔，这是合理的前端性能优化 |

## 八、建议补丁计划

按优先级列出应修改的 README 或 FEAT 章节：

1. **plan-02 §3.1 `_match_holdings`**：补充多组时关键词合并 + (symbol, holder_name) 去重的具体语义（S-08）✅ 已应用
2. **plan-02 §3.4 `_get_industry_for_stocks`**：补充 SectorStock/Sector/Stock 的显式 JOIN 条件说明（S-03）✅ 已应用
3. **plan-02 §3.3 `get_summary`**：明确 avg_hold_float_ratio 的聚合计算方式（S-04）✅ 已应用
4. **plan-01 §3.4 Admin API**：补充 `from src.api.deps import require_admin` import 路径（S-06）✅ 已应用
5. **plan-01 §2 文件清单**：modify 行补充"追加 import 和 __all__ 导出"说明（S-05）✅ 已应用
6. **plan-01 §3.2 Repository**：说明 BaseRepository 基本方法在 Service 中的使用方式（S-07）✅ 已应用
7. **plan-02 §3 Task 列表**：增加 `_get_report_periods()` 内部方法以复用报告期查询逻辑（S-02）✅ 已应用
8. **plan-04 §8 E2E 说明**：增强 Playwright E2E 补充计划，含 red/green TDD 和 docs/e2e/ 路径（S-01）✅ 已应用
