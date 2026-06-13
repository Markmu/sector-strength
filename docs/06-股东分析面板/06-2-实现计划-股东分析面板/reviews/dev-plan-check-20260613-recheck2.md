# 开发计划复查报告（第三次）

## 一、检查对象

- **架构文档**：`docs/06-股东分析面板/06-1-架构文档-股东分析面板.md`
- **实现计划**：`docs/06-股东分析面板/06-2-实现计划-股东分析面板/`（README + plan-01 ~ plan-04）
- **功能数**：4
- **前次报告**：
  - `dev-plan-check-20260613.md`（首检，8 项建议 S-01~S-08，结论"通过"）
  - `dev-plan-check-20260613-recheck.md`（复查，1 项新发现 plan-03 icon，结论"通过"）
- **本次检查日期**：2026-06-13

## 二、总评

- **结论**：⚠️ **有阻塞问题**（推翻前两次"通过"结论，需修补后复审）
- **阻塞问题数**：2
- **建议项数**：5（新发现）+ 0（前次 9 项已验证落地）

前两次检查以"文档对照"为主，结论为通过。本次**新增了前端客户端与后端路由挂载的代码级验证**（`web/src/lib/api.ts`、`web/src/lib/fetcher.ts`、`server/main.py` 路由注册链、现有 `funds.py` / `useFunds.ts` 模式），发现 1 处会导致前端用户侧 API **全量 404** 的路径错误（blocker），这是前两次均遗漏的真实阻塞。同时复核确认前两次的 9 项建议已全部正确落地（plan-03 §3.4 的 `icon: Users` 已修复）。

> 说明：本报告不重复首检已充分覆盖的维度结论（AC 映射、ADR 护栏、复用声明、契约对齐等均仍成立），仅聚焦**本次新发现**与**前次应用验证**。

## 三、前次建议应用验证

| 建议项 | 验证结果 | 证据 |
| --- | --- | --- |
| S-01 E2E-TDD 说明 | ✅ 文字已应用 / ⚠️ 但 §5 仍无实际 E2E 验收项 | plan-04 §8 已补 Playwright red/green 计划文字，但 §5 验收标准中**没有**指向具体 spec 的 E2E checklist——见本次 B-2 |
| S-02 _get_report_periods | ✅ 已应用 | plan-02 §3 Task 1 独立为 `_get_report_periods()`，含完整返回值 |
| S-03 SectorStock 显式 JOIN | ✅ 已应用 | plan-02 §3 `_get_industry_for_stocks` 明确 `stock_code`/`sector_code` 字符串关联 + 显式 core join |
| S-04 avg_hold_float_ratio 聚合 | ✅ 已应用 | plan-02 §3 get_summary 备注先按股票 SUM 再求 AVG |
| S-05 modify 文件定位 | ✅ 已应用 | plan-01 §2 modify 行补"追加 import 语句和注册到 __all__" |
| S-06 require_admin import | ✅ 已应用 | plan-01 §3 注明 `from src.api.deps import require_admin`（经代码验证路径正确） |
| S-07 BaseRepository 方法说明 | ✅ 已应用 | plan-01 §3 "BaseRepository 基本方法使用说明"段落已加 |
| S-08 多组去重语义 | ✅ 已应用 | plan-02 §3 `_match_holdings` 引用块说明关键词合并 + (symbol,holder_name) 去重 |
| 复查-1 AdminSidebar icon | ✅ 已修复 | plan-03 §3.4 现为 `{ id:'shareholder-groups', label:'股东分组管理', icon: Users, href:..., description:... }`，`Users` 已在 AdminSidebar imports 中 |

## 四、本次新发现问题

### 🔴 Blocker

| 编号 | 位置 | 问题 | 修补建议 |
| --- | --- | --- | --- |
| B-1 | plan-04 §3.1 `shareholderAnalysisApi` + §3.2 SWR key | **用户侧 API 路径双 `/v1` 前缀，前端全量 404。** `web/src/lib/api.ts` 中 `API_BASE_WITH_PREFIX = ${NEXT_PUBLIC_API_URL}/api/v1`，`apiClient`（line 139）默认 baseURL 即此值，`get()` 在 line 64 做 `${this.baseURL}${endpoint}` 拼接。现有 `fundsApi.getFunds()` 用 `/funds` → `/api/v1/funds` ✅。而 plan-04 写 `apiClient.get('/v1/shareholder-analysis/overview')` → 拼成 `/api/v1/v1/shareholder-analysis/overview` ❌。后端 `funds.py` 用 `APIRouter(prefix="/funds")` + v1 router `prefix="/v1"` + `main.py:113 app.include_router(api_router, prefix="/api")` → `/api/v1/funds`，故 plan-02 新路由应为 `prefix="/shareholder-analysis"`，前端必须用 `/shareholder-analysis/*`。**直接影响 AC-01~05/09/11 全部前端验收。** | 将 plan-04 §3.1 四个方法路径去掉前导 `/v1`：`/shareholder-analysis/overview`、`/summary`、`/industry-distribution`、`/holdings`；§3.2 四个 SWR key 同步去 `/v1`。 |
| B-2 | plan-04 §5（及 plan-03 §5） | **用户可观察页面缺 E2E-TDD 验收项。** 通过标准要求"用户可观察功能均有 E2E-TDD 验收项或严格的不适用说明"。plan-04 是核心用户面板，§8 虽补了"后续补 Playwright"文字（首检 S-01 据此判通过），但 §5 验收标准中**没有**指向具体 spec 的 E2E checklist，也不存在 red（预期失败）/ green（通过）两阶段证据的验收行——属于"推迟"而非"严格不适用"。本项目 `docs/e2e/` 已有 02 号需求用例先例，`test-e2e` skill 可用。 | 在 plan-04 §5 增加 E2E-TDD 验收项：目标 spec `docs/e2e/06-e2e-用例-股东分析面板.md`，证据入 `docs/e2e/evidence/`，至少覆盖概览加载→选中监控组→持仓详情渲染→筛选联动→报告期切换→空状态/降级，并要求 red/green 两阶段证据。plan-03 管理端补关键路径 E2E 或给出严格不适用理由。 |

> B-2 相对首检 S-01 为**判断升级**：首检将 E2E 缺失定为"💡 建议/接受当前写法"。本次依通过标准的硬性措辞（"均有…或严格的不适用说明"）升级为 blocker。若项目决策接受"首版手动验证"，可显式在 plan-04 §8 写明豁免理由并经确认，否则应补 E2E-TDD。

### 🟡 建议项

| 编号 | 位置 | 问题 | 修补建议 |
| --- | --- | --- | --- |
| S-1 | plan-04 §3.2 SWR hooks | **hooks 双 baseURL 轨道风险。** §3.2 描述"使用 fetcher 获取数据"且 key 为 URL 字符串，但 `lib/fetcher.ts` 的 `API_BASE` = `${NEXT_PUBLIC_API_URL}`（**不含** `/api/v1`），与 `api.ts` 的 `API_BASE_WITH_PREFIX`（**含** `/api/v1`）是两套体系。现有 `useFunds.ts` 用数组 key `['fundList', params]` + `() => fundsApi.xxx(params).then(res => res.data)`，不直接用 `lib/fetcher`。混用易在拼接时再次踩前缀坑。 | 明确 plan-04 hooks 统一采用 `useFunds.ts` 模式（数组 key + 调用 `shareholderAnalysisApi` 经 apiClient），避免直接用 `lib/fetcher.ts` 的 URL-key 路径。 |
| S-2 | plan-03 §3.3 管理页面路由入口 | **页面入口组件名/路径不精确。** 实现规格写"导入 AdminLayout 和 ShareholderGroupPanel，渲染 ShareholderGroupPanel"，但现有 `top10-holder-init/page.tsx` 实际用具名导出 `AdminLayoutWithSidebar`（来自 `@/components/layouts/AdminLayout`，复数 `layouts`）+ `DashboardHeader`（来自 `@/components/dashboard`）包裹 Panel。按当前写法实现者易用错组件名或路径。 | 将 §3.3 对齐现有模式：`import { AdminLayoutWithSidebar } from '@/components/layouts/AdminLayout'`、`import { DashboardHeader } from '@/components/dashboard'`，结构参照 `top10-holder-init/page.tsx`。 |
| S-3 | plan-04 §3.10 / Task 11（DashboardLayout 侧边栏） | **主侧边栏缺 `Users` 图标 import。** `DashboardLayout.tsx` 现有 lucide-react import 为 `{ Settings, ScatterChart, LineChart, BarChart3, LandmarkIcon }`，未导入 `Users`。plan-04 新增项用 `icon: <Users />`，但 Task 11 未提及补 import，会导致编译错误。（注：这与复查-1 发现的 AdminSidebar icon 是两处不同文件，DashboardLayout 此处仍遗漏。） | Task 11 补充：将 `Users`（或 `UserCheck`）加入 `DashboardLayout.tsx` 的 lucide-react import；并注意主侧边栏 `baseSidebarItems` 的 icon 是 JSX 元素 `<Users />`（与 AdminSidebar 的组件引用 `icon: Users` 写法不同，plan-03 该处已正确）。 |
| S-4 | plan-02 §3.6 + plan-04 hooks | **API 响应包裹契约未约定。** 现有 funds API 返回 `{ success, data: {...} }`（`ApiResponse[T]`），`useFunds` 中 `.then(res => res.data)` 解一层；而 `lib/fetcher.ts` 又有 `result.data \|\| result` 兜底解包。plan-02 §3.6 未明确 4 个用户侧 API 是否包裹 `ApiResponse[T]`，实现时易在"解一层/解两层"出错；camelCase 转换也未参照 `funds.py` 的 `to_camel` alias_generators。 | plan-02 §3.6 明确：4 个用户侧 API 统一返回 `ApiResponse[T]`（与 funds 一致），并用 `to_camel` alias_generators 处理 camelCase；plan-04 hooks 据此约定解包层级。 |
| S-5 | plan-02 §3 `_get_report_periods` / `report_period` 类型 | **Date→String 转换点未明确。** `top10_float_holders.report_period` 为 `Date` 类型（见 model），架构 §7.2 schema 要求 `report_periods: string[]`。DISTINCT 查询返回 date 对象，需 `isoformat()` 转字符串；入参 `report_period` 也需日期字符串校验。plan 未点明该转换。 | plan-02 §3 补一句：DISTINCT report_period 经 `isoformat()` 序列化为 `YYYY-MM-DD` 字符串返回；API 入参校验为日期字符串。 |

### 其他观察（非问题，记录备查）

- **AC-08 架构内部不一致**：架构 §6.1 的 `OverviewResponse` 未定义 `has_data` 字段，但 §8.2 / §3.2 关键分支提到 `overview API 返回 { has_data: false }`。plan-02/04 统一采用"空 report_periods 判断"为自洽路径，处理得当，无需改 plan；建议在 plan-04 §7 交接上下文标注该选择，避免实现者纠结 `has_data`。

## 五、本次维度复核（仅列与前次结论不同的项）

| 维度 | 前次结论 | 本次结论 | 变化原因 |
| --- | --- | --- | --- |
| 4 验收标准防漂移 | ✅ 良好（S-01 建议） | ⚠️ 有阻塞（B-2） | E2E-TDD 缺失依通过标准升级为 blocker |
| 9 数据模型与契约 | ✅ 良好 | ⚠️ 有建议（S-4、S-5） | 代码级验证发现响应包裹契约与 Date 转换未约定 |
| 14 可执行性 | ✅ 良好 | ⚠️ 有阻塞（B-1）+ 建议（S-1、S-2、S-3） | 代码级验证 apiClient/fetcher/路由挂载，发现双前缀 404 |

其余维度（1/2/3/5/6/7/8/10/11/12/13/15/16）结论与首检一致，维持"继承良好"。

## 六、建议补丁计划（按优先级）

1. **【blocker，必须】** plan-04 §3.1 + §3.2：去除用户侧 API 路径与 SWR key 中的前导 `/v1`（B-1）。
2. **【blocker，必须】** plan-04 §5：补 E2E-TDD 验收项（目标 `docs/e2e/06-e2e-用例-股东分析面板.md` + red/green 证据）；plan-03 §5 补关键路径 E2E 或严格不适用理由（B-2）。
3. **【建议】** plan-04 §3.2：hooks 统一 `useFunds.ts` 数组 key + apiClient 模式（S-1）。
4. **【建议】** plan-03 §3.3：页面入口对齐 `AdminLayoutWithSidebar` + `DashboardHeader`（S-2）。
5. **【建议】** plan-04 Task 11：补 `DashboardLayout.tsx` 的 `Users` import（S-3）。
6. **【建议】** plan-02 §3.6 + plan-04 hooks：约定 `ApiResponse[T]` 包裹与 `to_camel`（S-4）。
7. **【建议】** plan-02 §3：明确 `report_period` Date→String 转换点（S-5）。

修补 B-1、B-2 后建议再次复审本报告。建议项可在实现阶段随手修正，不阻塞开工——但 **B-1（双前缀）务必在 plan-04 进入实现前修正**，否则前端用户侧 API 将全量 404。
