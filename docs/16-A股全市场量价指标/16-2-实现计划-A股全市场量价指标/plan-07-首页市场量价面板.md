---
feat_id: "plan-07"
title: "首页市场量价面板"
dimension: mixed
phase: 3
status: done
depends_on: ["plan-06"]
---

# plan-07: 首页市场量价面板

## 功能概要

- **目标**: 新建 `MarketMetricsPanel` 组件（最新三值 + 单指标柱/线图 + 30/90/250 切换 + 空/缺口/错误/重试态），插入管理员首页（IndexMonitorPage 指数总览之前）与普通首页（快捷入口之后、市场强度之前）；配套前端类型、API 客户端方法、jest 组件测试与 Playwright E2E（red/green）。
- **完成后可观察结果**: 管理员登录主页后，在关键指数区上方看到市场量价面板：最近结果日的成交额/成交量/平均价三个数值与日期，默认成交额柱图；点指标切换成交量柱图或平均价折线，点 30/90/250 重新拉取对应趋势且不刷新整页。普通用户在快捷入口下方看到同一面板。无数据时管理员看到"前往数据管理"链接；有缺口时图表断线并提示；加载失败时点"重试"仅局部刷新。
- **依赖**: plan-06（GET /api/v1/market-metrics/trend 契约）
- **关联验收标准**: [AC-04]（两套首页）、[AC-05]（范围切换 UI）、[AC-06]（缺口展示）、[AC-12]（失败重试）
- **涉及架构模块**: 首页量价模块（架构 §4.2 模块 5）
- **前置条件**: plan-06 已合并；`pnpm dev`（3100 端口）与 Playwright 可用。
- **不在范围**: 数据管理同步面板（plan-08）；后端任何改动。

## 文件清单

### 后端维度

无。

### 前端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| create | `web/src/types/marketMetricsTypes.ts` | MarketMetricPoint / MarketMetricsTrendData / MetricKey |
| modify | `web/src/lib/api.ts` | 新增 `marketMetricsApi.getTrend`（apiClient，非 admin） |
| create | `web/src/components/market-metrics/MarketMetricsPanel.tsx` | 面板组件 |
| modify | `web/src/components/index-monitor/IndexMonitorPage.tsx` | 管理员首页：面板置于指数总览前（L150-160 区块之前） |
| modify | `web/src/app/dashboard/page.tsx` | 普通首页：快捷入口后、市场强度前（L47-63 与 L65 之间）插入 |
| create | `web/tests/market-metrics/MarketMetricsPanel.test.tsx` | jest 组件测试 |
| create | `web/tests/e2e/helpers/mock-market-metrics-api.ts` | E2E mock helper |
| create | `web/tests/e2e/market-metrics-panel.spec.ts` | Playwright spec（red/green） |
| create | `docs/e2e/16-e2e-用例-市场量价面板.md` | E2E 用例文档 |

## 实现规格

### 前端部分

#### 1. 类型（架构 §7.2 TS 契约逐字段一致）

`web/src/types/marketMetricsTypes.ts`：`MarketMetricPoint { tradeDate: string; volumeShares: number | null; amountYuan: number | null; averagePrice: number | null; finalStockCount: number | null; suspendedStockCount: number | null }`、`MarketMetricsTrendData { latest: MarketMetricPoint | null; points: MarketMetricPoint[]; range: 30 | 90 | 250; hasMissingDates: boolean }`、`export type MetricKey = 'amountYuan' | 'volumeShares' | 'averagePrice'`。

#### 2. API 客户端（四件套校验，见交接上下文）

```ts
export const marketMetricsApi = {
  getTrend: (range: 30 | 90 | 250) =>
    apiClient.get<{ success: boolean; data: MarketMetricsTrendData }>(
      `/market-metrics/trend?range=${range}`
    ),
}
```

注意泛型必须写完整业务包 `{ success, data }`——`ApiClient.request` 返回 `{ data: 完整响应体 }`，泛型即响应体类型（仓库约定见 api.ts 既有方法与 IndexMonitorPage.tsx:42-49 用法）。

endpoint `/market-metrics/trend?range=30` × baseURL `${API_BASE_URL}/api/v1` = `/api/v1/market-metrics/trend?range=30`，与后端挂载一致（无双前缀）；GET 走 `ApiClient`（自动携带 Authorization，api.ts L45-57）；query 名 `range` 与后端 Query 定义一致；响应 data 字段 camelCase / Decimal 已转 number，与类型一致。

#### 3. MarketMetricsPanel 组件（架构 §6.4.1/3/5）

- **SWR 范式（照抄 IndexMonitorPage.tsx:38-52）**：`useSWR(['marketMetricsTrend', range], () => marketMetricsApi.getTrend(range).then(res => res.data as unknown as { success: boolean; data: MarketMetricsTrendData }), SWR_OPTIONS)`（`as unknown as` 与锚点 L46-49 一致，直接 `as` 因 ApiResponse 类型交叠不通过 tsc）；`const trend = trendRes?.data ?? null`（SWR data = `{success, data}`，再取一层 `.data`，**不得多解一层**）
- **ECharts**：`const ReactECharts = dynamic(() => import('echarts-for-react').then(m => m.default), { ssr: false })`（与 IndexTrendChart.tsx:28-31 一致）；单个实例
- **指标切换**：`MetricKey` 三态（默认 `amountYuan`）；amountYuan/volumeShares 用 bar，averagePrice 用 line
- **范围切换**：30/90/250 按钮组改 state → SWR key 变化自动重拉；**不触发整页刷新**（不用 router.reload / 全局 mutate）
- **单位换算（§6.4 实现原则，仅显示层）**：`amountYuan / 1e8 → 亿元`、`volumeShares / 1e8 → 亿股`；tooltip 显示完整精度原始值；卡片平均价两位小数
- **缺口**：`connectNulls: false`；`hasMissingDates` → 图表上方提示"部分日期无数据"
- **空态**：`trend && (trend.latest === null)` → 管理员显示数据管理链接（`/dashboard/admin/data`，同 IndexMonitorPage.tsx:130-148 范式）；普通用户显示纯文案（无链接）
- **错误态**：`error` → 错误框 + "重试"按钮 → 仅 `mutate()`（AC-12，局部 mutate 不刷新整页）
- **最新值卡片区**：最近结果日三指标 + `tradeDate`（展示"最近成功结果及其日期"，§8.2-1）

#### 4. 两套首页插入（架构 §6.4.4）

- `IndexMonitorPage.tsx`：在正常渲染分支 `<IndexOverviewCards .../>`（L153）**之前**插入 `<MarketMetricsPanel />`
- `dashboard/page.tsx`：普通分支快捷入口 `</div>`（L63）之后、市场强度 Card（L65）之前插入 `<MarketMetricsPanel />`

#### 5. E2E（red → green）

- `docs/e2e/16-e2e-用例-市场量价面板.md`：用例覆盖管理员布局位置、普通布局位置、三指标切换、三范围切换、缺口断线提示、空态链接、错误重试
- `mock-market-metrics-api.ts`：`page.route('**/api/v1/market-metrics/trend*')` 按 query 返回固定 fixture（满数据 / 全空 / 部分缺口 / 500 错误四组），范式照抄 `helpers/mock-etf-monitor-api.ts`
- `market-metrics-panel.spec.ts`：admin 与 normal 两 layout 各断言上述场景；**实现前先运行记录 red 失败证据，实现后运行记录 green 通过证据**，证据写入 `docs/e2e/evidence/plan-07-e2e-{red|green}-{YYYYMMDD}.md`

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | marketMetricsTypes.ts 类型 | frontend | done | 与后端契约逐字段一致 |
| 2 | api.ts 增加 marketMetricsApi.getTrend | frontend | done | apiClient GET |
| 3 | MarketMetricsPanel 组件（图表/切换/空缺口错误态） | frontend | done | 单 ECharts 实例 |
| 4 | IndexMonitorPage 插入（指数总览前） | frontend | done | 管理员布局 |
| 5 | dashboard/page.tsx 插入（快捷入口后） | frontend | done | 普通布局 |
| 6 | jest 组件测试 | frontend | done | tests/market-metrics/ 路径 |
| 7 | E2E 用例文档 + mock helper + spec（red 证据） | frontend | done | red 阶段已产出；implement 已使 8/8 转 green（green 证据由 test-e2e 写入） |

## 验收标准

### 前端验收

- [ ] AC-04 管理员主页：面板渲染于关键指数区**之前**；普通主页：面板渲染于快捷入口**之后**、市场强度之前（E2E 断言 DOM 顺序）
- [ ] AC-04 指标切换：默认成交额柱图；切成交量为柱图、切平均价为折线（E2E 断言 canvas 存在 + 切换按钮态）
- [ ] AC-05 范围切换 30/90/250：发起对应 `?range=` 请求（E2E mock 断言 URL）且无整页刷新（断言 window 导航未发生）
- [ ] AC-06 缺口：fixture 缺 2 日 → `connectNulls:false` 断线 + "部分日期无数据"提示可见；不出现 0 值点
- [ ] AC-12 错误态：mock 500 → 错误框 + 重试按钮 → 点击仅重发 trend 请求（断言请求计数 +1、指数区请求计数不变）
- [ ] 空态：latest=null → 管理员见"前往数据管理"链接、普通用户见文案
- [ ] 单位：卡片与轴标签为亿元/亿股；平均价两位小数；tooltip 完整精度
- [ ] `pnpm exec tsc --noEmit` 与 `pnpm build` 通过；jest 组件测试通过
- [ ] E2E-TDD：`market-metrics-panel.spec.ts` red 证据（实现前失败截图/输出）与 green 证据齐备，存放 `docs/e2e/evidence/plan-07-e2e-{red|green}-{date}.md`

### 性能验收（架构 §8.1）

- [ ] 单个 ECharts 实例（渲染断言 container 数量=1）；切换指标/范围不触发整页刷新（AC-12 同款断言）

### 降级回归验收（架构 §8.2 + 本功能布局变更）

- [ ] 降级提示（L1 最新交易日未更新→展示最近成功结果及其日期；L2 趋势失败日→null 断点提示）在两套新布局中正确显示，不被新增面板遮挡（E2E 覆盖）

## 验证命令

```bash
cd web

# 1. 类型与构建
pnpm exec tsc --noEmit && pnpm build

# 2. 组件测试（jest testMatch 只收 tests/**，故放 web/tests/market-metrics/）
pnpm test -- tests/market-metrics/MarketMetricsPanel.test.tsx

# 3. E2E（需先 pnpm dev 起 3100 端口；mock 模式无真实后端依赖）
pnpm test:e2e -- tests/e2e/market-metrics-panel.spec.ts
```

## 交接上下文

- **架构章节**: §4.2 模块 5、§5 ADR-6、§6.4、§7.2（TS 契约）、§8.1/8.2
- **相关代码**: `web/src/components/index-monitor/IndexMonitorPage.tsx`（SWR 范式 L38-52、空态 L130-148）、`web/src/components/index-monitor/IndexTrendChart.tsx`（ECharts dynamic L28-31）、`web/src/app/dashboard/page.tsx`（isAdmin 分支 L32-37、普通分支 L47-76）、`web/src/lib/api.ts`（ApiClient L33-140）
- **契约 / 数据对象**: `MarketMetricsTrendData`（plan-06 §7.2 同源）；SWR 解包层级：`res.data` = `{success, data}`，组件再取 `.data`
- **下游消费方**: plan-08 复用 `marketMetricsTypes.ts` 与 api.ts（同文件顺序编辑，串行执行）
- **路径偏差标注**: 架构 §9 Phase C 写测试在 `web/src/components/market-metrics/__tests__/`，但 jest.config.ts testMatch 仅收 `<rootDir>/tests/**`——以代码约定为准，测试放 `web/tests/market-metrics/`
- **实现级补充项**: `MetricKey` 类型服务于 AC-04 指标切换，非新造 AC

## 风险与边界

- **执行顺序**: 按 Task 列表顺序执行；Task 7 的 red 证据必须先于 Task 3 实现采集（E2E-TDD）
- **验证失败排查方向**: E2E mock 未命中先查 URL 是否双前缀；图表不渲染查 dynamic ssr:false
- **允许修改的额外文件**: 无
- **暂停条件**: 若普通首页插入导致布局回归（现有板块热力图等错位），暂停并截图请求确认
- **风险备注**: 平均价折线 y 轴从 0 起会压扁曲线——axis 建议 `scale: true`

### 前端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| points 全 null（同步未跑） | 空态：管理员链接 / 普通文案 | done |
| 部分缺口 | connectNulls:false 断线 + 提示 | done |
| 请求失败 | 错误框 + mutate 局部重试 | done |
| 范围内点数 < N | 如实渲染已有交易日点 | done |
| 快速连续切换范围 | SWR key 去重，最后一次生效（dedupingInterval:0 保证显式切换重拉） | done |
