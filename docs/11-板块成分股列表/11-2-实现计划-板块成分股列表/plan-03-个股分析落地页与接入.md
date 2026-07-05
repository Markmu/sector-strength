---
feat_id: "plan-03"
title: "个股分析落地页与接入"
dimension: frontend
phase: 2
status: draft
depends_on: ["plan-01"]
---

# plan-03: 个股分析落地页与接入

## 功能概要

- **目标**: 新建个股分析页最小落地页 `/dashboard/stock-analysis/[id]`，展示该个股的代码/名称/强度分/趋势/最新价/市值，作为 plan-02 成分股点击下钻的目标页，确保跳转不落空。
- **完成后可观察结果**: 在成分股列表点击任意一行后，浏览器跳转到 `/dashboard/stock-analysis/{id}`，落地页正常加载并展示该股代码、名称、强度分（带趋势箭头）、最新价、市值等基础信息，不出现空白页或 404；落地页加载中显示加载态，加载失败显示失败提示；落地页顶部有返回按钮可回到板块详情页。
- **依赖**: plan-01（契约类型，复用 SectorStockItem 字段约定与格式化思路）
- **关联验收标准**: [AC-07]
- **涉及架构模块**: StockAnalysisPage（架构 §4.2）、链路 L2（架构 §6.2）
- **前置条件**: plan-01 完成；plan-02 完成行点击跳转（本功能的入口）
- **不在范围**: 个股深度功能（个股强度趋势图、均线分析、K线、资金流）；StockDetail 完整字段的全部展示（仅展示基础信息卡）

## 文件清单

### 前端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| create | `web/src/app/dashboard/stock-analysis/[id]/page.tsx` | 个股分析最小落地页 |
| create | `web/src/components/stock-analysis/StockInfoCard.tsx` | 个股基础信息卡组件（代码/名称/强度分/趋势/最新价/市值） |

## 实现规格

### 前端部分

#### 1. 数据获取

落地页调用既有 `stocksApi.getStock(stockId)`（`web/src/lib/api.ts:160`）。该方法当前返回 `any`，本功能可在 plan-01 契约层外就地定义消费类型（或复用 plan-01 的字段约定）。

后端 `GET /stocks/{stock_id}`（stocks.py:159-214）返回结构：外层 `{success, data}`，data 为 StockDetail，含 id/symbol/name/current_price/market_cap/strength_score/trend_direction/sectors/created_at/updated_at（snake_case）。

在落地页就地定义消费类型（最小集，不污染 plan-01 契约层）：

```ts
interface StockDetailItem {
  id: string
  symbol: string
  name: string
  current_price: number | null
  market_cap: number | null
  strength_score: number | null
  trend_direction: number | null
}
```

数据获取方式：落地页是 client component（'use client'），用 SWR（与项目数据获取范式一致，参考 useSectorStrengthHistory）。query key `/stocks/${id}`，fetcher 调 `stocksApi.getStock(id)` 后解包 `.data.data` 得 StockDetailItem；`!response.data` 抛错。SWR options：`{ revalidateOnFocus: false }`。返回 `{ data, isLoading, isError }` 分发给 StockInfoCard。

> 不单独建 hook 文件（个股落地页是单页消费，无需跨组件复用），SWR 调用直接写在 page.tsx 内即可。

#### 2. 路由参数

Next.js App Router 动态路由：`app/dashboard/stock-analysis/[id]/page.tsx`。从 `useParams()` 或 `searchParams` 取 id。注意：id 为数据库主键（字符串形式的数字），与 plan-02 行点击 `router.push('/dashboard/stock-analysis/${item.id}')` 对应。

#### 3. StockInfoCard 组件（web/src/components/stock-analysis/StockInfoCard.tsx）

Props：`{ stock: StockDetailItem | undefined; isLoading: boolean; isError: boolean }`。

复用 plan-02 helpers 的格式化函数（import from '@/components/sector-analysis/helpers'）：`formatPrice`、`formatMarketCap`、`formatScore`、`getTrendDisplay`。

布局（参考 PRD §3.1 线框图）：卡片式，展示：
- 标题行：`{name}（{symbol}）` + 返回按钮
- 强度分：formatScore + 趋势箭头（getTrendDisplay）
- 最新价：formatPrice
- 市值：formatMarketCap

三态：isLoading → 加载占位；isError → 失败提示；stock 为空 → 空态；否则渲染卡片。

#### 4. 落地页（app/dashboard/stock-analysis/[id]/page.tsx）

```tsx
'use client'
import { useParams, useRouter } from 'next/navigation'
import DashboardLayout, { DashboardHeader } from '@/components/dashboard'
import StockInfoCard from '@/components/stock-analysis/StockInfoCard'
// 数据获取 + 三态分发到 StockInfoCard
```

- 页面标题：`{stock.name} - 个股分析`（DashboardHeader）
- 顶部返回按钮：`router.back()` 或 `router.push('/dashboard/sector-analysis/...')`（简化用 router.back()）
- data-testid 约定：`stock-info-card`（卡片根）、`stock-back-btn`（返回按钮）

#### 四件套契约校验

- **路径拼接**：endpoint `/stocks/${id}` × baseURL `/api/v1` = `http://localhost:8000/api/v1/stocks/{id}`，无双前缀 ✓
- **HTTP 方法**：apiClient.get（stocksApi.getStock 内部用 get）携带鉴权；后端 `@router.get("/{stock_id}")` ✓
- **query 命名**：本接口无 query，仅路径参数 stock_id ✓
- **响应字段**：后端输出 snake_case（symbol/name/current_price/market_cap/strength_score/trend_direction），StockDetailItem 同 snake_case ✓

#### 序列化与包裹

- 外层 `{success, data}`，data 为 StockDetail。apiClient 返回 `ApiResponse`，解包 `.data`（得 {success,data}）→ `.data`（得 StockDetail）。strength_score 等为 number|null。

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | 创建 StockInfoCard 组件（复用 plan-02 helpers） | frontend | todo | 见实现规格 §3 |
| 2 | 创建个股分析落地页（数据获取+三态+返回按钮） | frontend | todo | 见实现规格 §2、§4 |
| 3 | 验证从 plan-02 表格点击可跳转到本页且正常渲染 | frontend | todo | 与 plan-02 联调（依赖 plan-02 完成） |
| 4 | type-check + build 验证 | frontend | todo | `pnpm type-check && pnpm build` |

## 验收标准

### 功能验收

- [ ] AC-07 从成分股列表点击任意行，跳转到 `/dashboard/stock-analysis/{id}`，落地页正常展示该股代码/名称/强度分（含趋势箭头）/最新价/市值，不出现空白页或 404
- [ ] 落地页加载中显示加载态，加载失败显示失败提示（不回退到上一页）
- [ ] 落地页顶部返回按钮可返回板块详情页

### 性能验收（架构 §8.1 目标）

- [ ] 个股详情请求响应时间 ≤ 500ms（DevTools Network 面板人工确认）

### 构建验收

- [ ] `pnpm type-check` 通过
- [ ] `pnpm build` 通过

> E2E：本功能用户可观察，E2E 由 plan-04 统一编写 red/green，覆盖 AC-07 下钻场景。本功能 ready-to-dev 前需 plan-04 red 用例就绪。

## 验证命令

```bash
cd web
pnpm type-check
pnpm build
# E2E（需先启动 pnpm dev，且 plan-04 spec 就绪后）
pnpm exec playwright test tests/e2e/sector-stocks.spec.ts -g "下钻"
```

## 交接上下文

- **架构章节**: §4.2 StockAnalysisPage、§6.2 链路 L2、ADR-5
- **相关代码**: 数据源 `stocksApi.getStock`（`web/src/lib/api.ts:160`）、后端锚点 `server/src/api/v1/stocks.py:159-214`、参考 `web/src/app/dashboard/funds/[ts_code]/page.tsx`（动态路由详情页范式）、复用 plan-02 helpers
- **契约 / 数据对象**: `StockDetailItem`（就地定义）、复用 plan-02 的 `formatPrice/formatMarketCap/formatScore/getTrendDisplay`
- **下游消费方**: plan-04（E2E 下钻场景验证本页）；上游 plan-02（发出跳转）

## 风险与边界

- **执行顺序**: 按 Task 列表顺序。Task 3（联调）需 plan-02 完成
- **验证失败排查方向**: 跳转后空白优先检查路由参数 id 是否为 item.id（非 symbol）；落地页无数据检查 stocksApi.getStock 解包层级（`.data.data`）；字段错位检查 snake_case 命名
- **允许修改的额外文件**: 无（仅清单内 2 个文件）
- **暂停条件**: 若 stocksApi.getStock 实际返回结构与 stocks.py:201-212 不符（理论上不会），停止并核对后端真实响应
- **E2E 不适用说明**: 本功能用户可观察，E2E 由 plan-04 承接，不豁免
- **风险备注**: 跳转参数必须是数据库主键 id，后端 isdigit 校验（stocks.py:170）；若误用 symbol 会被后端拒绝返回 404

### 前端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| 个股详情加载失败 | 落地页页内显示失败态，不回退 | todo |
| strength_score 等字段为 null | formatXxx 返回占位符 "—" | todo |
| 路由 id 非法（非数字） | 后端返回 404，落地页走失败态 | todo |
| 直接访问本页（非来自成分股点击） | 正常按 id 加载，返回按钮用 router.back() | todo |
