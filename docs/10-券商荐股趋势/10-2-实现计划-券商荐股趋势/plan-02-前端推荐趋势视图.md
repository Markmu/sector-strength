---
feat_id: "plan-02"
title: "前端推荐趋势视图（第三视图接入 + Sparkline + 趋势榜表格 + 状态机改造）"
dimension: frontend
phase: 2
status: done
depends_on: ["plan-01"]
---

# plan-02: 前端推荐趋势视图

## 功能概要

- **目标**: 在 09 券商荐股页面新增"推荐趋势"第三视图：ViewSwitcher 增加 trend 选项；view==='trend' 时隐藏月份选择器与板块筛选、渲染 BrokerTrendRanking 表格（四指标列 + Sparkline 迷你折线图列 + 行展开月度明细）。完成后用户可跨全部已同步月份查看"持续被推荐"的股票排行与走势曲线。
- **完成后可观察结果**: 用户从侧边栏进入"券商每月荐股"页面（默认股票维度），点击视图切换器的"推荐趋势"：月份选择器与板块筛选隐藏、板块分布排行榜隐藏、搜索框清空、表格切换为趋势榜。榜单按"连续被推荐月数"降序，每行展示股票代码/名称/行业/连续月数/累计家数/最新月家数/迷你折线图（走势形态直观可见）/展开控件。点击展开后按月降序展示每月家数与推荐券商（前3+省略）。搜索框输入股票代码或名称时全量重查并回第1页。从趋势切回股票/券商维度时月份选择器恢复、搜索清空、回第1页。
- **依赖**: plan-01（GET /trend-ranking API 契约）
- **关联验收标准**: [AC-01, AC-02, AC-03, AC-05, AC-06, AC-07, AC-08, AC-09, AC-10, AC-11, AC-12]
- **涉及架构模块**: ViewSwitcher（扩展）、BrokerRecommendPage（改造）、BrokerTrendRanking（新增）、Sparkline（新增）、useBrokerTrendRanking hook（新增）、brokerRecommendApi.getTrendRanking（新增）（架构 §4.2 / §6.2 / §7.2 / §9 Phase B）
- **前置条件**: plan-01 完成（GET /trend-ranking 端点可用）；09 前端组件范式可参照（ViewSwitcher.tsx / BrokerStockRanking.tsx / useBrokerRecommend.ts / BrokerRecommendPage.tsx / lib/api.ts 已读确认行号）
- **不在范围**: 后端趋势聚合（plan-01）；大图弹窗式走势图（首版用迷你折线图）；时间窗口切换（固定全窗口）；趋势行下钻单月排行（视图不联动）；券商维度趋势（不做）

## 文件清单

### 前端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| create | `web/src/components/broker-recommend-analysis/Sparkline.tsx` | 轻量 SVG 迷你折线图组件（ADR-6，约 30 行） |
| create | `web/src/components/broker-recommend-analysis/BrokerTrendRanking.tsx` | 趋势榜表格：四指标列 + Sparkline 列 + 行展开月度明细（预加载） |
| modify | `web/src/components/broker-recommend-analysis/ViewSwitcher.tsx` | OPTIONS 数组追加 trend 第三项 |
| modify | `web/src/hooks/useBrokerRecommend.ts` | 新增 useBrokerTrendRanking hook（范式照搬 useBrokerStockRanking） |
| modify | `web/src/lib/api.ts` | BrokerView 类型加 'trend'；brokerRecommendApi 新增 getTrendRanking；新增 TrendRankingItem 等 interface |
| modify | `web/src/components/broker-recommend-analysis/BrokerRecommendPage.tsx` | view==='trend' 分支：隐藏 MonthSelector/板块筛选/板块分布，渲染 BrokerTrendRanking，调用 useBrokerTrendRanking |

## 实现规格

### 前端部分

#### 1. 类型与 API 客户端（`web/src/lib/api.ts`）

范式参照 09 既有 `brokerRecommendApi`（`apiClient.get<{success, data}>(endpoint, queryObj)`，endpoint 不带 /v1，query snake_case）。

- `BrokerView` 类型：在现有 `'stock' | 'broker'` 基础上加 `'trend'`（架构 §7.2）。定位该 type 定义处（ViewSwitcher.tsx import 的 `BrokerView`），扩展联合类型。
- 新增 interface（对齐架构 §7.2，camelCase）：
  ```typescript
  interface TrendMonthPoint { month: string; brokerCount: number; }
  interface TrendMonthBroker { month: string; brokerCount: number; topBrokers: string[]; }
  interface TrendRankingItem {
    symbol: string;
    name: string | null;
    industries: string[];
    consecutiveMonths: number;
    cumulativeBrokerCount: number;
    latestMonthBrokerCount: number;
    monthlySeries: TrendMonthPoint[];
    monthlyBrokers: TrendMonthBroker[];
  }
  interface TrendRankingResponse {
    hasData: boolean;
    total: number;
    page: number;
    pageSize: number;
    items: TrendRankingItem[];
  }
  ```
- `brokerRecommendApi` 新增方法：
  ```typescript
  getTrendRanking(params: { search?: string; page?: number; pageSize?: number }) {
    return apiClient.get<{ success: boolean; data: TrendRankingResponse }>(
      '/broker-recommend-analysis/trend-ranking',
      {
        ...(params.search ? { search: params.search } : {}),
        page: params.page ?? 1,
        page_size: params.pageSize ?? 20,   // snake_case，FastAPI Query 不转 alias
      }
    );
  }
  ```

#### 2. SWR Hook（`web/src/hooks/useBrokerRecommend.ts`）

范式**照搬** `useBrokerStockRanking`（L66-96，`enabled` 控制 key null，`brokerRecommendApi.getXxx(query).then(res => res.data)`）。

```typescript
export interface UseBrokerTrendRankingParams {
  search?: string;
  page?: number;
  pageSize?: number;
  enabled?: boolean;  // false 时不发起请求（避免非激活视图无效请求触发 401）
}

export function useBrokerTrendRanking(params: UseBrokerTrendRankingParams) {
  const { enabled = true, ...query } = params;
  const key = enabled ? ['brokerTrendRanking', query] : null;
  const { data, error, isLoading, mutate } = useSWR<{
    success: boolean;
    data: TrendRankingResponse;
  }>(
    key,
    () =>
      brokerRecommendApi
        .getTrendRanking(query)
        .then((res) => res.data as unknown as { success: boolean; data: TrendRankingResponse }),
    SWR_OPTIONS
  );

  const body = data?.data ?? null;
  return {
    ranking: body ? { ...body, items: body.items as TrendRankingItem[] } : null,
    isLoading,
    isError: error,
    mutate,
  };
}
```

#### 3. Sparkline 组件（`web/src/components/broker-recommend-analysis/Sparkline.tsx`，新建，ADR-6）

轻量 SVG 自绘，约 30 行。**不复用 echarts**（趋势榜每页 20 行 × 20 echarts 实例渲染开销过大；sparkline 无交互、无坐标轴，SVG polyline 最轻量）。

```tsx
'use client'
import React from 'react'

export interface SparklineProps {
  values: number[]            // 数值序列（monthlySeries 的 brokerCount，已旧→新升序）
  width?: number              // 默认 80
  height?: number             // 默认 24
  color?: string              // 默认 currentColor（随主题）
  testId?: string             // 由调用方传入（如 `broker-trend-sparkline-${symbol}`），便于 E2E 定位
}

export default function Sparkline({ values, width = 80, height = 24, color = 'currentColor', testId }: SparklineProps) {
  if (!values || values.length === 0) {
    return <div style={{ width, height }} className="inline-block" data-testid={testId} />
  }
  const max = Math.max(...values, 1)   // 至少 1 防除零
  const min = Math.min(...values, 0)
  const range = max - min || 1
  const stepX = values.length > 1 ? width / (values.length - 1) : 0
  const points = values.map((v, i) => {
    const x = i * stepX
    const y = height - ((v - min) / range) * height
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
  return (
    <svg width={width} height={height} className="inline-block" data-testid={testId}>
      <polyline points={points} fill="none" stroke={color} strokeWidth={1.5} />
    </svg>
  )
}
```
单点场景（values.length===1）：stepX=0，points 为单点，polyline 退化为点（可加 `<circle>` 兜底，AC-11 单月数据）。实现时确认单点能正常渲染。

调用方（BrokerTrendRanking 表格行）渲染时传 `testId={`broker-trend-sparkline-${item.symbol}`}`，与 §4 data-testid 命名规范一致。

#### 4. BrokerTrendRanking 组件（`web/src/components/broker-recommend-analysis/BrokerTrendRanking.tsx`，新建）

范式参照 09 `BrokerStockRanking.tsx`（卡片内表格、展开机制、分页器、data-testid 命名）。

- Props：`{ items: TrendRankingItem[]; total; page; pageSize; isLoading; isError; onPageChange }`
- 表头：排名 / 代码 / 名称 / 行业 / 连续月数 / 累计家数 / 最新月家数 / 推荐走势（Sparkline）/ 操作
- 行折叠态：连续月数/累计家数/最新月家数为数字列；推荐走势列渲染 `<Sparkline values={item.monthlySeries.map(p => p.brokerCount)} />`（按 month 升序已是旧→新）；行业空显示"—"；name null 显示"—"
- 行展开（预加载，无 loading，AC-06）：`expandedSymbol` state，展开后 colSpan 渲染 monthlyBrokers（按月降序，新→旧），每月一行：月份 + 家数 + 券商（topBrokers 前3，超 3 显示"+X 家"）；某月 brokerCount=0 显示家数 0、券商"—"
- 分页器：total > pageSize 显示，data-testid `broker-trend-pagination`；≤20 隐藏（AC-08）
- data-testid：`broker-trend-table`（表格）/ `broker-trend-expand-{symbol}`（展开控件）/ `broker-trend-expand-content-{symbol}`（展开内容）/ `broker-trend-pagination`（分页器）/ `broker-trend-sparkline-{symbol}`（折线图，便于 E2E 定位）
- loading：`加载中…`；error：`加载失败，请重试`；items 空 + total 0：`所选月份暂无数据`（注：趋势视图固定全窗口，无"所选月"概念，但复用该空状态文案或改为"暂无趋势数据"由实现确认，保持与 09 一致优先）

#### 5. ViewSwitcher 扩展（`web/src/components/broker-recommend-analysis/ViewSwitcher.tsx`）

09 现有 `OPTIONS` 数组（L21-24）追加第三项：
```typescript
const OPTIONS: Array<{ value: BrokerView; label: string }> = [
  { value: 'stock', label: '股票维度' },
  { value: 'broker', label: '券商维度' },
  { value: 'trend', label: '推荐趋势' },   // 新增
]
```
渲染逻辑无需改动（已用 `OPTIONS.map` + `data-testid={`broker-view-${opt.value}`}` + `aria-pressed`），自动生成 `broker-view-trend`。

#### 6. BrokerRecommendPage 改造（`web/src/components/broker-recommend-analysis/BrokerRecommendPage.tsx`）

09 现有状态机（view/month/search/debouncedSearch/page/sectorType/sectorName）基础上增加 trend 分支。

- `handleViewChange`（L72-79，09 已有）已含 `setView + setSearch('') + setDebouncedSearch('') + setSectorName(undefined) + setPage(1)`，**无需改动**——切到 trend 自动清 search/sector/page（AC-10）。
- 调用趋势 hook：
  ```typescript
  const trendRanking = useBrokerTrendRanking({
    search: debouncedSearch || undefined,
    page,
    pageSize: DEFAULT_PAGE_SIZE,
    enabled: !hasNoData && view === 'trend',
  });
  ```
- 标题区（L191 MonthSelector 区域）：`view === 'trend'` 时不渲染 MonthSelector、不渲染 ViewSwitcher 的月份联动（MonthSelector 块整体条件渲染隐藏）
- 板块分布排行榜（L201 BrokerSectorRankings）：`view === 'trend'` 时不渲染（趋势不依赖单月板块分布）
- 排行榜 section（L208-293）：`view === 'trend'` 时不渲染板块筛选器（L234 BrokerSectorTypeSelector + SimpleSelect 块）；内容区三视图分支：
  ```tsx
  {view === 'stock' ? <BrokerStockRanking ... /> 
   : view === 'broker' ? <BrokerGroupList ... />
   : <BrokerTrendRanking 
       items={trendRanking.ranking?.items ?? []}
       total={trendRanking.ranking?.total ?? 0}
       page={page}
       pageSize={DEFAULT_PAGE_SIZE}
       isLoading={trendRanking.isLoading}
       isError={!!trendRanking.isError}
       onPageChange={handlePageChange}
     />}
  ```
- 标题文案：趋势视图时 h2 显示"持续推荐排行榜"（其他视图沿用 09 "卖方共识排行榜"/"券商推荐清单"）
- 搜索 placeholder：趋势视图 `搜索股票代码或名称`（与 stock 视图一致，因为趋势只搜股票）
- 搜索无结果提示（L275-292 区域）：增加 trend 分支 `view === 'trend' && trendRanking.ranking && items.length===0 && total===0` → "未找到匹配结果，请调整搜索词"
- 空状态（hasNoData，L156-178）：**无需改动**，复用 09 整页空状态（AC-12，趋势视图同样不展示）

### 前后端契约四件套校验结论（架构 §7.3 + 锚点 09 既有 api.ts）

- **路径拼接**：前端 endpoint `/broker-recommend-analysis/trend-ranking` × baseURL（已含 /api/v1）= `/api/v1/broker-recommend-analysis/trend-ranking`。✅ 与 plan-01 后端路由一致，无双前缀。
- **HTTP 方法存在性**：`apiClient.get` 继承自 `ApiClient`，携带 Authorization 头。✅
- **query 参数命名**：前端传 `page_size`（snake_case），后端 FastAPI Query 定义 `page_size`。✅ 与 09 `brokerRecommendApi.getStockRanking` 一致；**不**写 `pageSize`（FastAPI Query 不经 alias 转换，传错后端收不到）。
- **响应字段命名**：后端输出 camelCase（`consecutiveMonths`/`cumulativeBrokerCount`/`latestMonthBrokerCount`/`monthlySeries`/`monthlyBrokers`），前端 interface 与消费按 camelCase。✅ 后端 snake_case 语言层变量名（`consecutive_months` 等）经 `to_camel` + `_dict_to_camel` 转换。
- **响应包裹**：`{success: true, data: {...}}`，前端 SWR fetcher `.then(res => res.data)` 解一层 AxiosResponse → body，hook 内 `data?.data` 取业务对象（`ranking`）。✅ 与 09 既有 hook 一致。

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | lib/api.ts：BrokerView 加 'trend' + 新增 TrendRankingItem 等 4 interface + getTrendRanking 方法 | frontend | done | query 传 page_size（snake_case）；endpoint 不带 /v1 |
| 2 | useBrokerRecommend.ts：新增 useBrokerTrendRanking hook | frontend | done | 范式照搬 useBrokerStockRanking（enabled 控制 key null） |
| 3 | 新建 Sparkline.tsx（SVG 自绘迷你折线图） | frontend | done | ADR-6，不复用 echarts；处理单点场景 |
| 4 | 新建 BrokerTrendRanking.tsx（趋势榜表格 + Sparkline 列 + 行展开） | frontend | done | data-testid 命名见实现规格 #4；展开按月降序 |
| 5 | ViewSwitcher.tsx：OPTIONS 加 trend 项 | frontend | done | 渲染逻辑无需改，自动生成 broker-view-trend |
| 6 | BrokerRecommendPage.tsx：trend 分支（隐藏月份/板块筛选/板块分布，渲染 BrokerTrendRanking，调 trend hook，标题/placeholder 文案） | frontend | done | handleViewChange 无需改（09 已含 sectorName 重置） |
| 7 | E2E spec：趋势视图完整场景（切换/榜单/折线图/展开/搜索/分页/状态重置/单月/空状态） | frontend | done | TDD red→green；mock /trend-ranking；14/14 通过 |

## 验收标准

### 视图入口与状态验收（AC-01/10/12）

- [ ] AC-01 视图切换器出现"推荐趋势"第三选项，与股票/券商平级；切换到趋势视图时月份选择器隐藏、板块筛选隐藏、板块分布隐藏、搜索清空、回第1页
- [ ] AC-10 从趋势切回股票/券商维度时月份选择器恢复（默认最新月）、搜索清空、回第1页；反向切换同样清空+回第1页
- [ ] AC-12 数据从未同步时整页空状态"暂无券商金股数据，请联系管理员同步"（复用 09，09 hasNoData 分支仅渲染标题+空状态块，不渲染视图切换器，趋势视图同样不展示）

### 趋势榜展示验收（AC-02/03/05/07/11）

- [ ] AC-02 榜单跨全部已同步月份聚合，按"连续被推荐月数"降序；每行展示代码/名称/行业/连续月数/累计家数/最新月家数/推荐走势（Sparkline）；仅含至少被推荐过一次的股票
- [ ] AC-03 多级排序（连续月数↓→累计家数↓→最新月家数↓→代码↑）稳定，连续月数相同的股票按累计家数降序
- [ ] AC-05 每行 Sparkline 展示窗口内各月家数走势（横轴旧→新），含 0 家断档点，形态直观反映上升/下降/稳定
- [ ] AC-07 断档股（窗口中间某月无推荐）连续月数从最新月向前计到断档即停；累计家数与走势序列仍含断档前月份
- [ ] AC-11 仅一个已同步月份时正常展示，连续月数均为 1，Sparkline 显示为单点

### 展开与搜索分页验收（AC-06/08/09）

- [ ] AC-06 行展开后按月降序展示每月家数与推荐券商（前3+省略），某月无推荐家数 0 券商"—"；展开数据随列表预加载无 loading（无二次请求）
- [ ] AC-08 分页 total > 20 显示分页器，total 为全窗口+搜索条件下总数；≤20 隐藏分页器；搜索/切视图后回第1页
- [ ] AC-09 搜索框输入股票代码或名称时全量重查、仅保留匹配股票、回第1页、总数重算；无匹配"未找到匹配结果，请调整搜索词"；清空恢复完整榜单

### E2E / 集成验收

- [ ] E2E spec 覆盖：切到趋势视图（月份选择器隐藏）→ 看到榜单榜首（连续月数最大）→ Sparkline 渲染 → 展开月度明细 → 搜索过滤 → 分页 → 切回股票维度（月份选择器恢复、搜索清空）
- [ ] E2E red 阶段：实现前运行 spec 预期失败（趋势视图元素不存在）
- [ ] E2E green 阶段：实现后运行 spec 全部通过

### 降级回归验收（架构 §8.2）

- [ ] 单月数据（mock 仅一个月）下趋势榜正常展示，连续月数均为 1，Sparkline 单点不报错
- [ ] 整页空状态（mock hasData=false）：09 hasNoData 分支仅渲染标题+空状态块、不渲染视图切换器，趋势视图同样不展示、不发趋势请求

## 验证命令

```bash
cd web
# 类型检查
npx tsc --noEmit

# 构建
npm run build

# E2E（TDD red→green）
# red：实现前运行，预期趋势视图 spec 失败
npx playwright test -- tests/e2e/broker-recommend-trend.spec.ts
# green：实现后运行，全部通过
npx playwright test -- tests/e2e/broker-recommend-trend.spec.ts

# 全量 E2E 回归（确保趋势视图改动未破坏 09 既有双视图）
npx playwright test
```

E2E spec 新建：`web/tests/e2e/broker-recommend-trend.spec.ts`，mock helper 新建：`web/tests/e2e/helpers/mock-broker-recommend-trend-api.ts`（范式参照 09 既有 `mock-broker-recommend-api.ts`）。dev 端口 3100，mock 模式不依赖真实后端。

## 交接上下文

- **架构章节**: §4.2 模块职责（前端组件）、§6.2 视图切换链路、§7.2 最小 Schema（TrendRankingItem）、§9 Phase B
- **相关代码**:
  - `web/src/components/broker-recommend-analysis/ViewSwitcher.tsx`（L21-24 OPTIONS 数组扩展点）
  - `web/src/components/broker-recommend-analysis/BrokerRecommendPage.tsx`（L72-79 handleViewChange、L156-178 空状态、L191 MonthSelector、L201 板块分布、L208-293 排行榜 section）
  - `web/src/components/broker-recommend-analysis/BrokerStockRanking.tsx`（表格+展开+分页范式锚点）
  - `web/src/hooks/useBrokerRecommend.ts`（L66-96 useBrokerStockRanking 范式锚点）
  - `web/src/lib/api.ts`（brokerRecommendApi + BrokerView 类型）
  - `web/tests/e2e/broker-recommend-analysis.spec.ts` + `web/tests/e2e/helpers/mock-broker-recommend-api.ts`（E2E 范式锚点）
- **契约 / 数据对象**: TrendRankingItem（架构 §7.2，camelCase）；GET /trend-ranking（plan-01 §实现规格 #3，参数 search/page/page_size）
- **上游依赖方**: plan-01（GET /trend-ranking 端点）
- **复用声明调用细节**:
  - 复用 `apiClient.get`：`web/src/lib/api.ts`，baseURL 已含 /api/v1，携带 Authorization 头（getAuthHeaders）
  - 复用 `useSWR` + fetcher 范式：`useBrokerStockRanking`（L66-96），`SWR_OPTIONS`（revalidateOnFocus:false, dedupingInterval:30000）
  - 复用 `Pagination` 组件：`web/src/components/ui/Pagination.tsx`（09 BrokerStockRanking 已用）
  - 复用 `cn` 工具：`web/src/lib/utils`（ViewSwitcher 已用）
  - 复用 `DashboardLayout` / 侧边栏菜单：**无需改动**（09 已注册"券商每月荐股"菜单，趋势视图是同页第三视图）

## 风险与边界

- **执行顺序**: 按 Task 列表顺序（#1 api.ts 类型 → #2 hook → #3 Sparkline → #4 TrendRanking → #5 ViewSwitcher → #6 Page 改造 → #7 E2E）。Sparkline（#3）需先于 TrendRanking（#4，依赖 Sparkline）。
- **验证失败排查方向**: ①趋势视图不显示数据 → 检查 hook enabled 条件（`!hasNoData && view === 'trend'`）；②月份选择器在趋势视图未隐藏 → 检查 Page MonthSelector 块的条件渲染；③Sparkline 不渲染 → 检查 monthlySeries 是否为空数组、单点场景；④展开无数据 → 检查 monthlyBrokers 是否随列表预加载（plan-01 确认）；⑤camelCase 字段访问 undefined → 检查 interface 与后端输出字段名是否对齐（consecutiveMonths 非 consecutive_months）。
- **允许修改的额外文件**: `web/tests/e2e/broker-recommend-trend.spec.ts`（新建 E2E）、`web/tests/e2e/helpers/mock-broker-recommend-trend-api.ts`（新建 mock helper）
- **暂停条件**: ①plan-01 端点未就绪导致无法联调；②发现 09 既有 BrokerRecommendPage 状态机与架构链路 6.2 描述不符（阻塞，需回查 09 实际代码）
- **E2E 不适用说明**: 不适用——本功能为用户可观察的视图，必须 E2E 覆盖。
- **风险备注**: ①Sparkline 单点场景（AC-11 单月数据）需确认 SVG 能正常渲染，polyline 单点退化需兜底；②视图切换的显隐逻辑较多（月份选择器/板块筛选/板块分布/标题/placeholder），E2E 需覆盖切换前后状态；③改动 BrokerRecommendPage 是 09 核心页面，需全量 E2E 回归确保未破坏既有双视图。

### 前端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| 数据从未同步 | 复用 09 整页空状态（hasNoData）：09 hasNoData 分支仅渲染标题+空状态块、不渲染视图切换器，趋势视图同样不展示、不发趋势请求（AC-12） | done |
| 仅一个已同步月份 | 趋势榜正常展示，连续月数均为 1，Sparkline 单点（AC-11） | done |
| Sparkline 单点（values.length===1） | polyline 退化兜底：单点场景渲染 `<circle>` 确保可见（AC-11，TC-2.13 验证） | done |
| 搜索无匹配 | 表格区"未找到匹配结果，请调整搜索词"，清空恢复（AC-09，TC-2.12 验证） | done |
| 趋势榜加载失败 | 表格区"加载失败，请重试"（isError 分支渲染） | done |
| 展开项某月无券商 | 该月家数 0、券商列"—"（AC-06，TC-2.9 验证） | done |
| 切到/切离趋势视图状态错乱 | handleViewChange 统一清 search/sectorName + 回第1页；显隐由 view==='trend' 控制（AC-01/10，TC-2.2/2.3 验证） | done |
| name/industries 缺失 | name null 显示"—"，industries 空显示"—"（与 09 一致） | done |
