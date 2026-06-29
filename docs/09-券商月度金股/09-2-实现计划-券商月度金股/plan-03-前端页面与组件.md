---
feat_id: "plan-03"
title: "前端页面与组件（API 客户端 + 双视图页面 + 月份/视图控件 + 菜单注册 + 管理员同步面板）"
dimension: frontend
phase: 2
status: done
depends_on: ["plan-01", "plan-02"]
---

# plan-03: 前端页面与组件

## 功能概要

- **目标**: 交付券商金股的全部用户可见前端：① 用户侧分析页——新增 `brokerRecommendApi`（4 端点客户端）、`BrokerRecommendPage` 主页面（视图切换 + 月份选择 + 搜索 + 内容区）、`BrokerStockRanking`（股票维度表格，预加载展开）、`BrokerGroupList`（券商维度分组列表，懒加载展开）、`MonthSelector` / `ViewSwitcher` 控件、侧边栏菜单注册；② 管理员同步面板——`BrokerRecommendSyncPanel`（月份选择 + 触发同步 + 进度展示 + 同步记录表）+ 数据管理页路由 + AdminSidebar 菜单。完成后用户可完整走通券商金股的全部交互，管理员可在数据管理页触发并查看同步。
- **完成后可观察结果**: 用户登录后在侧边栏"基金扎堆分析"后看到"券商每月荐股"菜单项；点击进入页面默认展示股票维度·最新已同步月份的卖方共识排行榜（按推荐家数降序，每行折叠态显示前 3 家券商 + "+X 家"省略），点击行展开看全部券商及理由（预加载，无 loading）；切换到券商维度按券商分组列出本月推荐（折叠态显示推荐股票数），展开某券商懒加载其本月推荐明细（带骨架，失败可重试）；月份选择器切换历史月份（清空搜索词 + 回第 1 页 + 保持视图）；搜索为服务端全量重查 + 回第 1 页；从未同步展示整页空状态。管理员在数据管理区"券商金股同步"入口选择月份触发同步，看到进度与同步记录。所有视图切换/月份切换/搜索统一清搜索词 + 回第 1 页（AC-14）。
- **依赖**: plan-01（admin 同步 API + broker_recommend 数据）、plan-02（4 个用户侧 API 端点契约）
- **关联验收标准**: [AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-07, AC-09, AC-11, AC-12, AC-13, AC-14]
- **涉及架构模块**: 前端 BrokerRecommendPage / BrokerStockRanking / BrokerGroupList / MonthSelector / ViewSwitcher / BrokerRecommendSyncPanel（架构 §4.2 / §6.1 / §6.4 / §7.2 / §9 Phase C）
- **前置条件**: plan-01/plan-02 API 契约就绪；`web/src/lib/api.ts` / `web/src/app/dashboard/fund-crowd-analysis/page.tsx` / `web/src/components/fund-crowd-analysis/` / `web/src/components/dashboard/DashboardLayout.tsx` / `web/src/components/admin/StockTop10SyncPanel.tsx` / `web/src/components/admin/AdminSidebar.tsx` 现有范式可参照；Playwright 基础设施就绪（`web/playwright.config.ts`，testDir `./tests/e2e`，mock 模式）
- **不在范围**: 后端同步与查询（plan-01/plan-02）、跨路由下钻/sessionStorage 恢复（ADR-5 明确不做，双视图在同页切换）

## 文件清单

### 前端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| modify | `web/src/lib/api.ts` | 新增 `brokerRecommendApi` namespace + camelCase TS interface（对齐 §7.2），范式参照 fundCrowdAnalysisApi（line 994 区域） |
| create | `web/src/hooks/useBrokerRecommend.ts` | 新建 SWR hooks（getMonths/getStockRanking/getBrokerList/getBrokerDetail），范式参照 useFundCrowdAnalysis.ts |
| create | `web/src/app/dashboard/broker-recommend-analysis/page.tsx` | 新建页面路由（'use client' + DashboardLayout 包裹），范式参照 fund-crowd-analysis/page.tsx |
| create | `web/src/components/broker-recommend-analysis/BrokerRecommendPage.tsx` | 主页面（视图切换 + 月份选择 + 搜索 + 内容区 + 状态管理） |
| create | `web/src/components/broker-recommend-analysis/BrokerStockRanking.tsx` | 股票维度表格（家数列、前3家券商、行展开预加载全部券商理由） |
| create | `web/src/components/broker-recommend-analysis/BrokerGroupList.tsx` | 券商维度分组列表（折叠分组、懒加载展开明细带骨架/失败重试） |
| create | `web/src/components/broker-recommend-analysis/MonthSelector.tsx` | 月份选择器（YYYY-MM 显示，仅已同步月份，默认最新） |
| create | `web/src/components/broker-recommend-analysis/ViewSwitcher.tsx` | 视图切换控件（股票/券商单选） |
| modify | `web/src/components/dashboard/DashboardLayout.tsx` | baseSidebarItems 在"基金扎堆分析"项（line 42-46）后追加"券商每月荐股"项 |
| create | `web/src/components/admin/BrokerRecommendSyncPanel.tsx` | 管理员券商金股同步面板（月份选择 + 触发同步 + 进度 + 同步记录表），范式照搬 StockTop10SyncPanel.tsx |
| create | `web/src/app/dashboard/admin/broker-recommend-init/page.tsx` | 数据管理子页路由（AdminLayoutWithSidebar + BrokerRecommendSyncPanel），范式照搬 top10-holder-init/page.tsx |
| modify | `web/src/components/admin/AdminSidebar.tsx` | navItems 在"股票持仓同步"项（line 62-67）后追加"券商金股同步"项 |
| modify | `web/src/lib/api.ts` | adminApi 新增 `initBrokerRecommend(month)`（POST，最终路径 `/api/v1/admin/init/broker-recommend`），范式参照 adminApi.initStockTop10Holders |
| create | `web/tests/e2e/broker-recommend-analysis.spec.ts` | 新建 E2E spec（red→green），范式参照 fund-crowd-analysis.spec.ts |
| create | `web/tests/e2e/helpers/mock-broker-recommend-api.ts` | 新建 mock helpers，范式参照 mock-fund-crowd-api.ts |
| create | `docs/e2e/09-e2e-用例-券商月度金股.md` | 新建 E2E 用例文档，范式参照 08-e2e-用例-基金扎堆股票分析.md |

## 实现规格

### 前端部分

#### 1. API 客户端与类型（`web/src/lib/api.ts`）

范式**完全照搬** `fundCrowdAnalysisApi`（已读确认，api.ts line 994-1115）。

- TS interface（对齐架构 §7.2，**camelCase**，与后端 Pydantic to_camel 输出一致）：
  - `BrokerStockRankingItem { symbol: string; name: string | null; industries: string[]; brokerCount: number; brokers: { broker: string; reasons: string[] }[] }`
  - `BrokerGroupItem { broker: string; stockCount: number }`
  - `BrokerDetailItem { symbol: string; name: string | null; reasons: string[] }`
  - `BrokerRankingResponse { hasData: boolean; month: string | null; total: number; page: number; pageSize: number; items: BrokerStockRankingItem[] | BrokerGroupItem[] }`
  - `BrokerMonthsResponse { hasData: boolean; months: string[] }`
  - `BrokerDetailResponse { items: BrokerDetailItem[] }`
  - `BrokerView = 'stock' | 'broker'`（视图枚举，架构 §7.6）
- `export const brokerRecommendApi = { ... }`：
  - `.getMonths()` → `apiClient.get<{ success: boolean; data: BrokerMonthsResponse }>('/broker-recommend-analysis/months')`
  - `.getStockRanking(params: { month?: string; search?: string; page?: number; pageSize?: number })` → `apiClient.get<{ success: boolean; data: BrokerRankingResponse }>('/broker-recommend-analysis/stock-ranking', { month: params.month, search: params.search || undefined, page: params.page || 1, page_size: params.pageSize || 20 })`（**query snake_case**：`page_size` 而非 `pageSize`）
  - `.getBrokerList(params)` → `apiClient.get<{ success: boolean; data: BrokerRankingResponse }>('/broker-recommend-analysis/broker-list', { month, search, page, page_size })`
  - `.getBrokerDetail(params: { month: string; broker: string })` → `apiClient.get<{ success: boolean; data: BrokerDetailResponse }>('/broker-recommend-analysis/broker-detail', { month, broker })`

#### 2. SWR Hooks（`web/src/hooks/useBrokerRecommend.ts`）

范式照搬 `useFundCrowdAnalysis.ts`（已读确认）：
- `import useSWR from 'swr'`；`import { brokerRecommendApi, type ... } from '@/lib/api'`
- SWR 数组 key + fetcher 内调 brokerRecommendApi；**解包层级**：fetcher `.then(res => res.data)` 解一层（res 是 AxiosResponse，.data 取 body `{success, data}`），组件再读 `.data.data`（与 useFundCrowdAnalysis 注释一致，line 11-13）
- `SWR_OPTIONS = { revalidateOnFocus: false, revalidateOnReconnect: true, dedupingInterval: 30000 }`
- hooks：`useBrokerMonths()` / `useBrokerStockRanking({month, search, page, pageSize})` / `useBrokerList(...)` / `useBrokerDetail({month, broker})`（broker-detail 按需请求 key，懒加载时才触发）

#### 3. 页面路由（`web/src/app/dashboard/broker-recommend-analysis/page.tsx`）

范式照搬 `fund-crowd-analysis/page.tsx`（已读确认）：
```tsx
'use client'
import { DashboardLayout } from '@/components/dashboard'
import BrokerRecommendPage from '@/components/broker-recommend-analysis/BrokerRecommendPage'

export default function BrokerRecommendAnalysisRoute() {
  return (
    <DashboardLayout>
      <div className="px-4 py-6 md:px-6 md:py-8">
        <div className="max-w-7xl mx-auto">
          <BrokerRecommendPage />
        </div>
      </div>
    </DashboardLayout>
  )
}
```
**关键**：'use client' 必须加（参照 fund-crowd-analysis/page.tsx 注释，否则 build error 污染全局 E2E）。

#### 4. 主页面与状态管理（`BrokerRecommendPage.tsx`）

范式参照 `FundCrowdAnalysisPage.tsx`（React state + SWR hooks，DEFAULT_PAGE_SIZE=20，SEARCH_DEBOUNCE_MS=300）。

- 状态（ADR-5，React state 维护，**无 sessionStorage**）：
  - `view: BrokerView`（默认 'stock'）
  - `month: string | undefined`（默认 undefined → 首次让后端取 latest；months 加载后设为最新）
  - `search: string` + `debouncedSearch: string`（debounce 300ms）
  - `page: number`（默认 1）
- **AC-14 统一重置逻辑**（关键）：
  - 切视图（ViewSwitcher）：`setView(newView); setSearch(''); setDebouncedSearch(''); setPage(1)`
  - 切月份（MonthSelector）：`setMonth(newMonth); setSearch(''); setDebouncedSearch(''); setPage(1)`（保持 view）
  - 搜索：`setPage(1)`（search 通过 debounce 触发重查）
- 数据流：
  - 进入页 `useBrokerMonths()` → 若 hasData=false → 整页空状态"暂无券商金股数据，请联系管理员同步"（AC-09）
  - view='stock' → `useBrokerStockRanking({month, search: debouncedSearch, page, pageSize: 20})`；hasData=true & items=[] & total=0 → "所选月份暂无数据"
  - view='broker' → `useBrokerList(...)`
- 布局：标题 + ViewSwitcher + MonthSelector + 搜索框 + 内容区（根据 view 渲染 BrokerStockRanking / BrokerGroupList）

#### 5. 股票维度表格（`BrokerStockRanking.tsx`，AC-02/03/06/07/11）

- 表格列：排名 / 代码 / 名称（null→"—"）/ 行业（数组逗号拼接，空→"—"）/ 推荐家数 / 推荐券商（前 3 家 + "+X 家"省略）/ 展开控件
- **AC-03 预加载展开**：点击展开控件切换展开态，渲染 `item.brokers`（已是列表数据，无二次请求）；每个 broker 显示名称 + reasons（多条分行展示，不丢弃）
- 排序：后端已按 broker_count DESC, symbol ASC 返回（AC-07），前端不重排
- 搜索无结果（total=0）→ "未找到匹配结果，请调整搜索词"
- 分页：total > 20 显示分页器，≤20 隐藏（AC-06）；page 切换调 setPage

#### 6. 券商维度分组列表（`BrokerGroupList.tsx`，AC-04/12/13）

- 每家券商一个可折叠分组，折叠态：券商名 + "本月推荐 N 只"
- **AC-13 懒加载**：展开某分组时触发 `useBrokerDetail({month, broker})`；展开中显示骨架"展开加载中"；加载完成渲染明细（symbol/name/reasons）；失败显示"加载失败，请重试"可重新展开；明细空显示"暂无推荐理由"
- reasons 空数组 → "—"；多条分行展示
- 搜索（total=0）→ "未找到匹配结果，请调整搜索词"

#### 7. 控件（MonthSelector / ViewSwitcher）

- `MonthSelector`：YYYY-MM 显示，options 来自 `useBrokerMonths().months`（仅已同步月份，降序）；默认最新（首项）；切换 `onMonthChange`
- `ViewSwitcher`：股票/券商单选（aria-pressed 状态，参照 CrowdScopeSelector 范式 line 71-78）；切换 `onViewChange`

#### 8. 菜单注册（`web/src/components/dashboard/DashboardLayout.tsx`，AC-01）

在 `baseSidebarItems` 数组"基金扎堆分析"项（line 42-46）后追加：
```tsx
{
  title: '券商每月荐股',
  href: '/dashboard/broker-recommend-analysis',
  icon: <Star className="w-5 h-5" />,
},
```
import：`Star`（从 'lucide-react'，已在文件 import 风格内；现有 import line 5 可追加 `Star`）。

#### 9. adminApi 同步触发方法（`web/src/lib/api.ts`）

在 `adminApi`（line 540 区域）的 `initStockTop10Holders`（line 604-605）后追加：
```ts
initBrokerRecommend: (month: string) =>
  adminApiClient.post<{task_id: string}>('/admin/init/broker-recommend', { month }),
```
**关键**：`adminApiClient.post` 第二参为 body 对象（参照 initStockTop10Holders 的 `{ period }`），month 为 YYYYMM 字符串。`adminApiClient` 继承 `ApiClient`，baseURL = `API_BASE_WITH_PREFIX`（已含 `/api/v1`，api.ts:440），故 endpoint 写 `/admin/init/broker-recommend`，最终路径 `/api/v1/admin/init/broker-recommend`，与后端 router.py:29 `prefix="/v1/admin"` + init 子路由 `prefix="/init"` 挂载一致（无双前缀）。

#### 10. 管理员同步面板（`web/src/components/admin/BrokerRecommendSyncPanel.tsx`）

**范式照搬** `web/src/components/admin/StockTop10SyncPanel.tsx`（已完整读确认），核心改动：

- **SWR key**：`const RECORDS_SWR_KEY = '/api/v1/admin/tasks?task_types=sync_broker_recommend&page=1&page_size=20';`（task_types 改 `sync_broker_recommend`，后端 tasks.py 的 task_types 是通用逗号分隔过滤无白名单）
- **月份选择器**：替换 `getRecentQuarters`（季度末 YYYYMMDD）为 `getRecentMonths(count=12): string[]`——生成最近 12 个月的 YYYYMM（含当月，降序）；`formatMonth(yyyymm)` 显示为 YYYY-MM（如 "202606" → "2026-06"）
- **触发同步**：`adminApi.initBrokerRecommend(selectedMonth)`（替换 initStockTop10Holders）；返回 `response.data?.task_id`
- **同步记录表 params 字段**：`record.params?.month`（替换 `period`），显示用 `formatMonth`
- **复用**：`useTaskStatus` hook（轮询任务状态）、`StatusBadge`（状态徽章）、Toast 通知、进度条——**逐字复制** StockTop10SyncPanel 实现
- import：`adminApi`（line 14，新增 initBrokerRecommend）、`useTaskStatus` + `TaskData`、`useAuth` + `useRequireAdmin`、`fetcher`、lucide 图标（替换 `Users` 为 `Star` 或 `Landmark`）
- **useTaskStatus 回调**：onComplete（成功 Toast + 刷新记录）、onFailed（失败 Toast + 显示错误）、onProgress（更新 progress/total）；轮询 `pollInterval: 2000`
- **UI 结构**（与 StockTop10SyncPanel 一致）：Toast 区 + "券商金股同步"卡片区（月份 select + 同步按钮 + 进度条 + 错误）+ 同步记录表（时间/月份/状态/详情列）

#### 11. 数据管理子页路由（`web/src/app/dashboard/admin/broker-recommend-init/page.tsx`）

**范式照搬** `web/src/app/dashboard/admin/top10-holder-init/page.tsx`（已读确认结构）：
```tsx
'use client';
import React from 'react';
import { DashboardHeader } from '@/components/dashboard';
import AdminSidebar from '@/components/admin/AdminSidebar';
import { AdminLayoutWithSidebar } from '@/components/layouts/AdminLayout';
import BrokerRecommendSyncPanel from '@/components/admin/BrokerRecommendSyncPanel';

export default function BrokerRecommendInitPage() {
  return (
    <AdminLayoutWithSidebar sidebar={<AdminSidebar />}>
      <DashboardHeader title="券商金股同步" subtitle="券商月度金股数据采集和同步" />
      <BrokerRecommendSyncPanel />
    </AdminLayoutWithSidebar>
  );
}
```

#### 12. AdminSidebar 菜单注册（`web/src/components/admin/AdminSidebar.tsx`）

在 `navItems` 数组"股票持仓同步"项（line 62-67）后追加（范式照搬该数组项结构）：
```tsx
{
  id: 'broker-recommend-init',
  label: '券商金股同步',
  icon: Star,  // 或 Landmark，从 lucide-react import
  href: '/dashboard/admin/broker-recommend-init',
  description: '券商月度金股数据采集和同步',
},
```
import：`Star`（从 'lucide-react'，参照文件顶部 import 风格）。

### 前后端契约四件套校验结论（架构 §7.3 + 锚点 api.ts / fund_crowd_analysis.py）

- **路径拼接**：`apiClient.baseURL = API_BASE_WITH_PREFIX = ${API_BASE_URL}/api/v1`（api.ts line 9，已含 /v1）。endpoint 写 `/broker-recommend-analysis/stock-ranking`（不带 /v1），最终路径 `/api/v1/broker-recommend-analysis/stock-ranking`，与后端 v1 主路由 `/v1` + router prefix `/broker-recommend-analysis` 一致。✅ 无双前缀。
- **HTTP 方法存在性**：4 端点均 GET；`apiClient.get` 继承自 ApiClient（line 33）携带 Authorization 头（getAuthHeaders）。✅ 与 fundCrowdAnalysisApi 一致。
- **query 参数命名**：后端 FastAPI Query 定义 snake_case（`page_size`），前端 `.getStockRanking` 写 query 转 `page_size`（**不写 pageSize**）——FastAPI Query 不经 alias 转换，前端传错后端收不到会静默失效。✅ 锚点 fundCrowdAnalysisApi（api.ts line 1079）已验证此约定。
- **响应字段命名**：后端 Pydantic `to_camel` + 路由 `_dict_to_camel` 输出 camelCase（`brokerCount`/`stockCount`/`hasData`/`pageSize`）；前端 TS interface（实现规格 #1）全部 camelCase 对齐。✅ 不混用 snake/camel。
- **序列化**：date 字段（month）后端 isoformat() 输出 "YYYY-MM-01" 字符串，前端 month 状态为 string；本功能无数值精度风险（counts 为 int）。✅
- **响应包裹与解包层级**：后端 `{success:true, data:{...}}`；SWR fetcher `.then(res => res.data)` 解一层得 body，组件读 `.data.data` 取业务对象（与 useFundCrowdAnalysis 一致，line 11-13 注释）。E2E mock 必须 `{success:true, data}` 包裹。✅

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | api.ts 新增 brokerRecommendApi + TS interface（camelCase 对齐 §7.2，query snake_case） | frontend | done | 范式参照 fundCrowdAnalysisApi |
| 2 | 新建 useBrokerRecommend SWR hooks（4 个，fetcher 解包层级与 useFundCrowdAnalysis 一致） | frontend | done | SWR 数组 key + OPTIONS |
| 3 | 新建 MonthSelector + ViewSwitcher 控件 | frontend | done | YYYY-MM 显示 / aria-pressed 单选 |
| 4 | 新建 BrokerStockRanking（预加载展开 + 前3家省略 + 分页≤20隐藏） | frontend | done | AC-02/03/06/07/11 |
| 5 | 新建 BrokerGroupList（懒加载展开骨架/失败重试） | frontend | done | AC-04/12/13 |
| 6 | 新建 BrokerRecommendPage（状态管理 + AC-14 统一重置） | frontend | done | view/month/search/page state |
| 7 | 新建 page.tsx 路由（'use client' + DashboardLayout） | frontend | done | 范式参照 fund-crowd-analysis/page.tsx |
| 8 | DashboardLayout baseSidebarItems 追加菜单项（Star 图标） | frontend | done | 在"基金扎堆分析"项后 |
| 9 | adminApi 新增 initBrokerRecommend(month) + 新建 BrokerRecommendSyncPanel（范式照搬 StockTop10SyncPanel） | frontend | done | 月份 YYYYMM + SWR key task_types=sync_broker_recommend |
| 10 | 新建 broker-recommend-init 子页路由 + AdminSidebar 追加菜单项 | frontend | done | 范式照搬 top10-holder-init/page.tsx + navItems |
| 11 | 新建 E2E spec + mock helpers + 用例文档（red 用例） | frontend | done | npx playwright test，范式参照 fund-crowd-analysis.spec.ts |

## 验收标准

### 入口与菜单（AC-01）

- [ ] AC-01 侧边栏"基金扎堆分析"后出现"券商每月荐股"菜单项；点击进入 `/dashboard/broker-recommend-analysis` 页面

### 股票维度（AC-02/03/06/07/11）

- [ ] AC-02 默认展示股票维度·最新月排行榜，按推荐家数降序；折叠态前 3 家券商 + "+X 家"省略
- [ ] AC-03 行展开显示全部券商及理由（预加载无 loading），同券商多 reason 不丢弃；再次点击收起
- [ ] AC-06 分页 page 切换；total > 20 显示分页器，≤20 隐藏
- [ ] AC-07 家数相同按代码升序（后端排序，前端不重排）
- [ ] AC-11 股票搜索命中仅保留匹配 + 回第 1 页；无匹配"未找到匹配结果"；清空恢复

### 券商维度（AC-04/12/13）

- [ ] AC-04 切券商维度按券商分组 + 推荐股票数；展开显示明细；切换不改变月份
- [ ] AC-12 券商搜索命中仅保留匹配 + 回第 1 页；无匹配提示；清空恢复
- [ ] AC-13 展开懒加载骨架 → 明细；失败"加载失败，请重试"可重试；明细空"暂无推荐理由"

### 月份、空状态与重置（AC-05/09/14）

- [ ] AC-05 月份选择器仅已同步月份（YYYY-MM）；切换清搜索词+回第1页+保持视图
- [ ] AC-09 从未同步整页空状态；所选月无数据"所选月份暂无数据"
- [ ] AC-14 切视图/切月份清搜索词 + 回第 1 页 + 重载

### 管理员同步面板（AC-08 前端触发入口）

- [ ] AC-08-ui-1 AdminSidebar 出现"券商金股同步"菜单项，点击进入 `/dashboard/admin/broker-recommend-init` 页面
- [ ] AC-08-ui-2 月份选择器显示最近 12 个月 YYYY-MM；选择月份点击"同步"按钮调用 `adminApi.initBrokerRecommend(month)` 创建任务
- [ ] AC-08-ui-3 同步中显示进度条（progress/total）+ "同步中…"；完成 Toast"券商金股同步完成"；失败 Toast 显示错误
- [ ] AC-08-ui-4 同步记录表用 SWR key `task_types=sync_broker_recommend` 展示该类型任务（时间/月份/状态/详情），刷新按钮可手动刷新
- [ ] AC-08-ui-5 已有同类 running 任务时后端返回并发保护提示，前端展示

### E2E-TDD（用户可观察功能强制项）

- [ ] E2E 用例文档：`docs/e2e/09-e2e-用例-券商月度金股.md`（范式参照 `08-e2e-用例-基金扎堆股票分析.md`），覆盖 AC-01/02/03/04/05/06/07/09/11/12/13/14 场景
- [ ] E2E spec：`web/tests/e2e/broker-recommend-analysis.spec.ts` + `web/tests/e2e/helpers/mock-broker-recommend-api.ts`（范式参照 fund-crowd-analysis.spec.ts + mock-fund-crowd-api.ts；mock 用 `{success:true, data}` 包裹，URL.pathname 精确匹配，test data factory camelCase）
- [ ] **red 证据**：实现前运行 `npx playwright test broker-recommend-analysis` 看到预期失败（页面/菜单/组件不存在）
- [ ] **green 证据**：实现后运行 `npx playwright test broker-recommend-analysis` 全部通过；证据写入 `docs/e2e/evidence/plan-03-e2e-green-{date}.md`

### 全流程验收（US 覆盖矩阵，架构 §2.3）

> 架构文档 §2.3 定义的成功标准引用 US-01~US-04。本功能为依赖 DAG 叶子节点（最终集成功能），承接全流程验收。

| US 编号 | 用户故事简述 | 承接功能 | 验证方式 |
|---|---|---|---|
| US-01 | 看到"被最多券商推荐"的股票排行榜，发现卖方共识股 | plan-03（BrokerStockRanking） | E2E TC：进入页面默认股票维度排行榜按家数降序 |
| US-02 | 切券商分组视图，查看某券商本月推荐股票及理由 | plan-03（BrokerGroupList 懒加载） | E2E TC：切券商维度 + 展开某券商明细 |
| US-03 | 切换历史月份，回顾卖方共识变化 | plan-03（MonthSelector） | E2E TC：月份切换重载 + 回第1页 + 保持视图 |
| US-04 | 管理员手动触发月度同步并查看进度 | plan-01（admin 同步 API）+ plan-03（BrokerRecommendSyncPanel） | plan-01 §5 执行验证（触发任务→completed→查表）+ plan-03 AC-08-ui（前端面板触发与进度展示） |
- [ ] US-01~US-03 全部可在本页面正常走通（最终集成回归）；US-04 由 plan-01（后端同步）+ plan-03（前端 BrokerRecommendSyncPanel 触发与进度）联合承接

### 降级回归验收（架构 §8.2）

- [ ] (架构 §8.2) L1 部分股票无行业 → industries 空 → "—"（不影响家数）
- [ ] (架构 §8.2) L2 部分股票无 name → name null → "—"
- [ ] (架构 §8.2) L3 券商明细为空 → "暂无推荐理由"
- [ ] (架构 §8.2) L4 所选月无数据 → "所选月份暂无数据"
- [ ] (架构 §8.2) L5 无金股数据 → 整页空状态（不被新菜单/组件遮挡）
- [ ] (架构 §8.2) 降级提示在新增页面布局中正确显示

### 构建与类型

- [ ] `cd web && npx tsc --noEmit` 通过（类型无错）
- [ ] `cd web && npm run build` 通过
- [ ] `cd web && npm run lint` 通过

## 验证命令

```bash
# 1. 类型与构建
cd web
npx tsc --noEmit
npm run build
npm run lint

# 2. E2E-TDD（用户可观察功能主质量门，mock 模式，dev 端口 3100）
# red 阶段（实现前，预期失败）
npx playwright test broker-recommend-analysis
# green 阶段（实现后，全部通过）
npx playwright test broker-recommend-analysis

# 3. 跑全部 E2E 不回归
npx playwright test
```

前提：Playwright 基础设施已就绪（`web/playwright.config.ts`，testDir `./tests/e2e`，baseURL 3100，mock 模式不依赖真实后端）。E2E 用 mock helpers 拦截 4 个 API（`page.route` + URL.pathname 精确匹配），无需 plan-01/plan-02 后端运行。

## 交接上下文

- **架构章节**: §4.2（前端 BrokerRecommendPage/BrokerStockRanking/BrokerGroupList + 复用 fundCrowdAnalysisApi/DashboardLayout 范式）、§6.1（双视图加载前端渲染）、§6.2（懒加载展开）、§6.4（页面与菜单加载）、§7.2（Schema）、§7.3（API 边界）、§8.2（降级）、§2.3（US）、§9 Phase C
- **相关代码**:
  - 范式源（用户侧分析页）：`web/src/lib/api.ts`（fundCrowdAnalysisApi line 994）、`web/src/hooks/useFundCrowdAnalysis.ts`（SWR 解包层级）、`web/src/app/dashboard/fund-crowd-analysis/page.tsx`（'use client' + DashboardLayout）、`web/src/components/fund-crowd-analysis/FundCrowdAnalysisPage.tsx`（状态管理）、`web/src/components/dashboard/DashboardLayout.tsx`（baseSidebarItems line 16-47）、`web/src/components/dashboard/index.ts`（DashboardLayout 默认导出）、`web/tests/e2e/fund-crowd-analysis.spec.ts`（E2E fixture + mock 模式）、`web/tests/e2e/helpers/mock-fund-crowd-api.ts`（mock helper 模式）
  - 范式源（管理员同步面板）：`web/src/components/admin/StockTop10SyncPanel.tsx`（同步面板完整范式：RECORDS_SWR_KEY + useTaskStatus + Toast + 进度条 + 同步记录表 + StatusBadge）、`web/src/app/dashboard/admin/top10-holder-init/page.tsx`（admin 子页路由）、`web/src/components/admin/AdminSidebar.tsx`（navItems line 32-82）、`web/src/lib/api.ts`（adminApi.initStockTop10Holders line 604-605）
  - 本功能产出：见文件清单
- **契约 / 数据对象**: §7.2 camelCase Schema；API 边界 §7.3（4 端点）
- **下游消费方**: 无（本功能为依赖 DAG 叶子节点，最终集成）

## 风险与边界

- **执行顺序**: 按 Task 列表顺序执行。Task 9（E2E）的 red 阶段应在 Task 1-8 实现前先写 spec 看到失败（E2E-TDD），再实现到 green；或先建 mock helpers + spec 骨架。AC-14 状态重置逻辑集中在 Task 6（BrokerRecommendPage），是跨控件协同关键。
- **验证失败排查方向**:
  - E2E 401 重定向 /login → mock helpers 未注册或 URL 不匹配（参照 fund-crowd-analysis.spec.ts 注释，需 mock 认证 + API）
  - 搜索不生效 → 检查 query 是否 `page_size`（snake_case）+ debounce 是否触发
  - 切视图/月份后搜索词未清 → 检查 AC-14 重置逻辑（setSearch + setDebouncedSearch + setPage(1)）
  - broker-detail 不触发懒加载 → 检查 SWR key 是否含 broker（展开时才挂 key）
  - 菜单不显示 → 检查 DashboardLayout baseSidebarItems 是否在"基金扎堆分析"项后追加 + Star import
- **允许修改的额外文件**: 无
- **暂停条件**: 无（Playwright 基础设施已就绪）
- **E2E 不适用说明**: 不适用——本功能为用户可观察功能，已声明完整 E2E（spec + mock helpers + 用例文档 + red/green 证据路径）。
- **测试基础设施现状**: Playwright 已就绪（`web/playwright.config.ts`，testDir `./tests/e2e`，dev 端口 3100，mock 模式不依赖真实后端）。现有 8 个 spec（含 fund-crowd-analysis.spec.ts）证明模式成熟。E2E 用 `npx playwright test` 运行（package.json 无独立 e2e script，直接 npx）。

### 前端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| 从未同步（hasData=false） | 整页空状态"暂无券商金股数据，请联系管理员同步" | todo |
| 所选月无数据（items=[] total=0） | "所选月份暂无数据" | todo |
| 搜索无结果 | "未找到匹配结果，请调整搜索词" | todo |
| 股票无 name/行业 | "—"（不影响家数/排序） | todo |
| 同券商多 reason | reasons 数组分行展示不丢弃 | todo |
| 单股百家推荐（极端） | 后端 LIMIT 100 兜底，展开提示 | todo |
| 券商明细懒加载失败 | "加载失败，请重试"可重新展开 | todo |
| 券商明细为空 | "暂无推荐理由" | todo |
| 切视图/月份/搜索状态错乱 | AC-14 统一清搜索词+回第1页 | todo |
| 分页 total≤20 | 隐藏分页器（仅显示"共 N"） | todo |
| 降级提示被遮挡（架构 §8.2） | 新页面布局中降级提示正确显示 | todo |

### 后端边界场景

无（本功能无后端代码；后端边界由 plan-01/plan-02 覆盖）。
