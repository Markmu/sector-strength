# 开发计划检查报告

## 一、检查对象

- 架构基准：`docs/FEAT-0002-market-margin.md`（status: approved，`<frozen-after-approval>` 锁定；本期无独立 17-1 架构文档，spec 即唯一需求基准）
- 范式母本（继承关系对照）：`docs/16-A股全市场量价指标/16-1-架构文档-A股全市场量价指标.md` + `docs/16-A股全市场量价指标/16-2-实现计划-A股全市场量价指标/`
- 实现计划：`docs/17-融资融券数据同步与首页曲线图/17-2-实现计划-融资融券数据同步与首页曲线图/`（README.md + plan-01~plan-08）
- 功能数：8
- 检查日期：2026-08-14
- 检查方式：spec 全量承接核对 + D1~D5 决策一致性 + 真实代码锚点抽查（约 22 处）+ 依赖图推演 + E2E 约定核对

## 二、总评

- 结论：**通过**（无阻塞问题，2 个建议项）
- 阻塞问题数：0
- 建议项数：2（W1 spec 冻结区内部矛盾已由计划正确裁定、W2 plan-07 一处类型注释残留）
- 特别确认（本轮重点）：**D5 右轴口径为 rqye+rzmre，全计划无 rqmcl 入图残留**；plan-07 曾误写 rqye+rqmcl 已修正，并在"路径一致性说明"中显式记录了该裁定。唯一的残留是 MarginPoint.rqmcl 的注释文字（见 W2），不在图表配置、验收标准、E2E 断言任何实质位置。

## 三、Contract 预检

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| README frontmatter `workflow_type: create-dev-plan` | 通过 | L2 |
| README frontmatter `org_mode: feature` | 通过 | L7 |
| README `status: draft` ∈ readme_frontmatter_status | 通过 | 合法枚举 |
| `execution_order` 只引用真实 plan-XX | 通过 | 6 组全部指向 plan-01~08 真实文件 |
| `total_tasks`=8 与 plan-*.md 数量一致 | 通过 | total_tasks=8、total_task_files=8 |
| README 含 feature_readme_required_sections 全部 10 章节 | 通过 | 概览/输入摘要/验收标准追踪矩阵/模块地图/依赖图/阶段摘要/任务总览/未决策项/执行前置/变更记录齐备 |
| 追踪矩阵表头固定 | 通过 | `AC-ID / 需求原文 / 架构承接 / 计划承接 / 验证方式 / 当前状态` 与 contract 逐字一致 |
| plan 文件名 plan-XX 与 feat_id 一致 | 通过 | 8/8 |
| plan `status: draft` ∈ task_file_status | 通过 | 8/8 |
| plan 正文含 feature_task_required_sections 8 章节 | 通过 | 功能概要/文件清单/实现规格/Task 列表/验收标准/验证命令/交接上下文/风险与边界，8/8 齐 |
| Task 与边界场景状态只用 todo/done/waived | 通过 | 全部 todo，无非法值 |
| waived 有同行原因 | 通过 | README §7.2 状态机 red/green=waived 行均带"E2E 豁免：…"理由 |
| depends_on 引用真实功能 | 通过 | 全部可解析 |
| 报告命名/目录 contract | 通过 | 本报告按 workflow-schema `plan_review_pattern` 落 reviews/ |

## 四、验收标准追踪

| AC-ID | 架构要求（spec） | README 承接 | FEAT 承接 | 结论 |
| --- | --- | --- | --- | --- |
| AC-1 | 聚合正确（SSE+SZSE 求和、rzrqye 重算 1.88e12） | 追踪矩阵 L73 → plan-03 | plan-03 §5：spec 数值用例逐字段断言（1.8E12/8.0E10/1.1E11/1.88E12）+ 脏 rzrqye 重算断言 | 通过 |
| AC-2 | 幂等 upsert（覆盖非新增、updated_at 刷新） | L74 → plan-03 | plan-03 §5：同日两次恰一行 + updated_at 变化断言；§2 显式 func.now()（16 期 S1 教训） | 通过 |
| AC-3 | 同步任务互斥（重复触发被拒） | L75 → plan-04 | plan-04 §5：真 PG advisory lock 并发仅一成功（第二个 None）；plan-05 端点侧互斥 message | 通过 |
| AC-4 | 端点校验（end>today 拒绝不建任务） | L76 → plan-05 | plan-05 §5：五项校验逐一 + async_tasks 无新行断言 | 通过 |
| AC-5 | 查询缺口（缺失日 null、hasMissingDates、points=区间交易日数） | L77 → plan-06 | plan-06 §5：5 日轴 3 日数据场景 + 无 0/前值填充 + 七键契约断言 | 通过 |
| AC-6 | 首页面板（4 卡片 + 双 Y 轴 + legend + 切换） | L78 → plan-07 | plan-07 §5：E2E red/green 4 场景（渲染/切换/缺口/空错态） | 通过（右轴口径见 §六 W1/W2） |
| AC-7 | 同步面板（进度/明细/历史记录） | L79 → plan-08 | plan-08 §5：E2E red/green 4 场景（Tab/闭环/前端拦截/失败展开） | 通过 |
| AC-8 | 通用入口封堵（POST /admin/tasks 拒绝） | L80 → plan-04 | plan-04 §5：封堵用例 + 消息含 `POST /api/v1/admin/init/margin` 提示；plan-05 联动复跑 | 通过 |

REQ 承接：REQ-1→plan-02、REQ-2→plan-01、REQ-3→plan-03、REQ-4→plan-04、REQ-5→plan-05、REQ-6→plan-06、REQ-7→plan-07、REQ-8→plan-08，一一对应无遗漏。

边界承接：

- **必须**（4 条）：三大范式复用（D3 upsert→plan-03、D4 fencing→plan-04、缺口 null→plan-06）；margin 汇总接口+全市场合并不拆交易所（D1→plan-02/03）；ECharts 复用+÷1e8（D5→plan-07）；五字段求和+rzrqye 重算（D2→plan-03，"禁止直接 Σ row['rzrqye']" 双处强调）。全部承接。
- **先问**：spec"先问：无"→ README §8 未决策项=无，一致。
- **禁止**（3 条）：margin_detail 不引入（plan-02 不在范围+README D1）；不改动 market-metrics 现有代码逻辑（plan-04 §4 硬约束 + 16 期任务系统回归硬门槛 + plan-05/06"不动 16 期行"对称扩展）；不引入新图表库/状态管理库（plan-07 复用 echarts-for-react dynamic + SWR）。全部在"不在范围"或实现规格中呼应，无违反。

## 五、维度检查结果

| 维度 | 结论 | 问题数 | 摘要 |
| --- | --- | --- | --- |
| 1 核心闭环与系统目标 | 通过 | 0 | README §2.1 完整复述"拉取→聚合→存储→触发→展示"闭环与 spec 意图 |
| 2 范围与非目标 | 通过 | 0 | P0 全承接；非目标三禁止全呼应；无越界 P1/P2 |
| 3 成功标准 | 通过 | 0 | spec 无定量标准；plan-06 P95≤500ms、plan-07 单 ECharts 实例为合理量化补充 |
| 4 验收标准防漂移 | 通过 | 0 | AC-1~8 全映射（见 §四）；plan-07/08 有 red/green 两阶段证据要求与 docs/e2e 落点 |
| 5 ADR 约束（D1~D5） | 通过 | 0 | README §2.2 五决策逐条落地到 plan（见下"关键决策一致性"） |
| 6 用户流程与状态机 | 通过 | 0 | 触发→任务终态→展示全链路；校验拒绝/互斥/缺口/空态/错误重试/取消/recovery 均有验收项 |
| 7 模块职责与系统上下文 | 通过 | 0 | README §4 与 spec 代码地图一一对应；上下游在 depends_on+交接上下文体现 |
| 8 运行链路 | 通过 | 0 | 采集→聚合→任务→触发→查询→展示逐步落地；同步/异步边界、回滚、不降级旧批次一致 |
| 9 数据模型与契约 | 通过 | 0 | 六指标 Numeric(20,2)+唯一约束；MarginPoint 七键 / MarginTaskResult camelCase 三方（plan-04/06/07/08）逐字段一致；Decimal→float 显式且禁止字符串输出 |
| 10 非功能需求 | 通过 | 0 | 安全（require_admin/401/403/参数化/不透传 max_retries）、性能、错误回滚、可观测性、任务超时扫描全落地 |
| 11 实施建议与技术选型 | 通过 | 0 | 技术栈与母本一致；3 阶段符合依赖；未超首版范围 |
| 12 风险与未决策项 | 通过 | 0 | 各 plan 风险与边界含暂停条件；plan-04 标注最大风险面并列 16 期回归硬门槛 |
| 13 功能拆分质量 | 通过 | 0 | 8 功能各连贯；Task 最多 9 步（plan-04）≤12；DAG 无环 |
| 14 可执行性 | 通过 | 0 | 路径具体；modify 文件均真实存在（锚点实测）；验证命令可直接运行；red→implement→green 可留证 |
| 15 状态与报告契约 | 通过 | 0 | draft 合法；README §7.2 与 frontmatter 一致；报告未改动任何计划文件 |
| 16 复用声明链路验证 | 通过 | 0 | 复用方法实测存在：TradingCalendarRepository.get_record(:164)/refresh_range(:42)/get_trading_days(:172)、TaskFenceContext.lock_and_validate、AsyncTask.to_dict() 含 `"result"` 原样透传（async_task.py L79）、useTaskStatus options(enabled/pollInterval/onComplete/onFailed/onCancelled)+返回 cancel()；调用细节（签名/import/参数语义）写清 |
| 17 前后端 API 契约（代码级） | 通过 | 0 | 四件套：`/margin/trend` × baseURL `/api/v1` 无双前缀（后端 /api+/v1+/margin 挂载链实测）；GET 走 apiClient 带鉴权；query `range` 无风格歧义、body snake_case；响应 camelCase+float 与 MarginPoint 一致；`{success,data}` 包裹与 SWR 两层解包（res.data={success,data} 再 .data）与 MarketMetricsPanel 现行范式一致；`/admin/init/margin` × `/api/v1` 同理 |

### 关键决策一致性（本轮校验重点 2）

| 决策 | README | 落地 | 结论 |
| --- | --- | --- | --- |
| D1 margin 汇总接口 | §2.2 D1 | plan-02：`pro.margin(trade_date=)` 不传 fields、无分页、margin_detail 禁止 | 一致 |
| D2 五字段求和+rzrqye 重算 | §2.2 D2 | plan-03 §1 步骤 3：五字段 Σ + `rzrqye=Σrzye+Σrqye`，"禁止直接 Σ row['rzrqye']"；plan-02 声明 rzrqye 仅透传排查用 | 一致 |
| D3 单表日期级 upsert | §2.2 D3 | plan-01（唯一约束+索引+Numeric(20,2)）+ plan-03（on_conflict_do_update(trade_date) + 显式 updated_at + commit/rollback） | 一致 |
| D4 fencing 范式 | §2.2 D4 | plan-04：9001003/9001004 新 key 不冲突、FENCED_TASK_TYPES 集合化、create_exclusive_task 映射解析、stale 恢复参数化（旧方法薄包装保回归）、RESERVED 封堵 + 专用端点提示 | 一致 |
| D5 双 Y 轴右轴 rqye+rzmre | §2.2 D5（"rqmcl 股口径不入图、仅存类型与数据契约"） | plan-07：series 4 条 yAxisIndex 分配 rzye(0)/rzrqye(0)/rqye(1)/rzmre(1)；legend 4 项；验收标准与 E2E 断言均 rqye/rzmre；交接上下文"路径一致性说明"显式记录修正 | 一致（唯一残留为 W2 注释文字） |

### 代码锚点抽查（本轮校验重点 3，共 22 处全中）

| plan 引用锚点 | 实测 | 结果 |
| --- | --- | --- |
| task_handlers.py:92（SYNC_MARKET_METRICS 旁加新枚举） | L92 正是 `SYNC_MARKET_METRICS = "sync_market_metrics"` | 命中 |
| task_handlers.py:1876（sync_market_metrics_task 范式） | L1876 `@TaskRegistry.register(TaskType.SYNC_MARKET_METRICS)`、L1877 def | 命中 |
| task_handlers.py helper L1758 起（_build/_persist/_finalize） | L1758 `def _build_market_metrics_result(`，camelCase 注释与 plan-04 转述一致 | 命中 |
| task_manager.py:28（RESERVED_TASK_TYPES） | L28 `RESERVED_TASK_TYPES = {"sync_market_metrics"}` | 命中 |
| task_manager.py:38-39（锁 key 常量旁） | L38/39 `MARKET_METRICS_LOCK_KEY=9001001`/`OWNER=9001002` | 命中 |
| task_manager.py:508（create_exclusive_task） | L508 def | 命中 |
| task_manager.py:724（recover_stale_market_metrics_tasks） | L724 def | 命中 |
| task_fence.py:36 / :144（FENCED_TASK_TYPE / 类型校验） | L36 常量、L144 `if task.task_type != FENCED_TASK_TYPE` | 命中 |
| market_metrics_service.py:328 / :805 / :839-843 | L328 sync_date、L805 _atomic_upsert、L839-843 显式 updated_at 注释+`func.now()` | 命中 |
| tushare_client.py:115 / :1662 / :1711 / :1923 | _execute_with_retry / _df_to_rows / _decimal_field / get_market_daily_quotes 行号逐一相符 | 命中 |
| api.ts:9 / :649 / :1627 | API_BASE_WITH_PREFIX / initMarketMetrics / marketMetricsApi 行号相符 | 命中 |
| dashboard/page.tsx:69（MarketMetricsPanel 挂载点） | L69 `{!isLoading && <MarketMetricsPanel />}` | 命中 |
| data/page.tsx:15-22 / :106-116 / :127 | DataTab 联合类型 15-22、market-metrics 按钮 106-117、挂载 L127 | 命中 |
| admin/__init__.py L24/L46、v1/__init__.py L27/L49 | import 与 include_router 行号相符 | 命中 |
| admin/tasks.py:140（RESERVED 拒绝） | L140 `if request.task_type in RESERVED_TASK_TYPES:` | 命中 |
| init_market_metrics.py :80/:86/:94（三项校验锚点） | L80 起止倒置、L86 end>today、L94 跨度 | 命中 |
| market_metrics.py:103（trend Query pattern） | L103-113 与 plan-06 转述的 str+pattern 范式逐字一致 | 命中 |
| alembic head `a7d2e9f4c1b8` | versions 目录最后一个文件 `2026_08_15_0001-a7d2e9f4c1b8_add_async_task_result.py` | 命中 |
| MarketMetricsPanel.tsx L34-44/L67-70/L88-105 | dynamic/formatBillion/useSWR 行号相符 | 命中 |
| MarketMetricsSyncPanel.tsx 679 行、L44 TASK_TYPE | wc -l=679、L44 常量 | 命中 |
| useTaskStatus.ts L14-28 TaskData + options + cancel | 全部存在（result 字段当前缺失，正是 plan-08 Task 1 要加的，与现状吻合） | 命中 |
| index_monitor.py:55-80 helper | L55 `_serialize_value`、`_dict_to_camel` 同区间 | 命中 |

### 依赖图与 execution_order（本轮校验重点 4）

- mermaid 边与各 plan frontmatter `depends_on` 完全一致（plan-03:[01,02]、plan-04:[03]、plan-05:[04]、plan-06:[01,03]、plan-07:[06]、plan-08:[05,07]），无环。
- execution_order 6 组拓扑序合法：[01,02]→[03]→[04]→[05,06]→[07]→[08]，每组依赖均在前序组完成（用户关注的 plan-06 depends_on plan-01/03：01 在组 1、03 在组 2，先于组 4 ✓）。
- 并行声明有依据：plan-01（models+alembic）与 plan-02（tushare_client）文件不相交；plan-05（admin/__init__.py）与 plan-06（v1/__init__.py）文件不相交。
- 关键路径声明自洽：01→03→04→05→08 与 01→03→06→07→08 均 5 节点 4 边同长，"在 plan-08 前汇入"表述准确。
- 17 期拆分偏离母本处（handler 划入 plan-04 而非 16 期 plan-05）在 README §5 与 plan-04/05 功能概要三处显式说明理由，无矛盾。

### E2E 约定（本轮校验重点 5）

- plan-01~06：§5 均有"E2E 不适用"声明 + 理由（纯数据/采集/服务/API 层；用户可见效果由 plan-07/08 间接验证）；plan-04（task handler 执行验证：真实触发→等待终态→查库）与 plan-05（路由级 ASGITransport 执行验证）标注"不豁免"，README §7.2 状态机对应行 waived 均带理由。符合 skill"严格的不适用说明"要求。
- plan-07：完整 red/green——用例文档 `docs/e2e/17-e2e-用例-融资融券面板.md`（符合 `{requirement}-e2e-用例-{name}.md` 命名 contract，16 期先例 `16-e2e-用例-市场量价面板.md` 实存）+ spec + mock helper（母本 `mock-market-metrics-api.ts` 实存）+ 4 个 Given/When/Then 场景 + 证据路径 `docs/e2e/evidence/plan-07-e2e-{red|green}-{date}.md`。
- plan-08：同构完整（母本 `market-metrics-sync.spec.ts`/`mock-market-metrics-sync-api.ts` 实存）+ 4 场景 + 证据路径。

## 六、问题清单

| 严重级别 | 位置 | 问题 | 修补建议 |
| --- | --- | --- | --- |
| ⚠️ W1 | `docs/FEAT-0002-market-margin.md`（spec 冻结区自身，非计划缺陷） | spec 三处右轴口径不一致：REQ-7 写"右轴千亿级 rqye+**rzmre**"，任务清单 T7 写"右轴 rqye+**rqmcl**"，AC-6 写"右轴 rqye/**rqmcl**"。计划统一采用 rqye+rzmre（REQ-7 正文口径 + 已确认的修正意图），plan-07 交接上下文"路径一致性说明"已显式记录"曾误写 rqye+rqmcl（股口径与元混轴）已修正"；README 追踪矩阵 AC-6"需求原文"栏为概括转述（"4 卡片 + 双 Y 轴 + 范围切换"），未引入矛盾字样。计划侧无残留矛盾，但 spec 冻结文档与计划字面差异持续存在 | 计划无需修改。若要消除字面冲突需人工重新协商修改 frozen spec（记录本轮裁定即可）；实施者以 plan-07 为准 |
| ⚠️ W2 | plan-07-首页融资融券面板.md §1 类型定义（MarginPoint.rqmcl 行） | 注释写"融券卖出量（股，**显示层 ÷1e8 转亿股**）"——rqmcl 不入曲线图、4 张卡片亦不含 rqmcl，不存在 rqmcl 的显示层换算场景。该注释是修正前的旧口径残留文字，可能误导实现者为 rqmcl 做显示层处理（实质配置、验收标准、E2E 断言均无此要求，故仅注释级） | 将该行注释改为"（股，不入图，仅保留数据契约）"；一行改动，不影响其他章节 |

无 blocker。

## 七、合理扩展

| 位置 | 扩展内容 | 为什么合理 |
| --- | --- | --- |
| plan-02 §2 | 七字段非负复验、行 trade_date 一致性、exchange_id 非空校验 | 保障 AC-1 聚合输入质量，继承 16 期 `_build_market_daily_quote` 同款惯例，非新造 AC |
| plan-03 §边界 | 行数≠2 全部行求和 + WARNING | 求和口径天然兼容交易所扩展，与 spec"全市场合计"一致 |
| plan-06 §2 | latest/hasMissingDates 判据取 rzye；日历空表"未初始化"错误 | 16 期同位裁定（volume_shares）；"不伪造日期"符合零 Provider 约束 |
| plan-08 §3 | 默认日期近 1 年（today−364）；dateResults 懒加载 50 条 | 前者来自 spec 澄清"历史范围=近1年"；后者防 DOM 爆炸（1 年≈240+ 交易日），均有母本先例 |
| plan-01 §3 | 迁移文件名 `2026_08_15_0002` 替代 spec 的 `2026_08_14_XXXX` | head 已推进至 2026_08_15_0001，保持文件名单调递增，链条事实以 down_revision 为准，已显式标注偏离 |
| plan-04 §2 | MARGIN_LOCK_KEY=9001003 / MARGIN_OWNER_LOCK_KEY=9001004；recover_stale 参数化+旧方法薄包装 | 沿用 16 期"创建互斥锁与 owner 锁分 key"裁定且不撞号；薄包装保证既有调用方零改动 |
| plan-07 §3 | tooltip 显示完整精度原始值（元/股） | 卡片亿单位外的补充可观测性，不违背 ÷1e8 展示层口径 |

## 八、建议补丁计划

按优先级：

1. **P2（文字级）**：plan-07 §1 `MarginPoint.rqmcl` 注释由"（股，显示层 ÷1e8 转亿股）"改为"（股，不入图，仅保留数据契约）"——消除修正后的最后一处旧口径文字残留。
2. **P3（记录级，可选）**：在 README 变更记录或 plan-07"路径一致性说明"处补一句"spec T7/AC-6 字面 rqmcl 系冻结前笔误，以 REQ-7 正文 rqye+rzmre 为准"——当前说明已实质表达此意，此为强化可追溯性，非必需。

除上述两处文字级建议外，实现计划可按 README §9.2 execution_order 直接进入执行（plan-01/02 可并行起步），无需先行修改任何计划文件。
