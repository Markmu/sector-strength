---
feat_id: "plan-03"
title: "前端双视图页面"
dimension: frontend
phase: 3
status: done
depends_on: ["plan-02"]
---

# plan-03 前端双视图页面

## 1. 功能概要

- **目标**: 新建"板块资金流"独立页面，含资金流排行视图与盘中变化曲线视图，覆盖维度切换、排序、日期切换、分页、自选板块叠加、刷新延长、空/错/载态、跳转强度页等全部用户交互，并在主导航新增入口。
- **完成后可观察结果**: 用户从侧边栏"板块资金流"进入页面，默认看到行业维度净额降序排行表（净额正值红/负值绿）；切换"盘中变化"视图后选 2-3 个板块，曲线叠加显示盘中净额变化；盘中刷新曲线延长；点击可匹配板块名跳转强度分析页。加载中/失败/空数据三种状态正确呈现。
- **依赖**: plan-02（4 个 API 端点）
- **关联验收标准**: [AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-07, AC-08, AC-09, AC-10, AC-12]
- **涉及架构模块**: 前端模块 sector-fund-flow 页面+useSectorFundFlow hook
- **前置条件**: plan-02 完成，API 可用；项目已有 DashboardLayout、图表组件可复用
- **不在范围**: 后端 API（plan-02）

## 2. 文件清单

### 前端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| modify | `web/src/lib/api.ts` | 新增 sectorFundFlowApi + 类型定义 |
| create | `web/src/hooks/useSectorFundFlow.ts` | SWR hooks（排行/曲线/最新日期） |
| create | `web/src/app/dashboard/sector-fund-flow/page.tsx` | 双视图页面 |
| create | `web/src/types/fundFlowTypes.ts` | FundFlowRankingItem/TimeseriesData 等类型 |
| modify | `web/src/components/dashboard/DashboardLayout.tsx` | 导航新增"板块资金流"入口 |

## 3. 实现规格

### 前端部分

#### 1. api.ts 新增 sectorFundFlowApi

仿 fundCrowdAnalysisApi（web/src/lib/api.ts:1039）。**路径拼接四件套校验**：
- baseURL = API_BASE_WITH_PREFIX = `http://localhost:8000/api/v1`（api.ts:9）
- endpoint 写 `/sector-fund-flow/rankings`（**不带 /api/v1**，避免双前缀，与 fundCrowdApi 一致）
- query 参数 snake_case（sector_type/trade_date/sort_by/page_size）
- 响应 camelCase（后端 _dict_tocamel 已转）

```typescript
export const sectorFundFlowApi = {
  getRankings: (params: {...}) =>
    apiClient.get<{ success: boolean; data: FundFlowRankingsData }>('/sector-fund-flow/rankings', {
      sector_type: params.sectorType,
      trade_date: params.tradeDate,
      sort_by: params.sortBy,
      order: params.order,
      page: params.page || 1,
      page_size: params.pageSize || 20,
    }),
  getTimeseries: (params: {...}) =>
    apiClient.get<{ success: boolean; data: FundFlowTimeseriesData }>('/sector-fund-flow/timeseries', {
      sector_names: params.sectorNames.join(','),
      sector_type: params.sectorType,
      trade_date: params.tradeDate,
    }),
  getLatestDate: (params: {...}) =>
    apiClient.get<{ success: boolean; data: { latestDate: string | null } }>('/sector-fund-flow/latest-date', {
      sector_type: params.sectorType,
    }),
}
```

**响应解包**：apiClient.get 返回 ApiResponse<T>，其 `.data` = 整个 JSON body（`{success, data: 业务对象}`）。泛型 T 必须定义为 `{success, data: 业务对象}`（与锚点 fundCrowdAnalysisApi api.ts:1049 一致）。hook 层 `.then(res => res.data)` 得到 `{success, data}`，组件再读 `data.data` 取业务对象。**不可**把 T 直接写成业务对象类型（会导致类型撒谎 + 运行时取值 undefined）。

#### 2. fundFlowTypes.ts 类型定义

对应架构 §7.2 响应视角（camelCase）：
- FundFlowRankingItem（rank, sectorName, sectorId, changePercent, inflow, outflow, netInflow, companyCount, leadingStock, leadingStockChange, currentPrice）
- FundFlowRankingsData（hasData, tradeDate, items[], total, page, pageSize）
- FundFlowSeriesPoint（sampleTime, netInflow）
- FundFlowSeriesItem（sectorName, data: FundFlowSeriesPoint[]）
- FundFlowTimeseriesData（hasData, tradeDate, series[]）

#### 3. useSectorFundFlow.ts SWR hooks

仿 useFundCrowdAnalysis.ts（web/src/hooks/）。三个 hook：
- useFundFlowRankings(params) — SWR key ['fundFlowRankings', params]
- useFundFlowTimeseries(params) — SWR key ['fundFlowTimeseries', params]
- useFundFlowLatestDate(params) — SWR key ['fundFlowLatestDate', params]

SWR_OPTIONS 复用（revalidateOnFocus:false, dedupingInterval:30000）。

#### 4. 双视图页面（page.tsx）

仿 sector-analysis/[sectorId]/page.tsx 结构（DashboardLayout + DashboardHeader + 控制面板 + 内容区）。

**页面状态**（useState/useMemo，不引入新 Zustand store）：
- currentView: 'ranking' | 'chart'
- sectorType: 'industry' | 'concept'
- tradeDate: string | null（默认从 latestDate API 取）
- sortBy: 'net_inflow' | 'inflow' | 'outflow'
- order: 'desc' | 'asc'
- page, pageSize
- selectedSectors: string[]（变化视图自选板块）

**排行视图**：
- 表格列：排名、板块名称（sectorId 非 null 可点击跳转 /dashboard/sector-analysis/{id}）、涨跌幅、流入、流出、净额（排序箭头）、公司家数、领涨股、领涨股涨跌幅
- 净额正值红色负值绿色（A 股惯例）；流入流出中性色
- 分页器（仿 SectorStocksTable 的 Pagination 组件）
- 加载中骨架屏 / 失败+重试 / 空数据态

**变化曲线视图**：
- 板块选择区：多选（从当前 sectorType 板块列表选），已选板块以 chip 展示可移除
- 曲线图：复用项目现有图表组件（如 recharts LineChart），多线叠加，不同颜色+图例
- 横轴交易时段时间、纵轴净额（亿）；零轴基线
- 未选板块：引导态"请选择要对比的板块"
- 无采样数据：空态"暂无盘中采样数据"
- "刷新"按钮：调 mutate() 重新拉取（盘中延长）

#### 5. DashboardLayout 导航入口

在 baseSidebarItems 数组（DashboardLayout.tsx:16）"板块分析"项后插入：
```typescript
{
  title: '板块资金流',
  href: '/dashboard/sector-fund-flow',
  icon: <CoinIcon className="w-5 h-5" />,  // 或合适图标
},
```

## 4. Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | api.ts 新增 sectorFundFlowApi | frontend | done | 3 方法+类型 |
| 2 | 创建 fundFlowTypes.ts | frontend | done | camelCase 类型 |
| 3 | 创建 useSectorFundFlow.ts hooks | frontend | done | SWR 3 hook |
| 4 | 创建双视图页面 page.tsx | frontend | done | 排行+曲线+状态 |
| 5 | DashboardLayout 新增导航入口 | frontend | done | baseSidebarItems |
| 6 | 实现排行视图（表格+排序+分页+色标+跳转） | frontend | done | |
| 7 | 实现变化曲线视图（多选+叠加图+刷新） | frontend | done | |
| 8 | 实现三种状态（加载/失败/空） | frontend | done | 两视图各自 |
| 9 | type-check + build 通过 | frontend | done | |

## 5. 验收标准

### 排行视图验收
- [ ] AC-01 从导航进入默认显示行业维度净额降序排行，含排名/板块名/涨跌幅/流入/流出/净额/公司家数/领涨股列，净额正值红负值绿，顶部可见"盘中变化"入口
- [ ] AC-02 切换"概念"维度数据量变化，再切回行业
- [ ] AC-03 点击流入/流出/净额表头切换排序+箭头，不可排序列无反应
- [ ] AC-04 切换日期显示历史数据，无数据日期显示空态
- [ ] AC-10 sectorId 非 null 的板块名可点击跳转强度页，null 的不可点击
- [ ] AC-12 分页+每页条数切换正确，翻页滚动到顶部

### 变化曲线视图验收
- [ ] AC-05 切换到变化视图，未选板块显示引导态不画空坐标系
- [ ] AC-06 选 2-3 板块叠加显示不同颜色曲线+图例，移除板块线消失
- [ ] AC-07 盘中点刷新曲线延长
- [ ] AC-08 无采样数据日期显示空态，切换有数据历史日期能回看

### 通用验收
- [ ] AC-09 加载失败显示失败+重试，两视图独立降级
- [ ] type-check 无错误
- [ ] pnpm build 成功

### 性能验收（架构 §8.1 目标）
- [ ] 排行查询响应 ≤ 500ms（DevTools Network 人工确认）
- [ ] 曲线查询响应 ≤ 500ms（10 板块场景）

## 6. 验证命令

```bash
cd web
pnpm type-check
pnpm build
# E2E（用户可观察功能）
pnpm e2e -- e2e/sector-fund-flow.spec.ts
```

E2E spec 覆盖：导航进入→排行默认态→维度切换→排序切换→切变化视图→选板块叠加→空态。实现前先写 red spec（预期失败），完成后转 green。

## 7. 交接上下文

- **架构章节**: §3.1 主流程、§3.3 状态机、§7.2 Schema 响应视角、§7.3 API 边界
- **相关代码**: api.ts（apiClient 约定）、useFundCrowdAnalysis.ts（SWR 范式）、sector-analysis/[sectorId]/page.tsx（页面结构范式）、DashboardLayout.tsx:16（导航）
- **契约/数据对象**: FundFlowRankingsData/FundFlowTimeseriesData（camelCase 响应）
- **下游消费方**: 无（最终用户功能）

## 8. 风险与边界

- **执行顺序**: api→类型→hooks→页面骨架→排行视图→曲线视图→状态→导航→验证
- **验证失败排查方向**: 404 检查 endpoint 是否双前缀；数据不显示检查 camelCase 字段名；曲线不画检查 timeseries 响应结构
- **允许修改的额外文件**: 无（如需复用图表组件直接 import）
- **暂停条件**: API 契约与 plan-02 不一致时暂停对齐
- **风险备注**: 变化曲线图复用项目现有图表库，若无可用的多线叠加组件需评估引入成本

### 前端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| 排行无数据 | 空态文案，不显示表格 | done |
| 曲线无采样数据 | 空态"暂无盘中采样数据" | done |
| 曲线未选板块 | 引导态不画空坐标系 | done |
| 板块名不匹配 | 普通文字不可点击 | done |
| 加载失败 | 失败+重试，两视图独立 | done |
| 维度切换后已选板块失效 | 切换维度时清空已选板块 | done |
