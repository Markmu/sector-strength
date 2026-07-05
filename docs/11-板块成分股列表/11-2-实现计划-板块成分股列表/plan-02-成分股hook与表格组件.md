---
feat_id: "plan-02"
title: "成分股 hook 与表格组件"
dimension: frontend
phase: 2
status: draft
depends_on: ["plan-01"]
---

# plan-02: 成分股 hook 与表格组件

## 功能概要

- **目标**: 新建 `useSectorStocks` SWR hook 与 `SectorStocksTable` 组件，在板块详情页图表区下方呈现成分股列表，支持按强度分/市值排序、分页、三态（加载/失败/空），点击行跳转个股分析页。
- **完成后可观察结果**: 进入板块详情页，向下滑动在两张图表下方看到"板块成分股"区块；表格默认按强度分降序展示六列（代码/名称/强度分/趋势/最新价/市值）+ 总数；点击强度分或市值表头可切换升降序，表头箭头随之变化，不可排序列无响应；翻页或切换每页条数后列表更新并滚动到区块顶部；加载中显示骨架屏，加载失败显示重试按钮且不影响上方图表，无数据时显示空态文案。
- **依赖**: plan-01（契约类型与修正后的 getSectorStocks）
- **关联验收标准**: [AC-01, AC-02, AC-03, AC-04, AC-05, AC-06]
- **涉及架构模块**: useSectorStocks、SectorStocksTable（架构 §4.2）
- **前置条件**: plan-01 完成；板块详情页路由 `/dashboard/sector-analysis/[sectorId]` 存在
- **不在范围**: 个股分析落地页（plan-03 承接，本功能只负责发出 router.push）、E2E spec 编写（plan-04 承接）

## 文件清单

### 前端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| create | `web/src/hooks/useSectorStocks.ts` | 成分股数据获取 SWR hook |
| create | `web/src/components/sector-analysis/SectorStocksTable.tsx` | 成分股表格组件（含三态、排序、分页、行点击） |
| create | `web/src/components/sector-analysis/helpers.ts` | 市值量级格式化、趋势渲染辅助函数 |
| modify | `web/src/app/dashboard/sector-analysis/[sectorId]/page.tsx` | 图表区下方（约 313 行后）挂载 SectorStocksTable，传入 sectorId |

## 实现规格

### 前端部分

#### 1. useSectorStocks hook（web/src/hooks/useSectorStocks.ts）

仿 `useSectorStrengthHistory.ts` 范式。import：`useSWR` from 'swr'、`sectorsApi` from '@/lib/api'、`SectorStocksData, SectorStocksTableState` from '@/types/sectorTypes'。

```ts
interface UseSectorStocksParams {
  sectorId: number
  sortBy: 'strength_score' | 'market_cap'
  sortOrder: 'asc' | 'desc'
  page: number
  pageSize: number
  enabled?: boolean
}

interface UseSectorStocksResult {
  data: SectorStocksData | undefined
  isLoading: boolean
  isError: boolean
  error: unknown
  mutate: () => void
}
```

- fetcher：调用 `sectorsApi.getSectorStocks(sectorId, { page, page_size: pageSize, sort_by: sortBy, sort_order: sortOrder })`；解包 `response.data` 为 `SectorStocksResponse`，再取 `.data` 得 `SectorStocksData`；若 `!response.data` 抛错
- query key：`useMemo(() => sectorId ? \`/sectors/${sectorId}/stocks?sort_by=${sortBy}&sort_order=${sortOrder}&page=${page}&page_size=${pageSize}\` : null, [...])`
- SWR options：`{ refreshInterval: 0, revalidateOnFocus: false, dedupingInterval: 10000 }`（与 useSectorStrengthHistory 一致）
- 返回 `{ data, isLoading, isError: !!error, error, mutate }`

#### 2. 辅助函数（web/src/components/sector-analysis/helpers.ts）

```ts
// 趋势渲染：trend_direction 数值 → {arrow, colorClass, label}
// 1=上升 → ▲ 红（text-red-600，A 股红涨）；-1=下降 → ▼ 绿（text-green-600）；0/null → ▬ 灰（text-muted-foreground）
export function getTrendDisplay(trendDirection: number | null): { arrow: string; colorClass: string }

// 市值量级简写：number → 中文量级字符串（如 2100000000000 → "2.10万亿"，610000000000 → "6100.00亿"，<1亿 → "X.XX"）
export function formatMarketCap(value: number | null): string

// 最新价两位小数
export function formatPrice(value: number | null): string

// 强度分整数
export function formatScore(value: number | null): string
```

#### 3. SectorStocksTable 组件（web/src/components/sector-analysis/SectorStocksTable.tsx）

Props：

```ts
interface SectorStocksTableProps {
  sectorId: number
}
```

组件内部状态（useState）：`sortBy`（默认 'strength_score'）、`sortOrder`（默认 'desc'）、`page`（默认 1）、`pageSize`（默认 20）。类型用 `SectorStocksTableState`。

调用 `useSectorStocks({ sectorId, sortBy, sortOrder, page, pageSize })`。

**data-testid 约定**（照抄 CrowdRankingTable 范式，供 plan-04 E2E 选择器）：
- 区块根容器：`sector-stocks-table`
- 表头排序按钮：`sector-stocks-sort-{sortBy}`（如 `sector-stocks-sort-strength_score`）
- 分页器：复用 Pagination 组件（自带 testid 约定）
- 重试按钮：`sector-stocks-retry`
- 空态文案：`sector-stocks-empty`

**三态呈现**（参考 CrowdRankingTable）：
- isLoading 且无缓存 → 骨架屏（5-8 行灰色占位条，className 同 CrowdRankingTable 骨架）
- isError → 失败提示 + `<button data-testid="sector-stocks-retry" onClick={mutate}>重试</button>`
- data 且 data.items.length === 0 → 空态文案"该板块暂无成分股数据（请先在数据管理页同步该板块的成分股）"，data-testid=`sector-stocks-empty`
- data 且有数据 → 表格

**表格列**（六列）：
1. 代码（symbol）
2. 名称（name）
3. 强度分（strength_score，formatScore 整数）—— 可排序表头
4. 趋势（trend_direction，getTrendDisplay 渲染 ▲▼▬ + 颜色）
5. 最新价（current_price，formatPrice 两位小数）
6. 市值（market_cap，formatMarketCap 量级简写）—— 可排序表头

**排序交互**：
- 表头"强度分""市值"为可点击 button，data-testid=`sector-stocks-sort-${columnKey}`
- 点击逻辑：若点击当前排序列 → 切换 sortOrder（asc↔desc）；若点击另一可排序列 → 切换 sortBy 且 sortOrder 置 'desc'；同时 `setPage(1)`（重置到首页）
- 当前排序列显示箭头（▼desc / ▲asc），非当前排序列不显示箭头
- 代码/名称/最新价/趋势列不可排序，表头无 button、无 hover 反馈（纯 th 文本）
- sort_by 白名单：组件状态类型已约束为联合类型，不会传出白名单外值

**分页器**：复用 `Pagination` 组件（默认导出，import from '@/components/ui/Pagination'）。真实 props 签名（`Pagination.tsx:8-23`）：`currentPage`（非 page）、`totalPages`、`total`、`pageSize`、`onPageChange`、`onPageSizeChange`、`pageSizeOptions`、`showPageSizeSelector`。参照 CrowdRankingTable.tsx:121,292-300 的真实用法：

```tsx
const totalPages = pageSize > 0 ? Math.max(1, Math.ceil(total / pageSize)) : 1
// ...
<Pagination
  currentPage={page}
  totalPages={totalPages}
  total={total}
  pageSize={pageSize}
  onPageChange={setPage}
  onPageSizeChange={setPageSize}
  pageSizeOptions={[20, 50, 100]}   // 显式覆盖默认 [10,20,50,100]，与 AC-04 一致
  showPageSizeSelector
/>
```

注意：`Pagination` 默认 pageSizeOptions 含 10（`Pagination.tsx:6`），AC-04 要求 20/50/100，**必须显式传 `pageSizeOptions={[20,50,100]}`**。翻页/切 pageSize 后：`setPage`/`setPageSize`，并滚动到区块根 ref（`ref.current?.scrollIntoView({ behavior: 'smooth' })`）。仅当 total > pageSize 时显示分页器（Pagination 自身 total<=0 返回 null，但需由 pageSize<total 控制是否渲染）。

**行点击**：整行可点击，`onClick={() => router.push(\`/dashboard/stock-analysis/${item.id}\`)}`（用 next/navigation 的 useRouter；item.id 为数据库主键）。表头与分页器区域不触发行点击（它们是独立元素，事件不冒泡到行）。

**总数显示**：始终显示"共 N 只"（即使不足一页或不显示分页器）。仅当 total > pageSize 时显示分页器。

#### 4. 详情页接入（web/src/app/dashboard/sector-analysis/[sectorId]/page.tsx）

import `SectorStocksTable` from '@/components/sector-analysis/SectorStocksTable'。在图表区结束（约 313 行 `</div>` 后、免责声明区之前）新增：

```tsx
{/* 板块成分股列表 */}
<SectorStocksTable sectorId={sectorId} />
```

注意：详情页 `sectorId` 类型为 `number | null`（`page.tsx:36`），页面在 `!sectorId` 时会提前 return（`page.tsx:152`），故挂载点之后 `sectorId` 已收窄为 number。SectorStocksTable 的 `sectorId` prop 定义为 `number`，无需 `!` 断言（与 useSectorStrengthHistory 行 74/86 用 `sectorId!` 的场景不同——那些在守卫之前）。若 TS 收窄不足，挂载处可写 `{sectorId && <SectorStocksTable sectorId={sectorId} />}`。

#### 四件套契约校验（承接 plan-01）

- **路径拼接**：endpoint `/sectors/${sectorId}/stocks` × baseURL `/api/v1` = 正确路径，无双前缀 ✓
- **HTTP 方法**：apiClient.get 携带鉴权，后端 `@router.get` ✓
- **query 命名**：page/page_size/sort_by/sort_order（snake_case）与后端一致 ✓
- **响应字段**：snake_case，组件按 `item.symbol`/`item.strength_score` 等访问 ✓

#### 序列化与包裹

- apiClient 返回 `ApiResponse<SectorStocksResponse>`；hook 解包 `response.data`（得 SectorStocksResponse）→ `.data`（得 SectorStocksData，含 items/total/page/page_size/total_pages）。组件消费 `data.items`、`data.total`、`data.total_pages`。

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | 创建 useSectorStocks hook | frontend | todo | 仿 useSectorStrengthHistory，见实现规格 §1 |
| 2 | 创建 helpers.ts（市值/趋势/价格/分数格式化） | frontend | todo | 见实现规格 §2，A 股红涨绿跌 |
| 3 | 创建 SectorStocksTable 组件（三态+排序+分页+行点击+data-testid） | frontend | todo | 见实现规格 §3，复用 Pagination |
| 4 | 详情页接入 SectorStocksTable | frontend | todo | 见实现规格 §4，约 313 行后 |
| 5 | type-check + build 验证 | frontend | todo | `pnpm type-check && pnpm build` |

## 验收标准

### 功能验收

- [ ] AC-01 进入有成分股的板块详情页，图表下方出现"板块成分股"区块，表格按强度分降序，含代码/名称/强度分/趋势/最新价/市值六列，显示"共 N 只"
- [ ] AC-02 点击强度分表头切换为升序，箭头变 ▲；再点击切回降序 ▼
- [ ] AC-03 点击市值表头切换为市值降序，箭头变化；点击代码/名称/最新价/趋势列不触发排序
- [ ] AC-04 成分股 >20 只时可翻页；切换每页条数后从第 1 页开始；总页数随每页条数更新；翻页后滚动到区块顶部
- [ ] AC-05 成分股请求失败时显示失败提示+重试按钮，上方图表正常显示不受影响；点击重试后重新加载
- [ ] AC-06 无成分股板块显示"该板块暂无成分股数据"空态，不显示表格和分页器

### 性能验收（架构 §8.1 目标）

- [ ] 成分股列表请求响应时间 ≤ 500ms（page_size=20，DevTools Network 面板人工确认）

### 降级回归验收（架构 §8.2）

- [ ] 成分股区块的失败态独立呈现，不遮挡/破坏上方强度/均线图表（独立 SWR hook，互不阻塞）

### 构建验收

- [ ] `pnpm type-check` 通过
- [ ] `pnpm build` 通过

> E2E：本功能为用户可观察功能，E2E 由 plan-04 统一编写 red/green（sector-stocks.spec.ts），覆盖 AC-01~06。本功能 ready-to-dev 前需 plan-04 的 red 用例就绪。

## 验证命令

```bash
cd web
pnpm type-check
pnpm build
# E2E（需先启动 pnpm dev，且 plan-04 spec 就绪后）
pnpm exec playwright test tests/e2e/sector-stocks.spec.ts
```

## 交接上下文

- **架构章节**: §3.1 主流程、§3.2 关键分支、§3.3 状态机、§4.2 模块职责、§6.1 链路 L1、§7.2 Schema、ADR-1/2/3
- **相关代码**: 参考 `web/src/hooks/useSectorStrengthHistory.ts`（SWR 范式）、`web/src/components/fund-crowd-analysis/CrowdRankingTable.tsx`（表格三态+分页范式）、`web/src/components/ui/Pagination.tsx`（分页器）、接入点 `web/src/app/dashboard/sector-analysis/[sectorId]/page.tsx`
- **契约 / 数据对象**: `SectorStockItem`、`SectorStocksData`、`SectorStocksTableState`（plan-01 提供）
- **下游消费方**: plan-04（E2E spec 依赖 data-testid 约定与组件行为）；plan-03 的个股落地页承接本功能发出的 router.push

## 风险与边界

- **执行顺序**: 按 Task 列表顺序（hook → helpers → 组件 → 接入 → 验证）。组件依赖 hook 与 helpers
- **验证失败排查方向**: 排序无响应优先检查 sort_by 白名单与表头 button data-testid；分页不更新优先检查 Pagination props 透传与 SWR key 是否含 page/pageSize；趋势颜色错先检查 getTrendDisplay（注意 A 股红涨绿跌，上升=红非绿）
- **允许修改的额外文件**: 无（仅清单内 4 个文件）
- **暂停条件**: 若详情页 sectorId 变量名或类型与预期不符（如非 number），停止并核对页面既有代码
- **E2E 不适用说明**: 本功能用户可观察，E2E 由 plan-04 承接，不豁免
- **风险备注**: 行点击用 item.id（数据库主键），不要误用 item.symbol（会被后端 isdigit 拒绝）

### 前端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| 成分股请求失败 | 显示失败态+重试按钮，调用 mutate 重发，图表不受影响 | todo |
| 板块无成分股（total=0） | 显示空态文案，不渲染表格与分页器 | todo |
| 切换排序/每页条数后 page 越界 | 强制 setPage(1) | todo |
| strength_score/current_price/market_cap 为 null | formatXxx 函数返回占位符（如 "—"） | todo |
| 排序/分页加载中（有旧数据） | 保留旧数据，分页器/表头禁用态或加载指示（参考 CrowdRankingTable） | todo |
