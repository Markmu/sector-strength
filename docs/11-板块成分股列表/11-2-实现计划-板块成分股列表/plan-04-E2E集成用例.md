---
feat_id: "plan-04"
title: "E2E 集成用例"
dimension: frontend
phase: 3
status: draft
depends_on: ["plan-02", "plan-03"]
---

# plan-04: E2E 集成用例

## 功能概要

- **目标**: 编写 Playwright E2E spec 与 mock helpers，覆盖 AC-01~AC-07 全流程，遵循 E2E-TDD（先 red 后 green）；产出 e2e 用例文档作为测试设计基线。
- **完成后可观察结果**: 运行 `pnpm exec playwright test tests/e2e/sector-stocks.spec.ts` 全部通过（green）；实现前运行同一 spec 全部失败（red 证据有效）；spec 覆盖成分股加载、强度/市值排序、分页、加载失败重试、空数据、点击下钻个股页七个场景；e2e 用例文档 `docs/e2e/11-e2e-用例-板块成分股列表.md` 作为测试设计单一来源。
- **依赖**: plan-02（组件与 data-testid）、plan-03（个股落地页）
- **关联验收标准**: [AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-07]
- **涉及架构模块**: 全流程集成（架构 §6.1 链路 L1 + §6.2 链路 L2）
- **前置条件**: plan-02/03 的 data-testid 已固定（见各组件实现规格）；dev server 可启动
- **不在范围**: 真实后端联调（E2E 走 mock 模式）；性能自动化测试（性能目标人工确认）

## 文件清单

### 前端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| create | `web/tests/e2e/sector-stocks.spec.ts` | 成分股全流程 E2E spec |
| create | `web/tests/e2e/helpers/mock-sector-stocks-api.ts` | mock helpers + test data factory |
| reference | `docs/e2e/11-e2e-用例-板块成分股列表.md` | E2E 测试用例文档（已随本计划先生成，本功能执行时引用并按需更新） |

## 实现规格

### 前端部分

#### 1. mock helpers（web/tests/e2e/helpers/mock-sector-stocks-api.ts）

仿 `mock-fund-crowd-api.ts` 范式。类型在 helpers 内就地定义（mock 不从生产代码 import 类型，避免测试与生产耦合），字段 snake_case 对齐后端真实输出：

```ts
// 匹配 API path（pathname 精确匹配，参照 matchApiPath）
export function matchSectorStocksPath(page: Page): ... 

// mock 成分股列表（外层 { success: true, data: {...} }）
export async function mockSectorStocks(page: Page, data: SectorStocksData): Promise<void>
// mock 空成分股（total=0）
export async function mockSectorStocksEmpty(page: Page): Promise<void>
// mock 成分股请求失败（500）
export async function mockSectorStocksError(page: Page): Promise<void>
// mock 个股详情（用于 AC-07 下钻）
export async function mockStockDetail(page: Page, data: StockDetailItem): Promise<void>

// test data factory（camelCase 命名响应字段 → 注意：本接口 snake_case，factory 按 snake_case 造数）
export function createTestSectorStocks(opts?: { total?: number; pageSize?: number }): SectorStocksData
export function createTestStockDetail(): StockDetailItem
```

**关键约定**：
- test data 字段用 **snake_case**（与后端实际输出一致：id/symbol/name/current_price/market_cap/strength_score/trend_direction）
- 外层包裹 `{ success: true, data: { items, total, page, page_size, total_pages } }`
- mock 安装用 `route.fulfill()` + `route.fallback()` 防 LIFO 短路（参照 mock-shareholder-analysis-api.ts）
- pathname 精确匹配成分股接口：`/api/v1/sectors/{id}/stocks`；个股接口：`/api/v1/stocks/{id}`

createTestSectorStocks 造数示例（默认 3 条，按 strength_score 降序）：
- 600519 贵州茅台 strength_score=92 trend=1 price=1680 market_cap=2.1e12
- 000858 五粮液 strength_score=88 trend=1 price=156 market_cap=6.1e11
- 000568 泸州老窖 strength_score=85 trend=-1 price=220 market_cap=3.2e11

#### 2. spec（web/tests/e2e/sector-stocks.spec.ts）

仿 `fund-crowd-analysis.spec.ts`：复用 authedPage fixture（自定义 JWT，localStorage accessToken + Cookie access_token，role=user）。页面地址 `/dashboard/sector-analysis/1`（用任意存在的板块 id，mock 拦截）。

**需额外 mock 的接口**：板块详情页本身会请求 strength-history 与 ma-history 图表数据（避免图表请求未 mock 导致 401 重定向），需安装最小 mock 或参照 shareholder-analysis 的全量 mock 安装策略。同时 mock 成分股接口。

测试场景（对应 e2e 用例文档 TC）：

| TC | 场景 | AC | 关键断言 |
| --- | --- | --- | --- |
| TC-1.1 | 默认加载成分股按强度分降序 | AC-01 | `sector-stocks-table` 可见；3 行；首行 600519 strength_score=92 |
| TC-1.2 | 点击强度分表头切换升序 | AC-02 | 点击 `sector-stocks-sort-strength_score`；首行变为最低分；箭头 ▲ |
| TC-1.3 | 点击市值表头降序 | AC-03 | 点击 `sector-stocks-sort-market_cap`；首行变最高市值；点击代码列无变化 |
| TC-1.4 | 分页+每页条数 | AC-04 | 造 >20 条数据；点第 2 页；切 pageSize=50 从第 1 页开始 |
| TC-1.5 | 加载失败重试 | AC-05 | mockError；显示重试按钮；点击重试后（切成功 mock）数据出现 |
| TC-1.6 | 空数据 | AC-06 | mockEmpty；显示 `sector-stocks-empty` 空态；无表格无分页器 |
| TC-1.7 | 点击下钻个股页 | AC-07 | 点击首行；URL 变 `/dashboard/stock-analysis/{id}`；`stock-info-card` 可见含 600519 |

#### 3. e2e 用例文档（docs/e2e/11-e2e-用例-板块成分股列表.md）

参照 `docs/e2e/08-e2e-用例-基金扎堆股票分析.md` 格式：frontmatter（source/feat_id/created）+ 资产现状（Playwright projects/workers/baseURL/认证 fixture/外层契约/dev server）+ 每个 FEAT 的 TC 表（场景/类型/前置/步骤/断言/目标 spec）。本需求只一个功能集合，FEAT 章节按 plan-02/03 拆分。

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | 创建 mock-sector-stocks-api.ts（helpers + factory） | frontend | todo | snake_case 造数，{success,data} 包裹 |
| 2 | 创建 sector-stocks.spec.ts（authedPage + 7 个 TC） | frontend | todo | 含图表接口最小 mock |
| 3 | 创建 e2e 用例文档 11-e2e-用例 | frontend | todo | 测试设计基线 |
| 4 | 运行 red（实现前预期失败）保存证据 | frontend | todo | 证据存 docs/e2e/evidence/ |
| 5 | plan-02/03 实现后运行 green 通过 | frontend | todo | 全部 TC green |

## 验收标准

### E2E 验收

- [ ] AC-01~AC-07 各有对应 TC 覆盖（见规格 §2 场景表）
- [ ] red 阶段：plan-02/03 实现前运行 spec，所有 TC 预期失败，证据存 docs/e2e/evidence/
- [ ] green 阶段：plan-02/03 实现后运行 spec，所有 TC 通过
- [ ] mock helpers 字段为 snake_case，外层 `{success:true, data:{...}}` 包裹
- [ ] authedPage fixture 正确注入（role=user 可过 /dashboard 守卫）

### 构建验收

- [ ] `pnpm exec playwright test tests/e2e/sector-stocks.spec.ts` 全部 green
- [ ] `pnpm type-check` 通过

## 验证命令

```bash
cd web
# 启动 dev server（新终端）
pnpm dev
# red（实现前）
pnpm exec playwright test tests/e2e/sector-stocks.spec.ts
# green（实现后）
pnpm exec playwright test tests/e2e/sector-stocks.spec.ts
```

## 交接上下文

- **架构章节**: §6.1 链路 L1、§6.2 链路 L2、§3.3 状态机
- **相关代码**: 范式 `web/tests/e2e/fund-crowd-analysis.spec.ts`、`web/tests/e2e/helpers/mock-fund-crowd-api.ts`、`web/tests/e2e/helpers/mock-shareholder-analysis-api.ts`（matchApiPath + fallback 范式）、data-testid 来自 plan-02/03 实现规格
- **契约 / 数据对象**: mock factory 造 SectorStocksData / StockDetailItem（snake_case）
- **下游消费方**: 无（本功能为验证层，是 DAG 叶子）

## 风险与边界

- **执行顺序**: 本功能 Task 1-3 可在 plan-02/03 实现前完成（产出 red 用例与文档）；Task 4（red）须在 plan-02/03 实现前运行；Task 5（green）须在 plan-02/03 完成后运行。即 E2E-TDD：先 red 后 green
- **验证失败排查方向**: 401 重定向优先检查图表接口 mock 是否齐全（板块详情页会请求 strength-history/ma-history）；TC 无反应检查 data-testid 是否与 plan-02/03 实现一致；mock 不命中检查 pathname 匹配与 fallback
- **允许修改的额外文件**: 若运行时发现板块详情页图表接口未 mock 导致 401，可补充图表 mock 到 helpers（属合理范围）
- **暂停条件**: 若发现 plan-02/03 实际实现的 data-testid 与本 spec 预期不一致，停止并回写本 spec 对齐实现（实现为准）
- **E2E 不适用说明**: 不适用（本功能即 E2E）
- **风险备注**: 板块详情页已有图表 hook，E2E 进入页面会触发图表请求，须 mock 否则 401 重定向到 /login 使 fixture 失效

### 前端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| 图表接口未 mock 导致 401 | helpers 补充 strength-history/ma-history 最小 mock | todo |
| mock factory 字段命名错误（误用 camelCase） | 严格按 snake_case 造数（与后端输出一致） | todo |
| red 证据未保存 | red 运行后保存输出到 docs/e2e/evidence/ | todo |
