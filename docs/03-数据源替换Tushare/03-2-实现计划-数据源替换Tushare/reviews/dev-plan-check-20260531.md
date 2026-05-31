# 开发计划检查报告

## 一、检查对象

- 架构文档：docs/03-数据源替换Tushare/03-1-架构文档-数据源替换Tushare.md
- 实现计划：docs/03-数据源替换Tushare/03-2-实现计划-数据源替换Tushare/
- 功能数：3（plan-01, plan-02, plan-03）

## 二、总评

- 结论：**通过**
- 阻塞问题数：0
- 建议项数：2

## 三、Contract 预检

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| README workflow_type=create-dev-plan | ✅ | |
| README org_mode=feature | ✅ | |
| README status 合法 | ✅ | review_ready ∈ plan.readme_frontmatter_status |
| execution_order 引用真实 plan-XX | ✅ | plan-01, plan-02, plan-03 均存在 |
| total_tasks 与 plan-*.md 数量一致 | ✅ | 均为 3 |
| README 10 个必备章节完整 | ✅ | §1 概览 ~ §10 变更记录 |
| 追踪矩阵存在且表头正确 | ✅ | 7 条 AC，表头为 AC-ID / 需求原文 / 架构承接 / 计划承接 / 验证方式 / 当前状态 |
| plan-01 feat_id 与文件名一致 | ✅ | feat_id="plan-01" |
| plan-02 feat_id 与文件名一致 | ✅ | feat_id="plan-02" |
| plan-03 feat_id 与文件名一致 | ✅ | feat_id="plan-03" |
| 所有 FEAT 8 个必备章节完整 | ✅ | plan-01~03 均包含全部章节 |
| Task 列表状态合法（todo/done/waived） | ✅ | 全部 todo |
| 边界场景状态合法 | ✅ | 全部 todo |
| depends_on 引用真实功能 | ✅ | plan-02→plan-01, plan-03→plan-01+plan-02，无孤立引用 |
| 无残留 placeholder | ✅ | |

## 四、验收标准追踪

| AC-ID | 架构要求 | README 承接 | FEAT 承接 | 结论 |
| --- | --- | --- | --- | --- |
| AC-01 | 交易日历获取 | plan-02 | plan-02 §4, §5 | ✅ |
| AC-02 | 股票列表获取 | plan-02 | plan-02 §5 | ⚠️ list_date 字段未映射（见问题清单） |
| AC-03 | 板块列表获取 | plan-02 | plan-02 §6 | ✅ |
| AC-04 | 个股日线行情获取 | plan-02 | plan-02 §7 | ✅ 使用 pro_bar(adj='qfq')，符合 ADR-3 |
| AC-05 | 板块日线行情获取 | plan-02 | plan-02 §8 | ✅ |
| AC-06 | 数据源可切换 | plan-01, plan-03 | plan-01 §5 + plan-03 §5 | ✅ |
| AC-07 | 数据获取失败处理 | plan-02 | plan-02 §3, §5 | ✅ |

## 五、维度检查结果

| 维度 | 结论 | 问题数 | 摘要 |
| --- | --- | --- | --- |
| D1 核心闭环与系统目标 | ✅ | 0 | README §2.1 完整继承 Factory→DataSource→Model→DB 闭环 |
| D2 范围与非目标 | ✅ | 0 | P0 范围全部有 FEAT 承接，非目标未被引入 |
| D3 成功标准 | ✅ | 0 | 架构 §2.3 四条成功标准全部映射到 FEAT 验收标准 |
| D4 验收标准防漂移 | ✅ | 0 | AC-01~AC-07 完整映射；E2E 均有合理的不适用说明（纯后端，无用户可观察 UI） |
| D5 ADR 约束 | ✅ | 0 | ADR-1~6 全部在 FEAT 实现规格中体现；"不引入 DI 框架"在 plan-01 遵守 |
| D6 用户流程与状态机 | ✅ | 0 | 主流程 6 节点 + 4 关键分支全部有 FEAT 验收项覆盖 |
| D7 模块职责与系统上下文 | ✅ | 0 | 4 个架构模块（BaseDataSource/DataSourceFactory/TushareDataSource/服务层改造）全部有功能承接 |
| D8 运行链路 | ✅ | 0 | 3 条运行链路（数据初始化/TradingCalendar/数据源切换）步骤逐一落地到 FEAT 实现规格 |
| D9 数据模型与契约 | ⚠️ | 1 | plan-02 §5 get_stock_list 未映射 list_date 字段（架构 §7.2 明确要求） |
| D10 非功能需求 | ✅ | 0 | 性能目标(plan-02 §5)、重试策略(plan-02 §3)、安全(plan-02 §5)、可观测性(plan-01/02 §3)均覆盖 |
| D11 实施建议与技术选型 | ✅ | 0 | Phase A/B/C 与 plan-01/02/03 一一对应 |
| D12 风险与未决策项 | ✅ | 0 | 架构风险在 plan-02/03 风险与边界中有缓解措施；open_questions 为空已继承 |
| D13 功能拆分质量 | ✅ | 0 | 粒度合理，Task 数 4/9/6 均 ≤ 12；严格串行无循环依赖 |
| D14 可执行性 | ✅ | 0 | modify 文件已通过文件系统验证全部存在；验证命令可运行 |
| D15 状态与报告契约 | ⚠️ | 1 | README §7.2 开发状态机"当前步骤"使用 "ready-to-dev"，不在 auto_dev.current_steps 合法值中 |
| D16 复用声明链路验证 | ✅ | 0 | DataSourceFactory 复用链路正确传递，无未验证的额外复用声明 |

## 六、问题清单

| 严重级别 | 位置 | 问题 | 修补建议 | 状态 |
| --- | --- | --- | --- | --- |
| 🟡 建议 | plan-02 §5 get_stock_list | 未映射 `list_date` 字段。架构 §7.2 明确要求 `list_date` 映射（`YYYYMMDD` → date），StockInfo 模型定义了 `list_date: Optional[date]`，但 plan-02 实现规格中 StockInfo 构造未包含此字段 | 在 `StockInfo(...)` 构造中增加 `list_date=datetime.strptime(str(row['list_date']), "%Y%m%d").date() if pd.notna(row.get('list_date')) else None` | 待修补 |
| 🟡 建议 | README §7.2 开发状态机 | "当前步骤"列值为 "ready-to-dev"，不在 `auto_dev.current_steps` 合法值集合中（red-e2e / implement / green-e2e / task-review / done / blocked） | 将"当前步骤"改为 "red-e2e"（首步），或更新 workflow-schema.json 的 auto_dev.current_steps 增加 "ready-to-dev" 作为初始状态 | 待修补 |

## 七、合理扩展

| 位置 | 扩展内容 | 为什么合理 |
| --- | --- | --- |
| plan-02 §9 | health_check 使用 trade_cal(limit=1) 替代默认 get_stock_list | 架构 §9 Phase B 明确建议此优化，更轻量 |
| plan-03 §4 Task 6 | 新增全局 grep 验证无残留 AkShare 导入的 Task | 纯替换场景下确保不遗漏，属于质量门控 |
| plan-02 §7 | _symbol_to_ts_code 辅助方法 | 架构 §7.2 字段映射中隐含的转换逻辑，独立方法提高可读性 |

## 八、建议补丁计划

按优先级列出应修改的 README 或 FEAT 章节：

1. **plan-02 §5 get_stock_list**：在 `StockInfo(...)` 构造中补充 `list_date` 字段映射，与架构 §7.2 对齐。注意 AkShareDataSource 现有实现也未映射此字段（akshare_client.py:304-309），但架构明确要求 Tushare 实现，建议补上。

2. **README §7.2 开发状态机**：将 3 个 FEAT 的"当前步骤"从 "ready-to-dev" 改为合法值（如 "red-e2e"，配合 red_e2e 列的 waived 状态），或在 workflow-schema.json 的 `auto_dev.current_steps` 中增加 "ready-to-dev" 初始状态。

> 两条建议均为非阻塞项，不影响开发执行。plan-02 的 list_date 字段为 Optional，缺失不会导致运行时错误，但会造成 Tushare 数据源返回的股票信息不完整。
