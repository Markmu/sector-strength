# 开发计划检查报告（第二轮复检）

- 检查日期：2026-07-29
- 检查 skill：dev-plan-check
- 检查者：独立 subagent（全新上下文）
- 检查轮次：第 2 轮（针对第 1 轮 10 个问题的修复验证 + 全计划回归）

## 一、检查对象

- 架构文档：`docs/14-ETF份额与资金流监控/14-1-架构文档-ETF份额与资金流监控.md`
- PRD（语义参照）：`docs/14-ETF份额与资金流监控/14-0-需求设计-ETF份额与资金流监控.md`
- 实现计划：`docs/14-ETF份额与资金流监控/14-2-实现计划-ETF份额与资金流监控/`
  - `README.md` + `plan-01`~`plan-05`（共 5 个功能文件）
- 功能数：5

本轮在纯文档对照之外，额外读真实代码/运行脚本核对：跑了 `scripts/test_etf_apis.py`（验证 fund_daily 在当前数据源的真实返回）、读了 `server/src/services/trading_calendar.py`（核对 P-09 方法签名）、`web/src/lib/api.ts`（核对 P-01 修复依据与维度 17 契约）、`web/src/types/fundFlowTypes.ts`（核对 P-01 修复依据）、`server/src/services/task_handlers.py` / `data_updater/collector.py`（核对 TradingCalendar 调用范式）。

## 二、总评

- **结论：通过**
- 阻塞问题数（blocker）：0
- 中等问题数：0
- 轻微问题数：1（新发现，文档内交叉引用指向错误，非契约类）

第 1 轮提出的 10 个问题（4 中 + 6 轻）**全部已实质性修复到位**：每个修复点都能在对应 plan 找到具体证据行，且修复后与文档其他部分（架构、README、相邻 plan）保持一致，未引入新的契约矛盾。全计划回归检查（架构信息继承、8 章节完备、前后端契约四件套、验收可执行性、依赖顺序、复用调用细节、合理扩展）均通过，第 1 轮无问题的部分未发生回归。

唯一遗留项是 1 个轻微文档瑕疵：plan-05 §2 行展开说明里把 change_percent 来源指向"plan-01 §3"，实际 plan-01 的 change_percent 讨论在 §6 与风险节（§3 是 Tushare 获取方法），属交叉引用指向偏差，不影响实现与契约。

## 三、Contract 预检（回归）

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| README `workflow_type: create-dev-plan` | 通过 | frontmatter 命中 |
| README `org_mode: feature` | 通过 | frontmatter 命中 |
| README `status` 合法 | 通过 | `review_ready` |
| `execution_order` 仅引用真实 plan | 通过 | `[["plan-01"], ["plan-02","plan-03"], ["plan-04"], ["plan-05"]]` 全部存在 |
| `total_tasks` 与 plan 数量一致 | 通过 | 5=5 |
| README 必备章节齐全 | 通过 | 概览/输入摘要/验收标准追踪矩阵/模块地图/依赖图/阶段摘要/任务总览/未决策项/执行前置/变更记录 10 节齐 |
| 追踪矩阵表头固定 | 通过 | `AC-ID｜需求原文｜架构承接｜计划承接｜验证方式｜当前状态` |
| 各 plan `feat_id` 与文件名一致 | 通过 | plan-01~05 对齐 |
| 各 plan `status` 合法 | 通过 | 全 `draft` |
| 各 plan 必备 8 章节 | 通过 | 5 文件 `## ` 头计数均为 8 |
| Task/边界状态仅用 todo/done/waived | 通过 | 全 todo，无 waived |
| `depends_on` 引用真实功能 | 通过 | plan-02/03→01，plan-04→03，plan-05→04，DAG 无环 |

## 四、上一轮 10 个问题修复验证（逐一）

### 中等（4 个）

| 编号 | 问题（上轮） | 修复状态 | 证据（行号） |
| --- | --- | --- | --- |
| **P-01** | plan-04 §2 数据 interface 非 export，跨文件 import 会 TS 编译失败 | **已修复** | plan-04-前端基础设施.md:96-101，6 个数据 interface 全部为 `export interface`（EtfIndexRankingsData/EtfIndexRankingItem/EtfIndexDetailData/EtfDetailItem/EtfTrendData/EtfLatestDateData）。修复依据核对：`web/src/types/fundFlowTypes.ts` 范式确为全 `export interface`（fundFlowTypes.ts:12/21/47/59/67/75/84），与 plan §2"仿 fundFlowTypes.ts"自洽 |
| **P-02** | plan-01 §3 fund_share 的 fund_type 过滤未说清服务端/客户端 | **已修复** | plan-01-数据层与采集.md:63，明确写"返回后**在客户端按 fund_type=='ETF' 筛选**（fund_share 返回的每条含 fund_type 列，实测 fund_type='ETF' 可直接筛）"，并补"已实测按 trade_date 全量返回 728 条（含 fund_type 列）" |
| **P-03** | plan-01 §6 取净值方案自相矛盾（批量 vs 逐只） | **已修复** | plan-01-数据层与采集.md:87，收敛为单一方案："**逐只调 get_fund_nav(ts_code)** ... fund_nav 接口按 ts_code 取历史，不支持批量，已实测。逐只调用配 0.3s 限流 ... 约 3.5 分钟"。"未来优化（不在本期）"明确标注为本期外，不再与逐只方案并列矛盾 |
| **P-04** | plan-01/05 change_percent 取数不清 | **已修复（含合理性评估）** | 见下方专项评估 |

**P-04 专项评估（修复方向合理性）**：

修复方案：plan-01 §6（plan-01-数据层与采集.md:92）+ 风险节（:177）明确"实测 fund_daily 接口在当前数据源（自建代理）返回'Token无效或已过期'，不可用 → 首版 change_percent 存 null（注释 TODO）"；plan-05 §2（plan-05-ETF监控页面.md:55）明细行"涨跌幅列容错：对 null 展示 '-' 或留空，E2E 断言不要求该列有值"。两份 plan 口径一致。

- **修复方向合理性**：成立。"数据源不支持 → 存 null + 前端容错"是可接受的优雅降级——架构 §7.2 本就把 change_percent 定义为 `number \| null`（可空），plan-01 的细化（来源不可用存 null）与架构不冲突；PRD 明细列含涨跌幅但非核心指标，不阻塞任何核心 AC（AC-04 明细列的 E2E 断言已放宽）。不构成对架构/PRD 的静默改写。
- **实测核对（本轮新增）**：本轮实跑 `python scripts/test_etf_apis.py`，当前数据源对 fund_basic / fund_share / fund_nav / fund_daily **全部** 返回 "Token无效或已过期"（token 全局过期，非仅 fund_daily 特例）。此为运行环境状态（token 过期），非计划文档缺陷——架构文档此前已验证 fund_basic/share/nav 可用（728 条），plan 的"fund_daily 不可用"结论与架构的"三接口可用"前提并存合理（fund_daily 是 plan-01 新引入的取数尝试，其不可用属实测结论）。建议在 token 续费后重跑 test_etf_apis.py 复核 fund_daily 真实可用性，但这是执行阶段动作，不影响计划通过判定。

### 轻微（6 个）

| 编号 | 问题（上轮） | 修复状态 | 证据（行号） |
| --- | --- | --- | --- |
| **P-05** | README AC-12 验证方式漏 plan-03 | **已修复** | README.md:76，验证方式现为"plan-01 §5 执行验证（handler 直调）+ plan-03 §5 接口验证（admin POST /etf-daily 端点）"，与 plan-03 §后端验收 AC-12（完整）（plan-03-查询API.md:135）呼应 |
| **P-06** | README §2.2 护栏表漏 ADR-4/6 | **已修复** | README.md:44（ADR-4 排行/明细/趋势分多端点）+ :46（ADR-6 定时任务注释注册）两行已补全，护栏表现含 ADR-1~7 全部 7 条 |
| **P-07** | plan-05 §1 helpers 用途歧义 | **已修复** | plan-05-ETF监控页面.md:41-46，逐函数补服务对象：formatShare（亿份，正值，指数行+明细行份额）；formatSignedAmount（亿元/亿份，带正负，净流入额+份额变化共用，均带正负色标）；formatPercent（涨跌幅，change_percent 可能 null 容错） |
| **P-08** | plan-03 get_trend 指数交易日筛选未写清 | **已修复** | plan-03-查询API.md:53，明确"target_type='index' 时先 JOIN etf_basic 筛 index_name 得该指数的 ts_code 集合，再取该集合在 etf_daily 中 trade_date<=end_date 的最近 N 个 distinct 交易日（取该指数全量 ETF 交易日的并集，避免取成全表交易日导致 series 长度偏差），最后在该 N 日内按 index_name 聚合 SUM" |
| **P-09** | plan-02 TradingCalendar 缺调用细节 | **已修复** | plan-02-历史回填.md:47，补全：import 路径 `from src.services.trading_calendar import TradingCalendar`、对齐锚点 `与 collector.py:69/385、task_handlers.py:857 同款`、方法签名 `await TradingCalendar().get_trading_days_between(start_date, end_date) -> List[date]`、行号锚点 `services/trading_calendar.py:50`。代码核对：trading_calendar.py:50 确为 `async def get_trading_days_between(self, start: date, end: date) -> List[date]`；task_handlers.py:857-858 实际调用范式 `calendar = TradingCalendar(); await calendar.get_trading_days_between(start_date, end_date)` 与 plan 描述一致 |
| **P-10** | plan-01 upsert set_ 列未列全 | **已修复** | plan-01-数据层与采集.md:90，set_ 现显式列出全部 5 字段 `set_={share, unit_nav, share_change, net_inflow, change_percent}`，并追加一句"set_ 显式列出全部需覆盖字段：share / unit_nav / share_change / net_inflow / change_percent"，去掉省略号 |

**结论：10 个问题全部"已修复"，无部分修复、无未修复。**

## 五、全计划完整检查（回归 + 新增不一致排查）

### 5.1 架构关键信息继承（维度 1~9、13）

| 检查项 | 结论 | 摘要 |
| --- | --- | --- |
| AC 继承（架构 §2.4 → README 矩阵 → plan） | 通过 | 14 条 AC 全映射到 README 矩阵并落到 plan（AC-12 双 plan 承接已补全） |
| ADR 继承（7 条 → 护栏/实现规格） | 通过 | ADR-1~7 全有承接，README §2.2 护栏表现含全部 7 条（P-06 已补 ADR-4/6） |
| 模块承接（架构 §4.2） | 通过 | 8 类模块全部有 plan 承接，无遗漏 |
| 运行链路（架构 §6.1~6.5） | 通过 | 当日采集/历史回填/排行/明细/趋势 5 条链路在 plan-01/02/03 一一落地 |
| Schema / API 契约传递（§7.2/7.3/7.6） | 通过 | 存储视角/输出视角/单位口径/命名特例/响应包裹前后端一致 |
| 功能拆分（维度 13） | 通过 | 5 FEAT 均连贯，Task 步数 ≤12，DAG 无环 |

### 5.2 前后端契约一致性（维度 17，代码级回归）

| 链路 | 结论 | 核对（本轮重验） |
| --- | --- | --- |
| 路径前缀拼接 | 通过 | api.ts:9 `API_BASE_WITH_PREFIX=${API_BASE_URL}/api/v1` + endpoint `/etf-monitor/...` = `/api/v1/etf-monitor/...`；admin 三层前缀 `/api`+`/v1/admin`+`/init`+`/etf-daily` 一致 |
| HTTP 方法 + 鉴权 | 通过 | api.ts:33 `ApiClient` 类、:45 `getAuthHeaders`、:49-55 从 localStorage 读 accessToken 注入 Authorization、:140 具名导出 `apiClient`、:1086 `sectorFundFlowApi` 范式存在 |
| query 参数命名 | 通过 | 前端传 snake_case（category/trade_date/sort_by/target_type/target_code），sort_by/metric 值 camelCase，与后端 Query 一致（plan-04 §1 代码块正确写出映射） |
| 响应字段命名 | 通过 | _dict_to_camel 输出 camelCase，plan-04 §2 类型定义匹配（含 changePercent: number \| null） |
| 响应包裹解包层级 | 通过 | `{success,data}` 包裹 + hook `.then(res=>res.data)` 解包，层级一致 |

### 5.3 复用声明调用细节（维度 16，回归）

复用项调用细节全部写清（文件:行号锚点 + import 路径 + 签名 + 导出形式）：tushare_client.get_fund_list、collector._update_sector_fund_flow、FundDataInitService、init_historical_data_by_date_range、init_sector_fund_flow、_dict_to_camel/_serialize_value、sectorFundFlowApi、useSectorFundFlow、TaskType/@TaskRegistry.register/__all__、DashboardLayout.baseSidebarItems、TradingCalendar（P-09 本轮新补全）。本轮代码核对 anchors 均真实存在。

### 5.4 验收可执行性（维度 14，回归）

- task handler 类（plan-01/02）：含"执行验证"不可豁免项 + 曲线无断裂验证（plan-02），通过。
- 用户可观察（plan-05）：red→green E2E 覆盖 AC-01~11/13，data-testid 锚点要求齐全，通过。
- 纯接口（plan-03）：curl 接口验证 + 前端 E2E 在 plan-05 承接，通过。
- 基础设施（plan-04）：导航跳转 E2E + build/lint，通过。
- 性能目标（采集 <5min、查询 <500ms、回填 90 日 <3h）落到对应 plan，通过。

### 5.5 修复引入的新不一致排查

- change_percent 跨文档（架构 §7.2 / plan-01 §6+风险 / plan-03 §1 / plan-04 §2 / plan-05 §1+§2）：口径一致（可空、首版 null、前端容错），无矛盾。
- fund_nav 取净值方案：plan-01 §6（逐只）、风险节（3.5min 瓶颈）、§3（get_fund_nav 签名按 ts_code）三处自洽，无矛盾。
- admin 端点拆分（见下"备注"）：plan 把架构 §9 的单文件 `init_etf.py` 拆为 `init_etf_daily.py`（plan-03）+ `init_etf_history.py`（plan-02），端点路径与架构 §7.3 完全一致（`/api/v1/admin/init/etf-daily`、`/api/v1/admin/init/etf-history`），属合理实现细化，非契约漂移（第 1 轮已隐式接受，本轮维持）。
- "应改处全改、应留处未误伤"：grep 全量核查 export interface / set_ 字段 / fund_type 过滤 / TradingCalendar 等标识符，未发现半改。

## 六、问题清单（本轮新发现）

### 轻微（1）

| 编号 | 位置 | 问题 | 修补建议 |
| --- | --- | --- | --- |
| N-01 | plan-05 §2 行展开说明（plan-05-ETF监控页面.md:55） | change_percent 来源的交叉引用写"（**见 plan-01 §3**）"，但 plan-01 中 change_percent 的取数讨论实际在 §6（plan-01-数据层与采集.md:92）与风险节（:177）；§3 是 Tushare 获取方法（get_fund_basic_etf/get_fund_share/get_fund_nav），不含 change_percent 来源说明。指向偏差，不影响实现与契约。 | 把 plan-05 §2 该处的"见 plan-01 §3"改为"见 plan-01 §6"。 |

- 严重：0
- 中等：0
- 轻微：1

## 七、合理扩展（维持上轮判断）

| 位置 | 扩展内容 | 为什么合理 |
| --- | --- | --- |
| plan-01 §6 change_percent 字段来源说明 | 架构 §7.2 已定义该字段，plan 补"fund_daily 不可用→null"属合理实现细化 | 与架构可空定义一致，降级路径明确 |
| plan-03 §5（可选）提取 _dict_to_camel/_serialize_value 公共 helper | 架构 §9.12 建议顺手提取，plan 标可选 | 与架构建议一致，明确"不提取则复制"，非过度设计 |
| plan-01 §3 get_fund_basic_etf 沿用 offset 分页 | 架构 §4.2 复用声明区分三者分页策略 | 忠实区分 fund_basic(offset) / fund_share+fund_nav(单批)，与架构可行性验证一致 |
| plan-02/03 admin 端点拆为两个文件 | 架构 §9 单文件 `init_etf.py` 含两端点，plan 拆为 init_etf_daily.py + init_etf_history.py | 端点路径与架构 §7.3 完全一致；单文件单 router 更贴合 init_sector_fund_flow.py 现有范式，属合理实现细化 |
| plan-05 §4 Disclaimer 组件 + plan-04 §5 导航 icon TrendingUp | 架构未指定具体细节 | 与同模块页面/lucide-react 一致 |

## 八、结论与建议

- **结论：通过**。上一轮 10 个问题全部实质性修复，AC 全映射、ADR 全承接、前后端契约一致、依赖顺序正确、无新增中/严重问题。
- 唯一遗留 N-01（轻微，交叉引用指向偏差）可在执行阶段随手修正，不阻塞开发。
- 执行阶段建议（非阻塞）：token 续费后重跑 `scripts/test_etf_apis.py`，复核 fund_daily（及 fund_basic/share/nav）真实可用性，确认 plan-01 change_percent 取数策略是否需要据实调整。
