---
feat_id: "plan-04"
title: "股东分析面板页面"
dimension: frontend
phase: 3
status: done
depends_on: ["plan-02"]
---

# plan-04: 股东分析面板页面

## 1. 功能概要

- **目标**: 实现面向用户的"股东分析面板"独立页面，包含监控组概览卡片、持仓详情区（汇总统计 + 行业分布条形图 + 变动趋势 + 股票列表分页）、报告期选择器、行业/变动方向筛选。
- **完成后可观察结果**: 用户从侧边栏进入"股东分析"页面，页面顶部展示报告期下拉（默认最新期）和所有监控组概览卡片（组名、持仓数、增持/减持/新进/退出数量）。点击"国家队"卡片后卡片高亮，下方加载持仓详情：汇总统计（持仓股票数、总持股数、平均占流通比）、行业分布水平条形图、变动趋势数字、持仓股票分页表格（含筛选栏）。切换行业筛选后股票列表联动过滤。切换报告期后全页数据刷新。数据未同步时展示空状态提示。
- **依赖**: plan-02（用户侧 overview / summary / industry-distribution / holdings API 已就绪）
- **关联验收标准**: [AC-01, AC-02, AC-03, AC-04, AC-05, AC-08, AC-09, AC-11]
- **涉及架构模块**: ShareholderAnalysisPage, GroupOverviewCards, HoldingsDetail, IndustryDistribution, HoldingsTable, ReportPeriodSelector, SWR hooks
- **前置条件**: plan-02 的用户侧 API 可正常访问，top10_float_holders 有至少一个报告期的数据
- **不在范围**: 管理端分组管理（plan-03）、数据同步

## 2. 文件清单

### 前端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| create | `web/src/hooks/useShareholderAnalysis.ts` | SWR 数据获取 hooks |
| modify | `web/src/hooks/index.ts` | 导出新 hooks |
| modify | `web/src/lib/api.ts` | 新增用户侧 API 方法 |
| create | `web/src/components/shareholder-analysis/ShareholderAnalysisPage.tsx` | 主页面组件 |
| create | `web/src/components/shareholder-analysis/GroupOverviewCards.tsx` | 监控组概览卡片 |
| create | `web/src/components/shareholder-analysis/HoldingsDetail.tsx` | 持仓详情区容器 |
| create | `web/src/components/shareholder-analysis/IndustryDistribution.tsx` | 行业分布水平条形图（ECharts） |
| create | `web/src/components/shareholder-analysis/HoldingsTable.tsx` | 持仓股票列表（分页 + 筛选） |
| create | `web/src/components/shareholder-analysis/ReportPeriodSelector.tsx` | 报告期下拉选择器 |
| create | `web/src/app/dashboard/shareholder-analysis/page.tsx` | 页面路由入口 |
| modify | `web/src/components/dashboard/DashboardLayout.tsx` | 侧边栏新增"股东分析"导航项 |

## 3. 实现规格

### 前端部分

#### 1. 用户侧 API 方法

在 `web/src/lib/api.ts` 中新增 shareholderAnalysisApi 对象：

```typescript
// apiClient.baseURL 已含 /api/v1（见 lib/api.ts 的 API_BASE_WITH_PREFIX），路径不再带 /v1，避免双前缀
export const shareholderAnalysisApi = {
  getOverview: (params?: { report_period?: string }) => {
    const query = params?.report_period ? `?report_period=${params.report_period}` : '';
    return apiClient.get(`/shareholder-analysis/overview${query}`);
  },
  getSummary: (params: { group_ids: string; report_period: string; industry?: string; change_direction?: string }) => {
    const query = new URLSearchParams({ group_ids: params.group_ids, report_period: params.report_period });
    if (params.industry) query.append('industry', params.industry);
    if (params.change_direction) query.append('change_direction', params.change_direction);
    return apiClient.get(`/shareholder-analysis/summary?${query}`);
  },
  getIndustryDistribution: (params: { group_ids: string; report_period: string; change_direction?: string }) => {
    const query = new URLSearchParams({ group_ids: params.group_ids, report_period: params.report_period });
    if (params.change_direction) query.append('change_direction', params.change_direction);
    return apiClient.get(`/shareholder-analysis/industry-distribution?${query}`);
  },
  getHoldings: (params: { group_ids: string; report_period: string; industry?: string; change_direction?: string; page?: number; pageSize?: number }) => {
    // query key 用 snake_case（后端 Query 参数约定，to_camel 不作用于 query）；前端入参 pageSize 仅作命名友好
    const query = new URLSearchParams({ group_ids: params.group_ids, report_period: params.report_period, page: String(params.page || 1), page_size: String(params.pageSize || 20) });
    if (params.industry) query.append('industry', params.industry);
    if (params.change_direction) query.append('change_direction', params.change_direction);
    return apiClient.get(`/shareholder-analysis/holdings?${query}`);
  },
};
```

#### 2. SWR Hooks

新建 `web/src/hooks/useShareholderAnalysis.ts`，**参照现有 `useFunds.ts` 模式**：SWR 使用数组 key + fetcher 内部调用 `shareholderAnalysisApi`（经 `apiClient`，baseURL 已含 `/api/v1`），**不直接使用 `lib/fetcher.ts`**（其 `API_BASE` 不含 `/api/v1`，与 `apiClient` 是两套 baseURL 体系，混用易踩前缀坑）。

**`useShareholderOverview(reportPeriod?: string)`**：
- SWR key: `['shareholderOverview', reportPeriod ?? null]`
- fetcher: `() => shareholderAnalysisApi.getOverview({ report_period: reportPeriod }).then(res => res.data)`
- 返回 `{ data, error, isLoading, mutate }`

**`useShareholderSummary(params)`**：
- 仅当 params 含 `group_ids` + `report_period` 时启用（key 为 null）
- SWR key: `['shareholderSummary', params]`
- fetcher: `() => shareholderAnalysisApi.getSummary(params).then(res => res.data)`
- 返回 `{ data, error, isLoading, mutate }`

**`useShareholderIndustryDistribution(params)`**：
- 同 summary 模式，key: `['shareholderIndustryDist', params]`
- fetcher: `() => shareholderAnalysisApi.getIndustryDistribution(params).then(res => res.data)`

**`useShareholderHoldings(params)`**：
- 同 summary 模式，支持分页（params 含 `page`/`pageSize`），key: `['shareholderHoldings', params]`
- fetcher: `() => shareholderAnalysisApi.getHoldings(params).then(res => res.data)`

> **解包层级**：fetcher 的 `.then(res => res.data)` 解一层——`res` 是 `shareholderAnalysisApi` 方法返回的 `ApiResponse` 对象，`.data` 取其 `data` 字段即整个 body `{ success, data }`。故 hook 返回的 `data` 是该 body，组件再读 `data.data` 取业务对象（与 `useFunds.ts` 读 `data?.data?.items` 一致，见 plan-02 §3.6 的 `ApiResponse[T]` 包裹契约）。

在 `web/src/hooks/index.ts` 追加导出。

#### 3. ReportPeriodSelector 组件

新建 `web/src/components/shareholder-analysis/ReportPeriodSelector.tsx`：
- 使用 shadcn Select 组件
- Props: `periods: string[]`, `value: string | null`, `onChange: (period: string) => void`
- 展示最近 4 个报告期选项
- 格式化为 YYYY-MM-DD

#### 4. GroupOverviewCards 组件

新建 `web/src/components/shareholder-analysis/GroupOverviewCards.tsx`：
- 使用 CSS Grid 或 Flex 布局展示多张卡片
- Props: `groups: GroupOverview[]`, `selectedGroupIds: number[]`, `onGroupSelect: (groupIds: number[]) => void`
- 每张卡片展示：组名、持仓股票数、增持/减持/新进/退出数量
- 卡片支持多选点击（toggle 选中/取消），选中态高亮（边框颜色变化）
- 按 stock_count 降序排列（API 已排序）
- 空状态：无分组时展示"暂无监控组"

#### 5. IndustryDistribution 组件

新建 `web/src/components/shareholder-analysis/IndustryDistribution.tsx`：
- 使用 ECharts 水平条形图
- Props: `distribution: IndustryItem[]`, `onIndustryClick?: (industry: string) => void`
- 按占比降序排列，展示前 N 个行业 + "其他/未分类"
- 点击某个行业条目触发 onIndustryClick（联动筛选栏）
- 空数据时展示"暂无行业分布数据"

#### 6. HoldingsTable 组件

新建 `web/src/components/shareholder-analysis/HoldingsTable.tsx`：
- 使用 shadcn Table 组件
- 列：股票代码 | 股票名称 | 持股数量 | 占流通比 | 较上期 | 行业
- 顶部筛选栏：行业下拉（全部 + 各行业） | 变动方向下拉（全部/增持/减持/新进/退出）
- 分页：上一页/下一页 + 当前页码/总页数
- Props:
  - `holdings: HoldingItem[]`, `total: number`, `page: number`, `pageSize: number`
  - `industries: string[]`（从 distribution 中提取的行业列表）
  - `filters: { industry?: string, changeDirection?: string }`
  - `onFiltersChange`, `onPageChange`
- 变动方向渲染：↑增持（绿色）| ↓减持（红色）| ★新进（蓝色）| ✕退出（灰色）| —（无数据）
- 行业渲染：多个行业逗号分隔

#### 7. HoldingsDetail 组件

新建 `web/src/components/shareholder-analysis/HoldingsDetail.tsx`：
- 容器组件，整合汇总统计 + 行业分布 + 变动趋势 + 股票列表
- Props: `groupIds: number[]`, `reportPeriod: string`, `hasPrevPeriod: boolean`
- 状态管理：
  - `industry` 筛选值
  - `changeDirection` 筛选值
  - `page` 当前页码
- 调用 3 个 hooks 获取数据（summary + industry-distribution + holdings）
- 筛选联动逻辑（架构 §6.2）：
  - 切换 industry → 重发 summary + holdings（industry-distribution 不受影响）
  - 切换 changeDirection → 重发 summary + industry-distribution + holdings
  - 翻页 → 仅重发 holdings
- 汇总统计展示：持仓股票数 | 总持股数 | 平均占比
- 变动趋势展示：↑增持 X | ↓减持 Y | ★新进 Z | ✕退出 W
  - hasPrevPeriod 为 false 时展示"上期数据不完整，变动趋势暂不可用"
- 行业分布条形图（点击联动筛选栏）
- 股票列表表格（含筛选和分页）

#### 8. ShareholderAnalysisPage 主页面组件

新建 `web/src/components/shareholder-analysis/ShareholderAnalysisPage.tsx`：
- 页面状态：
  - `reportPeriod: string | null`（当前选中报告期）
  - `selectedGroupIds: number[]`（当前选中监控组）
- 调用 `useShareholderOverview(reportPeriod)` 获取概览数据
- 页面布局：
  1. 页面标题 "股东分析" + ReportPeriodSelector
  2. GroupOverviewCards（监控组概览）
  3. HoldingsDetail（持仓详情区，仅在选中组时展示）
- 交互逻辑：
  - 首次加载 → overview API（默认最新期）→ 渲染概览卡片，详情区展示"请选择监控组"
  - 点击监控组 → 更新 selectedGroupIds → HoldingsDetail 加载
  - 切换报告期 → 清空 selectedGroupIds → 重载 overview
  - 空状态判断：overview 返回空 report_periods → 展示"暂无股东数据，请联系管理员同步数据"
- 标题区域右侧可展示"数据来源: 十大流通股东（报告期数据，仅供参考）"

#### 9. 页面路由入口

新建 `web/src/app/dashboard/shareholder-analysis/page.tsx`：
- 导入 ShareholderAnalysisPage 组件
- 渲染页面

#### 10. 更新侧边栏导航

修改 `web/src/components/dashboard/DashboardLayout.tsx`：
- **在文件顶部 lucide-react import 中追加 `Users`**（现有 import 为 `{ Settings, ScatterChart, LineChart, BarChart3, LandmarkIcon }`，未含 `Users`，不补会导致编译错误）
- 在 `baseSidebarItems` 数组中“基金分析”之后新增：
  ```
  { title: '股东分析', href: '/dashboard/shareholder-analysis', icon: <Users /> }
  ```
- 注意：主侧边栏 `baseSidebarItems` 的 icon 是 **JSX 元素** `<Users />`（与 AdminSidebar 的组件引用 `icon: Users` 写法不同）

## 4. Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | 新增用户侧 API 方法到 api.ts | frontend | done | shareholderAnalysisApi 对象，4 个方法 |
| 2 | 创建 SWR hooks | frontend | done | 4 个 hooks：overview / summary / industry-distribution / holdings |
| 3 | 注册 hooks 到 hooks/index.ts | frontend | done | 追加导出 |
| 4 | 创建 ReportPeriodSelector 组件 | frontend | done | 报告期下拉选择器 |
| 5 | 创建 GroupOverviewCards 组件 | frontend | done | 监控组概览卡片（多选） |
| 6 | 创建 IndustryDistribution 组件 | frontend | done | 行业分布水平条形图（ECharts） |
| 7 | 创建 HoldingsTable 组件 | frontend | done | 持仓股票列表 + 筛选 + 分页 |
| 8 | 创建 HoldingsDetail 容器组件 | frontend | done | 汇总 + 行业分布 + 趋势 + 列表整合 |
| 9 | 创建 ShareholderAnalysisPage 主组件 | frontend | done | 页面状态管理 + 布局 |
| 10 | 创建页面路由 page.tsx | frontend | done | /dashboard/shareholder-analysis |
| 11 | 更新 DashboardLayout 侧边栏 | frontend | done | lucide-react import 追加 `Users` + 新增"股东分析"导航项（icon 为 JSX `<Users />`） |

## 5. 验收标准

### AC-01 验收：监控组概览展示

- [x] AC-01 进入"股东分析"页面，顶部展示所有监控组概览卡片，每张卡片显示组名、持仓股票数、增持/减持/新进/退出数量
- [x] 报告期下拉默认选中最新有数据的报告期

### AC-02 验收：监控组持仓详情查询

- [x] AC-02 点击"国家队"卡片后卡片高亮，下方展示：汇总统计（持仓股票数、总持股数、平均占比）、行业分布条形图、变动趋势数字、持仓股票列表表格
- [x] 表格包含股票代码、名称、持股数量、占流通比、较上期变动方向、行业

### AC-03 验收：多监控组联合查询

- [x] AC-03 依次点击"国家队"和"外资投行"卡片，两张卡片同时高亮，持仓详情展示两个组的合并数据（股票去重）

### AC-04 验收：行业筛选

- [x] AC-04 在筛选栏选择行业"银行"，股票列表仅显示行业含"银行"的股票，汇总统计同步更新
- [x] 点击行业分布图中的"银行"条目，筛选栏联动选中"银行"

### AC-05 验收：变动方向筛选

- [x] AC-05 在筛选栏选择变动方向"增持"，股票列表仅显示增持股票
- [x] 选择"退出"，展示退出股票列表

### AC-08 验收：数据未同步空状态

- [x] AC-08 当十大流通股东数据从未同步时（overview 返回空），页面展示"暂无股东数据，请联系管理员同步数据"，不展示监控组卡片和持仓详情

### AC-09 验收：报告期切换

- [x] AC-09 切换报告期后，概览卡片和持仓详情（如有选中组）全量刷新为新报告期数据
- [x] 切换报告期后清空已选监控组状态

### AC-11 验收：报告期数据不完整降级

- [x] AC-11 上期数据不完整时，变动趋势区域展示"上期数据不完整，变动趋势暂不可用"提示
- [x] 持仓股票列表中"较上期"列显示为"—"

### 全流程验收（US 覆盖矩阵）

> 架构文档 §2.3 定义的成功标准：US-01 ~ US-07 全部可正常走通。

| US 编号 | 用户故事简述 | 承接功能 | 验证方式 |
| --- | --- | --- | --- |
| US-01 | 看到各监控组概览卡片 | plan-04 | AC-01 验收 |
| US-02 | 查看持仓汇总、行业分布和变动趋势 | plan-04 | AC-02 验收 |
| US-03 | 查看持仓股票明细列表 | plan-04 | AC-02 验收（表格部分） |
| US-04 | 按行业筛选持仓股票 | plan-04 | AC-04 验收 |
| US-05 | 后台管理监控组 | plan-03 | plan-03 §5 验收 |
| US-06 | 多组对比查看 | plan-04 | AC-03 验收 |
| US-07 | 按变动方向筛选 | plan-04 | AC-05 验收 |

- [x] US-01 ~ US-04, US-06, US-07 全部可在股东分析面板页面正常走通

### E2E-TDD 验收

> 架构 §2.3 成功标准 + dev-plan-check 通过标准：用户可观察功能须有 E2E-TDD 验收项（red 预期失败 / green 实现后通过两阶段证据）。

- [x] **red 阶段**：在 `docs/e2e/06-e2e-用例-股东分析面板.md` 编写 Playwright 用例，实现前运行预期失败，证据存 `docs/e2e/evidence/plan-04-e2e-red-{date}.md`
- [x] **green 阶段**：实现完成后运行同一用例全部通过，证据存 `docs/e2e/evidence/plan-04-e2e-green-{date}.md`

核心覆盖场景（至少）：
1. 进入"股东分析"页面 → 概览卡片渲染（AC-01）
2. 点击监控组卡片 → 持仓详情区加载（汇总 + 行业分布 + 趋势 + 列表）（AC-02）
3. 多选卡片 → 合并展示去重（AC-03）
4. 行业筛选 → 列表与汇总联动（AC-04）
5. 变动方向筛选（含退出）→ 列表过滤（AC-05）
6. 切换报告期 → 全页刷新 + 清空选中组（AC-09）
7. 空状态/降级：无股东数据空状态（AC-08）、上期数据不完整降级提示（AC-11）

### 性能验收（架构 §8.1 目标）

- [x] 概览页首次加载 < 3s（浏览器 DevTools Network 面板确认）
- [x] 选中监控组后持仓详情加载 < 3s（3 个并行 API）

### 降级回归验收（架构 §8.2）

- [x] L3（无股东数据）："暂无股东数据"空状态在页面中正确展示，无布局错乱
- [x] L2（无上期数据）："变动趋势暂不可用"提示正确展示，较上期列显示"—"
- [x] L1（部分股票无行业）：行业列显示"—"，行业分布中归入"未分类"

### 构建验收

- [x] `npm run build` 通过，无类型错误
- [x] `npm run lint` 通过

## 6. 验证命令

```bash
# 前端构建
cd web && npm run build

# Lint 检查
cd web && npm run lint

# 启动开发服务器
cd web && npm run dev

# 手动验证流程：
# 1. 登录后从侧边栏进入"股东分析"页面
# 2. 验证概览卡片展示
# 3. 点击监控组卡片 → 验证持仓详情加载
# 4. 多选卡片 → 验证合并展示
# 5. 切换行业筛选 → 验证联动
# 6. 切换变动方向筛选 → 验证联动
# 7. 切换报告期 → 验证全页刷新
# 8. 验证行业分布条形图点击联动筛选栏
# 9. 翻页验证分页功能
```

## 7. 交接上下文

- **架构章节**: §3.1 流程 A（用户查看监控组持仓分析）、§3.2 关键分支、§6.1 监控组概览加载、§6.2 持仓详情查询、§6.3 报告期切换
- **相关代码**:
  - `web/src/lib/api.ts` — ApiClient 模式
  - `web/src/lib/fetcher.ts` — SWR fetcher
  - `web/src/hooks/` — 已有 hooks 模式参考
  - `web/src/components/dashboard/DashboardLayout.tsx` — 侧边栏导航
  - `web/src/components/funds/` — 基金分析页面参考（同类面板页）
  - plan-02 的 API 端点 — 数据来源
- **契约 / 数据对象**（前端消费，camelCase；与 plan-02 §7 / 架构 §7.2 一致）:
  - `OverviewResponse`: { reportPeriods, currentPeriod, hasPrevPeriod, groups: GroupOverview[] }
  - `SummaryResponse`: { summary, trend, hasPrevPeriod }
  - `IndustryDistributionResponse`: { distribution: IndustryItem[] }
  - `HoldingsResponse`: { holdings: HoldingItem[], total }
  - `GroupOverview`: { groupId, groupName, description, stockCount, increaseCount, decreaseCount, newCount, exitCount }
  - `HoldingItem`: { symbol, stockName, totalHoldAmount, totalHoldFloatRatio, changeDirection, industries }
  - `IndustryItem`: { industry, stockCount, percentage }
- **下游消费方**: 无（最终用户页面）

## 8. 风险与边界

- **执行顺序**: 按 Task 列表顺序执行（API → hooks → 子组件 → 容器 → 页面 → 导航）
- **验证失败排查方向**:
  1. 页面 404 → 检查路由文件路径
  2. API 数据为空 → 检查 plan-02 是否完成、top10_float_holders 是否有数据
  3. 概览卡片无数据 → 检查 overview API 响应结构
  4. 行业分布图不渲染 → 检查 ECharts 组件是否正确挂载
  5. 筛选不生效 → 检查 hooks 参数传递和 key 变化
  6. 分页不跳转 → 检查 page state 和 holdings hook key 更新
- **允许修改的额外文件**: 无
- **暂停条件**: API 响应结构与预期不符时暂停，需与 plan-02 确认契约
- **E2E 验收**: 本功能为核心用户可观察页面，按 §5 E2E-TDD 验收项执行 red/green 两阶段验证，用例入 `docs/e2e/`，证据入 `docs/e2e/evidence/`。

### 前端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| overview API 返回空 report_periods | 全页展示"暂无股东数据"空状态 | done |
| 无监控组（groups 为空） | 概览区展示"暂无监控组"提示 | done |
| 选中的组无持仓数据 | 详情区展示"该组暂无持仓数据" | done |
| 上期数据不完整（has_prev_period=false） | 变动趋势提示"暂不可用"，较上期列显示"—" | done |
| 股票无行业数据 | 行业列显示"—"，分布图归入"未分类" | done |
| API 请求中 | 展示 loading spinner | done |
| API 请求失败 | 展示"加载失败，请重试"错误提示 | done |
| 报告期切换 | 清空选中组 + 重载 overview + 若有选中组则重载详情 | done |
| 行业分布图点击联动 | 点击行业条目 → 筛选栏联动选中对应行业 → 重发 summary + holdings | done |
| 变动方向筛选含"退出" | holdings 展示退出股票（上期有本期无），持股数据为上期值 | done |

### 风险备注

- 3 个并行 API 请求（summary + industry-distribution + holdings）需确保 SWR key 正确变化触发重新请求，否则筛选切换时可能出现数据不一致。
- ECharts 行业分布图的点击事件需正确传递 industry 参数到父组件筛选逻辑。
- 变动方向筛选含"退出"时，需要重发所有 3 个 API（因退出数据影响汇总和行业分布），需确保 hooks 参数正确传递。
- 大量持仓数据分页时需确保翻页流畅，避免不必要的数据重载。
