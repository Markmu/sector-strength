---
feat_id: "plan-01"
title: "契约层类型与 API 修正"
dimension: frontend
phase: 1
status: draft
depends_on: []
---

# plan-01: 契约层类型与 API 修正

## 功能概要

- **目标**: 把前端 `sectorsApi.getSectorStocks` 的参数从错误的 `skip/limit` 修正为后端实际契约 `page/page_size/sort_by/sort_order`，并新增匹配后端返回的 TypeScript 类型，为 plan-02/03 提供类型安全的契约层。
- **完成后可观察结果**: `getSectorStocks` 调用时能正确传入 page/page_size/sort_by/sort_order 并被后端识别（不再静默失效）；返回类型完整描述成分股列表项与分页结构，IDE 中类型推导正确；类型可被 useSectorStocks hook 和组件直接引用；`pnpm build` 与 `pnpm type-check` 通过。
- **依赖**: 无
- **关联验收标准**: [AC-01, AC-02, AC-03, AC-04]（契约层为这些 AC 的前置，本功能不直接产生用户可观察行为，可观察验收由 plan-02 承接）
- **涉及架构模块**: sectorsApi.getSectorStocks、契约类型（架构 §4.2、§7.2、§7.3）
- **前置条件**: 无
- **不在范围**: hook 实现、组件实现、个股页（分别由 plan-02/03 承接）

## 文件清单

### 前端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| modify | `web/src/lib/api.ts` | 修正 getSectorStocks 参数与返回类型（第 191-192 行） |
| modify | `web/src/types/sectorTypes.ts` | 新增 SectorStockItem / SectorStocksData / SectorStocksResponse / SectorStocksTableState 类型 |

## 实现规格

### 前端部分

#### 1. 新增契约类型（web/src/types/sectorTypes.ts）

在文件末尾追加以下类型（对齐架构 §7.2，对齐后端 sectors.py:309-318 实际返回字段，snake_case）：

```ts
// 成分股列表项（对齐后端 GET /sectors/{id}/stocks 返回的 items 字段）
export interface SectorStockItem {
  id: string
  symbol: string
  name: string
  current_price: number | null
  market_cap: number | null
  strength_score: number | null
  trend_direction: number | null  // 1=上升, 0=横盘, -1=下降
}

// 分页响应 data（对齐后端 PaginatedData）
export interface SectorStocksData {
  items: SectorStockItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

// API 整体响应（对齐既有 { success, data } 包裹）
export interface SectorStocksResponse {
  success: boolean
  data: SectorStocksData
}

// 排序/分页 UI 状态
export interface SectorStocksTableState {
  sort_by: 'strength_score' | 'market_cap'
  sort_order: 'asc' | 'desc'
  page: number
  page_size: 20 | 50 | 100
}
```

> 不修改既有的 `SectorStock`（web/src/types/index.ts:123-127，字段 sector_id/stock_id/weight 与后端不符），新增上述类型作为成分股列表的契约类型。UI 渲染约定（最新价两位小数、强度分整数）由 plan-02 在组件层实现，不在类型层约束。

#### 2. 修正 getSectorStocks（web/src/lib/api.ts:191-192）

当前实现（错误）：

```ts
getSectorStocks: (sectorId: number, params?: { skip?: number; limit?: number }) =>
  apiClient.get<any[]>(`/sectors/${sectorId}/stocks`, params),
```

修正为：

```ts
getSectorStocks: (
  sectorId: number,
  params?: { page?: number; page_size?: number; sort_by?: string; sort_order?: string }
) =>
  apiClient.get<SectorStocksResponse>(`/sectors/${sectorId}/stocks`, params),
```

需在 api.ts 顶部 import `SectorStocksResponse` 类型（从 `@/types/sectorTypes`）。

#### 四件套契约校验

- **路径拼接**：endpoint `/sectors/${sectorId}/stocks` × apiClient baseURL `${API_BASE_URL}/api/v1` = `http://localhost:8000/api/v1/sectors/{id}/stocks`。endpoint 不重复 baseURL 已含的 `/api/v1` 前缀，无双前缀。✓
- **HTTP 方法存在性**：apiClient.get 方法存在于 ApiClient 类（api.ts），携带 getAuthHeaders 鉴权。后端路由 `@router.get("/{sector_id}/stocks")`。三方一致。✓
- **query 参数命名**：前端传 `page/page_size/sort_by/sort_order`（snake_case），与后端 Query 参数 `page/page_size/sort_by/sort_order`（sectors.py:257-260）完全一致。注意：响应字段别名转换只作用于响应体，query 参数保持 snake_case。✓
- **响应字段命名**：后端输出 snake_case（items 内 id/symbol/name/current_price/market_cap/strength_score/trend_direction），前端 SectorStockItem 类型同 snake_case，组件字段访问与输出一致。✓

#### 序列化与包裹

- 后端响应外层 `{success, data}`，data 为 PaginatedData。apiClient 返回 `ApiResponse<SectorStocksResponse>`，业务数据在 `.data`；下游消费需 `.data.data` 取 items/分页元信息（参考 useSectorStrengthHistory:70-73 的解包模式）。
- strength_score/current_price/market_cap 后端为 number 或 null，无高精度数值序列化字符串问题。

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | 在 sectorTypes.ts 追加 4 个契约类型 | frontend | todo | 见实现规格 §1 |
| 2 | 修正 api.ts getSectorStocks 参数与返回类型，补 import | frontend | todo | 见实现规格 §2 |
| 3 | type-check + build 验证 | frontend | todo | `pnpm type-check && pnpm build` 通过 |

## 验收标准

### 契约层验收

- [ ] `getSectorStocks` 参数签名为 `{ page?, page_size?, sort_by?, sort_order? }`，返回类型为 `ApiResponse<SectorStocksResponse>`
- [ ] `SectorStockItem` 字段与后端 sectors.py:309-318 返回字段一一对应（id/symbol/name/current_price/market_cap/strength_score/trend_direction）
- [ ] 四件套契约校验全部通过（路径拼接/方法/query 命名/响应字段命名）
- [ ] `pnpm type-check` 通过
- [ ] `pnpm build` 通过

> 本功能为纯契约层，无用户可观察行为，不单独写 E2E。E2E 不适用理由：本功能只产出类型定义和 API 客户端方法签名，无可点击的 UI 路径，可观察验收由 plan-02/03 承接并在 plan-04 覆盖 E2E。

## 验证命令

```bash
cd web
pnpm type-check
pnpm build
```

## 交接上下文

- **架构章节**: §4.2 模块职责（sectorsApi.getSectorStocks 修正）、§7.2 推荐最小 Schema、§7.3 API 边界、ADR-4
- **相关代码**: `web/src/lib/api.ts:191`、`web/src/types/sectorTypes.ts`、后端锚点 `server/src/api/v1/sectors.py:254-324`
- **契约 / 数据对象**: `SectorStockItem`、`SectorStocksData`、`SectorStocksResponse`、`SectorStocksTableState`
- **下游消费方**: plan-02（useSectorStocks hook 引用 SectorStocksResponse；组件引用 SectorStockItem/SectorStocksTableState）、plan-03（StockAnalysisPage 引用相关字段）

## 风险与边界

- **执行顺序**: 按 Task 列表顺序执行（先类型后 api 修正，因 api 修正依赖类型 import）
- **验证失败排查方向**: 若 type-check 报错，优先检查 import 路径（`@/types/sectorTypes`）与类型导出是否正确；若 build 报错，检查是否有其它文件仍引用旧的 skip/limit 参数（经核实当前无调用方）
- **允许修改的额外文件**: 无（仅 api.ts 与 sectorTypes.ts）
- **暂停条件**: 若发现既有代码已有调用 getSectorStocks 的地方（理论上无，但需复核），停止并报告，避免破坏性改动
- **E2E 不适用说明**: 本功能为纯类型/API 客户端契约层，无 UI 路径，E2E 由 plan-04 覆盖
- **风险备注**: ADR-4 已核实该方法当前无调用方（前端从未真正使用），修正无破坏性影响

### 前端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| sort_by 传入非白名单值 | 本功能不在 api 层限制，由 plan-02 组件层白名单限制（SectorStocksTableState 类型已约束 sort_by 联合类型） | todo |
| page_size 超过后端上限 100 | 由 plan-02 组件层约束可选值为 20/50/100 | todo |
