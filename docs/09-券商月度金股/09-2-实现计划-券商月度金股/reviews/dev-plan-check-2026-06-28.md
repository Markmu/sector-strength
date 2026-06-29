# 开发计划检查报告

> 检查方法：dev-plan-check skill（17 维度 + Contract 预检 + 复审修复彻底性 grep 全量核查）
> 检查日期：2026-06-28
> 本次为更新后首次复审（recheck 场景），已按"复审与修复彻底性"原则对变更 A/B/OQ 三项做 grep 全量核查 + 维度 17 读真实代码核对契约。

## 一、检查对象

- 架构文档（基准 / Source of Truth）：`docs/09-券商月度金股/09-1-架构文档-券商月度金股.md`（workflow_type: arch-gen, status: done）
- 实现计划：`docs/09-券商月度金股/09-2-实现计划-券商月度金股/`
- 功能数：3（plan-01 数据层与同步服务 / plan-02 后端查询服务与 API / plan-03 前端页面与组件）

## 二、总评

- **结论：有建议项（无阻塞）**
- **阻塞问题数：0**
- **建议项数：3**（均为文档自洽性/对齐补强，不影响可执行性）

核心判断：三份 plan 完整继承架构 §2.4 的 14 条 AC、6 条 ADR、§7 数据契约与 §9 实施方案；维度 17 前后端契约四件套读真实代码核对全部通过（路径拼接/方法鉴权/query 命名/response 命名/响应包裹解包层级均一致）；本次重大更新（ADR-2 简化 month 入参 + plan-03 新增同步面板 + OQ 闭环）在 plan 层面**彻底落地、无半改残留**。发现的 3 个建议项均集中在：架构基准文档自身有旧方案残留（plan 正确跟随 ADR-2，但基准未同步干净），以及一处已闭环 OQ 的措辞遗留。这些不阻塞按计划执行，建议下一轮架构/计划同步时收口。

## 三、Contract 预检

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| README frontmatter `workflow_type: create-dev-plan` | ✅ | README.md L2 |
| README frontmatter `org_mode: feature` | ✅ | README.md L6 |
| README `status: review_ready` ∈ readme_frontmatter_status | ✅ | README.md L3（合法集合 draft/review_ready/in_execution/in_review/accepted/released） |
| README `execution_order` 引用真实 plan | ✅ | L14 `[["plan-01","plan-02"],["plan-03"]]`，三者真实存在 |
| README `total_tasks` 与 plan 文件数一致 | ✅ | L9 `total_tasks:3` / L10 `total_task_files:3`，对应 3 份 plan |
| README 含 feature_readme_required_sections（10 节） | ✅ | 概览/输入摘要/验收标准追踪矩阵/模块地图/依赖图/阶段摘要/任务总览/未决策项/执行前置/变更记录 齐全 |
| README 验收追踪矩阵表头固定 | ✅ | L81 `\| AC-ID \| 需求原文 \| 架构承接 \| 计划承接 \| 验证方式 \| 当前状态 \|` |
| plan-01 frontmatter `feat_id: plan-01` 与文件名一致 | ✅ | plan-01 L2 |
| plan-02/03 frontmatter `feat_id` 与文件名一致 | ✅ | plan-02 L2 / plan-03 L2 |
| 各 plan `status: draft` ∈ task_file_status | ✅ | 合法集合 draft/ready-to-dev/in-progress/review/done/deprecated |
| 各 plan dimension/phase/depends_on 合法 | ✅ | plan-01 backend/phase1/[]；plan-02 backend/phase1/[plan-01]；plan-03 frontend/phase2/[plan-01,plan-02]（DAG 无环） |
| 各 plan 含 feature_task_required_sections（8 节） | ✅ | 功能概要/文件清单/实现规格/Task 列表/验收标准/验证命令/交接上下文/风险与边界 全齐 |
| Task/边界状态只用 todo/done/waived | ✅ | 全部 Task 状态为 `todo`；边界场景表状态均为 `todo`；无 waived 项 |
| depends_on 引用真实功能 | ✅ | plan-02→plan-01、plan-03→plan-01/plan-02 均存在 |
| 架构 frontmatter `open_questions: []` | ✅ | 架构文档 L7 |

## 四、验收标准追踪

架构 §2.4 共 14 条 AC，README 追踪矩阵 14 行全覆盖；下表抽样关键映射并标注 FEAT checklist 是否弱化。

| AC-ID | 架构要求 | README 承接 | FEAT 承接 | 结论 |
| --- | --- | --- | --- | --- |
| AC-01 | 侧边栏菜单与页面入口 | plan-03 | plan-03 §菜单注册验收 + E2E TC | ✅ FEAT checklist L234 未弱化 |
| AC-02 | 股票维度排行榜展示 | plan-02, plan-03 | plan-02 §5 股票聚合 + plan-03 §5 排行榜 E2E | ✅ 双 FEAT 联合 |
| AC-03 | 股票维度展开（预加载，不丢弃理由） | plan-02, plan-03 | plan-02 AC-03 + plan-03 行展开 E2E | ✅ 预加载+同券商多 reason 归并均落到 FEAT |
| AC-04 | 券商维度反查与展开（懒加载） | plan-02, plan-03 | plan-02 券商分组+明细 + plan-03 E2E | ✅ |
| AC-05 | 月份切换 | plan-02, plan-03 | plan-02 month 参数 + plan-03 月份切换 E2E | ✅ |
| AC-06 | 分页加载（≤20 隐藏分页器） | plan-02, plan-03 | plan-02 page/page_size + plan-03 分页 E2E | ✅ |
| AC-07 | 次级排序（双字段 ORDER BY） | plan-02 | plan-02 §5 双字段 ORDER BY 验收 | ✅ repository 实现规格明确双字段 |
| AC-08 | 数据同步任务 | plan-01, plan-03 | plan-01 执行验证 + plan-03 AC-08-ui-1~5 | ✅ 见下方变更 B 核查 |
| AC-09 | 数据从未同步的空状态 | plan-02, plan-03 | plan-02 has_data=false + plan-03 空状态 E2E | ✅ |
| AC-10 | 默认月份 MAX(month) | plan-02 | plan-02 latest_month 兜底验收 | ✅ |
| AC-11 | 股票维度搜索（服务端全量重查） | plan-02, plan-03 | plan-02 股票 search + plan-03 搜索 E2E | ✅ |
| AC-12 | 券商维度搜索 | plan-02, plan-03 | plan-02 券商 search + plan-03 E2E | ✅ |
| AC-13 | 券商维度展开懒加载（骨架/失败重试） | plan-02, plan-03 | plan-02 broker-detail + plan-03 懒加载 E2E | ✅ |
| AC-14 | 切换视图/月份时搜索词与分页重置 | plan-03 | plan-03 状态重置 E2E | ✅ AC-14 统一重置逻辑集中 BrokerRecommendPage |

**E2E-TDD 证据要求**：plan-03 为用户可观察功能，已声明完整 E2E（spec `web/tests/e2e/broker-recommend-analysis.spec.ts` + mock helper + 用例文档 `docs/e2e/09-e2e-用例-券商月度金股.md` + red/green 证据路径 L268-269），符合维度 4"red 预期失败 + green 通过两阶段证据"要求。plan-01/plan-02 为纯后端，已用"执行验证/curl 4 端点"作为强制验收并给出明确不适用说明，合理。

## 五、维度检查结果

| 维度 | 结论 | 问题数 | 摘要 |
| --- | --- | --- | --- |
| 1 核心闭环与系统目标 | ✅ | 0 | README §2.1 完整复述 Sync(month)→Snapshot→Aggregate→Browse 闭环与最小新增目标 |
| 2 范围与非目标 | ✅ | 0 | P0 范围全有 FEAT 承接；§2.2/§4.3 非目标（缓存层/预计算/独立券商表/AI/报告期选择/定时同步）在各 FEAT"不在范围"呼应 |
| 3 成功标准 | ✅ | 0 | §2.3 定量目标（<2s/默认月=MAX(month)/≤20 隐藏/懒加载）落到 plan-02 性能验收 + plan-03 边界场景 |
| 4 验收标准防漂移 | ✅ | 0 | 14 条 AC 全映射（见第四节）；FEAT 关联 AC 与 README 一致；checklist 未弱化 |
| 5 ADR 约束 | ⚠️ | 1 | 6 条 ADR 在 README 护栏/FEAT 实现规格均体现；**ADR-2 已简化为 month 入参，plan 层正确（见修复核查 A），但架构基准 §4.2 模块表/§7.5/§8.4/§10 仍有旧方案描述**（建议 S-1） |
| 6 用户流程与状态机 | ✅ | 0 | 流程 A/B/C/D 节点均有 FEAT；§3.2 关键分支（数据从未同步/所选月无数据/展开为空/懒加载失败/并发/搜索无结果）在 plan-02/03 边界场景表全覆盖 |
| 7 模块职责与系统上下文 | ✅ | 0 | README 模块地图含全部架构模块；上下游在 depends_on/交接上下文体现 |
| 8 运行链路 | ✅ | 0 | §6.1~§6.4 链路在对应 FEAT 实现规格一一落地（聚合算法 SQL/懒加载/同步先删后写/菜单注册） |
| 9 数据模型与契约 | ✅ | 0 | §7.1/7.2/7.3 核心对象/Schema/API 边界一致；数据来源标注（user_input/frontend_computed/derived）齐全；序列化（date→ISO/Decimal→float）显式；响应包裹 {success,data} 与前端解包层级一致 |
| 10 非功能需求 | ✅ | 0 | 性能/错误处理/降级 L1~L5/安全（JWT+require_admin+_escape_like_keyword）/成本/可观测性/超时（timeout_seconds=3600）均落到 FEAT |
| 11 实施建议与技术选型 | ✅ | 0 | 技术栈与架构一致；阶段划分符合依赖（plan-01→plan-02→plan-03） |
| 12 风险与未决策项 | ⚠️ | 1 | open_questions 空、OQ 已闭环；**plan-02 L207 暂停条件仍把已闭环的 OQ-3（积分）当风险描述**（建议 S-2） |
| 13 功能拆分质量 | ✅ | 0 | 每个 FEAT 连贯；Task 列表均 ≤11 步（plan-03=11）；DAG 无环 |
| 14 可执行性 | ✅ | 0 | 文件清单路径具体；modify 文件（models/__init__.py、api.ts、task_handlers.py、DashboardLayout.tsx、AdminSidebar.tsx、api/admin/__init__.py、api/v1/__init__.py）均真实存在并给行号锚点；验证命令可运行 |
| 15 状态与报告契约 | ✅ | 0 | frontmatter 状态合法；README 展示状态与 FEAT 一致（均 review_ready/draft）；报告路径符合 plan_review_filename_pattern |
| 16 复用声明链路 | ✅ | 0 | 6 条复用声明（异步任务体系/admin API 触发/查询服务范式/stocks+sector JOIN/前端 API 客户端/侧边栏菜单）在 FEAT 均有调用细节：构造签名 `(session)`、import 路径、BaseRepository 泛型继承、`_get_industry_for_stocks` 显式 JOIN 字段、cancel_check 直查 status 标量等齐全（已读真实代码核对） |
| 17 前后端 API 契约一致性（代码级） | ✅ | 0 | 四件套全通过（见下专节） |

### 维度 17 代码级核对详情（已读真实代码）

| 契约盲区 | 前端 | 后端 | 核对结论 |
| --- | --- | --- | --- |
| 路径前缀拼接（用户侧） | `apiClient.baseURL=API_BASE_WITH_PREFIX=${API_BASE_URL}/api/v1`（api.ts L9）；endpoint `/broker-recommend-analysis/stock-ranking` 不带 /v1 | v1 主路由 prefix `/v1`（v1/__init__.py L26）+ router prefix `/broker-recommend-analysis`（plan-02 §3） | ✅ 最终 `/api/v1/broker-recommend-analysis/stock-ranking`，无双前缀 |
| 路径前缀拼接（admin 同步触发） | `adminApiClient.baseURL=API_BASE_WITH_PREFIX=/api/v1`（api.ts L440）；endpoint `/admin/init/broker-recommend` | admin 挂载 `prefix="/v1/admin"`（router.py L29）+ init 子路由 prefix `/init`（init_top10_holders.py L22 范式） | ✅ 最终 `/api/v1/admin/init/broker-recommend`，无双前缀 |
| 路径前缀拼接（同步记录表） | SWR key `/api/v1/admin/tasks?...`（plan-03 §10）+ `fetcher` 用 `API_BASE`（不含 /v1）+ key 拼接（fetcher.ts L30） | tasks 路由 `/api/v1/admin/tasks`（router.py L29 + tasks.py L24 prefix `/tasks`） | ✅ 与 StockTop10SyncPanel L34 范式逐字一致，`task_types` 为通用逗号分隔过滤无白名单（tasks.py L178-207） |
| HTTP 方法存在性与鉴权 | `apiClient.get` 存在（api.ts L119）携带 Authorization（getAuthHeaders L45）；`adminApiClient.post` 存在（L520）继承鉴权 | 4 端点 GET + `Depends(get_current_user)`；admin POST + `Depends(require_admin)` | ✅ 三方一致；adminApiClient 继承 ApiClient，post 走同一 request 带 authHeaders |
| query 参数命名 | 前端 `.getStockRanking` 写 query 转 `page_size`（plan-03 §1，不写 pageSize） | FastAPI Query snake_case `page_size`（Query 不经 alias 转换） | ✅ 锚点 fundCrowdAnalysisApi（api.ts L1050 `page_size: params.pageSize`）已验证 |
| 响应字段命名 | TS interface camelCase（brokerCount/stockCount/hasData/pageSize，plan-03 §1） | Pydantic `ConfigDict(alias_generator=to_camel)` + 路由 `_dict_to_camel` 转 camelCase | ✅ 后端 snake 变量名与 camel 输出分离，不混用 |
| 响应包裹与解包层级 | 后端 `{success:true,data:{...}}`；SWR fetcher `.then(res=>res.data)` 解一层（plan-03 §2，注释与 useFundCrowdAnalysis.ts L8-10 一致）；组件读 `.data.data` | 路由层 `{"success":True,"data":_dict_to_camel(result)}` | ✅ 层级一致；注意 plan-03 用户侧 hooks 用 apiClient 体系（非 lib/fetcher），同步面板用 lib/fetcher（两套 baseURL 体系，与 StockTop10SyncPanel 范式一致） |

**复用范式代码核对**（plan-01 handler 伪代码 vs 真实 `sync_top10_holders_task` task_handlers.py L1172-1236）：构造 `BrokerRecommendDataInitService(manager.db)`、`_make_progress_callback`、cancel_check 直查 `AsyncTask.status` 标量、try/except + `getattr(e,"original_error")` 提取——逐项与真实范式一致 ✅。`BaseRepository.__init__(model, session)`（base.py L29）与 plan-02 `super().__init__(BrokerRecommend, session)` 一致 ✅。

## 六、问题清单

| 严重级别 | 位置 | 问题 | 修补建议 |
| --- | --- | --- | --- |
| 建议 S-1 | 架构基准 `09-1-架构文档` §4.2 模块表 L161/L164、§2.4 AC-08 L64、§7.5 L426、§8.4 L501、§10 L621 | **架构基准文档自身残留旧方案**：ADR-2/§5.x/§6.3/§9 已正确改为"month 入参直接拉取"，但 §4.2 模块表仍写 `get_broker_recommend(trade_date) + get_last_trade_date_of_month(month)` 与"月份→月末交易日→拉取"；§7.5/§8.4 仍写"Tushare（broker_recommend + trade_cal）"；§10 仍写"YYYYMM→月末交易日映射（trade_cal 单月范围）"。**plan 已正确跟随 ADR-2（见修复核查 A），此处仅基准文档自洽性问题**，不影响 plan 可执行性。 | 下一轮架构同步时，将架构 §4.2 模块表 Tushare 行改为 `get_broker_recommend(month)`，移除 §4.2 service 行"月份→月末交易日→"；§2.4 AC-08 风险列、§7.5/§8.4 数据源改为"broker_recommend（month 入参）"、§10 改为"YYYYMM 直接作为 month 入参"。属架构文档维护事项，非 plan 阻塞。 |
| 建议 S-2 | plan-02 §风险与边界 L207 | 暂停条件写"若 plan-01 因 Tushare 积分（OQ-3）无法真实同步"——OQ-3 已闭环（积分已满足 15000≥6000），此处把已闭环项当风险描述，措辞陈旧。 | 改为中性表述："若 plan-01 因 Tushare 调用异常无法真实同步，本功能可用手工 INSERT 测试数据验证聚合逻辑"，删除对已闭环 OQ-3 的引用。 |
| 建议 S-3 | plan-03 §实现规格 #9（adminApi initBrokerRecommend） | 文件清单 L40 与实现规格 L152 一致写 `adminApiClient.post<{task_id:string}>('/admin/init/broker-recommend', { month })`，路径与方法均正确。但 §1 与 §9 两处对 adminApi endpoint 的描述一处用 `/admin/init/broker-recommend`、README §2.4 约束写 `/api/admin/init/broker-recommend`——两种写法（含/不含 /api/v1）并存易让实现者困惑。实际 `adminApiClient.baseURL` 已含 `/api/v1`，故 endpoint 写 `/admin/init/broker-recommend`（实现规格 L153）是正确落地，README 的 `/api/admin/init/...` 是"完整路径视角"。 | 在 plan-03 §9 补一句澄清："endpoint 写 `/admin/init/broker-recommend`（不含 /api/v1，因 adminApiClient.baseURL 已含 /api/v1；完整路径为 /api/v1/admin/init/broker-recommend）"，避免实现者误加前缀。属可读性补强，非阻塞。 |

## 七、合理扩展

| 位置 | 扩展内容 | 为什么合理 |
| --- | --- | --- |
| plan-03 §10 | `BrokerRecommendSyncPanel` 用 `getRecentMonths(count=12)` 替换 Top10 的 `getRecentQuarters`，月份选择器显示最近 12 个月 YYYY-MM | 架构 ADR-2 month 入参为 YYYYMM，季度末不适配；12 个月覆盖用户回顾需求，不违背架构（§2.1 月份选择支持历史） |
| plan-03 §10 | 同步记录表 params 取 `record.params?.month`（替换 period） | plan-01 task params 用 `month` 键（AC-08b），与 StockTop10 的 `period` 键对应，命名与同步服务入参一致 |
| plan-02 §2 #1 | 新增 `get_stock_brokers` repository 方法（预加载 brokers） | 架构 §6.1"同表二次查询或 ARRAY_AGG 择优"留了实现余地，独立方法使预加载逻辑清晰，不违背 ADR-3 预加载决策 |
| plan-01 §实现规格 #4 | 按 (ts_code, broker) 去重保留最新 trade_date 的 dict 算法 | ADR-2 风险对策明确要求该去重，算法选择是合理实现细节 |
| plan-03 §4 | 状态管理用 `debouncedSearch`（debounce 300ms） | 架构 ADR-5 只规定 React state + 切换重置，debounce 是搜索体验合理增强，不违背"搜索回第 1 页"决策 |

## 八、建议补丁计划

按优先级（均非阻塞，可在下次架构/计划同步时一并处理）：

1. **【S-1 架构基准自洽】架构文档 `09-1`**：统一收口旧方案残留——§4.2 模块表 Tushare 行与服务行、§2.4 AC-08 风险列、§7.5 数据边界、§8.4 成本外部依赖、§10 架构结论，全部改为 ADR-2 的 month 入参口径，删除 `get_last_trade_date_of_month` / trade_cal 映射 / "月末交易日"措辞。优先级最高（消除基准与 ADR-2 的内部矛盾，避免后续按基准旧段落实现踩坑）。
2. **【S-2 措辞收口】plan-02 §风险与边界 L207**：删除对已闭环 OQ-3 的引用，改为中性异常表述。
3. **【S-3 可读性补强】plan-03 §实现规格 #9**：补一句 endpoint 前缀澄清，明确 `/admin/init/broker-recommend`（baseURL 已含 /api/v1）。

### 修复彻底性核查结果（本次复审专项，grep 全量）

**变更 A：ADR-2 简化为 month 入参** — ✅ plan 层彻底，⚠️ 架构基准有残留
- grep `get_last_trade_date_of_month`：plan-01 仅 L76 一处为"**不再需要** …（架构 ADR-2 简化）"说明性文字（明确标注已移除），无实现规格/Task 残留；README 仅 L194 变更记录说明已移除。**plan 实现规格与 Task 已彻底移除** ✅。架构基准 §4.2 L164 仍列该方法为模块职责（S-1）⚠️。
- grep `trade_cal`：plan-01 L76/L163、README L42/L194 均为"无需 trade_cal 映射"说明性文字（正确）；架构基准 §7.5 L426/§8.4 L501 仍写"trade_cal 数据源"（S-1）⚠️。
- grep `月末交易日`：plan 层 0 处（plan-01 实现规格/Task 无"月末交易日计算"步骤）✅；架构基准 §2.4 AC-08 L64/§4.2 L161/§10 L621 仍写旧方案（S-1）⚠️。
- grep `broker_recommend(trade_date`：plan 层 0 处；plan-01 §实现规格 #3 正确写 `pro.broker_recommend(month=...)` ✅；架构基准 §4.2 L164 仍写 `get_broker_recommend(trade_date)`（S-1）⚠️。
- plan-01 Task 列表 6 项（L149-154），编号连续，**已无原"Task 7 用真实接口验证字段名（OQ-1）"** ✅。

**变更 B：plan-03 新增同步面板** — ✅ 彻底
- 文件清单：`BrokerRecommendSyncPanel.tsx`（L37）+ `admin/broker-recommend-init/page.tsx`（L38）+ `AdminSidebar.tsx` modify（L39）+ `api.ts` adminApi `initBrokerRecommend`（L40）齐全 ✅
- Task 列表：Task 9（initBrokerRecommend+BrokerRecommendSyncPanel）+ Task 10（子页路由+AdminSidebar 菜单）齐全 ✅
- 验收标准：AC-08-ui-1~5（L258-262）覆盖菜单/触发/进度/记录表/并发保护 ✅
- US-04 承接：plan-01 §执行验证 + plan-03 AC-08-ui 联合（L280-281）✅
- README 同步：AC-08 验证方式（L89）+ 模块地图（L105）+ 依赖说明（L167）+ OQ-2 决策记录（L152）✅
- 调用细节：范式源 `StockTop10SyncPanel.tsx` + `top10-holder-init/page.tsx` + `AdminSidebar.tsx` + `adminApi.initStockTop10Holders`（api.ts L604-605）均经真实代码核对，SWR key/params.month/getRecentMonths/useTaskStatus 复用逐项落地 ✅

**OQ 闭环核查** — ✅ 彻底
- README §8 未决策项："无遗留未决策项。原 OQ-1/OQ-2/OQ-3 均已闭环"+ 逐条决策记录（L149-153）✅
- README frontmatter `open_questions: []` ✅；架构 frontmatter `open_questions: []` ✅
- grep `OQ-1/2/3 待验证/待确认`：plan/README 中无"待验证/待确认"措辞；plan-02 L207 引用 OQ-3 为"暂停条件"（已闭环项被当风险，S-2）⚠️；其余 OQ 引用均为"已决策/已闭环"说明性文字 ✅

---

**最终结论：通过（有 3 个建议项，0 阻塞）。** 三份实现计划完整继承架构 AC/ADR/数据契约，维度 17 前后端契约代码级核对全部通过，本次重大更新（ADR-2 简化 + plan-03 同步面板 + OQ 闭环）在 plan 层面彻底落地。3 个建议项均为文档自洽性/可读性补强（架构基准残留旧方案为主），不影响按计划执行；建议下一轮架构同步时收口 S-1（最高优先级）。
