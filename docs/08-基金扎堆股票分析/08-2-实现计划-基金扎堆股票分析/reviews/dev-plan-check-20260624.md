---
workflow_type: dev-plan-check
status: done
source_architecture: docs/08-基金扎堆股票分析/08-1-架构文档-基金扎堆股票分析.md
source_plan_dir: docs/08-基金扎堆股票分析/08-2-实现计划-基金扎堆股票分析
checked_at: "2026-06-24"
verdict: pass
blockers: 0
suggestions: 2
---

# 开发计划检查报告：08-2 实现计划-基金扎堆股票分析

## 一、检查对象

- **架构文档**（SSOT）：`docs/08-基金扎堆股票分析/08-1-架构文档-基金扎堆股票分析.md`（status: review_ready，arch-check 已通过）
- **实现计划目录**：`docs/08-基金扎堆股票分析/08-2-实现计划-基金扎堆股票分析/`
- **功能数**：3（plan-01 后端聚合 API / plan-02 前端扎堆分析页 / plan-03 前端下钻反查复用 04）
- **PRD**（AC 交付标准）：`docs/08-基金扎堆股票分析/08-0-需求设计-基金扎堆股票分析.md`（prd-doc-check 已通过，AC-01~08 共 8 条）

## 二、总评

- **结论**：**通过**（无 blocker，2 项建议改进）
- **阻塞问题数**：0
- **建议项数**：2（均非阻塞，不影响进入实现阶段）
- **能否进入 auto-dev / implementer**：**可以**。架构决策逐项继承完整，AC-01~08 全覆盖，路径前缀代码级核对无重复，前后端契约四件套对齐，两个非阻塞改进项已纳入交付，复用声明带 file:line 经抽查全部真实存在。

## 三、Contract 预检

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| README `workflow_type: create-dev-plan` | ✅ | frontmatter 命中 |
| README `org_mode: feature` | ✅ | frontmatter 命中 |
| README `status: in_review` | ✅ | 属合法枚举（`in_review`）|
| README `execution_order` 引用真实 plan | ✅ | `[plan-01, plan-02, plan-03]` 三者均存在 |
| README `total_tasks: 3` 与 plan 数一致 | ✅ | 3 个 `plan-*.md` |
| README 必备章节（10 项）| ✅ | 概览/输入摘要/验收标准追踪矩阵/模块地图/依赖图/阶段摘要/任务总览/未决策项/执行前置/变更记录 全齐 |
| README 验收追踪矩阵表头 | ✅ | `\| AC-ID \| 需求原文 \| 架构承接 \| 计划承接 \| 验证方式 \| 当前状态 \|` 固定格式 |
| FEAT frontmatter `feat_id` 与文件名一致 | ✅ | plan-01/02/03 三者对齐 |
| FEAT `status` 合法 | ✅ | 三者均 `ready-to-dev`，属合法枚举 |
| FEAT 必备章节（8 项）| ✅ | 功能概要/文件清单/实现规格/Task 列表/验收标准/验证命令/交接上下文/风险与边界 三份全齐 |
| Task 步骤状态合法 | ✅ | 全 `todo`，无 `waived` |
| `depends_on` 引用真实功能 | ✅ | plan-02→plan-01、plan-03→plan-01+plan-02，DAG 无循环 |
| README §7.2 状态机与 FEAT frontmatter 一致 | ✅ | 三者均为 `ready-to-dev`，`当前步骤` 均 `todo` |

## 四、验收标准追踪矩阵（架构 §2.4 ↔ README ↔ FEAT）

| AC-ID | 架构要求（§2.4 + 链路） | README 承接（§3 + §10） | FEAT 承接 | 结论 |
| --- | --- | --- | --- | --- |
| AC-01 扎堆度排行榜展示 | FundCrowdAPI.rankings + 链路 6.1（MAX(report_period) + GROUP BY stock_symbol + COUNT DISTINCT fund_ts_code 降序）| plan-01 + plan-02 | plan-01 §3 #1.2/#2.1 + §5 `test_rankings_returns_active_scope_only` / `test_rankings_order_by_fund_count_desc`；plan-02 §5 场景 1 | ✅ 充分承接 |
| AC-02 主动/被动口径切换 | scope=active/all + ADR-1 WHERE invest_type 过滤（含 NULL `.is_(None)` 显式处理）| plan-01 + plan-02 | plan-01 §3 #1.2 NULL 处理 + §5 `test_rankings_all_scope_includes_passive`；plan-02 §5 场景 2 | ✅ 充分承接（NULL 处理已落实）|
| AC-03 环比变化（含新进）| ADR-3 跨期 Python 内存对比 + is_new 三态 | plan-01 + plan-02 | plan-01 §3 #2.3 `_compute_changes` + §5 `test_rankings_change_computation`；plan-02 §3 #5 环比列渲染规则 + §5 场景 3 | ✅ 充分承接 |
| AC-04 行业分布展示 | ADR-5 复用 sectors/sector_stocks，主指标=扎堆股数量占比 | plan-01 + plan-02 | plan-01 §3 #1.3/#2.4 + §5 `test_industry_distribution_active_scope` / `test_industry_distribution_multi_industries_per_stock`；plan-02 §3 #4 + §5 场景 4 | ✅ 充分承接 |
| AC-05 下钻反查 + 返回口径/位置保持 | ADR-4 复用 04 reverse-lookup（≥1% 硬编码）+ from 参数 + sessionStorage + 提示文案 | plan-03 | plan-03 §3 #1-#3 + §5 场景 8/9 + 04 侧 3 场景 | ✅ 充分承接（独立承接）|
| AC-06 上期数据缺失降级 | has_prev_period=false 分支，环比统一 null | plan-01 + plan-02 | plan-01 §3 #2.3 has_prev_period=False 分支 + §5 `test_rankings_no_prev_period_returns_null_changes`；plan-02 §3 #5 hasPrevPeriod 统一「—」+ §5 场景 5 | ✅ 充分承接 |
| AC-07 持仓数据未同步空状态 | has_data=false 整页空状态 | plan-01 + plan-02 | plan-01 §3 #2.1 空表分支 + §5 `test_rankings_empty_portfolio_returns_has_data_false`；plan-02 §3 #6 isPortfolioEmpty 分支 + §5 场景 6 | ✅ 充分承接 |
| AC-08 排行榜内搜索 | search SQL WHERE 过滤（代码前缀 LIKE / 名称包含 ILIKE）+ 无结果提示 | plan-01 + plan-02 | plan-01 §3 #2.2 路径 A（SQL WHERE）+ §5 `test_rankings_search_by_code_prefix` / `_by_name_contains` / `_no_match` / `_escapes_like_wildcards`；plan-02 §3 #5 搜索框 + §5 场景 7 | ✅ 充分承接（含 SQL 注入回归）|

> AC-01~08 全部映射到 README 追踪矩阵 + 至少一个 FEAT，无落空、无重复。每个 AC 在 FEAT 验收标准与验证命令中可追溯。

## 五、维度检查结果

| 维度 | 结论 | 问题数 | 摘要 |
| --- | --- | --- | --- |
| 1 核心闭环与系统目标 | ✅ 继承良好 | 0 | README §2.1 完整复述核心闭环 Portfolio→Aggregate→Rank→Drilldown + 零存储新增判断 |
| 2 范围与非目标 | ✅ 继承良好 | 0 | P0 范围 6 项全有 FEAT 承接；非目标 8 项在 README §2.4 + 各 plan「不在范围」呼应；无 P1/P2 提前实施 |
| 3 成功标准 | ✅ 继承良好 | 0 | 性能指标（排行榜 <3s、行业分布 <2s）在 plan-01 §3 #8 + §5 性能验收；功能性指标由 AC pytest/E2E 覆盖 |
| 4 AC 防漂移 | ✅ 继承良好 | 0 | 见第四节，8 条 AC 全覆盖；用户可观察功能（plan-02/03）均有 Playwright E2E red/green 两阶段证据要求 |
| 5 ADR 约束 | ✅ 继承良好 | 0 | ADR-1~7 在 README §2.2 护栏表逐条映射到 FEAT；禁止事项（缓存层/新反查端点/复合加权/报告期选择）在「不在范围」呼应 |
| 6 用户流程与状态机 | ✅ 继承良好 | 0 | 流程 A/B/C 节点在 plan-02 §3 #6 主页面状态管理覆盖；状态机（Loading/Ready/SwitchingScope/Searching/Drilldown/EmptyData）在 plan-02 边界场景表对齐 |
| 7 模块职责与系统上下文 | ✅ 继承良好 | 0 | README §4 模块地图 + §5 依赖图体现 FundCrowdRepository/Service/API/前端组件上下游；depends_on 链路 plan-01→plan-02→plan-03 合理 |
| 8 运行链路 | ✅ 继承良好 | 0 | 链路 6.1（排行榜加载 5 步）在 plan-01 §3 #2.1 逐步落地；6.2（行业分布）在 §3 #2.4；6.3（下钻反查 6 步）在 plan-03 §3 #1-#3 |
| 9 数据模型与契约 | ✅ 继承良好 | 0 | RankingItem/IndustryItem Schema 在 plan-01 §3 #3 + plan-02 §3 #1 完全对齐；isNew 三态、totalFloatRatio 可空、date→ISO、Decimal→float 序列化约定均显式；响应包裹 `{success, data}` 一致 |
| 10 非功能需求 | ✅ 继承良好 | 0 | 性能（plan-01 §3 #8）、错误处理/降级 L1-L5（plan-01/02 边界场景表）、安全（`_escape_like_keyword` + `Query(le=100)` + JWT）、可观测性（logger.info/exception）均落地 |
| 11 实施建议与技术选型 | ✅ 继承良好 | 0 | 技术栈与架构一致；Phase A（后端）→Phase B（前端）划分符合依赖；未超首版范围 |
| 12 风险与未决策项 | ✅ 继承良好 | 0 | 架构 §8.6 风险表 6 项在 plan-01/02/03 风险与边界有缓解；open_questions 为空（架构 §5.x 已确认）|
| 13 功能拆分质量 | ✅ 继承良好 | 0 | 3 个 FEAT 各自连贯（后端语义/前端呈现/下钻闭环）；Task 列表 plan-01=9 / plan-02=12 / plan-03=8 步，plan-02 略多但含 mock+spec 合理 |
| 14 可执行性 | ✅ 继承良好 | 0 | 文件清单路径具体（含 modify 的 brownfield 真实文件）；验证命令可运行；red/green 顺序可执行留证；前置条件可验证 |
| 15 状态与报告契约 | ✅ 继承良好 | 0 | README/FEAT frontmatter 合法；状态机与 frontmatter 一致；本报告写入 `{plan-dir}/reviews/` |
| 16 复用声明链路验证 | ⚠️ 基本继承（1 处行号偏差）| 1 | 复用声明均带 file:line，抽查 12+ 处全部真实存在；唯一偏差：plan-01 §3 #4/#9 声明 `_escape_like_keyword` 参照 `shareholder_group_service.py:86-95`，实际定义在 line **87**（off-by-one），且 `shareholder_analysis_service.py:37` 也有同名函数。不影响实现 |
| 17 前后端 API 契约（代码级）| ⚠️ 基本一致（1 处文档内矛盾）| 1 | 路径前缀/HTTP 方法/query 命名/响应字段四件套代码级核对通过；唯一矛盾：plan-01 §1 概要 curl 示例用 `pageSize=20`（camelCase），与 §3 #4 契约校验 + README §2.4 + plan-02 §3 #1 声明的 `page_size`（snake_case）不一致，属文档内"半改"，非阻塞 |

## 六、问题清单

| 严重级别 | 位置 | 问题 | 修补建议 |
| --- | --- | --- | --- |
| 建议（非阻塞）| `plan-01-后端基金扎堆度聚合查询API.md` §1 功能概要 line 15 | curl 示例 `GET /api/v1/fund-crowd-analysis/rankings?scope=active&page=1&pageSize=20` 用了 camelCase `pageSize`，与同文件 §3 #4 契约校验（line 491「前端必须传 `page_size` 不是 `pageSize`」）+ README §2.4 + plan-02 §3 #1 三处声明矛盾。implementer 看 §3 #4 能写对，但文档自相矛盾 | 将 §1 概要的 curl 示例改为 `page_size=20`（snake_case），与全文统一 |
| 建议（非阻塞）| `plan-01-后端基金扎堆度聚合查询API.md` §3 #4（line 282）+ §3 #9（line 588）| `_escape_like_keyword` 参照位置声明为 `shareholder_group_service.py:86-95`，实际定义在该文件 line **87**（off-by-one）；且 `shareholder_analysis_service.py:37` 也有同名实现（plan-01 已复用该服务的 `_compute_change_directions`/`_get_industry_for_stocks`，从同文件 import 更内聚）| 行号改为 `:87-95`；或建议从 `shareholder_analysis_service.py:37` import（与 plan-01 其他复用声明同源，减少跨服务依赖）|

> 无 blocker。两项建议均为文档一致性/精确性改进，不影响 implementer 按 plan 执行。

## 七、合理扩展

| 位置 | 扩展内容 | 为什么合理 |
| --- | --- | --- |
| plan-01 §3 #2.2 | 提供 search 过滤「路径 A（SQL WHERE）」与「路径 B（Python 层）」两种实现，推荐 A | 架构 §6.1 step g 只说「search 在 SQL WHERE 层过滤」，plan 给出两种实现路径并推荐 A，帮助 implementer 理解权衡（分页 total 正确性），不违背架构 |
| plan-01 §3 #7 | pytest 用例扩展到 18 个（架构未列具体数量）| 覆盖更全（含 SQL 注入回归、L2/L3 降级、权限回归），是合理加严，不弱化架构要求 |
| plan-02 §3 #4 | `CrowdIndustryDistribution` tooltip 增加「合计占流通比」参考字段 | 架构 §7.2 IndustryItem 已含 `totalFloatRatio` 字段，plan 在 tooltip 展示是合理消费，贴合 PRD §3.3「辅以合计占流通比作为参考」 |
| plan-02 §3 #5 | 环比列渲染规则细化（先判 hasPrevPeriod → 再判 isNew → 最后数值）| 架构 §3.3 状态机只描述状态转移，plan 给出渲染顺序避免 AC-06 场景误显示新进标识，是必要的实现细节 |
| plan-03 §3 #3.4 | 发现并要求修改 04 反查页 `syncUrl` 保留 `from` 参数（line 77-86）| 架构 §6.3 未提及此细节，plan 在代码级核对中发现 `syncUrl` 的 `router.replace` 会丢失 `from`，主动补充修改，是高质量的 brownfield 复用边界识别 |

## 八、架构关键技术决策继承核查（逐项）

> 对应任务要求的 7 类架构关键技术决策，逐项核对 FEAT 继承情况。

| 架构决策 | 继承位置 | 结论 |
| --- | --- | --- |
| **扎堆度聚合**：GROUP BY stock_symbol + COUNT(DISTINCT fund_ts_code) 主 + SUM(stk_float_ratio) 辅，**持仓计入无 ≥1% 阈值**（存在即重仓）| plan-01 §3 #1.2 `get_crowd_aggregation` SQL（line 82-114）无 stk_mkv_ratio 阈值；§5 测试 #4 `test_rankings_total_float_ratio_sum` 验证 SUM | ✅ 完整继承 |
| **主动/被动口径**：invest_type IN ('被动指数型','增强指数型') 为被动；主动 = NOT IN (...) OR invest_type IS NULL（**NULL 处理**）| plan-01 §3 #1.2 line 95-100 `or_(Fund.invest_type.notin_(PASSIVE), Fund.invest_type.is_(None))`；§3 #2 常量 `PASSIVE_INVEST_TYPES`；§5 测试 #1/#4 显式覆盖 001004.OF invest_type=None 归主动；plan-01 §8 风险备注重申 | ✅ NULL 处理已落实（ADR-1 风险对策到位）|
| **环比**：current/prev 两期聚合 + Python 内存对比 + is_new 判定；has_prev_period=false 时环比 null | plan-01 §3 #2.1 步骤 3-4（两期聚合）+ §3 #2.3 `_compute_changes`（dict 对比 + is_new + has_prev_period=False 全 null 分支）；§5 测试 #5/#6 覆盖 | ✅ 完整继承（ADR-3）|
| **报告期** max(report_period) 为最新期、次大为上一期 | plan-01 §3 #1.1 `get_report_periods` DISTINCT DESC LIMIT 4；§3 #2.1 periods[0]=current、periods[1]=prev | ✅ 完整继承 |
| **行业分布**：扎堆股数量占比为主，复用 06 `_get_industry_for_stocks` | plan-01 §3 #1.3 `get_industry_for_stocks`（JOIN 范式参照 `shareholder_analysis_service.py:304-352`）+ §3 #2.4 行业聚合（一股多行业独立计数 + 未分类桶）；§5 测试 #12/#13/#14 | ✅ 完整继承（ADR-5）|
| **双轨下钻（S-3）**：复用 04 reverse-lookup 端点（≥1% 硬编码）+ 前端 from 参数 + 提示文案 + sessionStorage 状态恢复 | plan-03 §3 #1（sessionStorage 写入 + router.push 带 from）+ §3 #3（04 反查页 from 条件渲染 + 差异提示文案，与架构 §7.6 文案一字不差）+ §3 #2（返回状态恢复含 scroll）；§5 场景 8/9 + 04 侧 3 场景；plan-03 §3 #3.4 发现并修补 syncUrl 保留 from | ✅ 完整继承（ADR-4）|
| **性能**：不引入缓存 | plan-01 §1 不在范围「引入缓存层 / 预计算表 / 物化视图」+ §3 #10 非阻塞索引优化（依赖索引非缓存）；README §2.4 ADR-6 护栏 | ✅ 完整继承（ADR-6）|

## 九、两个非阻塞改进项落地核查

| 改进项 | 架构/arch-check 标注 | FEAT 落地位置 | 结论 |
| --- | --- | --- | --- |
| 索引前缀 `(report_period, stock_symbol)` | arch-check 标注；现有 `ix_fund_portfolio_symbol_period (stock_symbol, report_period)` 前缀不利于 WHERE report_period 过滤 | plan-01 §1 目标 + §2 文件清单（alembic 迁移）+ §3 #10 完整 upgrade/downgrade + Task 9 + §5 验收（含降级为运维手动建索引的暂停条件）| ✅ 已纳入交付（plan-01）|
| scroll 位置恢复 | arch-check 标注 | plan-03 §1 概要 + §3 #2（requestAnimationFrame + setTimeout 时机处理）+ Task 5 + §5 验收（允许 ±50px 误差）+ 场景 9（scrollY 断言）| ✅ 已纳入交付（plan-03）|

> 代码级核实：现有索引 `ix_fund_portfolio_symbol_period` + `ix_fund_portfolio_fund_period` 在 `server/src/models/fund_portfolio.py:27-28` 确认存在，plan-01 新增 `(report_period, stock_symbol)` 前缀索引确实与之互补（非重复），合理。

## 十、路径前缀代码级核对结论（维度 17 重点）

> 项目踩过双前缀 404 坑，必须代码级核对，不能只信 plan 声明。

### 后端路径拼装（实测）

| 层级 | 文件:line | 前缀 |
| --- | --- | --- |
| 应用挂载 | `server/main.py:113` | `app.include_router(api_router, prefix="/api")` |
| v1 主路由 | `server/src/api/v1/__init__.py:25` | `APIRouter(prefix="/v1")` |
| 子路由（plan-01 声明）| plan-01 §3 #4 `fund_crowd_analysis.py` | `APIRouter(prefix="/fund-crowd-analysis")` |
| endpoint | plan-01 §3 #4 | `@router.get("/rankings")` / `@router.get("/industry-distribution")` |

**最终后端路径**：`/api` + `/v1` + `/fund-crowd-analysis` + `/rankings` = `/api/v1/fund-crowd-analysis/rankings` ✅

### 前端 endpoint 拼装（实测）

| 层级 | 文件:line | 值 |
| --- | --- | --- |
| apiClient.baseURL | `web/src/lib/api.ts:8` | `API_BASE_WITH_PREFIX = ${API_BASE_URL}/api/v1` |
| endpoint（plan-02 声明）| plan-02 §3 #1 line 120 | `/fund-crowd-analysis/rankings`（不带 /v1）|

**最终请求 URL**：`http://localhost:8000/api/v1/fund-crowd-analysis/rankings` ✅ **无重复前缀**

### 四件套核对

| 项 | 后端（plan-01）| 前端（plan-02）| 一致性 |
| --- | --- | --- | --- |
| 路径 | `/api/v1/fund-crowd-analysis/rankings` | endpoint × baseURL = 同 | ✅ 一致 |
| HTTP 方法 | `@router.get` | `apiClient.get`（ApiClient 类有 get 方法）| ✅ 一致 |
| query 参数命名 | `scope` / `search` / `page` / `page_size`（snake_case）| `page_size: params.pageSize` 写 query 时转 snake_case（line 125）| ✅ 一致（与 04 `fundsApi.reverseLookup` line 428 同风格）|
| 响应字段命名 | `{success, data}` 外层 + `data.items[].stockSymbol` 等 camelCase（`_dict_to_camel` 转换）| TS 类型用 `stockSymbol/fundCount/isNew` 等 camelCase | ✅ 一致 |
| 响应解包层级 | 路由返回 `{success, data}` | fetcher `.then(res => res.data)` 解一层拿 body，组件读 `data.data` 取业务对象 | ✅ 一致（与 `useShareholderOverview`/`useFundList` 同范式）|

> 路径前缀代码级核对结论：**无重复前缀，无前缀缺失，前后端契约四件套完全对齐**。MEMORY `dev-plan-check 路径前缀验证` 要求满足。

## 十一、复用声明抽查（架空检测）

> 抽查 plan 中带 file:line 的复用声明，确认真实存在。

| 复用声明 | 声明位置 | 实测位置 | 结论 |
| --- | --- | --- | --- |
| `BaseRepository.__init__(model, session)` | plan-01 §3 #1（声明 base.py:18/29）| `server/src/repositories/base.py:18`（class）+ `:29`（__init__）| ✅ 真实 |
| `FundPortfolio` 字段 fund_ts_code/report_period/stock_symbol/stk_float_ratio | plan-01 §3 #1（声明 fund_portfolio.py:14-21）| `server/src/models/fund_portfolio.py:14-21` | ✅ 真实（7 字段全中）|
| `_compute_change_directions` 范式 | plan-01 §3 #2（声明 shareholder_analysis_service.py:264-302）| `:264` | ✅ 真实 |
| `_get_industry_for_stocks` JOIN 范式 | plan-01 §3 #1.3（声明 :304-352）| `:304` | ✅ 真实 |
| 04 reverse-lookup 阈值硬编码 | plan-01/03（声明 fund_repository.py:376）| `:376`（`FundPortfolio.stk_mkv_ratio >= 1.0`）| ✅ 精确命中 |
| 04 `/funds/reverse-lookup` 端点 | plan-03（声明 funds.py:196-238）| `funds.py:196`（`@router.get("/reverse-lookup")`）| ✅ 真实 |
| `_dict_to_camel` helper | plan-01 §3 #4（声明参照 funds.py）| `funds.py:118` | ✅ 真实 |
| `fundsApi.reverseLookup`（query snake_case 范式）| plan-02 §3 #1（声明 api.ts:415-432）| `api.ts:415`（page_size line 428）| ✅ 真实 |
| `shareholderAnalysisApi` 命名范式 | plan-02 §3 #1（声明 api.ts:892+）| `api.ts:892` | ✅ 真实 |
| `useReverseLookup` hook | plan-03（声明 useFunds.ts:108-145）| `useFunds.ts:108` | ✅ 真实 |
| `createTestOverview` + `hasPrevPeriod` 开关 | plan-02 §3 #9（声明 mock-shareholder-analysis-api.ts:126-189）| `:126`（hasPrevPeriod line 127/131）| ✅ 真实 |
| `matchApiPath` helper | plan-02 §3 #9（声明从 mock-api 或 helper import）| `mock-shareholder-analysis-api.ts:37` | ✅ 真实 |
| IndustryDistribution 双轨标签范式 | plan-02 §3 #4（声明 :22-26/54-100/121-156）| dynamic :23、yAxis :81、series :86、industry-bar :137 | ✅ 真实 |
| 04 反查页 `syncUrl` | plan-03 §3 #3.4（声明 reverse-lookup/page.tsx:77-86）| `:77`（确认未 set from）| ✅ 真实（且 plan 主动发现需修改）|
| `get_current_user` 依赖 | plan-01 §3 #4（声明 src.api.deps）| `server/src/api/deps.py:71` | ✅ 真实 |
| `ApiResponse{success, data}` | plan-01 §3 #4（声明 schemas/response.py）| `response.py:14`（success :25 / data :26）| ✅ 真实 |

> 抽查 16 处复用声明，全部真实存在，无架空。file:line 精度高（仅 `_escape_like_keyword` 一处 off-by-one）。

## 十二、测试方式适配核查

| FEAT | 测试方式 | 参照 | 证据命名 | 结论 |
| --- | --- | --- | --- | --- |
| plan-01（后端）| pytest API 集成测试 + `--no-cov` | `server/tests/test_fund_api.py` | `plan-01-08-pytest-red/green-{date}.md` | ✅ 符合 MEMORY `后端 FEAT E2E 适配 pytest` + `pytest 单文件加 --no-cov` |
| plan-02（前端）| Playwright E2E | `shareholder-analysis.spec.ts` + `mock-shareholder-analysis-api.ts` | `plan-02-08-e2e-red/green-{date}.md` | ✅ 符合前端用户可观察功能主质量门 |
| plan-03（前端）| Playwright E2E（追加场景）| `fund-reverse-lookup.spec.ts` + `fund-crowd-analysis.spec.ts` | `plan-03-08-e2e-red/green-{date}.md` | ✅ 符合前端跨页闭环测试 |

> 三者测试方式与 MEMORY 既有约定一致，证据命名带 `-08-` 后缀避免与 06/07 旧证据冲突（README §7.2 已说明）。

## 十三、建议补丁计划

按优先级列出应修改的文档章节（均非阻塞，可在 implementer 执行前或执行中修补）：

1. **plan-01 §1 功能概要 line 15**：curl 示例 `pageSize=20` → `page_size=20`（与 §3 #4 契约校验统一）
2. **plan-01 §3 #4 line 282 + §3 #9 line 588**：`_escape_like_keyword` 参照行号 `:86-95` → `:87-95`；或建议改从 `shareholder_analysis_service.py:37` import（与同 plan 其他复用声明同源）

## 十四、最终结论

**评级：通过（pass）**。

- 架构 7 类关键技术决策（聚合口径/主动被动 NULL 处理/环比/报告期/行业分布/双轨下钻/性能无缓存）逐项完整继承，无弱化、无漂移
- AC-01~08 全部映射到 README 追踪矩阵 + 至少一个 FEAT，无落空、无重复，每个 AC 有 pytest 或 Playwright 可追溯验证
- 路径前缀代码级核对：后端 `/api/v1/fund-crowd-analysis/rankings` × 前端 endpoint × baseURL，**无重复前缀、无缺失**，四件套（路径/方法/query/response）完全对齐
- 两个非阻塞改进项（索引前缀 / scroll 恢复）已分别纳入 plan-01 / plan-03 交付
- 复用声明抽查 16 处全部真实存在，无架空
- 测试方式适配（后端 pytest / 前端 Playwright）符合 MEMORY 既有约定
- 2 项建议改进（curl 示例 query 风格 / escape_like 行号）均为文档一致性/精确性问题，不影响 implementer 按 plan 执行

**可以进入 auto-dev / implementer 实现阶段**。建议 implementer 在执行 plan-01 时顺手修补 §1 curl 示例；执行 §3 #4 search 实现时用 grep 定位 `_escape_like_keyword` 实际位置（两处定义均可）。
