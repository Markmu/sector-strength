# 开发计划检查报告（第五次独立复审 recheck4）

## 一、检查对象

- **架构文档**：`docs/06-股东分析面板/06-1-架构文档-股东分析面板.md`
- **实现计划**：`docs/06-股东分析面板/06-2-实现计划-股东分析面板/`（README + plan-01 ~ plan-04）
- **功能数**：4
- **前次报告**：
  - `dev-plan-check-20260613.md`（首检，8 建议，通过）
  - `dev-plan-check-20260613-recheck.md`（复查，1 建议，通过）
  - `dev-plan-check-20260613-recheck2.md`（第二次复查，2 blocker B-1/B-2 + 5 建议，有阻塞）
  - `dev-plan-check-20260613-recheck3.md`（第三次复查，2 blocker B-3/B-4 + 4 建议，有阻塞）
- **本次检查日期**：2026-06-13
- **本轮身份**：全新上下文独立复审者，不盲从前序结论

## 二、总评

- **结论**：⚠️ **有阻塞问题**（B-3 的 PUT→PATCH 修复在 README 追踪矩阵未改到位；B-4 的 query 命名修复只改了前端 plan-04，未同步后端 plan-02 的端点描述/Service 签名/架构基准，造成 plan-02 与 plan-04 内部矛盾；另发现前三轮均遗漏的第 4 类契约盲区——Pydantic `to_camel` alias 与前端消费的 TS 字段命名不一致）
- **阻塞问题数**：3（B-3′、B-4′、B-5）
- **建议项数**：3（N-1 已落地确认记录 + 2 新建议）

本轮作为全新上下文独立复审，重点做了三件事：(1) 逐条代码级核实 recheck3 声称修复的 5 项；(2) 用怀疑的眼光重新过 16 个维度；(3) 主动寻找第四类、第五类契约盲区。结论：recheck3 的 5 项修复中 **B-3 改了一半**（漏了 README 追踪矩阵），**B-4 改了一半**（只改前端未同步后端 plan-02 与架构基准），并发现一个前三轮都未触及的 **Pydantic alias vs 前端消费字段命名** 维度的新 blocker（B-5）。

## 三、Contract 预检

全部通过（与前次一致）：

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

## 四、recheck3 五项修复独立核实（任务第一层）

> 逐条代码级核实，不因"声称已修"就放过。

| 编号 | 内容 | 核实结果 | 证据 |
| --- | --- | --- | --- |
| B-3 | 编辑分组接口 `PUT`→`PATCH`（架构 §6.4/§7.3/AC-07 + plan-01 + plan-03） | ❌ **改了一半** | 架构已修：`06-1` line 64 AC-07 `PATCH`、line 328 §6.4 `PATCH`、line 477 §7.3 `PATCH`、line 644 Phase B `PATCH /{id}` ✅；plan-01 §3.4 line 122 `PATCH /api/admin/shareholder-groups/{id}`、§5 line 171、验证 line 223 `-X PATCH` ✅；plan-03 §3.1 line 47 `adminApiClient.patch(\`/admin/shareholder-groups/${id}\`, data)` ✅；代码核对 `web/src/lib/api.ts` line 523-525 `AdminApiClient.patch` 存在且自动带鉴权 ✅。**但 README §3 追踪矩阵 line 79 AC-07 仍写 `Admin API PUT /shareholder-groups/{id}`** ❌ —— recheck3 变更记录（README line 173）声称改了"架构 §6.4/§7.3/AC-07"，实际只改了架构文档自身的 AC-07（line 64），漏改了 README 平行的追踪矩阵。追踪矩阵是 plan 执行者最先看的文档，残留 PUT 会误导实现者，且与 plan-01/03 不自洽。 |
| B-4 | plan-04 `getHoldings` query key `pageSize`→`page_size` | ❌ **只改前端，未同步后端 plan-02 与架构基准，造成跨 plan 矛盾** | plan-04 §3.1 line 68 已改 `page_size: String(params.pageSize || 20)`（query key snake_case）✅；line 67 补注释"query key 用 snake_case（后端 Query 参数约定，to_camel 不作用于 query）"✅。**但 plan-02 未同步**：§3.6 line 159 holdings 端点 Query 描述仍写 `pageSize（默认 20）`（camelCase）❌；§5 line 199 AC-02 验收 curl `&pageSize=20` ❌；§6 line 258 验证命令 curl `&pageSize=20` ❌；只有 §3 line 129 Service 方法签名是 `page_size: int = 20`（snake_case，与前端一致）✅。**架构基准（06-1）也未同步**：line 52/258/286/287/474/615/635 全部仍是 `pageSize`（camelCase）。recheck3 在 B-3 里同步改了架构保持基准一致，B-4 却刻意没改架构（变更记录 line 173 只提"plan-04"），导致架构基准（`pageSize`）、plan-02 端点描述（`pageSize`）、plan-02 Service 签名（`page_size`）、plan-04 query key（`page_size`）四方打架。 |
| N-1 | plan-01 §3.4 / plan-02 §3.6 明示新路由文件内 `APIRouter(prefix=...)` | ✅ 已落地 | plan-01 §3.4 line 117 "新建 `server/src/api/admin/shareholder_groups.py`，**文件内必须声明 prefix**：`router = APIRouter(prefix='/shareholder-groups', tags=['Admin - Shareholder Groups'])`（参照 users.py / data_status.py）"；plan-02 §3.6 line 147 同样明示 `APIRouter(prefix='/shareholder-analysis', tags=['Shareholder Analysis'])`（参照 funds.py）。代码核对 `users.py` line 24 `APIRouter(prefix='/users', ...)`、`funds.py` line 24 `APIRouter(prefix='/funds', ...)`、`admin/__init__.py` line 28-35 与 `v1/__init__.py` line 27-36 注册时均不再加 prefix —— 描述与真实代码完全一致 ✅ |
| N-2 | plan-02 补 Decimal→float 说明 | ✅ 已落地 | plan-02 §3.6 line 168 "Decimal 序列化：`total_hold_amount`/`total_hold_float_ratio`/`avg_hold_float_ratio` 经 SUM/AVG 聚合后为 Decimal，Pydantic v2 默认序列化为字符串会破坏前端数值比较与图表渲染。参照 funds.py 的 `_serialize_value`，这些字段显式 `float()` 转换后再放入响应（或在 Pydantic model 配 `model_config = ConfigDict(json_encoders={Decimal: float})`）"。代码核对 `funds.py` line 106-115 `_serialize_value` 确实 `float(Decimal)` + `date.isoformat()`；model line 19-21 确为 `Numeric(20,2)`/`Numeric(10,4)` → 描述准确 ✅ |
| N-4 | plan-03 §7 路径对齐备注 | ✅ 已落地 | plan-03 §7 line 186 "路径对齐备注：架构 §7.3 写 `/api/admin/shareholder-groups`，但代码实际挂载链为 `/api/v1/admin/*`（main.py prefix `/api` × admin router）。前端 `adminApiClient`（baseURL 已含 `/api/v1`）调用 `/admin/shareholder-groups` → `/api/v1/admin/shareholder-groups`，与代码一致；plan 按代码实际挂载链对齐，架构 §7.3 的 `/api/admin/` 前缀为文档笔误"。代码核对 `main.py:113 app.include_router(api_router, prefix='/api')` + `router.py:29 router.include_router(admin_router, prefix='/v1/admin')` → `/api/v1/admin/*`；`api.ts:8 API_BASE_WITH_PREFIX=/api/v1` —— 描述准确 ✅ |

**小结**：recheck3 的 5 项中 N-1/N-2/N-4 三项真实落地且正确；**B-3 漏改了 README 追踪矩阵（line 79）**；**B-4 只改了前端 plan-04，未同步 plan-02 后端端点描述/Service 签名/curl 示例，也未像 B-3 那样同步架构基准**，导致 plan-02 与 plan-04 内部矛盾。两项均需补修。

## 五、本轮新发现问题（recheck1~3 都遗漏）

### 🔴 Blocker

| 编号 | 位置 | 问题 | 修补建议 |
| --- | --- | --- | --- |
| B-3′ | README §3 追踪矩阵 line 79（AC-07） | **B-3 修复残留：追踪矩阵仍写 `PUT`。** 代码核实：架构 line 64、plan-01 line 122/171/223、plan-03 line 47 全部已是 `PATCH`；唯一残留是 README 追踪矩阵 line 79 `Admin API PUT /shareholder-groups/{id}`。追踪矩阵是 dev-plan-check 通过标准的核心校验对象（"架构 AC-XX 全部映射到 README 和至少一个 FEAT"），且实现者通常会照矩阵回查架构原文，残留 PUT 会让人怀疑架构是否还是 PATCH。 | README line 79 `PUT` → `PATCH`。同步在变更记录补一行"补修 recheck3 B-3 漏改的 README 追踪矩阵 AC-07"。 |
| B-4′ | plan-02 §3.6 line 159（端点描述）+ §5 line 199 / §6 line 258（curl 示例）+ 架构 06-1 line 52/258/286/287/474/615/635 | **B-4 修复不完整：前后端 query 命名矛盾未收敛。** plan-04 §3.1 line 68 已改 `page_size`（前端发 snake_case），但 plan-02 §3.6 line 159 holdings 端点 Query 描述仍写 `pageSize（默认 20）`、§5 line 199 + §6 line 258 curl 示例仍写 `&pageSize=20`、架构 06-1 line 52/258/286/287/474/615/635 仍是 `pageSize`。实现者照 plan-02 line 159 定义 `pageSize: int = Query(20)`（camelCase）则 plan-04 发的 `page_size` 匹配不上 → 分页静默失效（B-4 原始问题重现，只是方向反转）。plan-02 自身也不自洽：§3 line 129 Service 签名 `page_size`（snake_case）vs §3.6 line 159 端点描述 `pageSize`（camelCase）。 | 全量统一为 `page_size`（与 funds.py line 164/203/282 项目约定 + plan-04 前端 + plan-02 Service 签名一致）：(1) plan-02 §3.6 line 159 端点 Query 描述改 `page（默认 1）、page_size（默认 20）`；§5 line 199、§6 line 258 curl 改 `&page_size=20`；(2) 架构 06-1 line 52/258/286/287/474/615/635 全部 `pageSize` → `page_size`（保持基准一致，与 B-3 处理 PATCH 时同等待遇）。 |
| B-5 | plan-02 §3.6 line 166（Pydantic to_camel）↔ plan-02 §7 + plan-04 §7（HoldingItem 等消费字段） | **第 4 类契约盲区：Pydantic `to_camel` alias 与前端消费的 TS 字段命名不一致。** plan-02 §3.6 line 166 规定"Pydantic response model 使用 `alias_generator=to_camel` + `populate_by_name=True`（参照 funds.py）"，即 API 输出 camelCase（`stockName`/`totalHoldAmount`/`changeDirection`/`totalHoldFloatRatio`）。但 plan-02 §7 交接上下文与 plan-04 §7 交接上下文均把消费字段写成 **snake_case**：`HoldingItem: { symbol, stock_name, total_hold_amount, total_hold_float_ratio, change_direction, industries }`、`GroupOverview: { group_id, group_name, ..., stock_count, increase_count, ... }`、`IndustryItem: { industry, stock_count, percentage }`。两套命名不可能同时成立：若后端用 to_camel，API 实发 camelCase，前端按 §7 的 snake_case 类型访问会拿到 `undefined`；若 §7 的 snake_case 才是目标，则 plan-02 §3.6 的 to_camel 说明错误。参照对象 funds.py 是**自洽**的：后端 FundPortfolioOut 用 to_camel（funds.py line 70），前端 PortfolioItem TS 类型用 camelCase（api.ts line 335-349，`stockName`/`marketValue`/`stkMkvRatio` 等），两端一致。股东分析这一对没对齐。前三轮（B-1 路径前缀、B-3 HTTP 方法、B-4 query 命名）查的是"路径/方法/query 名"，**未触及"response body 字段名 alias"**，这是遗漏的第 4 类盲区。 | 二选一统一：(A) **推荐**：保持 to_camel（与 funds 一致），改 plan-02 §7 + plan-04 §7 的消费字段为 camelCase（`stockName`/`totalHoldAmount`/`totalHoldFloatRatio`/`changeDirection`/`groupId`/`groupName`/`stockCount`/`increaseCount`/`hasPrevPeriod`/`reportPeriods`/`currentPeriod` 等），plan-04 §3.4~3.8 组件内读取的字段名一并改 camelCase；(B) 保持 §7 snake_case，则删去 plan-02 §3.6 line 166 的 to_camel 说明，改为"response model 字段直接 snake_case 输出（不使用 alias），与前端消费类型一致"。无论哪种，plan-02 与 plan-04 必须同向。 |

> 说明：B-3′/B-4′ 是 recheck3 修复的"收尾未完成"，B-5 是前三轮完全未覆盖的新维度。三者都会导致运行时/编译期问题：B-3′ 误导文档读者，B-4′ 分页静默失效（方向反了），B-5 前端按错名字段访问拿到 undefined（概览卡片/持仓表格全空）。

### 🟡 建议项（新发现）

| 编号 | 位置 | 问题 | 修补建议 |
| --- | --- | --- | --- |
| N-5 | plan-01 §3.2 Repository 子类化 | **`BaseRepository.__init__(self, model, session)` 需双参，plan-01 未展示 `__init__` 写法。** 代码核实 `base.py` line 29 `def __init__(self, model, session)`，所有现有 repo（`fund_repository.py` line 38-39、`sector_repository.py` line 20、`stock_repository.py` line 20 等）均定义 `def __init__(self, session): super().__init__(Model, session)`。plan-01 §3.2 只说"继承 `BaseRepository[ShareholderGroup]`"并列举 `get_with_rules` 等自定义方法，未展示构造函数。实现者大概率照兄弟 repo 抄，但 plan 应明示避免漏 `super().__init__(ShareholderGroup, session)` 导致实例化时缺 `model` 参数报错。 | plan-01 §3.2 补一句"参照 `FundRepository.__init__(self, session): super().__init__(ShareholderGroup, session)`"。 |
| N-6 | plan-04 §3.2 SWR fetcher 解包层级 | **`.then(res => res.data)` 后组件读 `data` 还是 `data.data` 未明示，易踩坑。** 代码核实 useFunds.ts：fetcher `.then(res => res.data)`（解一层得到 `{success, data}` body），组件再读 `data?.data?.items`（再解一层）。这是因为 fundsApi 返回 `ApiResponse<{success, data}>`，`res.data` 是整个 body。plan-04 §3.2 fetcher 同样写 `.then(res => res.data)`，但未说明组件消费时是读 hook 返回的 `data`（= body `{success, data}`）还是 `data.data`（= 业务对象）。结合 B-5 的命名问题，如果按推荐方案 A 走 camelCase，这里层级说明更不能省。 | plan-04 §3.2 补一句"fetcher 返回的 `res.data` 即 `{success, data}` body，hook 的 `data` 字段是该 body，组件消费 `data.data` 取业务对象（与 useFunds.ts 一致）"。 |

## 六、维度检查结果

| 维度 | 结论 | 问题数 | 摘要 |
| --- | --- | --- | --- |
| 1 核心闭环与系统目标 | ✅ 继承良好 | 0 | README §2.1 + 各 plan 概要覆盖 Group→Match→Aggregate→Query 闭环 |
| 2 范围与非目标 | ✅ 继承良好 | 0 | P0 全承接，非目标（个股详情页、自定义分组、预计算等）在各 plan"不在范围"中呼应 |
| 3 成功标准 | ✅ 继承良好 | 0 | 性能目标（<3s/<2s/<1s）落到 plan-02/03/04 验收 |
| 4 验收标准防漂移 | ⚠️ 有 blocker | 1 | B-3′（README 追踪矩阵 AC-07 残留 PUT）；E2E-TDD red/green 实质内容齐全（plan-03/04 §5） |
| 5 ADR 约束 | ✅ 继承良好 | 0 | ADR-1~7 均在实现规格/护栏体现 |
| 6 用户流程与状态机 | ✅ 继承良好 | 0 | 流程 A/B、状态机、关键分支均在 plan-02/04 覆盖 |
| 7 模块职责与系统上下文 | ✅ 继承良好 | 0 | 模块地图 + depends_on 一致 |
| 8 运行链路 | ✅ 继承良好 | 0 | §6.1~6.5 各步在 plan-02/03/04 实现 |
| 9 数据模型与契约 | ⚠️ 有 blocker | 2 | B-4′（query 命名跨 plan 矛盾）、B-5（to_camel alias vs 消费 TS 字段不一致）；复用链路（top10_float_holders 字段、sectors/sector_stocks 关联、BaseRepository、require_admin）均核实正确 |
| 10 非功能需求 | ✅ 继承良好 | 0 | 性能/降级/安全/LIKE 转义均落地 |
| 11 实施建议与技术选型 | ✅ 继承良好 | 0 | 技术栈一致，阶段划分符合依赖 |
| 12 风险与未决策项 | ✅ 继承良好 | 0 | 架构风险在 plan 风险与边界有缓解 |
| 13 功能拆分质量 | ⚠️ 有建议 | 1 | N-5（Repository 构造函数未展示）；其余拆分合理 |
| 14 可执行性 | ⚠️ 有 blocker | 2 | B-3′、B-4′（文档/契约可执行性）；B-5（前后端字段名不匹配导致运行时取值 undefined） |
| 15 状态与报告契约 | ✅ 继承良好 | 0 | frontmatter/状态均合法 |
| 16 复用声明链路验证 | ✅ 继承良好 | 0 | top10_float_holders / sectors / sector_stocks / stocks / BaseRepository / require_admin / AdminApiClient 复用声明均与代码一致 |

## 七、验收标准追踪

AC-01 ~ AC-11 全部映射到 README 矩阵和至少一个 FEAT，无孤立验收项。受本轮 blocker 影响的 AC：

- **AC-07**（编辑匹配规则）：B-3′（README 追踪矩阵残留 PUT）—— 文档不一致，不阻塞实现但阻塞矩阵校验
- **AC-02 / AC-05**（持仓查询、变动方向筛选，含分页）：B-4′（query 命名 plan-02 vs plan-04 矛盾）—— 若实现者照 plan-02 line 159 写 `pageSize` 则分页失效
- **AC-01 ~ AC-05**（所有展示持仓数据的场景）：B-5（to_camel vs snake_case 消费字段不匹配）—— 前端按 §7 snake_case 访问会全空

## 八、合理扩展

| 位置 | 扩展内容 | 为什么合理 |
| --- | --- | --- |
| plan-04 §5 | E2E-TDD 验收项（7 核心场景 + red/green + spec/evidence 路径） | 落实 recheck2 B-2，覆盖 AC-01~05/08/09/11，符合通过标准 |
| plan-03 §5 | 管理端 E2E-TDD（新增→编辑关键词+预览→删除二次确认） | 管理端关键路径的端到端覆盖 |
| plan-04 §5 | US 覆盖矩阵 + 降级回归验收（L1~L3） | 首检已认定合理，维持 |
| plan-02 §3.1 | `_get_report_periods` 被 overview/summary 共用 | 合理的内部抽取，避免报告期逻辑重复 |

## 九、问题清单汇总

| 严重级别 | 位置 | 问题 | 修补建议 |
| --- | --- | --- | --- |
| 🔴 blocker | README §3 line 79 | B-3′ 追踪矩阵 AC-07 残留 PUT | `PUT`→`PATCH` |
| 🔴 blocker | plan-02 §3.6 line 159 / §5 line 199 / §6 line 258 + 架构 06-1 line 52/258/286/287/474/615/635 | B-4′ query 命名前后端矛盾未收敛 | 全量 `pageSize`→`page_size`（plan-02 端点描述 + curl + 架构基准） |
| 🔴 blocker | plan-02 §3.6 line 166 ↔ plan-02 §7 / plan-04 §7 | B-5 to_camel alias vs 消费 TS 字段命名不一致 | 二选一统一（推荐保持 to_camel，改 §7 + 组件为 camelCase） |
| 🟡 建议 | plan-01 §3.2 | N-5 Repository 构造函数未展示 | 补 `super().__init__(ShareholderGroup, session)` 写法 |
| 🟡 建议 | plan-04 §3.2 | N-6 SWR fetcher 解包层级未明示 | 补"组件读 `data.data` 取业务对象"说明 |

## 十、建议补丁计划（按优先级）

1. **【blocker，必须】** README §3 line 79：`PUT` → `PATCH`（B-3′）。同步变更记录补一行说明。
2. **【blocker，必须】** plan-02 §3.6 line 159 端点 Query 描述 `pageSize` → `page_size`；plan-02 §5 line 199 + §6 line 258 curl 示例 `&pageSize=20` → `&page_size=20`；架构 06-1 line 52/258/286/287/474/615/635 全部 `pageSize` → `page_size`（B-4′，保持基准与 plan-04/plan-02 Service 签名一致）。
3. **【blocker，必须】** B-5：统一 response body 字段命名。推荐方案 A——保持 plan-02 §3.6 的 to_camel，改 plan-02 §7 + plan-04 §7 消费字段为 camelCase（`stockName`/`totalHoldAmount`/`totalHoldFloatRatio`/`changeDirection`/`groupId`/`groupName`/`stockCount`/`increaseCount`/`decreaseCount`/`newCount`/`exitCount`/`hasPrevPeriod`/`reportPeriods`/`currentPeriod`），plan-04 §3.4~3.8 组件字段访问一并改。同步在 plan-04 §3.2 补 N-6 解包层级说明。
4. **【建议】** plan-01 §3.2：补 Repository 构造函数写法（N-5）。

修补 B-3′/B-4′/B-5 三个 blocker 后建议再次复审。三者均为"前后端契约不一致"类问题，修复成本很低（改字段名/方法名/示例 + 一句话说明），但**必须在 plan-02/03/04 进入实现前修正**：B-5 不修则前端按错名字段访问概览卡片/持仓表格全空，B-4′ 不修则分页静默失效，B-3′ 不修则追踪矩阵自相矛盾。
