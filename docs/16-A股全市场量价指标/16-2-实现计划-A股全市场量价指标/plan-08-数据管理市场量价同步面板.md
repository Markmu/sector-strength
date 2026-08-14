---
feat_id: "plan-08"
title: "数据管理市场量价同步面板"
dimension: frontend
phase: 3
status: done
depends_on: ["plan-05", "plan-07"]
---

# plan-08: 数据管理市场量价同步面板

## 功能概要

- **目标**: 数据管理页新增"市场量价"Tab，新建 `MarketMetricsSyncPanel`：起止日期输入与前端校验、调用专用创建入口、`useTaskStatus` 2s 轮询进度与三类日期计数、任务历史记录分页、从 `result.dateResults` 展示选中成功/失败日期的应参与/当日行情/全天停牌/最终参与四类计数与失败原因、同类任务互斥交互。
- **完成后可观察结果**: 管理员打开数据管理页切到"市场量价"Tab，选择合法起止日点"开始同步"后按钮进入运行态，面板每 2 秒刷新当前处理日期与进度；结束后显示成功/跳过/失败三类计数，点开某失败日期能看到四类完整性计数与截断的失败原因。起止倒置或结束日在未来时前端直接拦截；已有同类任务运行时创建按钮禁用并提示；同步记录列表按时间倒序可翻页。
- **依赖**: plan-05（POST /api/v1/admin/init/market-metrics + result 契约）；plan-07（`marketMetricsTypes.ts` 与 `api.ts` 同文件顺序编辑，避免并行冲突）
- **关联验收标准**: [AC-02]（同步面板观测）、[AC-07]（失败日期计数与原因展示）、[AC-10]（前端日期校验）、[AC-11]（前端互斥与权限入口）
- **涉及架构模块**: 数据管理同步面板（架构 §4.2 模块 6）
- **前置条件**: plan-05/07 已合并；`pnpm dev` 与 Playwright 可用。
- **不在范围**: 后端改动；首页面板（plan-07 已交付）。

## 文件清单

### 前端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| modify | `web/src/types/marketMetricsTypes.ts` | 新增 MarketMetricsTaskResult / MarketMetricsDateResult |
| modify | `web/src/hooks/useTaskStatus.ts` | TaskData 增加 `result?: MarketMetricsTaskResult \| null` |
| modify | `web/src/lib/api.ts` | adminApi 增加 `initMarketMetrics` |
| create | `web/src/components/market-metrics/MarketMetricsSyncPanel.tsx` | 同步面板 |
| modify | `web/src/app/dashboard/admin/data/page.tsx` | 新增 'market-metrics' Tab |
| create | `web/tests/market-metrics/MarketMetricsSyncPanel.test.tsx` | jest 组件测试 |
| create | `web/tests/e2e/helpers/mock-market-metrics-sync-api.ts` | E2E mock helper |
| create | `web/tests/e2e/market-metrics-sync.spec.ts` | Playwright spec（red/green） |
| create | `docs/e2e/16-e2e-用例-市场量价同步面板.md` | E2E 用例文档 |

## 实现规格

### 前端部分

#### 1. 类型与 Hook 扩展（架构 §7.2）

- `marketMetricsTypes.ts` 追加：`MarketMetricsDateResult { tradeDate: string; status: 'success' | 'failed'; expected: number; daily: number; suspended: number; final: number; reason?: string }`、`MarketMetricsTaskResult { successCount: number; skippedCount: number; failedCount: number; dateResults: MarketMetricsDateResult[]; unprocessedDates: string[] }`——result 键全 camelCase（plan-05 handler 构造时即 camelCase，`to_dict()` 原样透传），前端**直消费、无二次键转换**
- `useTaskStatus.ts` 的 `TaskData` 接口追加 `result?: MarketMetricsTaskResult | null`（后端 `to_dict()` 已含透传的 result，plan-04 交付）

#### 2. API 客户端（四件套校验）

```ts
// adminApi 内追加
initMarketMetrics: (start_date: string, end_date: string) =>
  adminApiClient.post<{ task_id: string }>('/admin/init/market-metrics', { start_date, end_date }),
```

endpoint `/admin/init/market-metrics` × AdminApiClient baseURL `${API_BASE_URL}/api/v1` = `/api/v1/admin/init/market-metrics`（与后端挂载一致）；POST 带 Authorization；**body 字段 snake_case（user_input），与后端 Pydantic payload 一致**；响应经 AdminApiClient 提取 `json.data` → `{task_id}`（snake_case，与既有 `initLimit`/`initIndexHistory` 同款）。

#### 3. MarketMetricsSyncPanel（架构 §4.2 模块 6、§6.4.5）

范式严格对齐 `IndexSyncPanel.tsx`（同目录最近交付的同步面板）：

- **创建区**：两个 date input（默认最近 30 个自然日）+ "开始同步"按钮
  - 前端校验（AC-10）：`start > end` / `end > 今天` / 跨度 > 10 年 → 按钮禁用 + 行内错误提示，不发请求
  - 点击 → `adminApi.initMarketMetrics(start, end)` → 拿 `task_id` 存 state → `useTaskStatus(taskId, { pollInterval: 2000 })` 轮询
  - 互斥（AC-11）：`isRunning`（pending/running 中）时按钮禁用并提示"已有市场量价任务在运行"；后端二次拒绝（success=false）时展示 message——前端禁用不承担一致性
- **进度区**：running 时显示 `progress/total`（交易日口径）+ 当前日期 + 百分比；completed/failed/cancelled 终态显示 `result.successCount/skippedCount/failedCount` 三类计数（页面同时显示三类日期计数，§6.2.7）
- **日期结果区**：`result.dateResults` 列表（默认最近在前）；点击某日期展开四类计数（应参与 expected / 当日日行情 daily / 全天停牌 suspended / 最终参与 final）与 `reason`（截断展示，AC-07）；`unprocessedDates` 非空时单独提示"未处理日期"
- **记录区**：SWR + `fetcher` 拉 `/api/v1/admin/tasks?task_types=sync_market_metrics&page=1&page_size=20`（key 含 `/api/v1` 前缀，fetcher 拼 `NEXT_PUBLIC_API_URL`，同 IndexSyncPanel 的 `RECORDS_SWR_KEY` 模式）；分页按钮；行显示 taskId/状态/progress/created
- 取消：复用 `useTaskStatus` 返回的 `cancel()`（后端 pending 立即 cancelled、running 写请求标记，UI 显示"取消中"直至终态）
- 失败重试：终态 failed → "重新同步"按钮重开创建区（同参数预填）

#### 4. 数据管理页 Tab（架构 §2.1 末条）

`data/page.tsx`：`DataTab` 联合类型追加 `'market-metrics'`；nav 增加按钮 `data-testid="tab-market-metrics"`（文案"市场量价"）；内容区 `{activeTab === 'market-metrics' && <MarketMetricsSyncPanel />}`（L14-20 / L36-105 / L107-113 三处对称扩展）。

#### 5. E2E（red → green）

- 用例文档覆盖：Tab 进入、合法创建→轮询→终态计数、前端校验四类拒绝、互斥禁用、失败日期四类计数展开、记录分页
- `mock-market-metrics-sync-api.ts`：mock `POST /api/v1/admin/init/market-metrics`（成功/互斥拒绝/校验拒绝）与 `GET /api/v1/admin/tasks*`（running→completed 状态序列 + result fixture）
- red 证据先于实现采集，green 证据实现后采集，存 `docs/e2e/evidence/plan-08-e2e-{red|green}-{YYYYMMDD}.md`

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | 类型扩展 + TaskData.result 字段 | frontend | done | camelCase 契约 |
| 2 | adminApi.initMarketMetrics | frontend | done | snake_case body |
| 3 | MarketMetricsSyncPanel 创建/轮询/进度/结果区 | frontend | done | 2s 轮询 + 三类计数 |
| 4 | dateResults 四类计数与失败原因展开 | frontend | done | unprocessedDates 提示 |
| 5 | 记录区分页与互斥交互 | frontend | done | fetcher SWR |
| 6 | data/page.tsx Tab 接入 | frontend | done | tab-market-metrics |
| 7 | jest 组件测试 | frontend | done | tests/market-metrics/ |
| 8 | E2E 用例 + mock + spec（red 证据） | frontend | done | 先 red 后实现 |

## 验收标准

### 前端验收

- [ ] AC-10 前端拦截：起止倒置 / 未来结束日 / 跨度 >10 年三种输入按钮禁用且不发请求（jest + E2E 断言网络零调用）
- [ ] AC-02 面板闭环：创建成功 → 轮询显示进度与当前日期 → 终态显示 success/skipped/failed 三类计数（E2E 用状态序列 mock 断言）
- [ ] AC-07 展开某失败日期显示 expected/daily/suspended/final 四类计数与截断原因；`unprocessedDates` 非空时有独立提示
- [ ] AC-11 互斥：已有 pending/running 时按钮禁用 + 提示；后端拒绝时展示返回 message；非管理员无入口（页面本身在 admin 布局内）
- [ ] 记录列表按 createdAt 倒序、分页可用、状态列正确渲染五态
- [ ] 取消：running 中点取消 → "取消中"过渡 → 终态 cancelled 后释放按钮
- [ ] `pnpm exec tsc --noEmit`、`pnpm build`、jest、E2E 全部通过
- [ ] E2E-TDD：`market-metrics-sync.spec.ts` red/green 证据齐备，存 `docs/e2e/evidence/plan-08-e2e-{red|green}-{date}.md`

## 验证命令

```bash
cd web

# 1. 类型与构建
pnpm exec tsc --noEmit && pnpm build

# 2. 组件测试
pnpm test -- tests/market-metrics/MarketMetricsSyncPanel.test.tsx

# 3. E2E（mock 模式）
pnpm test:e2e -- tests/e2e/market-metrics-sync.spec.ts

# 4. 既有面板回归（确认 plan-07 未被同文件编辑破坏）
pnpm test -- tests/market-metrics/
pnpm test:e2e -- tests/e2e/market-metrics-panel.spec.ts
```

## 交接上下文

- **架构章节**: §4.2 模块 6、§6.2.7-8、§7.2-7.3、§8.2
- **相关代码**: `web/src/components/index-monitor/IndexSyncPanel.tsx`（同步面板范式：互斥 isAnySyncRunning L488/L535、RECORDS_SWR_KEY L65、useTaskStatus 用法）、`web/src/hooks/useTaskStatus.ts`（TaskData L14-28）、`web/src/app/dashboard/admin/data/page.tsx`（Tab 枚举 L14-20）、`web/src/lib/api.ts`（adminApi L550+、initIndexHistory L626 / initLimit L631 范式）
- **契约 / 数据对象**: `MarketMetricsTaskResult`（plan-05 §2 step6 约定：handler 构造 result 时键全 camelCase，`to_dict()` 原样透传不经 `_dict_to_camel`）——本面板直消费，与 plan-05/plan-04 三方契约一致
- **下游消费方**: 无（终端展示功能）
- **实现级补充项**: `unprocessedDates` 展示服务于 AC-07 恢复语义，非新造 AC

## 风险与边界

- **执行顺序**: 按 Task 列表顺序执行；与 plan-07 共享 `marketMetricsTypes.ts`/`api.ts`，必须串行在 plan-07 之后
- **验证失败排查方向**: E2E mock 未命中查 URL 与 page 参数；轮询不推进查 useTaskStatus 的 enabled/taskId 传值
- **允许修改的额外文件**: 无
- **暂停条件**: 若 plan-05 实际交付的 result 键与 camelCase 契约不符导致类型冲突，暂停并回改 plan-05 写入侧（不得在前端放宽类型为 any 或私加转换层）
- **风险备注**: result 可能很大（250+ 日 × 字段）——列表用虚拟滚动或仅渲染最近 50 条 + 展开懒加载，避免一次性 DOM 爆炸

### 前端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| 创建请求被后端互斥拒绝 | 展示 message，按钮保持可用态 | done |
| 轮询期间网络错误 | isError 展示 + refetch 恢复 | done |
| result 为 null（任务未终态） | 隐藏日期结果区 | done |
| unprocessedDates 非空 | 独立提示块 | done |
| 空记录列表 | 空态文案 | done |
