---
feat_id: "plan-07"
title: "首页融资融券面板"
dimension: mixed
phase: 3
status: done
depends_on: ["plan-06"]
---

# plan-07: 首页融资融券面板

## 功能概要

- **目标**: 新建 `web/src/types/marginTypes.ts` 契约类型与 `web/src/components/market-margin/MarginPanel.tsx` 面板组件（最新值卡片 4 指标 ÷1e8 转亿 + 双 Y 轴曲线 + 30/90/250 范围切换 + 空/缺口/错误/重试态），插入普通用户首页（dashboard 非管理员分支，MarketMetricsPanel 旁）；`api.ts` 增加 `marginApi.getTrend`；配套 jest 组件测试与 Playwright E2E（**完整 red/green 循环**）。
- **完成后可观察结果**: 非管理员登录 /dashboard，在市场量价面板下方看到融资融券面板：最近结果日 + 融资余额/融券余额/两融合计余额/融资买入额 4 张卡片（单位亿）；双 Y 轴曲线——左轴 rzye+rzrqye 线图、右轴 rqye+rzmre 线图、legend 4 项；点 30/90/250 重新拉取对应趋势且不刷新整页。无数据时空态文案（含管理员数据管理链接）；有缺口时图表断线并提示；加载失败点"重试"仅局部刷新。
- **依赖**: plan-06（GET /api/v1/margin/trend 契约）
- **关联验收标准**: [AC-6]（首页面板渲染：4 卡片 + 双 Y 轴 + legend + 范围切换）
- **涉及架构模块**: 首页融资融券面板（spec REQ-7，对应 16 期 plan-07 的 MarketMetricsPanel）
- **前置条件**: plan-06 已合并；`pnpm dev`（3100 端口）与 Playwright 可用。
- **不在范围**: 数据管理同步面板（plan-08）；后端任何改动；管理员首页 IndexMonitorPage 的改动（spec REQ-7 明确仅 dashboard 非管理员视图）。

## 文件清单

### 后端维度

无。

### 前端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| create | `web/src/types/marginTypes.ts` | MarginPoint / MarginTrendData / MarginRange / MarginTaskResult（一次写全，plan-08 直消费） |
| modify | `web/src/lib/api.ts` | L1627 旁新增 `marginApi.getTrend`（apiClient，非 admin） |
| create | `web/src/components/market-margin/MarginPanel.tsx` | 面板组件 |
| modify | `web/src/app/dashboard/page.tsx` | L69 MarketMetricsPanel 之后挂载 `<MarginPanel />` |
| create | `web/tests/margin/MarginPanel.test.tsx` | jest 组件测试 |
| create | `web/tests/e2e/helpers/mock-margin-api.ts` | E2E mock helper |
| create | `web/tests/e2e/margin-panel.spec.ts` | Playwright spec（red/green） |
| create | `docs/e2e/17-e2e-用例-融资融券面板.md` | E2E 用例文档 |

## 实现规格

### 前端部分

#### 1. 类型（与 plan-06 输出契约逐字段一致）

`web/src/types/marginTypes.ts`（仿 marketMetricsTypes.ts:1-83 结构，本功能一次写全四类，plan-08 不再改本文件）：

```ts
/** 全市场单日两融指标点。缺失日六指标全 null（不补 0 / 前值，AC-5）。 */
export interface MarginPoint {
  tradeDate: string            // YYYY-MM-DD ISO 字符串
  rzye: number | null          // 融资余额（元，显示层 ÷1e8 转亿）
  rqye: number | null          // 融券余额（元，显示层 ÷1e8 转亿）
  rzmre: number | null         // 融资买入额（元，显示层 ÷1e8 转亿）
  rzche: number | null         // 融资偿还额（元，显示层 ÷1e8 转亿）
  rqmcl: number | null         // 融券卖出量（股，不入图，仅保留数据契约）
  rzrqye: number | null        // 两融合计余额（元，显示层 ÷1e8 转亿）
}

export type MarginRange = 30 | 90 | 250   // 与后端 Query pattern 一致

/** /trend 响应 data */
export interface MarginTrendData {
  latest: MarginPoint | null   // 最近成功结果日；全空为 null
  points: MarginPoint[]        // 升序，缺失日为 null 非 0
  range: MarginRange
  hasMissingDates: boolean     // 任一点 rzye 为 null → true
}

/** 单交易日同步结果（plan-04 handler camelCase result；两融无四类计数） */
export interface MarginDateResult {
  tradeDate: string
  status: 'success' | 'failed'
  reason?: string
}

/** 范围同步任务聚合结果（plan-08 消费；result 键 camelCase 直消费） */
export interface MarginTaskResult {
  successCount: number
  skippedCount: number
  failedCount: number
  dateResults: MarginDateResult[]
  unprocessedDates: string[]
}
```

#### 2. API 客户端（四件套校验，见交接上下文）

```ts
export const marginApi = {
  getTrend: (range: MarginRange) =>
    apiClient.get<{ success: boolean; data: MarginTrendData }>(
      `/margin/trend?range=${range}`
    ),
}
```

注意泛型必须写完整业务包 `{ success, data }`——`ApiClient.request` 返回 `{ data: 完整响应体 }`（仓库约定，api.ts 既有方法与 MarketMetricsPanel.tsx:93-105 用法）。

#### 3. MarginPanel 组件（仿 MarketMetricsPanel.tsx:1-350）

- **SWR 范式（照抄 MarketMetricsPanel.tsx:88-105）**：`useSWR(['marginTrend', range], () => marginApi.getTrend(range).then(res => res.data as unknown as { success: boolean; data: MarginTrendData }), SWR_OPTIONS)`；`SWR_OPTIONS = { revalidateOnFocus: false, dedupingInterval: 0 }`（range 进 key，显式切换必须重拉）；`const trend = trendRes?.data ?? null`（**不得多解一层**）
- **ECharts**：`const ReactECharts = dynamic(() => import('echarts-for-react').then(m => m.default), { ssr: false })`（单实例）
- **范围切换**：`RANGE_OPTIONS: MarginRange[] = [30, 90, 250]` 按钮组改 state → SWR key 变化自动重拉；**不触发整页刷新**
- **单位换算（仅显示层，锁定口径：存储元，前端 ÷1e8 转亿）**：`formatBillion(val) = (val / 1e8).toLocaleString('zh-CN', { maximumFractionDigits: 2 })`；tooltip 显示完整精度原始值（元/股）
- **最新值卡片区（AC-6）**：最近结果日 `tradeDate` + 4 指标卡片——融资余额（rzye）/融券余额（rqye）/两融合计余额（rzrqye）/融资买入额（rzmre），均 `formatBillion` + "亿元"标签（grid 5 格：`grid-cols-2 sm:grid-cols-5`）
- **双 Y 轴 option（useMemo，AC-6）**：
  - `xAxis: { type: 'category', data: points.map(p => p.tradeDate) }`
  - `yAxis: [{ type: 'value', name: '亿元', scale: true }, { type: 'value', name: '亿元', scale: true }]`——左轴 rzye+rzrqye（万亿级原始值，÷1e8 后万-十几万亿亿级）、右轴 rqye+rzmre（百亿-千亿级原始值，÷1e8 后同量级；右轴统一元口径，rqmcl 股口径不入图）；双轴均 `scale: true` 避免从 0 起压扁曲线
  - `series` 4 条全 `type: 'line'`：rzye（yAxisIndex 0）、rzrqye（0）、rqye（1）、rzmre（1）；每条 `connectNulls: false`、`smooth: false`；series data 为 `points.map(p => p[key] === null ? null : p[key] / 1e8)`
  - `legend: { data: ['融资余额', '两融合计余额', '融券余额', '融资买入额'] }`（4 项，AC-6 "含 legend"）
  - `tooltip: { trigger: 'axis' }`，formatter 显示该日各指标原始值（元/股完整精度）+ 亿换算；缺失日显示"无数据"
- **缺口**：`connectNulls: false`；`trend.hasMissingDates` → 图表上方提示"部分日期无数据"（data-testid="margin-missing-hint"）
- **空态**：`trend && trend.latest === null` → 管理员显示 `/dashboard/admin/data` 链接（useAuth isAdmin）；普通用户纯文案
- **错误态**：`error` → 错误框 + "重试"按钮 → 仅 `mutate()`（局部刷新不刷整页）
- **容器**：`data-testid="margin-panel"`；范围按钮 `data-testid="margin-range-{30|90|250}"`

#### 4. 首页插入（spec REQ-7：dashboard 非管理员视图）

`web/src/app/dashboard/page.tsx`：非管理员分支 `{!isLoading && <MarketMetricsPanel />}`（L69）之后并列插入 `{!isLoading && <MarginPanel />}`（顶部 import；沿用 `!isLoading` 认证就绪守卫，避免过渡帧误显）；**不改动**管理员分支（IndexMonitorPage，spec 范围外）。

#### 5. E2E（red → green，§5 适用性：完整循环）

用例文档 `docs/e2e/17-e2e-用例-融资融券面板.md`，spec `web/tests/e2e/margin-panel.spec.ts` + `helpers/mock-margin-api.ts`（`page.route('**/api/v1/margin/trend*')` 按 query 返回 fixture：满数据 / 全空 / 部分缺口 / 500 四组，范式照抄 `helpers/mock-market-metrics-api.ts`）。**实现前先运行记录 red 失败证据，实现后运行记录 green 通过证据**，证据写入 `docs/e2e/evidence/plan-07-e2e-{red|green}-{YYYYMMDD}.md`。

E2E 场景（Given/When/Then）：

1. **面板渲染**：Given 普通用户登录且 mock `/margin/trend?range=30` 返回满数据 fixture，When 打开 /dashboard，Then `margin-panel` 渲染于 `market-metrics-panel` 之后；最近结果日 + 4 张最新值卡片（亿元）可见；ECharts canvas 存在且 legend 含"融资余额/两融合计余额/融券余额/融资买入额"4 项。
2. **范围切换**：When 点击 `margin-range-90` 与 `margin-range-250`，Then 依次发起 `?range=90`、`?range=250` 请求（mock 断言 URL 与请求计数）且无整页刷新（断言 window 导航未发生）。
3. **缺口断线**：Given fixture 中 2 个交易日六指标为 null，When 打开 /dashboard，Then `margin-missing-hint` 提示可见且图表数据不含 0 值点（断言 null 点未被填充）。
4. **空态与错误重试**：Given latest=null fixture，Then 空态文案可见；Given mock 返回 500，Then 错误框 + 重试按钮出现，点击后仅重发 trend 请求（断言请求计数 +1、market-metrics 请求计数不变）。

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | marginTypes.ts 类型（含 plan-08 消费的 MarginTaskResult） | frontend | done | 与后端契约逐字段一致 |
| 2 | api.ts 增加 marginApi.getTrend | frontend | done | apiClient GET |
| 3 | MarginPanel 组件（卡片/双 Y 轴/切换/空缺口错误态） | frontend | done | 单 ECharts 实例 |
| 4 | dashboard/page.tsx 插入（MarketMetricsPanel 后） | frontend | done | 非管理员分支 |
| 5 | jest 组件测试 | frontend | done | tests/margin/ 路径 |
| 6 | E2E 用例文档 + mock helper + spec（red 证据） | frontend | done | 先 red 后实现；green 证据 docs/e2e/evidence/plan-07-e2e-green-2026-08-14.md（5/5 通过） |

## 验收标准

### 前端验收

- [x] AC-6 面板渲染：4 张最新值卡片（融资余额/融券余额/两融合计余额/融资买入额，单位亿）+ 双 Y 轴曲线（左轴 rzye/rzrqye、右轴 rqye/rzmre）+ legend 4 项 + 最近结果日（E2E 断言）
- [x] AC-6 范围切换 30/90/250：发起对应 `?range=` 请求（E2E mock 断言 URL）且无整页刷新
- [x] 缺口：fixture 缺 2 日 → `connectNulls:false` 断线 + "部分日期无数据"提示可见；不出现 0 值点
- [x] 空态：latest=null → 空态可见（管理员含数据管理链接 / 普通用户文案）
- [x] 错误态：mock 500 → 错误框 + 重试按钮 → 点击仅重发 trend 请求（断言请求计数 +1、相邻面板请求计数不变）
- [x] 单位：卡片与轴标签为亿元（÷1e8）；tooltip 完整精度原始值
- [x] 布局：面板渲染于 MarketMetricsPanel 之后、市场强度 Card 之前（E2E 断言 DOM 顺序）；管理员首页（IndexMonitorPage 分支）不受影响
- [x] `pnpm exec tsc --noEmit`、`pnpm run lint`、`pnpm build` 通过；jest 组件测试通过
- [x] E2E-TDD：`margin-panel.spec.ts` red 证据（实现前失败截图/输出）与 green 证据齐备，存 `docs/e2e/evidence/plan-07-e2e-{red|green}-{date}.md`

### 性能验收

- [x] 单个 ECharts 实例（渲染断言 container 数量=1）；切换范围不触发整页刷新

## 验证命令

```bash
cd web

# 1. 类型 / lint / 构建
pnpm exec tsc --noEmit && pnpm run lint && pnpm build

# 2. 组件测试（jest testMatch 只收 tests/**，故放 web/tests/margin/）
pnpm test -- tests/margin/MarginPanel.test.tsx

# 3. E2E（需先 pnpm dev 起 3100 端口；mock 模式无真实后端依赖）
pnpm test:e2e -- tests/e2e/margin-panel.spec.ts

# 4. 既有面板回归（确认 dashboard/page.tsx 同文件编辑未破坏 plan-07 前的 16 期面板）
pnpm test:e2e -- tests/e2e/market-metrics-panel.spec.ts
```

## 交接上下文

- **spec 章节**: REQ-7（首页面板）、边界（必须：÷1e8 转亿、复用 ECharts；禁止：新图表库/状态管理库）、任务清单 T7
- **相关代码**: `web/src/components/market-metrics/MarketMetricsPanel.tsx`（L1-350 全量对照母本：SWR L88-105、dynamic L34-44、formatBillion L67-70、option L107-172、空态 L271-293）、`web/src/types/marketMetricsTypes.ts`（类型文档范式）、`web/src/lib/api.ts`（marketMetricsApi L1627-1633 对照锚点）、`web/src/app/dashboard/page.tsx`（挂载点 L69）
- **契约 / 数据对象**: `MarginTrendData`（plan-06 §实现规格同源）；SWR 解包层级：`res.data` = `{success, data}`，组件再取 `.data`
- **下游消费方**: plan-08 复用 `marginTypes.ts` 与 `api.ts`（同文件顺序编辑，串行执行）
- **四件套校验结论**: endpoint `/margin/trend?range=30` × baseURL `${API_BASE_URL}/api/v1` = `/api/v1/margin/trend`（无双前缀）；GET 走 ApiClient 带鉴权；query 名 `range` 与后端 Query 定义一致；响应 data camelCase / Decimal→float 与类型一致
- **路径一致性说明**: 右轴按 spec REQ-7/AC-6 锁定口径执行 **rqye+rzmre**（融券余额+融资买入额，两者同为元口径且百亿-千亿级同量级适合同轴）。曾误写 rqye+rqmcl（股口径与元混轴）已修正；rqmcl 仅保留在 MarginPoint 类型与 API 数据契约中（数据完整性），不入曲线图

## 风险与边界

- **执行顺序**: 按 Task 列表顺序执行；Task 6 的 red 证据必须先于 Task 3 实现采集（E2E-TDD）
- **验证失败排查方向**: E2E mock 未命中先查 URL 是否双前缀；图表不渲染查 dynamic ssr:false；双轴一条线压底查 yAxisIndex 是否遗漏
- **允许修改的额外文件**: 无
- **暂停条件**: 若首页插入导致布局回归（板块热力图等错位），暂停并截图请求确认
- **风险备注**: 右轴统一元口径（rqye+rzmre 均为亿元），无股/元混轴问题；rqmcl（股）不入图，仅在类型与 API 契约中保留

### 前端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| points 全 null（同步未跑） | 空态：管理员链接 / 普通文案 | done |
| 部分缺口 | connectNulls:false 断线 + 提示 | done |
| 请求失败 | 错误框 + mutate 局部重试 | done |
| 范围内点数 < N | 如实渲染已有交易日点 | done |
| 快速连续切换范围 | SWR key 去重，最后一次生效（dedupingInterval:0 保证显式切换重拉） | done |
