---
feat_id: "plan-05"
title: "ETF 监控页面"
dimension: frontend
phase: 3
status: done
depends_on: ["plan-04"]
---

# plan-05: ETF 监控页面

## 功能概要

- **目标**: 实现 ETF 监控页面的完整业务——指数排行视图（含展开 ETF 明细、趋势入口跳转）+ 历史趋势视图（指数/单只 ETF × 份额/净流入额 × 7/30/90 日曲线），维度/视图/排序/日期/区间切换、四态（载/错/空/数据）、正负色标，完整覆盖所有前端交互 AC。
- **完成后可观察结果**: 进入 /dashboard/etf-monitor 默认显示宽基维度的指数排行表（按合计净流入额降序，正值红负值绿，含趋势入口），可切换行业维度、切换排序、切换日期、翻页、展开某指数看其 ETF 明细；点击趋势入口跳到历史趋势视图，对象自动定位，曲线绘制份额或净流入额（指标可切、7/30/90 区间可切），可在指数与单只 ETF 间切换；加载中骨架屏、加载失败重试、空数据引导态正确；趋势对象历史不足区间正常绘制已有部分、完全无数据走空态。
- **依赖**: plan-04（etfMonitorApi/hooks/类型/路由壳/导航）
- **关联验收标准**: [AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-07, AC-08, AC-09, AC-10, AC-11, AC-13]（全部前端交互 AC 的端到端验证）
- **涉及架构模块**: EtfMonitorPage、EtfIndexRankingTable、EtfTrendChart、helpers
- **前置条件**: plan-04 已完成；plan-01/03 已完成且库内有测试数据（含多日，供趋势验证）
- **不在范围**: 后端（plan-01/02/03）

## 文件清单

### 前端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| create | `web/src/components/etf-monitor/EtfMonitorPage.tsx` | 页面主组件（双视图协调 + 状态管理） |
| create | `web/src/components/etf-monitor/EtfIndexRankingTable.tsx` | 指数排行表格（含展开明细 + 趋势入口） |
| create | `web/src/components/etf-monitor/EtfTrendChart.tsx` | 历史趋势曲线（指标/区间切换） |
| create | `web/src/components/etf-monitor/helpers.ts` | 工具函数（格式化/色标） |
| modify | `web/src/app/dashboard/etf-monitor/page.tsx` | 接入 EtfMonitorPage（替换占位） |
| create | `web/tests/e2e/etf-monitor.spec.ts` | E2E 测试（覆盖 AC-01~11/13） |

## 实现规格

### 前端部分

#### 1. helpers.ts

仿 `sector-fund-flow/helpers.ts`（src/components/sector-fund-flow/helpers.ts）。纯函数：
- `formatShare(亿份)`：份额（亿份，正值），用于指数行合计份额与 ETF 明细行份额
- `formatSignedAmount(亿元/亿份, isPositive)`：带正负号，用于净流入额（亿元）与份额变化（亿份），两者共用此函数（均带正负色标）
- `formatPercent`：涨跌幅带百分号（change_percent 首版可能 null，容错处理）
- `formatPrice`：净值保留三位小数
- `getAmountColorClass(value)`：正值红色 class、负值绿色 class、零中性（沿用项目"红涨绿跌"惯例）

#### 2. EtfIndexRankingTable.tsx

仿 `FundFlowRankingTable.tsx`（src/components/sector-fund-flow/FundFlowRankingTable.tsx）范式：**原生 `<table>`（不用 shadcn Table）+ 四态（loading 骨架/error 重试/empty/数据）+ data-testid 锚点**。

- 列：指数名称、ETF 数、合计份额(亿份)、合计份额变化(亿份)、合计净流入额(亿元)、操作（▶ 展开标记 + 趋势入口）。
- 默认按 totalNetInflow 降序（由父组件 sortBy/order 控制，列头点击切换，三态箭头）。
- 份额/份额变化/净流入额正负色标（getAmountColorClass）。
- **行展开**：点击 ▶ 展开该指数下 ETF 明细（调 useEtfIndexDetail，明细列：基金代码/简称/净值/份额/份额变化/净流入额/涨跌幅/趋势入口），按 netInflow 降序；展开行下方渲染明细（跟随指数行所在页）。**涨跌幅列容错**：change_percent 首版因数据源 fund_daily 不可用而存 null（见 plan-01 §6 change_percent 来源与风险备注），明细列涨跌幅对 null 容错展示（显示 "-" 或留空），E2E 断言不要求该列有值。
- **趋势入口**：每指数行 + 每明细 ETF 行有"趋势"入口，点击回调父组件切到趋势视图并定位对象（指数→target_type=index，ETF→target_type=etf）。**展开标记（▶/▼）与趋势入口分离**：点展开只展开，点趋势才跳视图（架构 §3.3、PRD 3.3 跳转规则）。
- props: items, total, page, pageSize, sortBy, order, loading, error, hasData, expandedIndex, onSort, onExpand, onTrend, onRetry, onPaginate。
- 四态分支：loading→骨架屏；error→"⚠ ETF 数据加载失败 [重试]"；empty(hasData=false)→"该日期暂无 ETF 数据"；数据→表格。

#### 3. EtfTrendChart.tsx

仿 `FundFlowTimeseriesChart.tsx`（src/components/sector-fund-flow/FundFlowTimeseriesChart.tsx）范式：**`dynamic(() => import('echarts-for-react').then(m=>m.default), {ssr:false, loading:()=><div>加载图表中...</div>})`**（不建全局 wrapper）。

- 对象选择器（指数/单只 ETF 切换）+ 指标选择（份额/净流入额）+ 区间选择（7/30/90 日）。
- 横轴日期（交易日），纵轴指标值（份额亿份 / 净流入额亿元）。
- netInflow 曲线零轴基线，正负段色标；share 曲线单条。
- 调 useEtfTrend({targetType, targetCode, metric, days, endDate}) 取序列。
- 四态：未选对象→"请选择要查看的指数或 ETF"（不画空坐标系）；完全无数据(hasData=false)→"该对象暂无数据"；有部分数据→正常绘制已有部分；loading/error 同标准态。

#### 4. EtfMonitorPage.tsx

仿 `SectorFundFlowPage.tsx`（src/components/sector-fund-flow/SectorFundFlowPage.tsx）范式：**纯 useState/useMemo/useCallback 管理状态，不引入 Redux slice**（页面注释声明，参照 sector-fund-flow）。

- 状态：currentView（'ranking'|'trend'）、category（'broad'|'industry'，默认 broad）、tradeDate、sortBy（默认 netInflow）、order（默认 desc）、page/pageSize、expandedIndex、trendTarget（{type, code}）、trendMetric、trendDays。
- 顶部控制栏：维度切换 [宽基|行业] + 视图切换 [指数排行|历史趋势] + 日期选择器（默认最新有数据日，调 useEtfLatestDate）。
- ranking 视图：渲染 EtfIndexRankingTable（调 useEtfIndexRankings）。
- trend 视图：渲染 EtfTrendChart + 对象/指标/区间选择器（调 useEtfTrend）。
- 视图切换保留维度与日期；维度切换保留视图与排序；趋势对象在视图切换后保留；展开行在切维度/排序/翻页时收起（架构 §3.3）。
- 趋势入口跳转：onTrend({type,code}) → setCurrentView('trend') + setTrendTarget。
- 底部 Disclaimer 组件（components/ui/Disclaimer.tsx）。

**降级回归验收（架构 §8.2）**：双视图各自独立加载，一个失败不影响另一个；页面数据来自入库快照不实时依赖外部接口。

#### 5. page.tsx 接入

替换 plan-04 的占位为 `<EtfMonitorPage />`（import from '@/components/etf-monitor/EtfMonitorPage'），保留 DashboardLayout 包裹。

#### 6. E2E spec（tests/e2e/etf-monitor.spec.ts）

仿 `tests/e2e/sector-fund-flow.spec.ts` 范式，覆盖 AC-01~11/13：
- AC-01 进入页面默认显示宽基指数排行 + 骨架屏→数据
- AC-02 切换行业维度
- AC-03 排序切换（netInflow/shareChange/share）
- AC-04 展开指数看 ETF 明细
- AC-05 切换日期
- AC-06 切到趋势视图
- AC-07 份额/净流入额曲线 + 区间切换
- AC-08 下钻单只 ETF
- AC-09 历史不足区间
- AC-10 加载失败重试（mock 接口失败）
- AC-11 趋势入口跳转（展开标记不跳转）
- AC-13 分页

每个 AC 用 data-testid 锚点（EtfIndexRankingTable/EtfTrendChart 需暴露 testid）。

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | 新建 helpers.ts | frontend | done | 格式化/色标纯函数 |
| 2 | 新建 EtfIndexRankingTable.tsx | frontend | done | 原生 table 四态 + 展开明细 + 趋势入口 + 排序 |
| 3 | 新建 EtfTrendChart.tsx | frontend | done | dynamic echarts + 对象/指标/区间切换 + 四态 |
| 4 | 新建 EtfMonitorPage.tsx | frontend | done | 双视图协调 + 状态管理 + 控制栏 |
| 5 | page.tsx 接入 EtfMonitorPage | frontend | done | 替换占位 |
| 6 | 新建 etf-monitor.spec.ts（red 用例） | frontend | waived | red spec 在 plan-04 red-e2e 阶段已建好（TC-4.1~4.6 green、TC-5.1~5.12 red），本功能直接复用 |
| 7 | 实现 → green，所有 AC E2E 通过 | frontend | done | TC-4.1~4.6 + TC-5.1~5.12 共 18 用例全 green |

## 验收标准

### 前端验收

- [ ] AC-01 进入 /dashboard/etf-monitor 默认宽基维度指数排行，骨架屏→数据，按 totalNetInflow 降序，正负色标
- [ ] AC-02 宽基/行业维度切换，数据随之变化，再切回正常
- [ ] AC-03 表头点击 netInflow/shareChange/share 切换排序，三态箭头，不可排序列不触发
- [ ] AC-04 点击 ▶ 展开指数显示 ETF 明细（按 netInflow 降序），再点收起
- [ ] AC-05 日期切换显示对应日数据，无数据日期走空态
- [ ] AC-06 切到趋势视图，未选对象显示引导态不画坐标系
- [ ] AC-07 选指数显示份额/净流入额曲线，指标切换/7-30-90 区间切换正常
- [ ] AC-08 对象切换为单只 ETF，曲线量级变化（单只小于汇总）
- [ ] AC-09 历史不足区间正常绘制已有部分，不报错
- [ ] AC-10 接口失败显示重试，点重试重新加载；双视图独立降级
- [ ] AC-11 趋势入口跳转视图并定位对象；展开标记点击不跳转
- [ ] AC-13 分页正常，翻页滚动顶部、展开行收起

### 降级回归验收（架构 §8.2）

- [ ] 完全无数据对象走"该对象暂无数据"空态（L4）；日期无数据走空态（L1）；接口失败重试（L2）

### E2E / 验收

- [ ] E2E-TDD：`tests/e2e/etf-monitor.spec.ts` red 先失败，实现后 green 通过，覆盖 AC-01~11/13
- [ ] data-testid 锚点齐全（表格/图表/控制栏各状态）
- [ ] `npm run build` 通过
- [ ] `npm run lint` 通过

## 验证命令

```bash
cd web
# red 阶段：先写 spec 跑，预期失败
npx playwright test tests/e2e/etf-monitor.spec.ts
# green 阶段：实现后重跑，全部通过
npx playwright test tests/e2e/etf-monitor.spec.ts
npm run build
npm run lint
```

## 交接上下文

- **架构章节**: §3.1/3.3 用户流程与状态、§3.3 业务规则、§6.3/6.4/6.5 查询链路（前端消费）、§7.2 输出 Schema
- **相关代码**: SectorFundFlowPage.tsx（页面范式）、FundFlowRankingTable.tsx（表格范式）、FundFlowTimeseriesChart.tsx（图表范式）、helpers.ts（工具范式）、sector-fund-flow.spec.ts（E2E 范式）
- **契约/数据对象**: EtfIndexRankingsData/EtfIndexDetailData/EtfTrendData（plan-04 类型）；趋势入口回调 {type:'index'|'etf', code}
- **下游消费方**: 无（最终用户可见功能）

## 风险与边界

- **执行顺序**: 按 Task 列表顺序（helpers→表格→图表→页面→接入→E2E red→green）
- **验证失败排查方向**: E2E red 失败先确认 data-testid 与 selector；图表不渲染检查 dynamic/ssr:false；数据不显示核对 camelCase 字段名与 hook 解包
- **允许修改的额外文件**: 无（page.tsx 已在文件清单）
- **暂停条件**: 某个 AC 的 E2E 始终无法 green 时暂停，核对后端返回结构或前端状态流转
- **E2E 不适用说明**: 不适用——本功能是用户可观察功能，必须有 red/green E2E
- **风险备注**: 趋势入口与展开标记分离是高频坑（易误把展开做成跳转）；条件 hook（未选对象不请求）需传 null key；echarts 必须 ssr:false 否则 SSR 污染

### 前端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| 日期无数据 | 排行区显示空态文案 | done |
| 趋势未选对象 | 引导态，不画空坐标系 | done |
| 趋势完全无数据 | "该对象暂无数据"空态 | done |
| 趋势历史不足区间 | 正常绘制已有部分 | done |
| 接口加载失败 | 失败提示 + 重试，双视图独立 | done |
| 翻页/切维度 | 展开行收起，滚动顶部 | done |
| 展开标记误触发跳转 | 展开与趋势入口分离，点展开不跳视图 | done |
| echarts SSR 报错 | dynamic + ssr:false | done |
