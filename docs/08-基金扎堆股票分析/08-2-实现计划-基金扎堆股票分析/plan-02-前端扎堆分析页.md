---
feat_id: "plan-02"
title: "前端扎堆分析页"
dimension: frontend
phase: 2
status: done
depends_on: ["plan-01"]
---

# plan-02: 前端扎堆分析页

## 1. 功能概要

- **目标**: 实现面向用户的「基金扎堆分析」独立路由页 `/dashboard/fund-crowd-analysis`（与 04 基金分析、06 股东分析平级，架构 ADR-7）。包含：口径切换控件（仅主动 / 全部，默认仅主动）、行业分布水平条形图（以扎堆股数量占比为主指标，AC-04）、扎堆度排行榜表格（含股票代码 / 名称 / 行业 / 持有基金数 / 合计占流通比 / 环比变化列 / 反查按钮 + 搜索框 + 分页器）。数据经 SWR hooks 调用 plan-01 的两个端点 `/api/v1/fund-crowd-analysis/rankings` 和 `/api/v1/fund-crowd-analysis/industry-distribution`。承接 AC-01/02/03/04/06/07/08 的前端呈现（AC-05 下钻反查归 plan-03）。
- **完成后可观察结果**: 用户从侧边栏进入「基金扎堆分析」页面，页面顶部展示口径切换控件（默认「仅主动基金」选中）+ 报告期标识；下方行业分布区按扎堆股数量占比降序展示水平条形图（Top N 截断 + 可点击行业标签联动筛选）；再下方是扎堆度排行榜表格（含搜索框、分页器），按持有基金数降序、合计占流通比次降序排列，每行展示股票代码、名称（缺失显示「—」）、行业（多行业逗号分隔）、持有基金数、合计占流通比、环比变化列（含 +/- 数值 + 方向箭头或「新进」标识或「—」）、反查按钮。用户点击口径切换「全部基金」→ 排行榜与行业分布同步按新口径重新加载（旧数据灰显或骨架）。用户在搜索框输入股票代码前缀或名称包含（不区分大小写）→ 排行榜实时过滤，无匹配时显示「未找到匹配股票，请调整搜索词」，清空恢复完整榜单。当持仓数据未同步（`hasData=false`，AC-07）→ 整页空状态「暂无基金持仓数据，请联系管理员同步」；上期数据缺失（`hasPrevPeriod=false`，AC-06）→ 环比列统一显示「—」、当期排名正常。
- **依赖**: plan-01（提供 `/rankings` + `/industry-distribution` 两个用户侧 API 端点契约，camelCase 输出）
- **关联验收标准**: [AC-01, AC-02, AC-03, AC-04, AC-06, AC-07, AC-08]
- **涉及架构模块**: `fundCrowdAnalysisApi`（新增于 `lib/api.ts`）、`useFundCrowdRankings` / `useFundCrowdIndustryDistribution` SWR hooks（新增于 `hooks/useFundCrowdAnalysis.ts`）、`FundCrowdAnalysisPage`（主页面组件）、`CrowdRankingTable`（排行榜表格）、`CrowdIndustryDistribution`（行业分布 ECharts 条形图）、`CrowdScopeSelector`（口径切换控件）、页面路由入口（`/dashboard/fund-crowd-analysis`）、侧边栏导航新增项
- **前置条件**:
  - plan-01 已完成（端点可调用，响应字段 camelCase：`hasData/currentPeriod/prevPeriod/hasPrevPeriod/items[].stockSymbol/stockName/industries/fundCount/totalFloatRatio/fundCountChange/totalFloatRatioChange/isNew/pageSize`、`distribution[].industry/stockCount/percentage/totalFloatRatio`）
  - `web/src/lib/api.ts` 的 `apiClient`（普通用户客户端）已存在（line 32-362），`API_BASE_WITH_PREFIX = ${API_BASE_URL}/api/v1`（line 8）
  - `web/src/hooks/useShareholderAnalysis.ts` 已存在（参照 SWR + fetcher 解包范式）
  - `web/src/components/shareholder-analysis/` 已存在（参照前端组件结构范式）
  - `web/src/components/dashboard/DashboardLayout.tsx` 已存在（line 16-42 `baseSidebarItems` 数组，含 `Users` 等图标）
  - `fund_portfolio` 表至少有一个报告期数据（否则前端走 AC-07 空状态分支）
- **不在范围**:
  - 下钻反查跳转 + 返回状态恢复 + 差异提示文案（AC-05 全部归 plan-03）
  - 后端任何改动（plan-01 负责）
  - 历史多期扎堆度走势曲线（PRD §1.4 明确不做）
  - 用户报告期手动选择（PRD §1.4 明确不做；首版固定取最新期）
  - 复合加权得分排序（ADR-2 明确不做）
  - 数据导出 / 预警通知（PRD §1.4 明确不做）

## 2. 文件清单

### 前端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| modify | `web/src/lib/api.ts` | 新增 `fundCrowdAnalysisApi` 对象（含 `getRankings` / `getIndustryDistribution` 两个方法）+ 5 个 TS 类型定义（`CrowdRankingItem` / `CrowdRankingsResponse` / `CrowdIndustryItem` / `CrowdIndustryDistributionResponse` / `CrowdScope`）。紧邻现有 `shareholderAnalysisApi`（line 892+）之后，line 812 注释「apiClient.baseURL 已含 /api/v1」已说明命名规范 |
| create | `web/src/hooks/useFundCrowdAnalysis.ts` | 新建 SWR hooks 文件：`useFundCrowdRankings(params)` / `useFundCrowdIndustryDistribution(scope)`，参照 `useShareholderAnalysis.ts` 模式（数组 key + fetcher 解包一层 `.then(res => res.data)`） |
| modify | `web/src/hooks/index.ts` | 追加导出 `useFundCrowdAnalysis` 的两个 hooks |
| create | `web/src/components/fund-crowd-analysis/FundCrowdAnalysisPage.tsx` | 主页面组件：状态管理（scope/page/search）+ 加载/空状态/错误态分支 + 布局编排（口径切换 + 行业分布 + 排行榜） |
| create | `web/src/components/fund-crowd-analysis/CrowdScopeSelector.tsx` | 口径切换控件（仅主动 / 全部，单选按钮组，默认仅主动） |
| create | `web/src/components/fund-crowd-analysis/CrowdIndustryDistribution.tsx` | 行业分布水平条形图（ECharts 动态导入 + Top N 截断 + 可点击行业标签）。复用 `shareholder-analysis/IndustryDistribution.tsx` 的 ECharts + 标签双轨范式 |
| create | `web/src/components/fund-crowd-analysis/CrowdRankingTable.tsx` | 排行榜表格：搜索框 + 表头（排名/代码/名称/行业/基金数/合计占流通比/环比/操作）+ 环比列渲染（数值+箭头 / 新进 / —）+ 反查按钮 onClick 跳转（plan-03 实现具体跳转，本 plan 仅渲染按钮 + onClick 调用 `onReverseLookup` 回调 prop，由父组件 wire 到路由）+ 分页器 |
| create | `web/src/app/dashboard/fund-crowd-analysis/page.tsx` | 页面路由入口（`'use client'`，参照 `shareholder-analysis/page.tsx` 范式；page 直接 import `@/components/dashboard` 的 `DashboardLayout`，需 `'use client'` 避免全局 build 错误） |
| modify | `web/src/components/dashboard/DashboardLayout.tsx` | 侧边栏 `baseSidebarItems` 数组在「股东分析」之后追加「基金扎堆分析」导航项；line 5 的 lucide-react import 追加 `UsersRound`（或 `Layers`）图标 |
| modify | `web/tests/e2e/helpers/mock-fund-crowd-api.ts` | 新建 mock helper 文件：`createTestCrowdRankings` / `createTestCrowdRankingsEmpty` / `createTestCrowdIndustryDistribution` / `mockCrowdRankings` / `mockCrowdRankingsEmpty` / `mockCrowdIndustryDistribution` 等 helper（参照 `mock-shareholder-analysis-api.ts` 命名风格） |
| create | `web/tests/e2e/fund-crowd-analysis.spec.ts` | 新建 Playwright spec：7+ 个场景覆盖 AC-01/02/03/04/06/07/08 前端语义（参照 `shareholder-analysis.spec.ts` 的 `authedPage` fixture + mock 安装范式） |
| create | `docs/e2e/08-e2e-用例-基金扎堆股票分析.md` | E2E 用例文档（参照 `06-e2e-用例-股东分析面板.md` 风格），列出场景步骤、断言、red/green 证据路径 |

## 3. 实现规格

### 前端部分

#### 1. `fundCrowdAnalysisApi` 对象（新增于 `lib/api.ts`）

**位置**：紧邻现有 `shareholderAnalysisApi`（line 892+）之后，文件末尾前。

**复用声明**：
- `apiClient`：`web/src/lib/api.ts:32-362` 导出的 `ApiClient` 实例（普通用户客户端，`baseURL = API_BASE_WITH_PREFIX = ${API_BASE_URL}/api/v1`，line 8）
- `apiClient.get<T>(endpoint, params?)`：line 32-362 内的方法，自动拼 endpoint + query params，返回 `Promise<AxiosResponse<T>>`；组件消费时 `res.data` 取 body
- TS 类型范式：参照 `shareholderAnalysisApi` 的 `getOverview/getSummary`（line 892+）和 `fundsApi.reverseLookup`（line 415-432）的 query 参数 snake_case 风格

**实现要点**：

```typescript
// ===================== 基金扎堆分析（08）=====================

export type CrowdScope = 'active' | 'all'

export interface CrowdRankingItem {
  stockSymbol: string
  stockName: string | null
  industries: string[]
  fundCount: number
  totalFloatRatio: number | null
  fundCountChange: number | null
  totalFloatRatioChange: number | null
  isNew: boolean | null
}

export interface CrowdRankingsResponse {
  hasData: boolean
  currentPeriod: string | null
  prevPeriod: string | null
  hasPrevPeriod: boolean
  items: CrowdRankingItem[]
  total: number
  page: number
  pageSize: number
}

export interface CrowdIndustryItem {
  industry: string
  stockCount: number
  percentage: number
  totalFloatRatio: number
}

export interface CrowdIndustryDistributionResponse {
  hasData: boolean
  currentPeriod: string | null
  distribution: CrowdIndustryItem[]
}

// apiClient.baseURL 已含 /api/v1（见上方 API_BASE_WITH_PREFIX），路径不再带 /v1，避免双前缀
export const fundCrowdAnalysisApi = {
  // 扎堆度排行榜（AC-01/02/03/06/07/08）
  getRankings: (params: {
    scope: CrowdScope
    search?: string
    page?: number
    pageSize?: number
  }) =>
    apiClient.get<{
      success: boolean
      data: CrowdRankingsResponse
    }>('/fund-crowd-analysis/rankings', {
      scope: params.scope,
      search: params.search || undefined,
      page: params.page || 1,
      // query 参数 snake_case（FastAPI Query 不经 alias 转换，参照 fundsApi.reverseLookup line 427）
      page_size: params.pageSize || 20,
    }),

  // 行业分布（AC-04）
  getIndustryDistribution: (params: { scope: CrowdScope }) =>
    apiClient.get<{
      success: boolean
      data: CrowdIndustryDistributionResponse
    }>('/fund-crowd-analysis/industry-distribution', {
      scope: params.scope,
    }),
}
```

**前后端契约校验（四件套）**：

- **路径拼接**：前端 endpoint `/fund-crowd-analysis/rankings` × `apiClient.baseURL` `${API_BASE_URL}/api/v1`（line 8）= 实际请求 URL `${API_BASE_URL}/api/v1/fund-crowd-analysis/rankings`，与后端 v1_router 在 `/v1` + 子 router 在 `/fund-crowd-analysis`（plan-01 §3 #6）拼出的 `/api/v1/fund-crowd-analysis/rankings` 完全一致，**无重复前缀**
- **HTTP 方法**：`apiClient.get` → GET；后端 `@router.get` → GET；一致
- **query 参数命名**：前端传 `scope` / `search` / `page` / `page_size`（snake_case）；后端 `Query(scope: str)` + `Query(search: Optional[str])` + `Query(page: int)` + `Query(page_size: int)`（snake_case）；**注意 `pageSize` 入参 → 写 query 时必须转 `page_size`**（参照 plan-01 §3 #4 的契约校验，与 `fundsApi.reverseLookup` line 427 一致）—— query 参数不经 Pydantic alias 转换
- **响应字段命名**：后端响应 `data.hasData/currentPeriod/prevPeriod/hasPrevPeriod/items[].stockSymbol/stockName/industries/fundCount/totalFloatRatio/fundCountChange/totalFloatRatioChange/isNew/pageSize`（camelCase，由 plan-01 `_dict_to_camel` 转换）；前端类型定义用这些 camelCase 名，**完全对齐**

**响应解包层级**：`apiClient.get` 返回 `AxiosResponse<T>`，fetcher 内 `.then(res => res.data)` 解一层拿到 body `{ success, data: CrowdRankingsResponse }`；hook 返回的 `data` 是该 body，组件再读 `data.data` 取业务对象（与 `useShareholderOverview` 在 `useShareholderAnalysis.ts:67-70` 的解包一致，与 `useFundList` 在 `useFunds.ts:25` 的 `.then(res => res.data as ...)` 一致）。

#### 2. SWR Hooks（新建 `hooks/useFundCrowdAnalysis.ts`）

**复用声明**：
- `useSWR` + 数组 key + fetcher 解包范式：参照 `useShareholderAnalysis.ts:13-80`（`useShareholderOverview`）、`useFunds.ts:19-46`（`useFundList`）
- SWR 配置 `SWR_OPTIONS`：`useShareholderAnalysis.ts:22-26`（`revalidateOnFocus: false, dedupingInterval: 30000`）
- **不直接使用 `lib/fetcher.ts`**（其 `API_BASE` 不含 `/api/v1`，与 `apiClient` 是两套 baseURL 体系，参照 `useShareholderAnalysis.ts:4-7` 注释的混用前缀坑）

**实现要点**：

```typescript
/**
 * 基金扎堆分析 SWR Hooks（plan-02）
 *
 * 参照 useShareholderAnalysis.ts 模式：
 * - SWR 使用数组 key + fetcher 内部调用 fundCrowdAnalysisApi（经 apiClient，baseURL 已含 /api/v1）
 * - 不直接使用 lib/fetcher.ts（其 API_BASE 不含 /api/v1，与 apiClient 是两套 baseURL 体系）
 *
 * 解包层级：fetcher 的 `.then(res => res.data)` 解一层 —— res 是 fundCrowdAnalysisApi 方法
 * 返回的 AxiosResponse 对象，.data 取其 body { success, data }。
 * 故 hook 返回的 data 是该 body，组件再读 data.data 取业务对象。
 */
import useSWR from 'swr'
import {
  fundCrowdAnalysisApi,
  type CrowdRankingsResponse,
  type CrowdIndustryDistributionResponse,
  type CrowdScope,
} from '@/lib/api'

const SWR_OPTIONS = {
  revalidateOnFocus: false,
  revalidateOnReconnect: true,
  dedupingInterval: 30000,
} as const

export interface UseFundCrowdRankingsParams {
  scope: CrowdScope
  search?: string
  page?: number
  pageSize?: number
}

/**
 * 扎堆度排行榜（含环比 + 搜索 + 分页）
 *
 * 始终启用（scope 默认 'active'）—— 即使 hasData=false 也返回 hasData 标志供组件判断空状态
 */
export function useFundCrowdRankings(params: UseFundCrowdRankingsParams) {
  const { data, error, isLoading, mutate } = useSWR<{
    success: boolean
    data: CrowdRankingsResponse
  }>(
    ['fundCrowdRankings', params],
    () =>
      fundCrowdAnalysisApi
        .getRankings(params)
        .then((res) => res.data as unknown as {
          success: boolean
          data: CrowdRankingsResponse
        }),
    SWR_OPTIONS
  )

  return {
    rankings: data?.data ?? null,
    isLoading,
    isError: error,
    mutate,
  }
}

/**
 * 行业分布（与排行榜联动，scope 变化时同步重发）
 */
export function useFundCrowdIndustryDistribution(scope: CrowdScope) {
  const { data, error, isLoading, mutate } = useSWR<{
    success: boolean
    data: CrowdIndustryDistributionResponse
  }>(
    ['fundCrowdIndustryDistribution', scope],
    () =>
      fundCrowdAnalysisApi
        .getIndustryDistribution({ scope })
        .then((res) => res.data as unknown as {
          success: boolean
          data: CrowdIndustryDistributionResponse
        }),
    SWR_OPTIONS
  )

  return {
    distribution: data?.data?.distribution ?? [],
    currentPeriod: data?.data?.currentPeriod ?? null,
    hasData: data?.data?.hasData ?? false,
    isLoading,
    isError: error,
    mutate,
  }
}
```

在 `web/src/hooks/index.ts` 追加：

```typescript
export { useFundCrowdRankings, useFundCrowdIndustryDistribution } from './useFundCrowdAnalysis'
export type { UseFundCrowdRankingsParams } from './useFundCrowdAnalysis'
```

#### 3. `CrowdScopeSelector` 组件（口径切换）

**复用声明**：参照 `shareholder-analysis/ReportPeriodSelector.tsx`（单选下拉）的 props 风格，但本组件是**单选按钮组**（而非下拉），更贴合 PRD §3.1 线框图的 `[● 仅主动基金   ○ 全部基金]` 设计。

**实现要点**：

```tsx
'use client'

import React from 'react'
import { cn } from '@/lib/utils'
import type { CrowdScope } from '@/lib/api'

export interface CrowdScopeSelectorProps {
  value: CrowdScope                  // 'active' | 'all'
  onChange: (scope: CrowdScope) => void
  disabled?: boolean
}

const OPTIONS: Array<{ value: CrowdScope; label: string; hint: string }> = [
  { value: 'active', label: '仅主动基金', hint: '剔除被动指数型/增强指数型' },
  { value: 'all', label: '全部基金', hint: '含场内 ETF 与被动指数' },
]

export default function CrowdScopeSelector({ value, onChange, disabled }: CrowdScopeSelectorProps) {
  return (
    <div className="inline-flex items-center gap-1 p-1 bg-secondary/50 rounded-lg" data-testid="crowd-scope-selector">
      {OPTIONS.map((opt) => (
        <button
          key={opt.value}
          type="button"
          disabled={disabled}
          data-testid={`crowd-scope-${opt.value}`}
          aria-pressed={value === opt.value}
          title={opt.hint}
          onClick={() => onChange(opt.value)}
          className={cn(
            'px-3 py-1.5 text-sm rounded-md transition-colors',
            value === opt.value
              ? 'bg-card text-foreground shadow-sm font-medium'
              : 'text-muted-foreground hover:text-foreground',
            disabled && 'opacity-50 cursor-not-allowed'
          )}
        >
          {opt.label}
        </button>
      ))}
    </div>
  )
}
```

#### 4. `CrowdIndustryDistribution` 组件（行业分布 ECharts 条形图）

**复用声明**：
- ECharts 动态导入范式：`shareholder-analysis/IndustryDistribution.tsx:22-26`（`dynamic(() => import('echarts-for-react').then(mod => mod.default), { ssr: false })`）
- ECharts 水平条形图 option 范式：`IndustryDistribution.tsx:54-100`（`yAxis: { type: 'category' }` + `series: [{ type: 'bar', label: { show: true, position: 'right' } }]`）
- **双轨渲染范式**（ECharts canvas + 可点击 DOM 标签）：`IndustryDistribution.tsx:121-156`（canvas 旁渲染 `<button data-testid="industry-bar-{industry}">` 兼容 spec 点击断言）
- 空状态范式：`IndustryDistribution.tsx:103-110`（`<BarChart3Icon />` + "暂无行业分布数据"）

**Props 与渲染要点**：

```tsx
'use client'

import React, { useMemo } from 'react'
import dynamic from 'next/dynamic'
import { BarChart3Icon } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { CrowdIndustryItem } from '@/lib/api'

// 动态导入 ECharts（禁用 SSR，参照 shareholder-analysis/IndustryDistribution.tsx:22-26）
const ReactECharts = dynamic(() => import('echarts-for-react').then((mod) => mod.default), {
  ssr: false,
  loading: () => <div className="h-64 flex items-center justify-center text-muted-foreground text-sm">加载图表中...</div>,
})

// 与 06 一致：仅渲染 Top N，长尾合并"其他"或留待筛选
const TOP_N = 10

export interface CrowdIndustryDistributionProps {
  distribution: CrowdIndustryItem[]
  isLoading?: boolean
  // 行业点击回调（暂不联动排行榜筛选，留作扩展；首版仅展示）
  onIndustryClick?: (industry: string) => void
}

export default function CrowdIndustryDistribution({
  distribution,
  isLoading,
  onIndustryClick,
}: CrowdIndustryDistributionProps) {
  // 按扎堆股数量占比（percentage）降序，截 Top N（后端 distribution 返回全量，前端截断展示）
  const sorted = useMemo(
    () => [...distribution].sort((a, b) => b.stockCount - a.stockCount || b.percentage - a.percentage),
    [distribution]
  )
  const displayed = useMemo(() => sorted.slice(0, TOP_N), [sorted])

  // ECharts option：水平条形图，主指标 = stockCount（数量），label 显示 percentage%
  // 参照 IndustryDistribution.tsx:54-100 的 yAxis category + series bar 范式
  const option = useMemo(() => {
    if (displayed.length === 0) return null
    // ECharts 自下而上展示，故 categories 反序使最大值在顶部
    const cats = displayed.map((d) => d.industry).reverse()
    const values = displayed.map((d) => d.stockCount).reverse()
    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (params: Array<{ dataIndex?: number }>) => {
          const idx = params[0]?.dataIndex
          if (idx === undefined) return ''
          const item = displayed[displayed.length - 1 - idx]
          if (!item) return ''
          return `<div>${item.industry}</div>
            <div>扎堆股数：${item.stockCount}</div>
            <div>占比：${item.percentage.toFixed(1)}%</div>
            <div>合计占流通比：${item.totalFloatRatio.toFixed(2)}%</div>`
        },
      },
      grid: { left: '15%', right: '8%', top: 10, bottom: 20, containLabel: true },
      xAxis: { type: 'value', axisLabel: { formatter: '{value}' } },
      yAxis: { type: 'category', data: cats, axisLabel: { fontSize: 12 } },
      series: [
        {
          type: 'bar',
          data: values,
          barMaxWidth: 24,
          itemStyle: { borderRadius: [0, 4, 4, 0] },
          // label 显示占比%（主指标是占比，而非绝对数量）
          label: { show: true, position: 'right', formatter: (p: { dataIndex?: number }) => {
            const item = displayed[displayed.length - 1 - (p.dataIndex ?? 0)]
            return item ? `${item.percentage.toFixed(1)}%` : ''
          }},
        },
      ],
    }
  }, [displayed])

  // 空状态（AC-04 边界：扎堆股无行业关联归"未分类"，distribution 至少含"未分类"桶；
  // 仅当 distribution 完全为空时进入此分支）
  if (!isLoading && sorted.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-10 text-muted-foreground">
        <BarChart3Icon className="w-10 h-10 mb-2 opacity-50" />
        <p className="text-sm">暂无行业分布数据</p>
      </div>
    )
  }

  return (
    <div data-testid="crowd-industry-distribution" className="space-y-3">
      {isLoading && (
        <div className="h-64 flex items-center justify-center text-muted-foreground text-sm">加载图表中...</div>
      )}
      {!isLoading && option && (
        <>
          <ReactECharts
            option={option}
            style={{ height: `${Math.max(200, displayed.length * 36 + 40)}px`, width: '100%' }}
            opts={{ renderer: 'canvas' }}
          />
          {/* 可点击的行业标签列表：兼容 spec getByText 点击（参照 IndustryDistribution.tsx:129-150） */}
          <div className="flex flex-wrap gap-2">
            {displayed.map((d) => (
              <button
                key={d.industry}
                type="button"
                data-testid={`crowd-industry-bar-${d.industry}`}
                onClick={() => onIndustryClick?.(d.industry)}
                className="px-2.5 py-1 text-xs rounded-full border border-border bg-card text-foreground hover:border-muted-foreground transition-colors"
              >
                {d.industry}（{d.stockCount}，{d.percentage.toFixed(1)}%）
              </button>
            ))}
          </div>
          <p className="text-xs text-muted-foreground">
            仅展示扎堆股数前 {TOP_N} 行业（按数量占比，辅以合计占流通比参考）。
          </p>
        </>
      )}
    </div>
  )
}
```

**关键差异（与 06 `IndustryDistribution`）**：
- 06 的主指标是 `percentage`（持仓股票数占比），08 同样以 `stockCount`（扎堆股数）作为条形长度、`percentage` 作为 label —— 两者本质一致（PRD §3.3「以扎堆股数量占比为主指标」），label 显示 `percentage%` 更贴合用户直觉
- 08 不联动排行榜筛选（首版范围外，行业点击仅作可视化交互入口预留），06 联动 HoldingsTable 行业筛选
- tooltip 增加「合计占流通比」参考字段（PRD §3.3「辅以合计占流通比作为参考」）

#### 5. `CrowdRankingTable` 组件（排行榜表格）

**复用声明**：
- 表格骨架范式：`funds/ReverseLookupTable.tsx:127-188`（`<table>` + `<thead>` + `<tbody className="divide-y">` + 骨架/错误/空态分支）
- 加载骨架范式：`ReverseLookupTable.tsx:68-105`（`Array.from({ length: 8 })` 骨架行）
- 空数据态范式：`ReverseLookupTable.tsx:122-125`（`items.length === 0 → return null`，由父组件渲染提示文案）
- 分页器：复用 `funds/Pagination.tsx`（与 04 一致）
- 搜索框范式：`funds/FundSearchBar.tsx` 或 `shareholder-analysis/HolderSearchBar.tsx`（debounce + onChange）

**Props 接口**：

```tsx
export interface CrowdRankingTableProps {
  items: CrowdRankingItem[]
  total: number
  page: number
  pageSize: number
  isLoading: boolean
  isError: boolean
  hasPrevPeriod: boolean        // AC-06：false 时环比列统一 "—"
  search: string
  onSearchChange: (value: string) => void
  onPageChange: (page: number) => void
  // 反查回调：由父组件 wire 到 plan-03 的路由跳转；plan-02 仅渲染按钮 + 触发回调
  onReverseLookup: (stockSymbol: string) => void
}
```

**列定义与渲染要点**：

| 列 | 字段 | 渲染规则 |
| --- | --- | --- |
| 排名 | （前端按 item 顺序计算） | `(page - 1) * pageSize + idx + 1` |
| 代码 | `stockSymbol` | `font-mono` |
| 名称 | `stockName` | `stockName ?? '—'`（L2 降级，架构 §8.2） |
| 行业 | `industries[]` | `industries.length > 0 ? industries.join('、') : '—'`（L1 降级） |
| 持有基金数 | `fundCount` | 整数，右对齐 |
| 合计占流通比 | `totalFloatRatio` | `totalFloatRatio !== null ? totalFloatRatio.toFixed(1) + '%' : '—'`（L3 降级，NULL 时显示「—」不计入 SUM） |
| 环比变化 | `fundCountChange` + `totalFloatRatioChange` + `isNew` + `hasPrevPeriod` | 见下方"环比列渲染规则" |
| 操作 | （反查按钮） | `<button onClick={() => onReverseLookup(item.stockSymbol)}>反查</button>` |

**环比列渲染规则（AC-03 + AC-06）**：

```tsx
function renderChangeColumn(item: CrowdRankingItem, hasPrevPeriod: boolean) {
  // AC-06：上期完全缺失 → 统一 "—"
  if (!hasPrevPeriod) {
    return <span className="text-muted-foreground">—</span>
  }
  // AC-03：新进（is_new=true，上期无记录）→ "新进" 标识
  if (item.isNew === true) {
    return (
      <span className="inline-flex items-center gap-1 text-blue-600" data-testid={`crowd-new-badge-${item.stockSymbol}`}>
        ★ 新进
      </span>
    )
  }
  // AC-03：正常环比（fund_count_change + total_float_ratio_change）
  const countChange = item.fundCountChange
  const ratioChange = item.totalFloatRatioChange
  const direction = countChange !== null && countChange > 0 ? 'up' : countChange !== null && countChange < 0 ? 'down' : 'flat'
  const arrow = direction === 'up' ? '↑' : direction === 'down' ? '↓' : '→'
  const colorClass = direction === 'up' ? 'text-green-600' : direction === 'down' ? 'text-red-600' : 'text-muted-foreground'
  return (
    <span className={`inline-flex items-center gap-2 text-sm ${colorClass}`}>
      <span>
        基金 {countChange !== null ? (countChange > 0 ? `+${countChange}` : `${countChange}`) : '—'} {arrow}
      </span>
      <span>
        占比 {ratioChange !== null ? (ratioChange > 0 ? `+${ratioChange.toFixed(2)}%` : `${ratioChange.toFixed(2)}%`) : '—'}
      </span>
    </span>
  )
}
```

**边界**：
- `hasPrevPeriod=false`（AC-06）：所有行的环比列统一「—」（无论 isNew/fundCountChange 为何值；后端在该场景已统一返回 null）
- `isNew=true`：显示「★ 新进」，不显示数值（后端 `fundCountChange=null`）
- `fundCountChange=null` 但 `isNew !== true` 且 `hasPrevPeriod=true`：理论上不应出现（后端逻辑保证），兜底显示「—」
- `totalFloatRatioChange=null`（如 stk_float_ratio 全 NULL）：占比部分显示「—」，基金数部分正常显示

**搜索框（AC-08）**：

```tsx
<div className="flex items-center gap-2">
  <SearchIcon className="w-4 h-4 text-muted-foreground" />
  <input
    type="text"
    value={search}
    onChange={(e) => onSearchChange(e.target.value)}
    placeholder="搜索股票代码或名称"
    className="block w-64 text-sm border rounded-lg px-3 py-2 border-border bg-card text-foreground placeholder-faint focus:outline-none focus:ring-2 focus:ring-primary-light"
    data-testid="crowd-search-input"
  />
  {search && (
    <button
      type="button"
      onClick={() => onSearchChange('')}
      className="text-sm text-muted-foreground hover:text-foreground"
      data-testid="crowd-search-clear"
    >
      清空
    </button>
  )}
</div>
```

**搜索无结果提示（AC-08 边界）**：

```tsx
{!isLoading && !isError && items.length === 0 && search && (
  <div className="bg-card rounded-xl border border-border shadow-sm p-12 text-center">
    <SearchIcon className="w-12 h-12 mx-auto mb-3 text-faint" />
    <p className="text-lg font-medium text-foreground mb-2">未找到匹配股票</p>
    <p className="text-sm text-muted-foreground">请调整搜索词，或清空搜索词恢复完整榜单</p>
  </div>
)}
```

**分页器**：复用 `funds/Pagination.tsx`，props `currentPage/totalPages/total/pageSize/onPageChange`。

**E2E 稳定选择器**（参照 `.claude/rules/e2e-playwright-best-practices.md` 规则 7）：
- 反查按钮：`getByRole('button', { name: /^反查$/ }).filter({ hasText: '反查' })` 或 `data-testid="crowd-reverse-lookup-{stockSymbol}"`
- 环比新进标识：`data-testid="crowd-new-badge-{stockSymbol}"`
- 搜索框：`data-testid="crowd-search-input"`（不依赖 placeholder 文案）
- 表格行：`page.getByRole('row').filter({ hasText: stockSymbol })`

#### 6. `FundCrowdAnalysisPage` 主页面组件

**复用声明**：
- 页面状态管理 + 加载/空状态/错误态分支范式：`shareholder-analysis/ShareholderAnalysisPage.tsx:28-179`
- SWR hooks 调用范式：`ShareholderAnalysisPage.tsx:37-39`（`useShareholderOverview`）

**状态管理**：

```tsx
'use client'

import React, { useState, useEffect, useRef } from 'react'
import { useFundCrowdRankings, useFundCrowdIndustryDistribution } from '@/hooks/useFundCrowdAnalysis'
import type { CrowdScope } from '@/lib/api'
import CrowdScopeSelector from './CrowdScopeSelector'
import CrowdIndustryDistribution from './CrowdIndustryDistribution'
import CrowdRankingTable from './CrowdRankingTable'

const DEFAULT_PAGE_SIZE = 20
const SEARCH_DEBOUNCE_MS = 300
const RETURN_STATE_STORAGE_KEY = 'fund-crowd-return-state'  // plan-03 复用

export default function FundCrowdAnalysisPage() {
  const [scope, setScope] = useState<CrowdScope>('active')        // AC-02 默认仅主动
  const [search, setSearch] = useState('')                         // AC-08 搜索词
  const [debouncedSearch, setDebouncedSearch] = useState('')       // debounce 后传给 API
  const [page, setPage] = useState(1)

  // AC-05 返回状态恢复：plan-03 在离开时写入 sessionStorage，本页加载时读取并恢复
  // （具体读写由 plan-03 实现；本 plan 仅预留读取入口，restoreReturnState 函数在 plan-03 接入）
  useEffect(() => {
    const saved = typeof window !== 'undefined'
      ? window.sessionStorage.getItem(RETURN_STATE_STORAGE_KEY)
      : null
    if (saved) {
      try {
        const state = JSON.parse(saved) as { scope?: CrowdScope; page?: number; search?: string }
        if (state.scope) setScope(state.scope)
        if (state.page) setPage(state.page)
        if (state.search) { setSearch(state.search); setDebouncedSearch(state.search) }
        // plan-03 会在此追加 scroll 恢复（window.scrollTo(state.scrollX, state.scrollY)）
        window.sessionStorage.removeItem(RETURN_STATE_STORAGE_KEY)
      } catch {
        window.sessionStorage.removeItem(RETURN_STATE_STORAGE_KEY)
      }
    }
  }, [])

  // debounce search（AC-08 实时过滤，避免逐字请求）
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      setDebouncedSearch(search)
      setPage(1)  // 搜索变化时重置到第 1 页
    }, SEARCH_DEBOUNCE_MS)
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current) }
  }, [search])

  // 数据获取（rankings + industry-distribution 联动，scope 变化时两者都重发）
  const rankingsParams = { scope, search: debouncedSearch || undefined, page, pageSize: DEFAULT_PAGE_SIZE }
  const { rankings, isLoading, isError } = useFundCrowdRankings(rankingsParams)
  const { distribution, hasData: hasIndustryData, isLoading: isIndustryLoading } =
    useFundCrowdIndustryDistribution(scope)

  // AC-07：持仓数据未同步 → 整页空状态
  const isPortfolioEmpty = !isLoading && rankings?.hasData === false

  const handleScopeChange = (nextScope: CrowdScope) => {
    setScope(nextScope)
    setPage(1)  // 切换口径重置到第 1 页
    // search 保留（用户搜索意图跨口径保持，PRD §3.3「切换状态在当次浏览会话内保持」）
  }

  const handlePageChange = (nextPage: number) => {
    setPage(nextPage)
    if (typeof window !== 'undefined') window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  // 反查跳转回调（plan-03 实现：记录 sessionStorage + router.push）
  // 本 plan 暂用占位：实际跳转逻辑在 plan-03 接入
  const handleReverseLookup = (stockSymbol: string) => {
    // plan-03 接入：
    //   window.sessionStorage.setItem(RETURN_STATE_STORAGE_KEY, JSON.stringify({
    //     scope, page, search, scrollX: window.scrollX, scrollY: window.scrollY,
    //   }))
    //   router.push(`/dashboard/funds/reverse-lookup?symbol=${encodeURIComponent(stockSymbol)}&from=fund-crowd`)
    // 本 plan 占位（按钮渲染但跳转在 plan-03 启用）：
    if (typeof window !== 'undefined') {
      console.warn('[plan-02] reverse lookup not yet wired (plan-03)', stockSymbol)
    }
  }

  // AC-07 空状态：持仓数据未同步
  if (isPortfolioEmpty) {
    return (
      <div className="space-y-6">
        <header className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-foreground">基金扎堆分析</h1>
            <p className="text-sm text-muted-foreground mt-1">
              数据来源：基金定期报告披露的十大重仓股（按报告期聚合，仅供参考）
            </p>
          </div>
        </header>
        <div className="bg-card rounded-xl border border-border shadow-sm p-12 text-center" data-testid="crowd-empty-portfolio">
          <p className="text-lg font-medium text-foreground mb-2">暂无基金持仓数据</p>
          <p className="text-sm text-muted-foreground">请联系管理员同步基金持仓数据</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* 标题 + 口径切换 + 报告期标识 */}
      <header className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-foreground">基金扎堆分析</h1>
          <p className="text-sm text-muted-foreground mt-1">
            数据来源：基金定期报告披露的十大重仓股（按报告期聚合，仅供参考）
          </p>
        </div>
        <div className="flex items-center gap-3">
          {rankings?.currentPeriod && (
            <span className="text-sm text-muted-foreground whitespace-nowrap">
              报告期 {rankings.currentPeriod}
            </span>
          )}
          <CrowdScopeSelector value={scope} onChange={handleScopeChange} />
        </div>
      </header>

      {/* 行业分布（AC-04） */}
      <section className="bg-card rounded-xl border border-border shadow-sm p-4">
        <h2 className="text-base font-semibold text-foreground mb-3">行业分布（按扎堆股数量占比）</h2>
        <CrowdIndustryDistribution
          distribution={distribution}
          isLoading={isIndustryLoading}
        />
      </section>

      {/* 排行榜（AC-01/02/03/06/08） */}
      <section className="bg-card rounded-xl border border-border shadow-sm p-4 space-y-4">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-base font-semibold text-foreground">
            扎堆度排行榜
            {rankings && rankings.total > 0 && (
              <span className="ml-2 text-sm text-muted-foreground">共 {rankings.total} 只</span>
            )}
          </h2>
        </div>

        {isError ? (
          <div className="p-8 text-center text-sm text-muted-foreground">
            加载失败，请重试
          </div>
        ) : (
          <CrowdRankingTable
            items={rankings?.items ?? []}
            total={rankings?.total ?? 0}
            page={rankings?.page ?? page}
            pageSize={rankings?.pageSize ?? DEFAULT_PAGE_SIZE}
            isLoading={isLoading}
            isError={isError}
            hasPrevPeriod={rankings?.hasPrevPeriod ?? false}
            search={search}
            onSearchChange={setSearch}
            onPageChange={handlePageChange}
            onReverseLookup={handleReverseLookup}
          />
        )}
      </section>
    </div>
  )
}
```

#### 7. 页面路由入口（新建 `app/dashboard/fund-crowd-analysis/page.tsx`）

**复用声明**：参照 `shareholder-analysis/page.tsx:1-22` 范式（`'use client'` + `DashboardLayout` 包裹 + `max-w-7xl mx-auto` 容器）。

> **MEMORY 提醒（`admin 路由页 use client`）**：新建 `/dashboard` 路由页若 import `@/components/dashboard` 必须加 `'use client'`，否则 build error 污染全局 E2E。本 page 顶部已加 `'use client'`。

```tsx
/**
 * 基金扎堆分析页面路由（plan-02）
 *
 * 进入路径：/dashboard/fund-crowd-analysis（侧边栏"基金扎堆分析"导航项）
 * 布局参照 shareholder-analysis/page.tsx：DashboardLayout 包裹业务内容，main 区域渲染主组件。
 */
'use client'

import { DashboardLayout } from '@/components/dashboard'
import FundCrowdAnalysisPage from '@/components/fund-crowd-analysis/FundCrowdAnalysisPage'

export default function FundCrowdAnalysisRoute() {
  return (
    <DashboardLayout>
      <div className="px-4 py-6 md:px-6 md:py-8">
        <div className="max-w-7xl mx-auto">
          <FundCrowdAnalysisPage />
        </div>
      </div>
    </DashboardLayout>
  )
}
```

#### 8. 侧边栏导航更新（修改 `DashboardLayout.tsx`）

**位置**：`web/src/components/dashboard/DashboardLayout.tsx:5` 的 lucide-react import + line 16-42 的 `baseSidebarItems` 数组。

**改造点**：
- line 5 import 追加 `UsersRound`（与现有 `Users` 区分，语义更贴合「基金群体」）：
  ```tsx
  import { Settings, ScatterChart, LineChart, BarChart3, LandmarkIcon, Users, UsersRound } from 'lucide-react'
  ```
- `baseSidebarItems` 数组在「股东分析」（line 37-41）之后追加：
  ```tsx
  {
    title: '基金扎堆分析',
    href: '/dashboard/fund-crowd-analysis',
    icon: <UsersRound className="w-5 h-5" />,
  },
  ```

**注意**：主侧边栏 `baseSidebarItems` 的 icon 是 **JSX 元素** `<UsersRound />`（与现有 `<Users />` 写法一致，参照 `DashboardLayout.tsx:40`；与 `AdminSidebar` 的组件引用 `icon: Users` 写法不同，参照 06 plan-04 §3 #10 备注）。

#### 9. mock helper（新建 `web/tests/e2e/helpers/mock-fund-crowd-api.ts`）

**复用声明**：
- mock 注册范式：`mock-shareholder-analysis-api.ts:384-419`（`page.route(url => matchApiPath(url, pathname), route => { if GET fulfill; else continue })`）
- `{ success: true, data }` 包裹结构：`mock-fund-api.ts:437-440`（`mockReverseLookup`）
- 工厂函数范式：`mock-shareholder-analysis-api.ts:126-189`（`createTestOverview` 含 `hasPrevPeriod` 开关）
- `matchApiPath` helper：从 `mock-api.ts` 或现有 helper import（与 `mock-fund-api.ts:431` 一致）

**实现要点**：

```typescript
import { type Page } from '@playwright/test'
// matchApiPath 与现有 helper 一致来源（mock-fund-api.ts 顶部 import 的 helper）
import { matchApiPath } from './mock-api'  // 或现有 import 路径

// ===================== 类型定义（与 lib/api.ts 对齐）=====================
export interface CrowdRankingItemData {
  stockSymbol: string
  stockName: string | null
  industries: string[]
  fundCount: number
  totalFloatRatio: number | null
  fundCountChange: number | null
  totalFloatRatioChange: number | null
  isNew: boolean | null
}

export interface CrowdRankingsData {
  hasData: boolean
  currentPeriod: string | null
  prevPeriod: string | null
  hasPrevPeriod: boolean
  items: CrowdRankingItemData[]
  total: number
  page: number
  pageSize: number
}

export interface CrowdIndustryItemData {
  industry: string
  stockCount: number
  percentage: number
  totalFloatRatio: number
}

export interface CrowdIndustryDistributionData {
  hasData: boolean
  currentPeriod: string | null
  distribution: CrowdIndustryItemData[]
}

// ===================== 工厂函数 =====================

/**
 * 默认排行榜测试数据（覆盖 AC-01/02/03 各场景）
 *
 * - 600519 贵州茅台：基金数 286，环比 +12（抱团加强）
 * - 300750 宁德时代：基金数 198，环比 -8（抱团瓦解）
 * - 688981 中芯国际：isNew=true（新进，AC-03）
 */
export function createTestCrowdRankings(opts?: {
  hasPrevPeriod?: boolean
  scope?: 'active' | 'all'
}): CrowdRankingsData {
  const hasPrevPeriod = opts?.hasPrevPeriod ?? true
  return {
    hasData: true,
    currentPeriod: '2025-12-31',
    prevPeriod: hasPrevPeriod ? '2025-09-30' : null,
    hasPrevPeriod,
    items: [
      {
        stockSymbol: '600519',
        stockName: '贵州茅台',
        industries: ['食品饮料'],
        fundCount: 286,
        totalFloatRatio: 8.2,
        fundCountChange: hasPrevPeriod ? 12 : null,
        totalFloatRatioChange: hasPrevPeriod ? 0.8 : null,
        isNew: hasPrevPeriod ? false : null,
      },
      {
        stockSymbol: '300750',
        stockName: '宁德时代',
        industries: ['电力设备'],
        fundCount: 198,
        totalFloatRatio: 5.4,
        fundCountChange: hasPrevPeriod ? -8 : null,
        totalFloatRatioChange: hasPrevPeriod ? -1.1 : null,
        isNew: hasPrevPeriod ? false : null,
      },
      {
        stockSymbol: '688981',
        stockName: '中芯国际',
        industries: ['电子'],
        fundCount: 45,
        totalFloatRatio: 3.1,
        fundCountChange: null,  // 新进无变化数值
        totalFloatRatioChange: null,
        isNew: hasPrevPeriod ? true : null,  // AC-06：hasPrevPeriod=false 时 isNew=null
      },
    ],
    total: 3,
    page: 1,
    pageSize: 20,
  }
}

/** AC-07 空状态：持仓数据未同步 */
export function createTestCrowdRankingsEmpty(): CrowdRankingsData {
  return {
    hasData: false,
    currentPeriod: null,
    prevPeriod: null,
    hasPrevPeriod: false,
    items: [],
    total: 0,
    page: 1,
    pageSize: 20,
  }
}

/** 行业分布测试数据（AC-04） */
export function createTestCrowdIndustryDistribution(): CrowdIndustryDistributionData {
  return {
    hasData: true,
    currentPeriod: '2025-12-31',
    distribution: [
      { industry: '食品饮料', stockCount: 32, percentage: 16.0, totalFloatRatio: 12.5 },
      { industry: '电力设备', stockCount: 28, percentage: 14.0, totalFloatRatio: 9.8 },
      { industry: '银行', stockCount: 20, percentage: 10.0, totalFloatRatio: 7.2 },
    ],
  }
}

// ===================== Mock Helpers =====================

/**
 * Mock GET /api/v1/fund-crowd-analysis/rankings — 排行榜
 *
 * 支持按 scope/search 过滤（spec 场景用）：
 * - scope=all 时 fundCount 翻倍（模拟纳入被动型）
 * - search 命中时仅返回匹配项（模拟 SQL WHERE 过滤）
 */
export async function mockCrowdRankings(
  page: Page,
  data: CrowdRankingsData
): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/fund-crowd-analysis/rankings'),
    async (route) => {
      if (route.request().method() !== 'GET') {
        await route.continue()
        return
      }
      const urlObj = new URL(route.request().url())
      const scope = urlObj.searchParams.get('scope') || 'active'
      const search = urlObj.searchParams.get('search') || ''

      let items = [...data.items]
      // scope=all 模拟：fundCount 翻倍（被动型纳入）
      if (scope === 'all') {
        items = items.map((it) => ({ ...it, fundCount: it.fundCount * 2 }))
      }
      // search 过滤（代码前缀 OR 名称包含，不区分大小写）
      if (search) {
        const s = search.toLowerCase()
        items = items.filter(
          (it) =>
            it.stockSymbol.toLowerCase().startsWith(s) ||
            (it.stockName ?? '').toLowerCase().includes(s)
        )
      }
      const total = items.length
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: { ...data, items, total },
        }),
      })
    }
  )
}

/** Mock rankings 空状态（AC-07） */
export async function mockCrowdRankingsEmpty(page: Page): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/fund-crowd-analysis/rankings'),
    async (route) => {
      if (route.request().method() !== 'GET') {
        await route.continue()
        return
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: createTestCrowdRankingsEmpty() }),
      })
    }
  )
}

/** Mock GET /api/v1/fund-crowd-analysis/industry-distribution — 行业分布 */
export async function mockCrowdIndustryDistribution(
  page: Page,
  data: CrowdIndustryDistributionData
): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/fund-crowd-analysis/industry-distribution'),
    async (route) => {
      if (route.request().method() !== 'GET') {
        await route.continue()
        return
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data }),
      })
    }
  )
}

/** Mock industry-distribution 空数据（AC-04 边界） */
export async function mockCrowdIndustryDistributionEmpty(page: Page): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/fund-crowd-analysis/industry-distribution'),
    async (route) => {
      if (route.request().method() !== 'GET') {
        await route.continue()
        return
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: { hasData: true, currentPeriod: '2025-12-31', distribution: [] },
        }),
      })
    }
  )
}
```

#### 10. Playwright spec（新建 `web/tests/e2e/fund-crowd-analysis.spec.ts`）

**复用声明**：
- `authedPage` fixture（普通用户 role）：`shareholder-analysis.spec.ts:22-53`（注入 `access_token` cookie + localStorage token + user JSON）
- mock 安装范式：`shareholder-analysis.spec.ts`（`mockShareholderOverview` + `mockShareholderSummary` 等并行注册）
- 路径常量：`SHAREHOLDER_ANALYSIS_PAGE = '/dashboard/shareholder-analysis'`（line 16），本 spec 用 `FUND_CROWD_ANALYSIS_PAGE = '/dashboard/fund-crowd-analysis'`

**场景清单（7+ 个，覆盖 AC-01/02/03/04/06/07/08）**：

```typescript
import { test as base, expect } from '@playwright/test'
import {
  mockCrowdRankings,
  mockCrowdRankingsEmpty,
  mockCrowdIndustryDistribution,
  mockCrowdIndustryDistributionEmpty,
  createTestCrowdRankings,
  createTestCrowdRankingsEmpty,
  createTestCrowdIndustryDistribution,
} from './helpers/mock-fund-crowd-api'

const FUND_CROWD_ANALYSIS_PAGE = '/dashboard/fund-crowd-analysis'

// authedPage fixture：参照 shareholder-analysis.spec.ts:22-53（普通用户 role: 'user'）
const test = base.extend<{ authedPage: void }>({
  authedPage: [
    async ({ page }, use) => {
      await page.context().addCookies([
        { name: 'access_token', value: 'test-mock-jwt-token', domain: 'localhost', path: '/' },
      ])
      await page.addInitScript(() => {
        localStorage.setItem('accessToken', 'test-mock-jwt-token')
        localStorage.setItem('tokenType', 'Bearer')
        localStorage.setItem('user', JSON.stringify({
          id: 'test-user-id', email: 'user@test.com', username: 'TestUser',
          is_active: true, role: 'user',
        }))
      })
      await use()
    },
    { auto: true },
  ],
})

// 场景 1（AC-01 排行榜展示）：进入页面 → 默认仅主动 → 排行榜按基金数降序
test('AC-01: 进入页面默认展示仅主动基金扎堆度排行榜', async ({ page }) => {
  await mockCrowdRankings(page, createTestCrowdRankings({ hasPrevPeriod: true }))
  await mockCrowdIndustryDistribution(page, createTestCrowdIndustryDistribution())
  await page.goto(FUND_CROWD_ANALYSIS_PAGE)

  // 默认仅主动选中
  await expect(page.getByTestId('crowd-scope-active')).toHaveAttribute('aria-pressed', 'true')

  // 排行榜表格可见，按基金数降序（286 > 198 > 45）
  const rows = page.locator('[data-testid="crowd-ranking-table"] tbody tr')
  await expect(rows).toHaveCount(3)
  await expect(rows.first()).toContainText('600519')
  await expect(rows.first()).toContainText('286')
  await expect(rows.nth(1)).toContainText('300750')
})

// 场景 2（AC-02 口径切换）：切换全部基金 → 基金数翻倍 → 切回仅主动恢复
test('AC-02: 切换口径为全部基金后排行榜重新计算', async ({ page }) => {
  await mockCrowdRankings(page, createTestCrowdRankings({ hasPrevPeriod: true }))
  await mockCrowdIndustryDistribution(page, createTestCrowdIndustryDistribution())
  await page.goto(FUND_CROWD_ANALYSIS_PAGE)

  // 初始：600519 基金数 286
  await expect(page.locator('[data-testid="crowd-ranking-table"] tbody tr').first()).toContainText('286')

  // 切换为全部基金（mock 内 scope=all 时 fundCount 翻倍）
  await page.getByTestId('crowd-scope-all').click()
  await expect(page.getByTestId('crowd-scope-all')).toHaveAttribute('aria-pressed', 'true')
  await expect(page.locator('[data-testid="crowd-ranking-table"] tbody tr').first()).toContainText('572')

  // 切回仅主动
  await page.getByTestId('crowd-scope-active').click()
  await expect(page.locator('[data-testid="crowd-ranking-table"] tbody tr').first()).toContainText('286')
})

// 场景 3（AC-03 环比变化 + 新进）：环比列展示 +/- 数值 + 新进标识
test('AC-03: 环比变化列展示升降数值与新进标识', async ({ page }) => {
  await mockCrowdRankings(page, createTestCrowdRankings({ hasPrevPeriod: true }))
  await mockCrowdIndustryDistribution(page, createTestCrowdIndustryDistribution())
  await page.goto(FUND_CROWD_ANALYSIS_PAGE)

  // 600519：基金 +12（抱团加强，绿色 ↑）
  const row1 = page.locator('[data-testid="crowd-ranking-table"] tbody tr').first()
  await expect(row1).toContainText(/基金\s*\+12/)

  // 300750：基金 -8（抱团瓦解，红色 ↓）
  const row2 = page.locator('[data-testid="crowd-ranking-table"] tbody tr').nth(1)
  await expect(row2).toContainText(/基金\s*-8/)

  // 688981：新进标识（AC-03）
  await expect(page.getByTestId('crowd-new-badge-688981')).toBeVisible()
})

// 场景 4（AC-04 行业分布）：行业分布条形图渲染 + 标签可点击
test('AC-04: 行业分布按扎堆股数量占比展示', async ({ page }) => {
  await mockCrowdRankings(page, createTestCrowdRankings())
  await mockCrowdIndustryDistribution(page, createTestCrowdIndustryDistribution())
  await page.goto(FUND_CROWD_ANALYSIS_PAGE)

  // 行业分布区可见
  await expect(page.getByTestId('crowd-industry-distribution')).toBeVisible()
  // 食品饮料标签（占比最高）
  await expect(page.getByTestId('crowd-industry-bar-食品饮料')).toBeVisible()
  await expect(page.getByTestId('crowd-industry-bar-食品饮料')).toContainText('16.0%')
})

// 场景 5（AC-06 上期缺失降级）：hasPrevPeriod=false → 环比列统一 "—"
test('AC-06: 上期数据缺失时环比列显示占位符', async ({ page }) => {
  await mockCrowdRankings(page, createTestCrowdRankings({ hasPrevPeriod: false }))
  await mockCrowdIndustryDistribution(page, createTestCrowdIndustryDistribution())
  await page.goto(FUND_CROWD_ANALYSIS_PAGE)

  // 所有行的环比列均显示 "—"（无新进标识、无 +/- 数值）
  await expect(page.getByTestId('crowd-new-badge-688981')).toHaveCount(0)
  const rows = page.locator('[data-testid="crowd-ranking-table"] tbody tr')
  await expect(rows).toHaveCount(3)
  // 每行的环比列包含 "—"（具体选择器由 implementer 根据实际 DOM 微调）
})

// 场景 6（AC-07 空状态）：持仓数据未同步 → 整页空状态
test('AC-07: 持仓数据未同步展示空状态', async ({ page }) => {
  await mockCrowdRankingsEmpty(page)
  await mockCrowdIndustryDistributionEmpty(page)
  await page.goto(FUND_CROWD_ANALYSIS_PAGE)

  await expect(page.getByTestId('crowd-empty-portfolio')).toBeVisible()
  await expect(page.getByText('暂无基金持仓数据')).toBeVisible()
  // 不渲染排行榜与行业分布
  await expect(page.getByTestId('crowd-ranking-table')).toHaveCount(0)
  await expect(page.getByTestId('crowd-industry-distribution')).toHaveCount(0)
})

// 场景 7（AC-08 搜索）：代码前缀 + 名称包含 + 无结果提示 + 清空恢复
test('AC-08: 搜索过滤与无结果提示', async ({ page }) => {
  await mockCrowdRankings(page, createTestCrowdRankings())
  await mockCrowdIndustryDistribution(page, createTestCrowdIndustryDistribution())
  await page.goto(FUND_CROWD_ANALYSIS_PAGE)

  // 输入代码前缀 "600" → 仅命中 600519
  await page.getByTestId('crowd-search-input').fill('600')
  await expect(page.locator('[data-testid="crowd-ranking-table"] tbody tr')).toHaveCount(1)
  await expect(page.locator('[data-testid="crowd-ranking-table"] tbody tr').first()).toContainText('600519')

  // 输入名称包含 "茅台" → 仅命中 600519
  await page.getByTestId('crowd-search-input').fill('茅台')
  await expect(page.locator('[data-testid="crowd-ranking-table"] tbody tr')).toHaveCount(1)

  // 输入无匹配词 → 无结果提示
  await page.getByTestId('crowd-search-input').fill('不存在的股票')
  await expect(page.getByText('未找到匹配股票')).toBeVisible()

  // 清空 → 恢复完整榜单（3 条）
  await page.getByTestId('crowd-search-clear').click()
  await expect(page.locator('[data-testid="crowd-ranking-table"] tbody tr')).toHaveCount(3)
})
```

**E2E 编写规则（参照 `.claude/rules/e2e-playwright-best-practices.md`）**：
- **规则 4**（键盘事件前聚焦）：本 spec 暂无 Escape/Enter 键盘事件；若 implementer 增加搜索框 Enter 触发，需先 `await page.getByTestId('crowd-search-input').click()` 聚焦
- **规则 5**（选择器避免多匹配）：用 `data-testid="crowd-{element}-{stockSymbol}"` 缩小到具体行（如 `crowd-new-badge-688981`）；表格行用 `[data-testid="crowd-ranking-table"] tbody tr` + `.nth(idx)`
- **规则 6**（workers 控制）：`playwright.config.ts` 已配置 `workers: 1`（确认无误），无需调整
- **规则 7**（稳定选择器）：所有等待条件用 `data-testid`（`crowd-scope-active/all`、`crowd-empty-portfolio`、`crowd-search-input`），不依赖文案「暂无基金持仓数据」做等待（文案做断言可，做等待条件易碎）
- **规则 8**（Node 内置模块动态 require）：本 spec 暂不涉及；若 implementer 增加 cookie/JWT 生成，参照 `shareholder-analysis.spec.ts` 的 `addInitScript` 内联方式（不引入 Node 模块）

**E2E 用例文档**：在 `docs/e2e/` 新建 `08-e2e-用例-基金扎堆股票分析.md`（参照 `06-e2e-用例-股东分析面板.md` 风格），列出 7 个场景的步骤、断言、red/green 证据路径。

#### 11. 表格 `data-testid` 约定（implementer 必须在 `CrowdRankingTable` 渲染时加上）

为保证 spec 选择器稳定，`CrowdRankingTable` 的根容器 + 每行需加：
- 表格根容器：`<div data-testid="crowd-ranking-table" className="...">`（包裹 `<table>`）
- 每行 `<tr>`：可省略 data-testid（用 `.nth(idx)` 定位）；但环比新进标识 `data-testid="crowd-new-badge-{stockSymbol}"` 必须加
- 反查按钮（plan-02 渲染 + plan-03 wire 跳转）：`data-testid="crowd-reverse-lookup-{stockSymbol}"`（plan-03 场景会用）

## 4. Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | red：编写 `docs/e2e/08-e2e-用例-基金扎堆股票分析.md`（7 个场景） | frontend | done | 含步骤、断言、red/green 证据路径 |
| 2 | red：新建 `helpers/mock-fund-crowd-api.ts`（3 工厂 + 4 mock helper） | frontend | done | `createTestCrowdRankings` / `createTestCrowdRankingsEmpty` / `createTestCrowdIndustryDistribution` + `mockCrowdRankings` / `mockCrowdRankingsEmpty` / `mockCrowdIndustryDistribution` / `mockCrowdIndustryDistributionEmpty` |
| 3 | red：新建 `fund-crowd-analysis.spec.ts`（7 个场景） | frontend | done | 运行预期失败（页面 404 / 组件未实现），证据见 `docs/e2e/evidence/plan-02-08-e2e-red-{date}.md` |
| 4 | 新增 `fundCrowdAnalysisApi` 对象 + 5 个 TS 类型到 `lib/api.ts` | frontend | done | 紧邻 `shareholderAnalysisApi` 之后；query 参数 `page_size` snake_case |
| 5 | 新建 `hooks/useFundCrowdAnalysis.ts`（2 个 SWR hooks）+ 注册到 `hooks/index.ts` | frontend | done | 参照 `useShareholderAnalysis.ts` 模式；数组 key + fetcher 解包一层 |
| 6 | 新建 `CrowdScopeSelector` 组件 | frontend | done | 单选按钮组，默认 active，`data-testid="crowd-scope-{active/all}"` |
| 7 | 新建 `CrowdIndustryDistribution` 组件 | frontend | done | ECharts 动态导入 + Top N 截断 + 双轨标签（参照 `shareholder-analysis/IndustryDistribution.tsx`） |
| 8 | 新建 `CrowdRankingTable` 组件 | frontend | done | 搜索框 + 8 列表格 + 环比列渲染规则（AC-03/06）+ 反查按钮（onClick 触发 `onReverseLookup` 回调，plan-03 wire）+ 分页器 |
| 9 | 新建 `FundCrowdAnalysisPage` 主组件 | frontend | done | scope/page/search 状态 + AC-07 空状态分支 + AC-06 环比降级传递 + debounce search + 返回状态恢复预留（plan-03 接入） |
| 10 | 新建 `app/dashboard/fund-crowd-analysis/page.tsx` 路由入口（`'use client'`） | frontend | done | 参照 `shareholder-analysis/page.tsx`；MEMORY 提醒：必须 `'use client'` |
| 11 | 更新 `DashboardLayout.tsx` 侧边栏（import `UsersRound` + 新增导航项） | frontend | done | 「股东分析」之后追加「基金扎堆分析」；icon 为 JSX `<UsersRound />` |
| 12 | green：运行 Playwright 7 个场景全部通过 | frontend | done | `cd web && npx playwright test tests/e2e/fund-crowd-analysis.spec.ts`；7 passed；green 证据由 test-e2e 写入 |

## 5. 验收标准

### 前端核心功能验收

- [ ] AC-01 进入「基金扎堆分析」页面，默认展示「仅主动基金 · 最新报告期」扎堆度排行榜，按持有基金数降序、合计占流通比次降序；每行展示股票代码、名称（缺失「—」）、行业（多行业逗号分隔）、持有基金数、合计占流通比、环比变化、反查按钮
- [ ] AC-02 切换口径为「全部基金」→ 排行榜与行业分布同步按新口径重新加载（纳入被动型后基金数增加）；切回「仅主动基金」恢复原结果
- [ ] AC-03 环比变化列展示「+/-N」配合方向箭头（绿↑加强 / 红↓瓦解）；上一报告期无记录的股票以「★ 新进」标识
- [ ] AC-04 行业分布区以「扎堆股数量占比」为主指标可视化展示（水平条形图 Top N + 可点击行业标签 + tooltip 含合计占流通比参考）
- [ ] AC-06 上期数据缺失（`hasPrevPeriod=false`）时，环比列统一显示「—」，当期排名正常展示（无新进标识、无 +/- 数值）
- [ ] AC-07 持仓数据未同步（`hasData=false`）时，整页展示「暂无基金持仓数据，请联系管理员同步」空状态，不渲染排行榜与行业分布
- [ ] AC-08 搜索框输入股票代码前缀或名称包含（不区分大小写）→ 排行榜实时过滤；无匹配显示「未找到匹配股票，请调整搜索词」；清空恢复完整榜单

### 类型与构建验收

- [ ] `cd web && npm run build` 通过，无 TypeScript 错误（特别注意 `CrowdScope` 联合类型 + `CrowdRankingItem.isNew: boolean | null` 的 null 处理）
- [ ] `cd web && npm run lint` 通过

### 前后端契约验收（对接 plan-01）

- [ ] `fundCrowdAnalysisApi.getRankings` 调用 `/api/v1/fund-crowd-analysis/rankings`，无重复前缀（endpoint `/fund-crowd-analysis/rankings` × baseURL `/api/v1`）
- [ ] `fundCrowdAnalysisApi.getIndustryDistribution` 调用 `/api/v1/fund-crowd-analysis/industry-distribution`，无重复前缀
- [ ] query 参数 `scope` / `search` / `page` / `page_size`（snake_case，非 `pageSize`）
- [ ] 响应字段消费 `hasData` / `currentPeriod` / `prevPeriod` / `hasPrevPeriod` / `items[].stockSymbol/stockName/industries/fundCount/totalFloatRatio/fundCountChange/totalFloatRatioChange/isNew` / `pageSize`（camelCase）
- [ ] `isNew === null`（`hasPrevPeriod=false`）时组件渲染「—」（不与 `true` 新进标识混淆）
- [ ] `totalFloatRatio === null` 时显示「—」（L3 降级）
- [ ] `stockName === null` 时显示「—」（L2 降级）

### 降级回归验收（架构 §8.2）

- [ ] L5（无持仓数据）：AC-07 空状态正确展示，无布局错乱
- [ ] L4（无上期数据）：AC-06 环比列统一「—」，当期排名正常
- [ ] L3（stk_float_ratio 全 NULL）：`totalFloatRatio=null` 显示「—」，`fundCount` 正常
- [ ] L2（stocks 表缺失）：`stockName=null` 显示「—」
- [ ] L1（无行业关联）：`industries=[]` 显示「—」，行业分布归入「未分类」桶（后端处理）

### Playwright E2E 验收（E2E-TDD）

- [ ] **red 阶段**：在 `docs/e2e/08-e2e-用例-基金扎堆股票分析.md` 编写 7 个场景的 Playwright 用例；在 `web/tests/e2e/fund-crowd-analysis.spec.ts` 新建 spec；在 `helpers/mock-fund-crowd-api.ts` 新建 mock helper。实现前运行 `cd web && npx playwright test tests/e2e/fund-crowd-analysis.spec.ts` 预期失败（页面 404 / 组件未实现），证据存 `docs/e2e/evidence/plan-02-08-e2e-red-{date}.md`
- [ ] **green 阶段**：实现完成后运行同一套 7 个场景全部通过，证据存 `docs/e2e/evidence/plan-02-08-e2e-green-{date}.md`
- [ ] 现有 `shareholder-analysis.spec.ts` 与 `fund-reverse-lookup.spec.ts` 测试不破坏（green 阶段验证）

> **MEMORY 提醒（`前端 E2E implementer 改 red spec 把关`）**：green 阶段 implementer 改 red spec 是常态，主 agent 必须核查断言未放宽。重点关注：场景 5（AC-06）的「所有行环比列均显示 —」断言不应被放宽为「部分行」；场景 7（AC-08）的「清空后恢复 3 条」断言不应被放宽为「恢复非空」。

### 全流程/集成验收（US 覆盖矩阵）

> 架构文档 §2.3 成功标准 + PRD §2.2 用户故事承接：US-01（扎堆排行榜）/ US-02（主动/被动切换）/ US-03（环比变化）/ US-04（行业分布）。

| US 编号 | 用户故事简述 | 承接功能 | 验证方式 |
| --- | --- | --- | --- |
| US-01 | 看到被最多基金持有的股票排行榜 | plan-01, plan-02 | plan-01 §5 AC-01 pytest + plan-02 §5 场景 1 |
| US-02 | 切换仅主动/全部基金口径 | plan-01, plan-02 | plan-01 §5 AC-02 pytest + plan-02 §5 场景 2 |
| US-03 | 看环比变化（加强/瓦解/新进） | plan-01, plan-02 | plan-01 §5 AC-03/06 pytest + plan-02 §5 场景 3 + 场景 5 |
| US-04 | 看扎堆股集中在哪些行业 | plan-01, plan-02 | plan-01 §5 AC-04 pytest + plan-02 §5 场景 4 |

- [ ] US-01/02/03/04 的前端呈现可在「基金扎堆分析」页面正常走通

## 6. 验证命令

```bash
# 类型检查 + 构建
cd web && npm run build

# Lint
cd web && npm run lint

# red 阶段：预期失败（页面 404 / 组件未实现）
cd web && npx playwright test tests/e2e/fund-crowd-analysis.spec.ts

# green 阶段：7 个场景全部通过
cd web && npx playwright test tests/e2e/fund-crowd-analysis.spec.ts

# 现有相关 spec 不应被破坏（green 阶段验证）
cd web && npx playwright test tests/e2e/shareholder-analysis.spec.ts
cd web && npx playwright test tests/e2e/fund-reverse-lookup.spec.ts

# 手动验证（启动 dev server + 后端 plan-01）
cd web && npm run dev  # localhost:3100
# 浏览器：普通用户登录 → 侧边栏「基金扎堆分析」→ 验证排行榜/行业分布/口径切换/搜索/空状态
```

E2E（Playwright）是前端用户可观察功能的主质量门。开发必须先运行 red E2E 看到预期失败，再实现到 green 全部通过。

## 7. 交接上下文

- **架构章节**: §1 系统摘要、§2.1 范围、§3.1 流程 A/B/C、§3.2 关键分支（持仓未同步/上期缺失/口径切换中/搜索无结果/行业分布为空）、§3.3 状态机、§4.2 模块职责（前端 `FundCrowdAnalysisPage` / `CrowdRankingTable` / `CrowdIndustryDistribution`）、§5 ADR-5/7、§6.1/6.2 运行链路、§7.2 Schema（TS interface 视角）、§7.3 API 边界、§7.6 命名规则、§8.1 性能、§8.2 降级（L1-L5）
- **相关代码**:
  - 现有 ApiClient：`web/src/lib/api.ts:32-362`（`apiClient` 实例，baseURL 含 `/api/v1`）
  - 现有 fundsApi.reverseLookup：`web/src/lib/api.ts:415-432`（query 参数 snake_case 范式）
  - 现有 shareholderAnalysisApi：`web/src/lib/api.ts:892+`（命名 + endpoint 拼接范式）
  - 现有 SWR hooks 范式：`web/src/hooks/useShareholderAnalysis.ts:13-80`（数组 key + fetcher 解包 + `SWR_OPTIONS`）
  - 现有 ECharts 组件范式：`web/src/components/shareholder-analysis/IndustryDistribution.tsx:22-156`（动态导入 + 水平条形图 + 双轨标签）
  - 现有表格组件范式：`web/src/components/funds/ReverseLookupTable.tsx:56-188`（骨架/错误/空态 + `<table>` 结构）
  - 现有主页面组件范式：`web/src/components/shareholder-analysis/ShareholderAnalysisPage.tsx:28-179`（状态管理 + 加载/空/错误分支）
  - 现有页面路由范式：`web/src/app/dashboard/shareholder-analysis/page.tsx:1-22`（`'use client'` + DashboardLayout）
  - 现有侧边栏：`web/src/components/dashboard/DashboardLayout.tsx:5`（lucide-react import）+ `:16-42`（baseSidebarItems）
  - 现有 E2E fixture：`web/tests/e2e/shareholder-analysis.spec.ts:22-53`（authedPage 普通用户）
  - 现有 mock helper：`web/tests/e2e/helpers/mock-shareholder-analysis-api.ts:384-419`（page.route + matchApiPath + fulfill 范式）
  - plan-01 的 API 端点契约 — 数据来源（`/rankings` + `/industry-distribution`）
- **契约 / 数据对象**（前端消费，camelCase；与 plan-01 §3 #3 / 架构 §7.2 一致）:
  - `CrowdRankingsResponse`: `{ hasData, currentPeriod, prevPeriod, hasPrevPeriod, items: CrowdRankingItem[], total, page, pageSize }`
  - `CrowdRankingItem`: `{ stockSymbol, stockName, industries, fundCount, totalFloatRatio, fundCountChange, totalFloatRatioChange, isNew }`
  - `CrowdIndustryDistributionResponse`: `{ hasData, currentPeriod, distribution: CrowdIndustryItem[] }`
  - `CrowdIndustryItem`: `{ industry, stockCount, percentage, totalFloatRatio }`
  - `CrowdScope`: `'active' | 'all'`
  - `ApiResponse<T>` 外层包裹：`{ success, data }`；`apiClient.get` 返回 `AxiosResponse<T>`，fetcher 内 `.then(res => res.data)` 解一层
- **下游消费方**:
  - plan-03（前端下钻反查复用 04）：复用本 plan 的 `CrowdRankingTable.onReverseLookup` 回调 wire 到路由跳转；复用本 plan 的 `FundCrowdAnalysisPage` 返回状态恢复入口（`RETURN_STATE_STORAGE_KEY` sessionStorage 读写）

## 8. 风险与边界

- **执行顺序**: 按 Task 列表顺序执行。Task 1-3（red：用例文档 + mock + spec）必须先于 Task 4-11（实现）。Task 12（green）最后。
- **验证失败排查方向**:
  - red 阶段 E2E 报「页面 404」→ 正常失败（路由未创建）
  - red 阶段 E2E 报「元素未找到」→ 正常失败（组件未实现）
  - green 阶段某个场景一直 timeout → 检查 `data-testid` 是否正确加上、debounce 时间（300ms）是否合理、selector 是否多元素匹配（规则 5）
  - 现有 shareholder-analysis.spec.ts 失败 → 检查是否破坏了 DashboardLayout 侧边栏结构（如漏加 icon import 导致编译错误污染全局）
  - TypeScript 报类型错误 → 检查 `isNew: boolean | null` 的三态处理（true/false/null）+ `totalFloatRatio: number | null` 的 null 兜底
- **允许修改的额外文件**:
  - 如发现 `CrowdRankingTable` 需要拆子组件（如 `CrowdChangeCell` 环比列独立），可新建 `web/src/components/fund-crowd-analysis/CrowdChangeCell.tsx`（保持父组件 props 不变）
  - 如需复用通用 `Pagination`，直接 import `funds/Pagination.tsx`（无需新建）
- **暂停条件**:
  - plan-01 端点契约与预期不符（如字段名不一致）→ 暂停，与 plan-01 确认契约后再继续
  - 某个 AC 在 Playwright 中难以稳定断言（如 debounce 时序、ECharts canvas 渲染时机）→ 暂停，与用户讨论是否改为单元测试或调整断言策略（参照 06 IndustryDistribution 的双轨标签解法）
- **E2E 不适用说明**: 不适用。本功能是用户可观察的前端页面，必须 Playwright E2E。
- **风险备注**:
  - **`isNew` 三态处理**：`true`（新进）/ `false`（正常环比）/ `null`（`hasPrevPeriod=false`）；渲染时必须先判 `hasPrevPeriod`，再判 `isNew === true`，最后渲染数值（顺序错会导致 AC-06 场景误显示新进标识）
  - **debounce 时序**：Playwright 等待 search 触发要预留 400ms+ buffer（300ms debounce + 网络 mock 响应）；场景 7 验证搜索过滤时避免 race condition
  - **ECharts canvas 点击不稳定**：参照 06 `IndustryDistribution.tsx:129-150` 的双轨标签解法（canvas 旁渲染可点击 DOM button），spec 用 `getByTestId('crowd-industry-bar-{industry}')` 而非 canvas 点击
  - **口径切换重置 page**：切换 scope 时必须 `setPage(1)`，否则用户在第 3 页切换口径后可能停留在不存在的页码（后端返回空 items）
  - **搜索重置 page**：search 变化时同样 `setPage(1)`（debounce 回调内）
  - **MEMORY 提醒（`dev-plan-check 路径前缀验证`）**：endpoint `/fund-crowd-analysis/rankings` × baseURL `/api/v1` = `/api/v1/fund-crowd-analysis/rankings`，**无重复前缀**；implementer 必须代码级核对（不依赖文档描述）

### 前端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| `hasData=false`（持仓未同步） | 整页空状态「暂无基金持仓数据」（AC-07） | done |
| `hasPrevPeriod=false`（上期缺失） | 环比列统一「—」，当期排名正常（AC-06） | done |
| `isNew=true`（新进） | 环比列显示「★ 新进」标识，无数值（AC-03） | done |
| `isNew=null`（hasPrevPeriod=false 时） | 环比列显示「—」，不显示新进标识 | done |
| `totalFloatRatio=null`（stk_float_ratio 全 NULL） | 合计占流通比列显示「—」（L3） | done |
| `totalFloatRatioChange=null`（任一期 ratio 为 null） | 占比环比部分显示「—」，基金数部分正常 | done |
| `stockName=null`（stocks 表缺失） | 名称列显示「—」（L2） | done |
| `industries=[]`（无行业关联） | 行业列显示「—」，行业分布归入「未分类」桶（后端，L1） | done |
| search 无匹配 | 表格区显示「未找到匹配股票，请调整搜索词」（AC-08） | done |
| search 清空 | 恢复完整榜单（AC-08） | done |
| 口径切换中（SWR 重新请求） | 排行榜与行业分布显示 loading（旧数据灰显或骨架） | done |
| 分页越界（如切换口径后停留在旧页码） | 切换口径/搜索时强制 `setPage(1)` 兜底 | done |
| API 请求失败 | 排行榜区显示「加载失败，请重试」错误提示 | done |
| 行业分布 distribution 为空 | 显示「暂无行业分布数据」空状态（AC-04 边界） | done |
| 排行榜 items 为空但 hasData=true（搜索无结果） | 显示「未找到匹配股票」提示，不与 AC-07 空状态混淆 | done |
