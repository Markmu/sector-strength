---
feat_id: "plan-04"
title: "前端基础设施"
dimension: frontend
phase: 3
status: done
depends_on: ["plan-03"]
---

# plan-04: 前端基础设施

## 功能概要

- **目标**: 搭建 ETF 监控页面的前端基础设施——API 客户端对象、TypeScript 类型定义、SWR 数据获取 hooks、路由壳页面、侧边栏导航入口。完成后页面可空载渲染（无业务组件，但路由可达、API 客户端可调通）。
- **完成后可观察结果**: 侧边栏出现"ETF 监控"导航项，点击跳转到 /dashboard/etf-monitor 页面（空壳，渲染 DashboardLayout 包裹）；etfMonitorApi 对象的 4 个方法可调用 plan-03 的端点；4 个 SWR hooks（useEtfIndexRankings/useEtfIndexDetail/useEtfTrend/useEtfLatestDate）能正确解包 {success,data} 响应；TypeScript 类型检查与构建通过。
- **依赖**: plan-03（查询 API 端点契约）
- **关联验收标准**: 无直接 AC（基础设施功能，为 plan-05 提供 API/hooks/类型支撑；AC 交互验证在 plan-05）
- **涉及架构模块**: etfMonitorApi、etfMonitorTypes、SWR hooks、路由壳、导航菜单
- **前置条件**: plan-03 已完成（端点可用）；前端依赖已安装
- **不在范围**: 业务组件（plan-05）、表格/图表渲染（plan-05）

## 文件清单

### 前端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| modify | `web/src/lib/api.ts` | 新增 etfMonitorApi 对象（4 方法） |
| create | `web/src/types/etfMonitorTypes.ts` | TypeScript 类型定义（camelCase 业务对象） |
| create | `web/src/hooks/useEtfMonitor.ts` | SWR hooks（4 个） |
| create | `web/src/app/dashboard/etf-monitor/page.tsx` | 路由壳（'use client' + DashboardLayout） |
| modify | `web/src/components/dashboard/DashboardLayout.tsx` | baseSidebarItems 新增 ETF 监控入口 |

## 实现规格

### 前端部分

#### 1. etfMonitorApi（lib/api.ts）

仿 `sectorFundFlowApi`（src/lib/api.ts:1086）范式。**关键：endpoint 不带 /api/v1**（apiClient.baseURL 已含 /api/v1，带则双前缀 404）。

```ts
export const etfMonitorApi = {
  // 指数排行（AC-01/02/03/05/13）
  getIndexRankings: (params: {
    category?: EtfCategory  // 'broad' | 'industry'
    tradeDate?: string | null
    sortBy?: EtfSortBy      // 'netInflow' | 'shareChange' | 'share'（camelCase 值）
    order?: 'desc' | 'asc'
    page?: number
    pageSize?: number
  }) => apiClient.get<{ success: boolean; data: EtfIndexRankingsData }>(
    '/etf-monitor/index-rankings',
    {
      category: params.category,
      trade_date: params.tradeDate || undefined,  // query 名 snake_case
      sort_by: params.sortBy,                      // query 值 camelCase（架构 §7.6 特例）
      order: params.order,
      page: params.page || 1,
      page_size: params.pageSize || 20,
    }
  ),
  // 指数明细（AC-04）
  getIndexDetail: (params: { indexName: string; category?: EtfCategory; tradeDate?: string | null }) =>
    apiClient.get<{ success: boolean; data: EtfIndexDetailData }>('/etf-monitor/index-detail', {
      index_name: params.indexName, category: params.category, trade_date: params.tradeDate || undefined,
    }),
  // 历史趋势（AC-06/07/08/09）
  getTrend: (params: {
    targetType: 'index' | 'etf'; targetCode: string; metric: 'share' | 'netInflow'; days: 7 | 30 | 90; endDate?: string | null
  }) => apiClient.get<{ success: boolean; data: EtfTrendData }>('/etf-monitor/trend', {
    target_type: params.targetType, target_code: params.targetCode, metric: params.metric,
    days: params.days, end_date: params.endDate || undefined,
  }),
  // 最新交易日
  getLatestDate: (params: { category?: EtfCategory }) =>
    apiClient.get<{ success: boolean; data: EtfLatestDateData }>('/etf-monitor/latest-date', { category: params.category }),
}
```

**契约四件套校验**：
- 路径拼接：apiClient.baseURL（API_BASE_WITH_PREFIX = `${NEXT_PUBLIC_API_URL}/api/v1`，api.ts:9）+ endpoint `/etf-monitor/index-rankings` = `/api/v1/etf-monitor/index-rankings` ✓（与 plan-03 后端一致）
- HTTP 方法：apiClient.get（api.ts:33 ApiClient 类方法，带 getAuthHeaders 鉴权）✓
- query 命名：传 snake_case（category/trade_date/sort_by/target_type/target_code），与后端 Query 参数一致 ✓；sort_by/metric 值用 camelCase（netInflow/shareChange/share）与后端取值一致 ✓
- 响应字段：泛型 `{success, data}`，data 内 camelCase，与 etfMonitorTypes.ts 匹配 ✓

#### 2. etfMonitorTypes.ts（types/）

仿 `fundFlowTypes.ts`（全 camelCase）。**注意 query 参数保持 snake_case，响应字段 camelCase**（fundFlowTypes.ts:11-13 注释）。

```ts
export type EtfCategory = 'broad' | 'industry'
export type EtfSortBy = 'netInflow' | 'shareChange' | 'share'
export type EtfTrendMetric = 'share' | 'netInflow'

export interface EtfIndexRankingsData { hasData: boolean; tradeDate: string | null; items: EtfIndexRankingItem[]; total: number; page: number; pageSize: number }
export interface EtfIndexRankingItem { indexName: string; category: string; etfCount: number; totalShare: number | null; totalShareChange: number | null; totalNetInflow: number | null }
export interface EtfIndexDetailData { hasData: boolean; items: EtfDetailItem[] }
export interface EtfDetailItem { tsCode: string; name: string; unitNav: number | null; share: number | null; shareChange: number | null; netInflow: number | null; changePercent: number | null }
export interface EtfTrendData { hasData: boolean; metric: string; unit: string; series: { tradeDate: string; value: number | null }[] }
export interface EtfLatestDateData { hasData: boolean; tradeDate: string | null }
```

#### 3. useEtfMonitor.ts（hooks/）

仿 `useSectorFundFlow.ts`（src/hooks/useSectorFundFlow.ts）范式：SWR 数组 key + 内联 fetcher `etfMonitorApi.xxx(params).then(res => res.data)` 解包、`SWR_OPTIONS = { revalidateOnFocus: false, revalidateOnReconnect: true, dedupingInterval: 30000 }`、返回 `{数据, isLoading, isValidating, isError, mutate}`。**深路径导入，不改 hooks/index.ts**（与 useSectorFundFlow 一致）。导出 4 个 hook：useEtfIndexRankings / useEtfIndexDetail(params) / useEtfTrend(params) / useEtfLatestDate。注意 useEtfIndexDetail/useEtfTrend 是条件 hook（有 indexName/targetCode 才请求，传 null key 触发 SWR 不请求）。

**复用声明调用细节**：useSWR 从 'swr' 导入；apiClient 单例从 '@/lib/api' 导入（具名导出 `apiClient`，api.ts:140）；SWR_OPTIONS 常量本地定义（与 useSectorFundFlow 一致）；fetcher 内联 `etfMonitorApi.xxx(params).then(res => res.data)`（res.data 是 ApiResponse 的 data 字段即 {success,data}，再取 .data 是业务对象）。

#### 4. 路由壳 page.tsx

仿 `app/dashboard/sector-fund-flow/page.tsx`：`'use client'`（**/dashboard 路由必须，否则 build error 污染 E2E）+ import `DashboardLayout`（from '@/components/dashboard'）包裹 + 占位（本期空壳，业务组件在 plan-05 接入 EtfMonitorPage）。

```tsx
'use client'
import { DashboardLayout } from '@/components/dashboard'
// plan-05 完成后替换为 EtfMonitorPage，本期渲染占位
export default function EtfMonitorRoute() {
  return (
    <DashboardLayout>
      <div className="px-4 py-6 md:px-6 md:py-8">
        <div className="max-w-7xl mx-auto">
          <div>ETF 监控（建设中）</div>
        </div>
      </div>
    </DashboardLayout>
  )
}
```

#### 5. 导航菜单（DashboardLayout.tsx）

`baseSidebarItems`（src/components/dashboard/DashboardLayout.tsx:16-52）新增一项，置于"板块资金流"后（:27-31 之后）：

```tsx
{ title: 'ETF 监控', href: '/dashboard/etf-monitor', icon: <TrendingUp className="w-5 h-5" /> },
```

icon 从 lucide-react 取（与现有项一致，如 TrendingUp）。

**降级回归验收（架构 §8.2）**：新增导航项不影响现有布局，确认其他菜单项与 active 高亮（usePathname）仍正常。

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | 新增 etfMonitorApi（4 方法） | frontend | done | api.ts 末尾，endpoint 不带 /api/v1 |
| 2 | 新建 etfMonitorTypes.ts | frontend | done | 全 camelCase 业务对象 |
| 3 | 新建 useEtfMonitor.ts（4 SWR hooks） | frontend | done | 仿 useSectorFundFlow，深路径导入 |
| 4 | 新建 etf-monitor/page.tsx 路由壳 | frontend | done | 'use client' + DashboardLayout 占位 |
| 5 | DashboardLayout.tsx 新增导航入口 | frontend | done | baseSidebarItems 加 ETF 监控 |
| 6 | type-check + build 验证 | frontend | done | npm run build 通过 |

## 验收标准

### 前端验收

- [x] etfMonitorApi 4 方法类型正确，apiClient.get 泛型为 {success, data}
- [x] etfMonitorTypes.ts 类型与后端响应 camelCase 字段一致
- [x] 4 SWR hooks 正确解包（.then(res=>res.data)），条件 hook 传 null key 不请求
- [x] 侧边栏出现"ETF 监控"，点击跳转 /dashboard/etf-monitor 渲染占位页
- [x] 现有导航项与 active 高亮不受影响（降级回归）

### 降级回归验收（架构 §8.2）

- [x] 新增导航项不遮挡/破坏现有布局结构

### E2E / 验收

- [x] E2E-TDD：导航可点击跳转到 /dashboard/etf-monitor（`tests/e2e/etf-monitor.spec.ts` 的导航 red 用例，plan-05 完成业务后转 green；本期导航跳转可先验）
- [x] `npm run build` 通过
- [ ] `npm run lint` 通过（注：仓库存在 192 个 pre-existing lint errors，均位于测试/helper 文件与 api.ts 既有 `any` 代码，plan-04 新增代码零新增 lint 错误；详见完成摘要）

## 验证命令

```bash
cd web
npm run build        # 确认类型检查与构建通过
npm run lint
# 手动验证导航（dev 服务）
# npm run dev 后访问 /dashboard 确认侧边栏有 ETF 监控且可跳转
```

## 交接上下文

- **架构章节**: §7.2 输出视角 Schema、§7.3 API 边界（前端客户端部分）
- **相关代码**: api.ts:1086（sectorFundFlowApi 范式）、useSectorFundFlow.ts（SWR 范式）、fundFlowTypes.ts（类型范式）、DashboardLayout.tsx:16-52（导航）、app/dashboard/sector-fund-flow/page.tsx（路由壳）
- **契约/数据对象**: etfMonitorTypes.ts（EtfIndexRankingsData 等）；API 契约四件套见实现规格 #1
- **下游消费方**: plan-05（EtfMonitorPage 等组件消费 hooks/api/类型）

## 风险与边界

- **执行顺序**: 按 Task 列表顺序（api→类型→hooks→路由壳→导航→验证）
- **验证失败排查方向**: endpoint 双前缀 404 → 检查是否误带 /api/v1；类型不匹配 → 核对 camelCase 字段名；build error → 检查 'use client' 是否缺失
- **允许修改的额外文件**: 无
- **暂停条件**: apiClient.get 调用返回结构与后端不一致时暂停，核对四件套
- **E2E 不适用说明**: 本功能是基础设施，导航跳转 E2E 可先验；完整交互 E2E 在 plan-05
- **风险备注**: 严禁使用 lib/fetcher.ts（baseURL 不含 /api/v1，与 apiClient 两套体系）；严禁为 ETF 建 Redux slice（参照 sector-fund-flow 本地 state 决策）

### 前端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| apiClient baseURL 已含 /api/v1 | endpoint 不带 /api/v1，避免双前缀 | done |
| 条件 hook 无 indexName/targetCode | 传 null key，SWR 不请求 | done |
| 后端 {success,data} 包裹 | hook 内 .then(res=>res.data) 解包再取 .data | done |
| 未登录访问 | middleware 路由守卫拦截（现有机制） | done |
| 导航 icon 缺失 | lucide-react 取 TrendingUp | done |
