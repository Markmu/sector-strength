# 开发计划检查报告（第六次独立复审 recheck5 — 收敛建模）

## 一、检查对象

- **架构文档**：`docs/06-股东分析面板/06-1-架构文档-股东分析面板.md`
- **实现计划**：`docs/06-股东分析面板/06-2-实现计划-股东分析面板/`（README + plan-01 ~ plan-04）
- **功能数**：4
- **前次报告**：
  - `dev-plan-check-20260613.md`（首检，8 建议，通过）
  - `dev-plan-check-20260613-recheck.md`（复查，1 建议，通过）
  - `dev-plan-check-20260613-recheck2.md`（第二次复查，2 blocker B-1/B-2 + 5 建议，有阻塞）
  - `dev-plan-check-20260613-recheck3.md`（第三次复查，2 blocker B-3/B-4 + 4 建议，有阻塞）
  - `dev-plan-check-20260613-recheck4.md`（第四次复查，3 blocker B-3′/B-4′/B-5 + 2 建议，有阻塞）
- **本次检查日期**：2026-06-13
- **本轮身份**：全新上下文独立复审者，重点核实 recheck4 五项修复的彻底性，并主动找新盲区

## 二、总评

- **结论**：✅ **通过**（无 blocker）
- **阻塞问题数**：0
- **建议项数**：2（S-1 Admin response 命名约定缺失 + GroupListItem 字段 snake_case 残留；S-2 描述性文字 snake_case 字段名与契约块 camelCase 不一致）

本轮作为全新上下文独立复审，重点做了三件事：(1) 逐条代码级核实 recheck4 声称修复的 5 项；(2) 用怀疑的眼光重新过 16 个维度；(3) 主动寻找第五类、第六类契约盲区。结论：**recheck4 的 5 项修复全部彻底落地，无"半改"复发**；本轮发现的 2 个建议项均为"文档内部命名风格不统一的轻微不一致"，不影响实现者照 §7 契约块（已 camelCase）写代码，不阻塞开发。

## 三、Contract 预检

全部通过（与 recheck4 一致）：

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| README frontmatter `workflow_type` | ✅ | `create-dev-plan` |
| README frontmatter `org_mode` | ✅ | `feature` |
| README `status` 合法 | ✅ | `review_ready` |
| `execution_order` 引用真实 plan-XX | ✅ | `[["plan-01"], ["plan-02", "plan-03"], ["plan-04"]]` |
| `total_tasks` 与文件数一致 | ✅ | 4 |
| README 必备章节完整 | ✅ | 10/10 |
| 追踪矩阵表头 | ✅ | 固定 6 列 |
| 各 FEAT `feat_id` 与文件名一致 | ✅ | plan-01~04 |
| 各 FEAT `status` 合法 | ✅ | 全部 `draft` |
| 各 FEAT 必备章节完整 | ✅ | 4×8 |
| Task / 边界场景状态合法 | ✅ | 全部 `todo` |
| `depends_on` 引用真实 | ✅ | plan-02/03→plan-01，plan-04→plan-02 |

## 四、recheck4 五项修复独立核实（任务第一层 — 关键）

> 本轮核心任务：recheck3 的修复被 recheck4 发现"半改"，本轮要核实 recheck4 的修复有没有再次半改。逐条代码级核实，不放过。

| 编号 | 内容 | 核实结果 | 证据 |
| --- | --- | --- | --- |
| B-3′ | README §3 追踪矩阵 AC-07 `PUT`→`PATCH` | ✅ **彻底** | README line 79 `Admin API PATCH /shareholder-groups/{id}` 已改 PATCH；架构 line 64/328/477/644、plan-01 line 128/177/229、plan-03 line 47 全部 PATCH。全文档唯一残留 PUT 在 README line 173 变更记录的"历史描述"（"编辑分组接口 `PUT`→`PATCH`（B-3）"），属正常历史记录，非契约残留。代码核对 `web/src/lib/api.ts` AdminApiClient 无 put 方法、有 patch（line 524），与 PATCH 约定一致。 |
| B-4′ | `pageSize`→`page_size` 全局同步（架构 + plan-02），plan-04 前端变量 `pageSize` 保留 | ✅ **彻底** | 架构 06-1：line 52/258/286/287/474/615/635 共 7 处全部 `page_size`（snake_case），无 `pageSize` 残留；plan-02：§3 line 129 Service 签名 `page_size: int = 20`、§3.6 line 159 端点描述 `page_size（默认 20）`、§5 line 199 curl `&page_size=20`、§6 line 258 curl `&page_size=20`、line 232 性能验收 `page_size=20`——5 处全部 snake_case。plan-04：§3.1 line 66/67/68 query 字符串拼 `page_size`（snake_case）+ 注释"query key 用 snake_case"，前端 TS 入参 `pageSize`（line 66/96）+ Props `pageSize`（line 138）共 3 处保留 camelCase（正确，前端变量命名友好）。**无"该改未改"或"该留误改"**。代码核对 funds.py line 164/203/282 Query 参数全用 `page_size`，与 plan-02 一致。 |
| B-5 | response 字段统一 camelCase（架构 §7.2 + plan-02 §7 + plan-04 §7），后端 Python 视角 snake_case 保留 | ✅ **彻底**（契约块层面） | **架构 §7.2**：6 个 API response interface（OverviewResponse/GroupOverview/SummaryResponse/IndustryItem/HoldingItem/GroupListItem）字段全 camelCase（`reportPeriods`/`currentPeriod`/`hasPrevPeriod`/`groupId`/`groupName`/`stockCount`/`totalHoldAmount`/`avgHoldFloatRatio`/`changeDirection`/`stockName`/`isSystem`/`ruleCount`/`matchedStockCount` 等）；ShareholderGroup/ShareholderGroupRule（DB 模型层）正确保留 snake_case（`sort_order`/`is_system`/`group_id`/`created_at`）。**架构 §7.6 术语映射表**："后端字段"列正确保留 snake_case（`stock_count`/`total_hold_amount`/`avg_hold_float_ratio`）。**架构 §6.1/§6.2 运行链路**：统计变量正确保留 snake_case（后端 Python 视角）。**plan-02 §7 契约块**：7 个对象全 camelCase（line 291-297）。**plan-02 §3 实现规格**：Service 内部变量、SQL 别名正确保留 snake_case（`total_hold_amount`/`stock_count` 等）。**plan-02 §3.6**：明确 `alias_generator=to_camel` + `populate_by_name=True`，Decimal `float()` 转换。**plan-04 §7 契约块**：7 个对象全 camelCase（line 338-344）。**plan-04 §3.2**：fetcher 解包层级说明完整。**残留轻微不一致**：plan-02 §5 line 190-192 AC-01 验收描述 + plan-04 §3 line 180/365/368 边界场景描述用 snake_case 字段名（`report_periods`/`has_prev_period`/`stock_count`/`group_id` 等）——属描述性文字未跟随 camelCase 化，见建议项 S-2。契约块（实现者写代码的真正依据）已全部对齐。 |
| N-5 | plan-01 §3.2 补 Repository `super().__init__` | ✅ **彻底** | plan-01 §3.2 line 67-71 给出完整代码示例：`def __init__(self, session: AsyncSession): super().__init__(ShareholderGroup, session)  # BaseRepository.__init__ 需双参 (model, session)`。代码核对 `base.py` line 29 `def __init__(self, model, session)` 双参签名，`fund_repository.py` line 38-39 `super().__init__(Fund, session)` 模式——plan-01 示例与真实代码完全一致。 |
| N-6 | plan-04 §3.2 补 fetcher 解包层级 | ✅ **彻底** | plan-04 §3.2 line 99 完整说明："fetcher 的 `.then(res => res.data)` 解一层——`res` 是 `shareholderAnalysisApi` 方法返回的 `ApiResponse` 对象，`.data` 取其 `data` 字段即整个 body `{ success, data }`。故 hook 返回的 `data` 是该 body，组件再读 `data.data` 取业务对象（与 `useFunds.ts` 读 `data?.data?.items` 一致）"。代码核对 useFunds.ts line 24/53/80/122 的 SWR key + `.then(res => res.data)` + 组件读 `data?.data?.items` 模式——plan-04 描述与真实代码层级完全一致。 |

**小结**：recheck4 的 5 项修复**全部彻底落地，无"半改"复发**。B-3′/B-4′ 的全局同步（架构 + 多 plan）完整，B-5 的契约块层面 camelCase 化完整、后端 Python 视角 snake_case 正确保留，N-5/N-6 的代码示例与真实代码一致。

## 五、本轮新发现问题

### 🔴 Blocker

无。

### 🟡 建议项（新发现）

| 编号 | 位置 | 问题 | 修补建议 |
| --- | --- | --- | --- |
| S-1 | plan-01 §3.4（Admin API 路由规格）+ plan-01 §7 line 251 + plan-03 §7 line 192（GroupListItem 契约） | **Admin API response 命名约定缺失 + GroupListItem 字段 snake_case 残留。** 架构 §7.2 的 `GroupListItem` 已是 camelCase（`isSystem`/`ruleCount`/`matchedStockCount`），但 plan-01 §7 和 plan-03 §7 仍写 snake_case（`is_system`/`rule_count`/`matched_stock_count`）。更关键的是 plan-01 §3.4 Admin API 路由规格**没有明确 response 命名约定**（既没说 to_camel alias，也没说直接 camelCase 字段定义）——而 plan-02 §3.6 对用户侧 API 明确了 to_camel。代码核实项目里 Admin API 有两种模式并存：`admin/users.py` 用**直接 camelCase 字段定义**（`UserListItem` 字段 `isActive`/`createdAt`/`lastLoginAt`，注释明确"驼峰字段"），`v1/funds.py` 用 **to_camel alias**。plan-01 没指明参照哪种，实现者可能照 plan-01 §7 的 snake_case 写后端 model 字段，若不配 alias 则 API 输出 snake_case，与架构 §7.2 camelCase 契约矛盾，前端 plan-03 按 §7 snake_case 消费反而能对上但偏离架构基准。**不构成 blocker 的理由**：实现者写后端时会参照现有 `admin/users.py`（直接 camelCase 字段），不会照 plan-01 §7 的 snake_case 写——因为 plan-01 §3.4 没有给出"照 snake_case 写"的指令，§7 只是交接上下文的字段语义列举。 | (1) plan-01 §3.4 补一句"Admin API response 参照 `admin/users.py` 直接用 camelCase 字段定义 Pydantic model（如 `isSystem`/`ruleCount`/`matchedStockCount`），不走 to_camel alias"；(2) plan-01 §7 line 251 + plan-03 §7 line 192 的 `GroupListItem` 字段对齐架构 §7.2 camelCase：`{ id, name, description, isSystem, ruleCount, matchedStockCount, keywords }`。 |
| S-2 | plan-02 §5 line 190-192（AC-01 验收）+ plan-04 §3 line 180 + §8 line 365/368（边界场景描述） | **描述性文字用 snake_case 字段名，与 §7 契约块 camelCase 不一致。** plan-02 §5 AC-01 验收写"包含 report_periods 列表、current_period、has_prev_period""每个 group 包含 group_id, group_name, stock_count, increase_count, decrease_count, new_count, exit_count"；plan-04 §3 line 180 "overview 返回空 report_periods"、§8 line 365 "report_periods"、line 368 "has_prev_period=false"。这些是描述 API 返回字段的语义文字，用了 snake_case，而 §7 契约块（实现者写代码的真正依据）已是 camelCase。**不构成 blocker 的理由**：这些是验收 checklist / 边界场景的"字段语义指代"，不是代码契约或字段访问声明。实现者写 `data.reportPeriods` 时看的是 §7（camelCase），不会因 §5 描述"包含 report_periods"就写成 `data.report_periods`。属文档内部命名风格未统一的轻微不一致。 | 将 plan-02 §5 line 190-192 + plan-04 line 180/365/368 的描述性字段名改为 camelCase（`reportPeriods`/`currentPeriod`/`hasPrevPeriod`/`groupId`/`groupName`/`stockCount` 等），与 §7 契约块对齐。或保留并加一句说明"§5/§8 描述用字段语义名，实际命名见 §7 camelCase 契约块"。 |

### 观察项（不升级为建议项，仅记录）

| 编号 | 位置 | 观察 | 说明 |
| --- | --- | --- | --- |
| O-1 | plan-02 §3.6 line 165 | `response_model=ApiResponse[OverviewResponse]` 表述与 funds.py 实际（端点无 response_model 参数）有出入 | funds.py line 158/196/241/278 的 `@router.get` 都不用 response_model，而是手动构造返回。plan-02 说"参照 funds API"但建议用 response_model。两者都能工作，response_model 是可选增强（提供 OpenAPI schema）。不阻塞，实现者可自由选择。 |
| O-2 | plan-02 §3.6 line 168 | Decimal 序列化建议"或配 `model_config = ConfigDict(json_encoders={Decimal: float})`" | Pydantic v2 的 `json_encoders` 已被 deprecate（推荐用 serializer）。但 plan-02 主建议是"参照 funds.py 的 `_serialize_value` 显式 float() 转换"（这条是对的），`json_encoders` 只是备选。funds.py line 106-115 `_serialize_value` 确实 `float(Decimal)`，plan-02 主建议准确。不阻塞。 |

## 六、维度检查结果

| 维度 | 结论 | 问题数 | 摘要 |
| --- | --- | --- | --- |
| 1 核心闭环与系统目标 | ✅ 继承良好 | 0 | README §2.1 + 各 plan 概要覆盖 Group→Match→Aggregate→Query 闭环 |
| 2 范围与非目标 | ✅ 继承良好 | 0 | P0 全承接，非目标（个股详情页、自定义分组、预计算等）在各 plan"不在范围"中呼应 |
| 3 成功标准 | ✅ 继承良好 | 0 | 性能目标（<3s/<2s/<1s）落到 plan-02/03/04 验收 |
| 4 验收标准防漂移 | ✅ 继承良好 | 0 | AC-01~11 全部映射 README 矩阵 + 至少一个 plan（已逐条 grep 核实）；E2E-TDD red/green 实质内容齐全（plan-03/04 §5） |
| 5 ADR 约束 | ✅ 继承良好 | 0 | ADR-1~7 均在实现规格/护栏体现；ADR-1 CASCADE 在 plan-01 line 52/56/106 落地、ADR-2 LIKE 转义在 plan-01 §3.3/plan-02 §3 落地、ADR-6 ON CONFLICT 在 plan-01 §3.5 落地 |
| 6 用户流程与状态机 | ✅ 继承良好 | 0 | 流程 A/B、状态机、关键分支均在 plan-02/04 覆盖 |
| 7 模块职责与系统上下文 | ✅ 继承良好 | 0 | 模块地图 + depends_on 一致 |
| 8 运行链路 | ✅ 继承良好 | 0 | §6.1~6.5 各步在 plan-02/03/04 实现；report_period Date→String 转换（plan-02 §3.1 line 44）落地 |
| 9 数据模型与契约 | ⚠️ 有建议 | 2 | S-1（Admin response 命名约定缺失 + GroupListItem snake_case 残留）、S-2（描述性文字 snake_case）；契约块层面 camelCase 已统一（B-5 彻底）；复用链路（top10_float_holders 字段、sectors/sector_stocks 关联、BaseRepository、require_admin、AdminApiClient）均核实正确 |
| 10 非功能需求 | ✅ 继承良好 | 0 | 性能/降级/安全/LIKE 转义均落地；Decimal 序列化（N-2）落地 |
| 11 实施建议与技术选型 | ✅ 继承良好 | 0 | 技术栈一致，阶段划分符合依赖 |
| 12 风险与未决策项 | ✅ 继承良好 | 0 | 架构风险在 plan 风险与边界有缓解；SWR key 抖动风险 plan-04 §8 line 378 已标注 |
| 13 功能拆分质量 | ✅ 继承良好 | 0 | N-5 已落地，Repository 构造函数示例完整；拆分合理 |
| 14 可执行性 | ✅ 继承良好 | 0 | 文件清单路径具体；前置条件可验证；E2E-TDD red/green 顺序可执行；复用声明（top10_float_holders/sectors/sector_stocks/stocks/BaseRepository/require_admin/AdminApiClient）对照真实代码全部核实通过 |
| 15 状态与报告契约 | ✅ 继承良好 | 0 | frontmatter/状态均合法 |
| 16 复用声明链路验证 | ✅ 继承良好 | 0 | 见维度 9/14，全部核实通过 |

## 七、四类契约盲区逐 endpoint 复核 + 新盲区搜索

### 已知四类盲区复核（memory `dev-plan-check-path-prefix`）

| 盲区 | 检查范围 | 结论 |
| --- | --- | --- |
| 1 路径前缀 | 用户侧 `/api/v1/shareholder-analysis/*`（main `/api` × v1 `/v1` × 子 router `/shareholder-analysis`）；管理侧 `/api/v1/admin/shareholder-groups/*`（main `/api` × admin router `/v1/admin` × 子 router `/shareholder-groups`） | ✅ 挂载链核实通过：`main.py:113` `/api`、`router.py:29` `/v1/admin`、`v1/__init__.py:36` `/v1`、子 router 自带 prefix。plan-02 §3.6/plan-01 §3.4 "文件内声明 prefix，注册时不再加"准确。plan-03 §7 路径对齐备注准确。前端 `api.ts:8` `API_BASE_WITH_PREFIX=/api/v1` 与调用路径吻合。 |
| 2 HTTP 方法存在性 | GET（用户侧 4 + 管理侧 2）/ POST（管理侧 1）/ PATCH（管理侧 1）/ DELETE（管理侧 1） | ✅ AdminApiClient 有 get/post/patch/delete（line 514/519/524/529），无 put（印证 B-3 PATCH 正确）；ApiClient 有 get/post/put/delete（line 118/123/128/133）。所有方法在客户端真实存在。 |
| 3 query 命名 | `report_period`/`group_ids`/`industry`/`change_direction`/`page`/`page_size`/`keywords`/`exclude_group_id` 全 snake_case | ✅ 与 funds.py Query 参数约定（line 164/203/282 `page_size`）一致；plan-04 §3.1 query 字符串拼 snake_case、TS 入参 camelCase 的分离正确；to_camel 不作用于 query（Pydantic alias 只影响 response body）。 |
| 4 response 字段 alias | 架构 §7.2 + plan-02 §7 + plan-04 §7 契约块全 camelCase | ✅ 契约块层面彻底（B-5 核实）；残留 S-1（plan-01/03 GroupListItem）+ S-2（描述性文字），均非契约块。 |

### 主动搜索第五类、第六类盲区

| 候选盲区 | 检查方式 | 结论 |
| --- | --- | --- |
| 5 response 解包层级（ApiResponse 包裹 vs fetcher `.then(res=>res.data)` vs 组件 `data.data`） | 核实 useFunds.ts 真实模式 + plan-04 §3.2 N-6 说明 | ✅ 已被 recheck4 N-6 覆盖，plan-04 §3.2 line 99 说明完整，与 useFunds.ts `data?.data?.items` 一致。无新问题。 |
| 6 SWR key 抖动/漏触发 | 核实 plan-04 SWR key 模式 vs useFunds.ts | ✅ plan-04 用 `['key', params]` 数组 key，与 useFunds.ts `['fundList', params]` 一致；plan-04 §8 line 378 已主动标注"需确保 SWR key 正确变化触发重新请求"风险。无新问题。 |
| 7 Decimal/date 序列化 | 核实 plan-02 §3.6 + funds.py `_serialize_value`/`_dict_to_camel` | ✅ plan-02 §3.6 line 168 明确 Decimal `float()` 转换；report_period Date→String 在 plan-02 §3.1 line 44 明确 `.isoformat()`。funds.py `_serialize_value`（line 106-115）+ `_dict_to_camel`（line 119-124）模式可参照。观察项 O-1/O-2 记录了 funds.py 实际用 `_dict_to_camel` 而非 response_model 的细节差异，不阻塞。 |
| 8 外键 CASCADE | 核实 plan-01 §3.1 line 56 + 架构 ADR-1 | ✅ `ForeignKey("shareholder_groups.id", ondelete="CASCADE")` + `cascade="all, delete-orphan"` 双保险；架构 §6.5 line 346 明确 CASCADE 删除。无新问题。 |
| 9 索引 | 核实 plan-01 §3.1 line 60 | ✅ `ix_sgr_group_id` on group_id；top10_float_holders 表已有 `ix_top10_symbol_period`/`ix_top10_report_period`（model 自带）。无新问题。 |
| 10 AC 映射完整性 | 逐条 grep AC-01~11 在 README + plan 出现 | ✅ 全部 11 个 AC 在 README 矩阵 + 至少一个 plan 承接，与架构 §2.4 对齐。无孤立验收项。 |
| 11 ADR 护栏 | ADR-1~7 是否在 README/plan 体现 | ✅ README §2.2 护栏表覆盖 ADR-1~7；禁止事项（物化视图/缓存/股东实体表/用户自定义分组）在各 plan"不在范围"呼应。 |
| 12 E2E-TDD 实质性 | plan-03/04 §5 是否有 red/green 两阶段 + spec/evidence 路径 | ✅ plan-03 §5 line 159-162、plan-04 §5 line 273-285 均有 red/green 阶段 + `docs/e2e/` 用例路径 + `docs/e2e/evidence/` 证据路径 + 核心覆盖场景列举。 |
| 13 复用声明对照真实代码 | top10_float_holders/sectors/sector_stocks/stocks/BaseRepository/require_admin/AdminApiClient | ✅ 见维度 16，全部核实通过。 |

**未发现第五类、第六类新盲区。** recheck1~4 已覆盖路径前缀、HTTP 方法、query 命名、response alias、解包层级、SWR key 六大类，本轮逐一复核均通过。

## 八、验收标准追踪

AC-01 ~ AC-11 全部映射到 README 矩阵和至少一个 FEAT（已逐条 grep 核实），无孤立验收项，无弱化或改写。本轮无 blocker 影响 AC 验收。建议项 S-1/S-2 不影响 AC 可验证性。

## 九、合理扩展

| 位置 | 扩展内容 | 为什么合理 |
| --- | --- | --- |
| plan-04 §5 | E2E-TDD 验收项（7 核心场景 + red/green + spec/evidence 路径） | recheck2 B-2 落实，覆盖 AC-01~05/08/09/11 |
| plan-03 §5 | 管理端 E2E-TDD（新增→编辑关键词+预览→删除二次确认） | 管理端关键路径的端到端覆盖 |
| plan-04 §5 | US 覆盖矩阵 + 降级回归验收（L1~L3） | 首检已认定合理 |
| plan-02 §3.1 | `_get_report_periods` 被 overview/summary 共用 | 合理的内部抽取 |
| plan-02 §3.6 | Decimal 序列化 + ApiResponse 包裹 + to_camel alias 三项明确 | recheck3 N-2 + recheck4 B-5 落实 |

## 十、问题清单汇总

| 严重级别 | 位置 | 问题 | 修补建议 |
| --- | --- | --- | --- |
| 🟡 建议 | plan-01 §3.4 + §7 line 251 + plan-03 §7 line 192 | S-1 Admin response 命名约定缺失 + GroupListItem snake_case 残留 | §3.4 补"参照 admin/users.py 直接 camelCase 字段"；§7 GroupListItem 改 camelCase |
| 🟡 建议 | plan-02 §5 line 190-192 + plan-04 line 180/365/368 | S-2 描述性文字 snake_case 字段名与 §7 契约块 camelCase 不一致 | 描述性字段名改 camelCase 或加说明 |

## 十一、建议补丁计划（按优先级）

1. **【建议，非阻塞】** S-1：plan-01 §3.4 补 Admin API response 命名约定说明（参照 `admin/users.py` 直接 camelCase 字段定义，不走 to_camel alias）；plan-01 §7 line 251 + plan-03 §7 line 192 的 `GroupListItem` 字段对齐架构 §7.2 camelCase（`isSystem`/`ruleCount`/`matchedStockCount`）。
2. **【建议，非阻塞】** S-2：plan-02 §5 line 190-192 + plan-04 line 180/365/368 的描述性字段名改 camelCase，与 §7 契约块统一。

两项均为文档内部命名风格统一的轻微优化，**不影响实现者照 §7 契约块（已 camelCase）和 §3.6/§3.4 实现规格写代码**。可在 plan-01/02/03/04 进入实现前顺手修正，也可在实现过程中发现时修正。

## 十二、收敛建模结论

经过六轮 dev-plan-check（首检 + 5 次 recheck），实现计划已从最初的 8 建议 → 1 建议 → 2 blocker → 2 blocker → 3 blocker → **本轮 0 blocker / 2 建议**，呈现明确的收敛趋势。recheck4 的 3 个 blocker（B-3′/B-4′/B-5）在本轮逐条代码级核实确认**全部彻底落地，无"半改"复发**——这是本轮最关键的结论，因为 recheck3→recheck4 曾出现过两次"半改"（B-3 漏 README 矩阵、B-4 只改前端未同步后端），本轮特别警惕此模式，对每个修复点都做了跨文档 grep 全量核实。

本轮发现的 2 个建议项（S-1/S-2）都是"文档内部命名风格未完全统一"的轻微不一致，影响的是文档可读性而非实现正确性——实现者写代码时依据的是 §7 契约块（已 camelCase）和 §3 实现规格，不会因描述性文字的 snake_case 而写错字段访问。

**四类契约盲区（路径前缀、HTTP 方法、query 命名、response alias）+ 主动搜索的第五~第十三类候选盲区（解包层级、SWR key、Decimal/date 序列化、CASCADE、索引、AC 映射、ADR 护栏、E2E-TDD、复用声明）全部逐一核实通过。**
