# 开发计划检查报告（第四次独立复审 recheck3）

## 一、检查对象

- **架构文档**：`docs/06-股东分析面板/06-1-架构文档-股东分析面板.md`
- **实现计划**：`docs/06-股东分析面板/06-2-实现计划-股东分析面板/`（README + plan-01 ~ plan-04）
- **功能数**：4
- **前次报告**：
  - `dev-plan-check-20260613.md`（首检，8 项建议 S-01~S-08，结论"通过"）
  - `dev-plan-check-20260613-recheck.md`（复查，1 项 plan-03 icon，结论"通过"）
  - `dev-plan-check-20260613-recheck2.md`（第二次复查，2 blocker B-1/B-2 + 5 建议 S-1~S-5，结论"有阻塞"）
- **本次检查日期**：2026-06-13

## 二、总评

- **结论**：⚠️ **有阻塞问题**（本轮在确认 recheck2 七项修复基本落地的同时，新发现 1 个会导致前端编译失败的 blocker + 1 个 query 命名契约不一致的 blocker，以及若干建议项）
- **阻塞问题数**：2（B-3、B-4，均为 recheck2 遗漏的新问题）
- **建议项数**：4（N-1~N-4，均为本轮新发现）

本轮作为**全新上下文独立复审**，重点做了两件事：(1) 逐条代码级核实 recheck2 声称修复的 7 项；(2) 用怀疑的眼光重新过路由挂载链、HTTP 方法集合、query 命名约定、Numeric 序列化等代码层细节，发现 recheck2 仅核对了"路径前缀"和"E2E 文字"，但**漏检了 HTTP 方法（put vs patch）和 query 参数命名（pageSize vs page_size）两个会直接导致编译失败/契约不匹配的问题**。

## 三、Contract 预检

与前次结论一致，全部通过：

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
| Task / 边界场景状态合法 | ✅ | 全部 `todo`，无 `waived` |
| `depends_on` 引用真实 | ✅ | plan-02/03→plan-01，plan-04→plan-02 |

## 四、验收标准追踪

AC-01 ~ AC-11 全部映射到 README 矩阵和至少一个 FEAT，映射关系与前次结论一致，无孤立验收项。本轮不重复展开，仅标注受本轮新 blocker 影响的 AC：

- **AC-07（编辑匹配规则）** 受 B-3（`adminApiClient.put` 不存在）影响 —— 前端编译失败，整个 plan-03 无法构建。
- **AC-02/AC-05（持仓查询、变动方向筛选）** 受 B-4（`pageSize` query 命名）影响 —— 分页参数传不到后端，holdings 永远走默认 page_size。

## 五、recheck2 七项修复独立核实

> 本节是任务第一层。逐条代码级核实，不因"声称已修"就放过。

| 编号 | 内容 | 核实结果 | 证据 |
| --- | --- | --- | --- |
| B-1 | plan-04 §3.1/§3.2 用户侧 API 去除双 `/v1` 前缀 | ✅ 已落地 | plan-04 §3.1 四个方法路径现为 `/shareholder-analysis/overview`、`/summary`、`/industry-distribution`、`/holdings`（无前导 `/v1`）；§3.1 line 49 明确注释"apiClient.baseURL 已含 /api/v1...路径不再带 /v1，避免双前缀"。代码核对：`web/src/lib/api.ts` line 8 `API_BASE_WITH_PREFIX = ${API_BASE_URL}/api/v1`、line 64 拼接 `${this.baseURL}${endpoint}`；后端 `funds.py` line 24 `APIRouter(prefix="/funds")` + v1 router `prefix="/v1"` + `main.py:113 app.include_router(api_router, prefix="/api")` → `/api/v1/funds`。前端 `/shareholder-analysis/overview` 拼成 `/api/v1/shareholder-analysis/overview`，与后端新路由（文件内 `prefix="/shareholder-analysis"`）一致 ✅ |
| B-2 | plan-03/04 补实质 E2E-TDD 验收项（red+green+spec+evidence） | ✅ 已落地（实质内容） | plan-04 §5 "E2E-TDD 验收"段（line 270-284）含：red 阶段指向 `docs/e2e/06-e2e-用例-股东分析面板.md`、证据 `docs/e2e/evidence/plan-04-e2e-red-{date}.md`；green 阶段同 spec + green 证据；并列出 7 个核心覆盖场景（AC-01~05/08/09/11）。plan-03 §5（line 157-162）同样有 red/green + spec `docs/e2e/06-e2e-用例-股东分组管理.md` + 覆盖场景。两处均为"两阶段+具体 spec+evidence 路径"实质内容，非空话 ✅ |
| S-1 | plan-04 hooks 改 `useFunds.ts` 模式（数组 key + apiClient，不用 lib/fetcher） | ✅ 已落地 | plan-04 §3.2（line 77-98）明确"参照现有 useFunds.ts 模式""SWR 使用数组 key + fetcher 内部调用 shareholderAnalysisApi（经 apiClient）...不直接使用 lib/fetcher.ts"；四个 hooks key 均为数组形式（`['shareholderOverview', reportPeriod ?? null]` 等），fetcher 均 `.then(res => res.data)`。代码核对 `useFunds.ts` 确为数组 key + `fundsApi.xxx().then(res => res.data)`，描述一致 ✅ |
| S-2 | plan-03 admin 入口对齐 `AdminLayoutWithSidebar` + `DashboardHeader` | ✅ 已落地 | plan-03 §3.3（line 92-108）代码示例：`import { DashboardHeader } from '@/components/dashboard'` + `import { AdminLayoutWithSidebar } from '@/components/layouts/AdminLayout'`，结构与 `top10-holder-init/page.tsx`（代码核对一致）完全对齐 ✅ |
| S-3 | plan-04 DashboardLayout 补 `Users` import 说明 | ✅ 已落地 | plan-04 §3.10（line 191-196）明确"在文件顶部 lucide-react import 中追加 Users（现有 import 为 { Settings, ScatterChart, LineChart, BarChart3, LandmarkIcon }，未含 Users，不补会导致编译错误）"，并区分主侧边栏 JSX `<Users />` 与 AdminSidebar 组件引用。代码核对 DashboardLayout.tsx line 5 现有 import 确不含 Users ✅ |
| S-4 | plan-02 明确 `ApiResponse[T]` 包裹 + `to_camel` | ✅ 已落地 | plan-02 §3.6（line 164-167）"4 个用户侧 API 统一返回 ApiResponse[T] 包裹结构（{ success: true, data: T }），与 funds.py 一致""字段命名：Pydantic response model 使用 alias_generator=to_camel + populate_by_name=True（参照 funds.py）"。代码核对 `funds.py` line 13 `from pydantic.alias_generators import to_camel`、各 model `ConfigDict(alias_generator=to_camel, populate_by_name=True)`，描述一致 ✅ |
| S-5 | plan-02 明确 `report_period` Date→String 转换 | ✅ 已落地 | plan-02 §3 `_get_report_periods`（line 44-46）"top10_float_holders.report_period 在表中为 Date 类型，DISTINCT 结果为 date 对象，须经 .isoformat() 序列化为 YYYY-MM-DD 字符串后再放入返回值...API 入参 report_period 校验为日期字符串（YYYY-MM-DD），内部按需转换为 date 用于 DB 查询"。代码核对 model `top10_float_holder.py` line 16 `report_period = Column(Date)` 确为 Date ✅ |

**小结：recheck2 声称修复的 7 项全部真实落地，无虚报。** 但 recheck2 的核实停留在"路径文字"和"E2E 文字"层面，未触及 HTTP 方法集合与 query 命名约定，导致下面两个新 blocker 漏检。

## 六、本轮新发现问题（recheck2 遗漏）

### 🔴 Blocker

| 编号 | 位置 | 问题 | 修补建议 |
| --- | --- | --- | --- |
| B-3 | plan-03 §3.1 `updateShareholderGroup` | **`AdminApiClient` 没有 `put` 方法，前端编译失败。** 代码核对 `web/src/lib/api.ts`：`AdminApiClient`（line 437-532）仅定义 `get/post/patch/delete`（line 514/519/524/529），**无 `put`**；`put` 只在父类 `ApiClient`（line 128）上，但子类未继承使用。plan-03 §3.1 写 `adminApiClient.put('/admin/shareholder-groups/${id}', data)` 会触发 TS2339 "Property 'put' does not exist on type AdminApiClient"。现有所有 admin 更新操作（users 的 role/status/字段）都用 `adminApiClient.patch`（line 592/594/596），项目实际约定是 PATCH。**与 B-3 联动的架构冲突**：架构 §7.3 规定 `PUT /api/admin/shareholder-groups/{id}`，而项目代码约定（admin/users.py 全用 `@router.patch`）是 PATCH。两套约定打架。**直接影响 AC-07（编辑匹配规则）**：plan-03 整个文件无法通过 `npm run build`。 | 二选一：(A) 改 plan-03 §3.1 为 `adminApiClient.patch(...)`，并同步改 plan-01 §3.4 后端为 `@router.patch`，在 README 变更记录标注"对齐项目 admin PATCH 约定，偏离架构 §7.3 的 PUT 表述"——**推荐 A**，与项目现有约定一致；(B) 保持 PUT，给 `AdminApiClient` 增加 `put` 方法（偏离项目约定，需额外改 api.ts）。无论哪种，plan-01 §3.4 和 plan-03 §3.1 的 HTTP 方法必须前后端一致。 |
| B-4 | plan-04 §3.1 `getHoldings` 的 query 命名 | **`pageSize` query 参数与后端 `page_size` 不匹配，分页失效。** plan-04 §3.1 line 67 `query.set('pageSize', ...)` 用 camelCase；而项目现有约定（`funds.py` line 164/203/282 后端 Query 全是 `page_size`；`fundsApi` line 397 前端转 `page_size` 传）是 snake_case。FastAPI 的 `Query(None)` 参数直接读取 query string key，不走 Pydantic `to_camel` alias（alias 只作用于 response model）。后端若按 plan-02 定义 `page_size: int = Query(20)`，前端传 `pageSize` 会匹配不上，后端永远用默认 20，前端翻页参数静默丢失。`to_camel` 仅对 response body 生效是常见误区。**直接影响 AC-02/AC-05 的持仓列表分页**。 | plan-04 §3.1 `getHoldings` 将 `pageSize` 改为 `page_size`（与 fundsApi 一致），保持 `group_ids/report_period/change_direction/industry/page` 已是 snake_case。同步在 plan-02 §3.6 明确"query 参数沿用 snake_case（与 funds.py 一致），to_camel alias 仅作用于 response model"，避免实现者误以为 query 也走 camelCase。 |

> 说明：B-3、B-4 都是 recheck2 未覆盖的代码层维度。B-3 是"HTTP 方法集合"维度（recheck2 只看了路径 prefix，没看客户端支持哪些方法）；B-4 是"query 命名约定"维度（recheck2 看了 response 包裹 ApiResponse[T]，没看 query 参数是否也走 alias）。

### 🟡 建议项（新发现）

| 编号 | 位置 | 问题 | 修补建议 |
| --- | --- | --- | --- |
| N-1 | plan-01 §3.4 / plan-02 §3.6 | **新路由文件内 `APIRouter(prefix=...)` 未明确。** 代码核对 `server/src/api/admin/__init__.py` 所有子路由（init/tasks/users/sector_classifications 等）均在**文件内**自带 `APIRouter(prefix="/xxx")`，admin/__init__.py 注册时不加前缀。同理 `v1/__init__.py` 下各业务路由也文件内自带 prefix（funds 用 `prefix="/funds"`）。plan-01 §3.4 只说"新建路由文件 + 在 admin/__init__.py 注册 `router.include_router(...)`"，plan-02 §3.6 同理，**两处都未明确新文件内必须 `APIRouter(prefix="/shareholder-groups")` / `APIRouter(prefix="/shareholder-analysis")`**。这是 B-1 修复成立的前提：若文件内漏写 prefix，前端 `/admin/shareholder-groups` 会 404。实现者大概率照约定写，但 plan 应明示。 | plan-01 §3.4 补一句"新建 `shareholder_groups.py` 内 `router = APIRouter(prefix='/shareholder-groups', tags=[...])`（参照 users.py）"；plan-02 §3.6 同理补 `prefix='/shareholder-analysis'`（参照 funds.py）。 |
| N-2 | plan-02 §3 | **Numeric/Decimal 字段 JSON 序列化未提及。** `top10_float_holders` 的 `hold_amount`/`hold_float_ratio` 都是 `Numeric(20,2)`/`Numeric(10,4)`（model line 19-21），SUM 聚合后是 Decimal。plan-02 已补 `report_period` Date→String（S-5），但未提 Decimal→float。参照对象 `funds.py` 用 `_serialize_value`（line 107-115）显式把 Decimal 转 float、date 转 isoformat。若 plan-02 用 Pydantic `model_dump()`，Pydantic v2 默认会把 Decimal 转为字符串（非 float），前端拿到 `"123.45"` 字符串会破坏数值比较和图表渲染。 | plan-02 §3 补充：参照 funds.py 的 `_serialize_value`，聚合结果中的 Decimal 字段（total_hold_amount/total_hold_float_ratio/avg_hold_float_ratio）序列化时显式 `float()` 转换，或在 Pydantic model 上配置 `model_config = ConfigDict(json_encoders={Decimal: float})`。 |
| N-3 | plan-01 §3.4 / plan-03 §3.1 | **preview 的 `exclude_group_id` query 命名。** plan-03 §3.1 line 52 `params.append('exclude_group_id', ...)` 用 snake_case（与 B-4 的 pageSize 错误方向相反，这里反而正确）。但 plan-01 §3.4 描述 `exclude_group_id: Optional[int]` 也 snake_case，前后端一致 ✅。仅作为核对记录，无问题。本条标注为"已核对正确"，提醒实现者保持 snake_case。 | 无需修改。记录备查。 |
| N-4 | plan-02 §3.6 / 架构 §7.3 | **admin API 路径在架构文档与代码挂载链不一致（非 plan 错误，记录备查）。** 架构 §7.3 写 `/api/admin/shareholder-groups`，但代码实际挂载链为 `main.py:113 prefix="/api"` × `router.py include_router(admin_router, prefix="/v1/admin")` → `/api/v1/admin/*`。plan-03 §3.1 前端 `/admin/shareholder-groups` × baseURL `/api/v1` = `/api/v1/admin/shareholder-groups` ✅（plan 正确）。架构文档的 `/api/admin/...` 是笔误或历史路径，但不影响 plan 执行。 | 无需改 plan。建议在 plan-03 §7 交接上下文或 README 变更记录备注一句"架构 §7.3 的 `/api/admin/` 实际为 `/api/v1/admin/`（前端 baseURL 已含 /v1），plan 按代码实际挂载链对齐"，避免实现者纠结。 |

### 其他观察（非问题）

- **架构 §6.1 `OverviewResponse` 无 `has_data` 字段，但 §8.2/§3.2 提到 `{ has_data: false }`**：plan-02/04 统一采用"空 report_periods 判断"为自洽路径，处理得当（recheck2 已记录，本轮复核确认无误）。

## 七、维度检查结果（仅列与 recheck2 结论不同的项）

| 维度 | recheck2 结论 | 本轮结论 | 变化原因 |
| --- | --- | --- | --- |
| 9 数据模型与契约 | ⚠️ 有建议（S-4、S-5） | ⚠️ 有 blocker（B-4）+ 建议（N-2） | 代码级核对发现 query 命名约定（pageSize vs page_size）会直接导致分页失效；Decimal 序列化未约定 |
| 13 功能拆分质量 | ✅ 良好 | ⚠️ 有 blocker（B-3） | 代码级核对发现 AdminApiClient 无 put 方法，plan-03 前端编译失败 |
| 14 可执行性 | ⚠️ 有 blocker（B-1）+ 建议 | ⚠️ B-1 已修 + 新 blocker（B-3、B-4）+ 建议（N-1） | B-1 修复确认；新增 HTTP 方法与 query 命名两个可执行性阻塞 |
| 16 复用声明链路验证 | ✅ 良好 | ✅ 良好（补记录） | 复用声明均核实正确：top10_float_holders 字段、sectors/sector_stocks 关联链（stock_code↔symbol、sector_code↔code、type='industry'）、BaseRepository 方法签名（update(id, obj_in: Dict)）、require_admin 位于 src.api.deps —— 全部与代码一致 |

其余维度（1/2/3/4/5/6/7/8/10/11/12/15）结论与 recheck2 一致，维持"继承良好"。其中维度 4（AC 防漂移）的 B-2 已确认修复落地，E2E-TDD 验收项实质内容齐全。

## 八、合理扩展

| 位置 | 扩展内容 | 为什么合理 |
| --- | --- | --- |
| plan-04 §5 | E2E-TDD 验收项（7 核心场景 + red/green + spec/evidence 路径） | 落实 recheck2 B-2 要求，覆盖 AC-01~05/08/09/11，符合通过标准 |
| plan-03 §5 | 管理端 E2E-TDD（新增→编辑关键词+预览→删除二次确认） | 管理端关键路径的端到端覆盖 |
| plan-04 §5 | US 覆盖矩阵 + 降级回归验收（L1~L3） | 首检已认定合理，本轮复核维持 |

## 九、建议补丁计划（按优先级）

1. **【blocker，必须】** plan-03 §3.1：`updateShareholderGroup` 改为 `adminApiClient.patch(...)`；plan-01 §3.4 后端对应改为 `@router.patch`，并在 README 变更记录标注"对齐项目 admin PATCH 约定，偏离架构 §7.3 的 PUT 表述"（B-3）。
2. **【blocker，必须】** plan-04 §3.1：`getHoldings` 的 `pageSize` 改为 `page_size`（与 fundsApi 一致）；plan-02 §3.6 补一句"query 参数沿用 snake_case，to_camel alias 仅作用于 response model"（B-4）。
3. **【建议】** plan-01 §3.4 / plan-02 §3.6：明确新路由文件内 `APIRouter(prefix="/shareholder-groups")` / `APIRouter(prefix="/shareholder-analysis")`（N-1）。
4. **【建议】** plan-02 §3：补充 Numeric/Decimal 字段 JSON 序列化（参照 funds.py `_serialize_value` 转 float）（N-2）。
5. **【建议】** plan-03 §7 或 README 变更记录：备注架构 §7.3 `/api/admin/` 实际为 `/api/v1/admin/`（N-4）。

修补 B-3、B-4 后建议再次复审。两个 blocker 均为"代码层契约不一致"，修复成本极低（改方法名/参数名 + 一句话说明），但**必须在 plan-03/04 进入实现前修正**，否则前者编译失败、后者分页静默失效。
