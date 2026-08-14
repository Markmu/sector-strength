---
title: '市场量价总览位置调整与双曲线图拆分'
type: 'feature'
created: '2026-08-14'
status: 'done'
context:
  - docs/16-A股全市场量价指标/16-2-实现计划-A股全市场量价指标/README.md
---

<frozen-after-approval reason="人工意图 — 除非人类重新协商，否则不可修改">

## 意图

**问题：** 管理员首页的市场量价总览面板位于"指数总览"上方，遮挡阅读顺序；且单图表内三个指标靠按钮切换（成交量/成交额为柱状图），对比成交量与平均价需要来回切换、无法同屏。

**方案：** 管理员首页将市场量价面板移到"指数总览"卡片正下方（总览与指数走势图之间）；面板图表区拆分为左右两个并排曲线图——左"成交额"折线、右"平均价"折线，移除指标切换按钮，30/90/250 范围切换由双图共享。（左图原定成交量，2026-08-15 用户改定为成交额）

## 边界

**必须：**
- 左图成交量（volumeShares）与右图平均价（averagePrice）均为 `type: 'line'` 折线，禁止柱状图；左图单位亿股（÷1e8），右图单位元、`scale: true`。
- 双图共享同一 range state（30/90/250），切换时两图同时重新请求/刷新（数据仍来自同一 trend 接口）。
- 最新值卡片区保持 4 张不变（最近结果日/成交额/成交量/平均价）；成交额不再上图、仅保留卡片展示。
- 桌面端左右并排（grid 两列），移动端上下堆叠（单列）。
- 非管理员首页顺序不变（基金分析 → 量价总览 → 融资融券 → 市场强度…），仅管理员 IndexMonitorPage 内调整位置。
- 16 期既有 E2E/jest 断言按新契约更新（顺序断言翻转、chart count 1→2、指标切换用例移除），17 期 margin-panel 位置断言不得破坏。

**先问：** 无（双图共享 range、成交额留卡片、移动端堆叠为实现层合理默认，如需调整在审批时提出）。

**禁止：**
- 不改动融资融券面板（MarginPanel）与数据管理同步面板。
- 不改后端接口（trend 契约不变，仍是单次请求全指标）。
- 不引入新图表库；仍复用单次动态加载的 echarts-for-react 范式（两个图各一个 ReactECharts 实例）。

## 需求变更

### 修改

- **REQ-1（管理员首页布局）**：IndexMonitorPage 中 MarketMetricsPanel SHALL 从"指数总览之前"移动到 IndexOverviewCards（h2"指数总览"）之后、IndexTrendChart 之前。
- **REQ-2（面板双图拆分）**：MarketMetricsPanel 图表区 SHALL 拆分为左右两个折线图：左图成交额（`market-metrics-chart-amount`，亿元；2026-08-15 由成交量改定）、右图平均价（`market-metrics-chart-price`），均 `connectNulls: false`；原单图 `market-metrics-chart` 与指标切换按钮组（`market-metrics-metric-*`）SHALL 移除。
- **REQ-3（卡片与 range）**：最新值卡片 4 张保持不变；range 切换按钮组（`market-metrics-range-*`）保留，控制双图共享的 range state。
- **REQ-4（既有测试更新）**：16 期 market-metrics-panel E2E（TC-7.1 顺序断言改为"指数总览之后"、chart count=2、TC-7.3 指标切换用例改为双图断言）与 jest（metric 切换用例移除、新增双图容器断言）SHALL 随契约更新；17 期 margin-panel 与 16 期 market-metrics-sync E2E 回归 SHALL 通过。

</frozen-after-approval>

## 代码地图

**前端 — 修改：**
- `web/src/components/market-metrics/MarketMetricsPanel.tsx` — 双图拆分主改动（METRIC_CONFIG/切换按钮移除、option 拆两个 useMemo、容器 grid 两列）
- `web/src/components/index-monitor/IndexMonitorPage.tsx:155` — 面板移动到 :157 IndexOverviewCards 之后
- `web/tests/market-metrics/MarketMetricsPanel.test.tsx` — jest 契约更新
- `web/tests/e2e/market-metrics-panel.spec.ts` — 16 期 E2E 契约更新（顺序/count/双图）

**回归不动：**
- `web/tests/e2e/margin-panel.spec.ts`（17 期，断言 margin 在 market-metrics 之后、市场强度之前——非管理员分支顺序未动，应保持绿）
- `web/src/app/dashboard/page.tsx`（非管理员分支零改动）

## 任务清单

- [x] **T1 面板双图拆分**：MarketMetricsPanel.tsx——移除 metric state/METRIC_ORDER/切换按钮组/METRIC_CONFIG 的 bar 配置；新增两个 option useMemo（左 volumeShares line 亿股、右 averagePrice line 元 scale:true）；图表容器 grid-cols-1 md:grid-cols-2；testid `market-metrics-chart-volume`/`market-metrics-chart-price`；缺口提示、空态、错误重试、range 切换逻辑保持。
- [x] **T2 管理员首页位置**：IndexMonitorPage.tsx 将 `<MarketMetricsPanel />` 移至 IndexOverviewCards 之后、IndexTrendChart 之前，同步更新注释。
- [x] **T3 测试契约更新**：jest 移除 metric 切换用例、补双图容器/卡片断言；16 期 E2E 更新 TC-7.1（面板在"指数总览"之后、走势图之前）、TC-7.3（双图断言：两个 chart testid 各 count=1、经 `__echartsInst__` 钩子断言两图 series 均 line、左图成交量右图平均价）。
- [x] **T4 回归**：market-metrics-sync（16 期）、margin-panel + margin-sync（17 期）E2E 与 tsc/lint/build 全绿。

## 实施记录（2026-08-14，直接开发模式）

- **验证结果**：tsc 零新增错误（8 个历史基线不变）；jest 34/34（market-metrics + margin）；E2E market-metrics-panel 8/8（新契约）、回归 margin-panel + market-metrics-sync + margin-sync 24/24；lint 零新增（test 文件 3 处发现为 16 期既有基线行）；build 通过。
- **实施中的三处测试侧修正**（均非放宽断言）：
  1. TC-7.1 增加"多指数走势对比"标题等待，并覆写共享 watchlist mock 为非空（原 fixture 空列表导致走势区块整体不渲染，顺序断言无目标）；trend/valuation/weights 三个子请求一并 mock 防止 401 竞态。
  2. TC-7.3 的 echarts option 读取改为 `expect.poll().toEqual()` 直接断言 series（双图 dynamic 加载存在瞬时未挂窗口，先 poll 再读会竞态返回 null）。
  3. 普通首页 beforeEach 补 `/margin/trend` 宿主稳定 mock（17 期 MarginPanel 挂上普通首页后，未 mock 会 401 竞态重定向——与该 spec 自身"宿主页稳定"原则一致）。
- **组件侧新增约定**：双图容器挂 `__echartsInst__` 测试钩子（沿用 17 期 margin-panel 先例）；图内小标题用"成交量趋势/平均价趋势"（避免与卡片同名文案的 getByText 多匹配冲突）。
- **2026-08-15 追加（用户改定）**：左图由成交量曲线换为成交额曲线（amountYuan ÷1e8 亿元，testid `market-metrics-chart-volume` → `market-metrics-chart-amount`，series 名"成交额"，图题"成交额趋势"）；成交量保留在最新值卡片。验证：jest 10/10、market-metrics E2E 8/8、tsc 零新增。

## 验收标准

- **AC-1（管理员位置）**：Given 管理员登录且指数数据已初始化，when 打开首页，then 市场量价面板位于"指数总览"标题之后、指数走势图之前（E2E DOM 顺序断言）。
- **AC-2（双图渲染）**：Given trend 数据存在，when 面板渲染，then 出现两个图表容器（amount/price testid 各一），左图 series 为成交额折线（亿元）、右图为平均价折线（元），无任何 bar series（经 echarts option 断言）。
- **AC-3（无切换按钮 + range 共享）**：then 页面无 `market-metrics-metric-*` 按钮；点击 range-90 时双图对应数据同步刷新（E2E 断言仅一次 trend 请求且两图更新）。
- **AC-4（卡片不变）**：then 最近结果日/成交额/成交量/平均价 4 张卡片仍在且数值口径不变。
- **AC-5（非管理员与相邻面板回归）**：then 非管理员首页顺序保持（基金分析后、市场强度前），融资融券面板仍在量价面板之后；17 期 margin 两个 E2E spec 回归通过。
- **AC-6（质量门）**：then 16 期 market-metrics E2E（更新后）全绿、jest 全绿、tsc/lint 无新增错误、build 通过。
