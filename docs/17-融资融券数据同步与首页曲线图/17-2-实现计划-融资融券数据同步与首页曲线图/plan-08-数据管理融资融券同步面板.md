---
feat_id: "plan-08"
title: "数据管理融资融券同步面板"
dimension: frontend
phase: 3
status: done
depends_on: ["plan-05", "plan-07"]
---

# plan-08: 数据管理融资融券同步面板

## 功能概要

- **目标**: 数据管理页新增"融资融券"Tab，新建 `web/src/components/market-margin/MarginSyncPanel.tsx`（仿 MarketMetricsSyncPanel.tsx 679 行，裁剪两融不适用的四类计数）：起止日期输入（默认近 1 年）与前端校验、调用 `adminApi.initMargin`（plan-05 专用创建入口）、`useTaskStatus` 2s 轮询进度、成功/跳过/失败三类计数、逐日 `dateResults` 展开（tradeDate/status/截断 reason）与 `unprocessedDates` 提示、`sync_market_margin` 历史任务记录分页、同类任务互斥交互；配套 jest 组件测试与 Playwright E2E（**完整 red/green 循环**）。
- **完成后可观察结果**: 管理员打开数据管理页切到"融资融券"Tab，选择合法起止日（默认近 1 年）点"开始同步"后按钮进入运行态，面板每 2 秒刷新当前进度；结束后显示成功/跳过/失败三类计数，点开某日期能看到状态与截断的失败原因（两融无四类完整性计数）。起止倒置/未来日/超 10 年时前端直接拦截不发请求；已有同类任务运行时按钮禁用并提示；同步记录列表按时间倒序可翻页。
- **依赖**: plan-05（POST /api/v1/admin/init/margin + 互斥 message 契约）；plan-07（`marginTypes.ts` 与 `api.ts` 同文件顺序编辑，避免并行冲突）
- **关联验收标准**: [AC-7]（同步面板：进度/明细/历史记录）
- **涉及架构模块**: 数据管理同步面板（spec REQ-8，对应 16 期 plan-08 的 MarketMetricsSyncPanel）
- **前置条件**: plan-05/07 已合并；`pnpm dev` 与 Playwright 可用。
- **不在范围**: 后端改动；首页面板（plan-07 已交付）。

## 文件清单

### 前端维度

| 动作 | 路径 | 说明 |
| --- | --- | --- |
| modify | `web/src/hooks/useTaskStatus.ts` | TaskData 增加 `result?: MarginTaskResult \| null` |
| modify | `web/src/lib/api.ts` | adminApi L649 旁增加 `initMargin` |
| create | `web/src/components/market-margin/MarginSyncPanel.tsx` | 同步面板 |
| modify | `web/src/app/dashboard/admin/data/page.tsx` | L15-22 DataTab 加 `'market-margin'`；L106-116 加 tab 按钮；L127 旁挂载 |
| create | `web/tests/margin/MarginSyncPanel.test.tsx` | jest 组件测试 |
| create | `web/tests/e2e/helpers/mock-margin-sync-api.ts` | E2E mock helper |
| create | `web/tests/e2e/margin-sync.spec.ts` | Playwright spec（red/green） |
| create | `docs/e2e/17-e2e-用例-融资融券同步面板.md` | E2E 用例文档 |

注：`marginTypes.ts` 的 `MarginTaskResult`/`MarginDateResult` 已在 plan-07 一次写全，本功能直消费、不再改该文件。

## 实现规格

### 前端部分

#### 1. Hook 扩展（仿 16 期 plan-08 Task 1）

`web/src/hooks/useTaskStatus.ts` 的 `TaskData` 接口（L14-28 旁）追加 `result?: MarginTaskResult | null`（后端 `AsyncTask.to_dict()` 已含透传的 result，plan-04 交付）。result 键全 camelCase（plan-04 handler 构造即 camelCase，`to_dict()` 原样透传不经 `_dict_to_camel`），前端**直消费、无二次键转换**。

#### 2. API 客户端（四件套校验）

```ts
// adminApi 内追加（L649 initMarketMetrics 旁）
initMargin: (start_date: string, end_date: string) =>
  adminApiClient.post<{ task_id: string }>('/admin/init/margin', {
    start_date,
    end_date,
  }),
```

endpoint `/admin/init/margin` × AdminApiClient baseURL `${API_BASE_URL}/api/v1` = `/api/v1/admin/init/margin`（与后端挂载一致）；POST 带 Authorization；**body 字段 snake_case（user_input），与后端 MarginRangePayload 一致**；响应经 AdminApiClient 提取 `json.data` → `{task_id}`（与 `initMarketMetrics` 同款）。

#### 3. MarginSyncPanel（仿 MarketMetricsSyncPanel.tsx:1-679，裁剪四类计数）

- **创建区**：两个 date input（**默认最近 1 年**：endDate=today、startDate=today−364 自然日，`formatLocalDate(subtractDays(new Date(), 364))`——spec 边界"历史范围=近1年"；16 期默认 30 自然日，此处不同）+ "开始同步"按钮：
  - 前端校验：`start > end` / `end > 今天` / 跨度 > 10 年（`TEN_YEARS_MS`）→ 按钮禁用 + 行内错误提示，不发请求（与后端 plan-05 五项校验中的前三项同口径，前端拦截不承担一致性）
  - 点击 → `adminApi.initMargin(startDate, endDate)` → `response.data?.task_id` 存 state → `useTaskStatus(taskId, { enabled: !!taskId, pollInterval: 2000, onComplete/onFailed/onCancelled })` 轮询
  - 互斥（AC-3 前端侧）：记录列表含同类型 pending/running（`recordsHaveRunning`）或本地任务运行中 → 按钮禁用 + 提示"已有融资融券任务在运行"；后端二次拒绝（success=false）时展示 message——前端禁用不承担一致性
- **进度区**：running 时显示 `progress/total`（交易日口径）+ 百分比进度条；本地任务 running 时隐藏历史结果回退、显示"结果待任务完成后展示"占位（16 期 review S-1 同款裁定）
- **终态结果区**：completed/failed/cancelled 终态显示 `result.successCount/skippedCount/failedCount` 三类计数（成功/跳过非交易日/失败）；展示优先级：本地终态回调 terminalResult → 当前轮询 `task?.result` → 最近一条带 result 的历史记录
- **日期结果区**：`result.dateResults` 列表（按 tradeDate 倒序，最近在前；`MAX_VISIBLE_DATE_RESULTS = 50` 懒加载防 DOM 爆炸）；点击某日期展开 **状态 + 失败原因**（`reason` 截断 100 字符、title 保留全文）——两融无 16 期 expected/daily/suspended/final 四类计数，`MarginDateResult` 仅 `{tradeDate, status, reason?}`（plan-03/04 契约）；`unprocessedDates` 非空时独立提示块"未处理日期（取消/超时/重启恢复遗留）"
- **记录区**：SWR + `fetcher`（拼 `NEXT_PUBLIC_API_URL` 前缀）拉 `/api/v1/admin/tasks?task_types=sync_market_margin&page={n}&page_size=20`（key 含 `/api/v1` 前缀，同 IndexSyncPanel 的 `RECORDS_SWR_KEY` 模式）；分页按钮；行显示时间/taskId（前 8 位）/params 范围/状态徽章五态/progress/详情（failed 显 errorMessage）
- 取消：复用 `useTaskStatus` 返回的 `cancel()`（"取消中"过渡直至终态）；失败重试：终态 failed → "重新同步"重开创建区（同参数预填）
- **容器**：`data-testid="margin-sync-panel"`；按钮 `data-testid="margin-sync-start-button"`；计数 `margin-sync-{success|skipped|failed}-count`；进度 `margin-sync-progress`；校验错误 `margin-sync-validation-error`；互斥提示 `margin-sync-mutex-hint`；列表 `margin-sync-date-result-list` / `margin-sync-date-result-{tradeDate}`；未处理 `margin-sync-unprocessed-dates`；记录 `margin-sync-records`

#### 4. 数据管理页 Tab（spec REQ-8）

`web/src/app/dashboard/admin/data/page.tsx` 三处对称扩展（不动 16 期行）：

- L15-22 `DataTab` 联合类型追加 `| 'market-margin'`
- L106-116 旁 tab 按钮：`data-testid="tab-market-margin"`、文案"融资融券"（市场量价按钮之后）
- L127 旁挂载：`{activeTab === 'market-margin' && <MarginSyncPanel />}` + 顶部 import

#### 5. E2E（red → green，§5 适用性：完整循环）

用例文档 `docs/e2e/17-e2e-用例-融资融券同步面板.md`，spec `web/tests/e2e/margin-sync.spec.ts` + `helpers/mock-margin-sync-api.ts`（mock `POST /api/v1/admin/init/margin` 成功/互斥拒绝/校验拒绝 + `GET /api/v1/admin/tasks*` running→completed 状态序列与 result fixture，范式照抄 `helpers/mock-market-metrics-sync-api.ts`）。**实现前先运行记录 red 失败证据，实现后运行记录 green 通过证据**，证据写入 `docs/e2e/evidence/plan-08-e2e-{red|green}-{YYYYMMDD}.md`。

E2E 场景（Given/When/Then）：

1. **Tab 进入**：Given 管理员登录，When 打开 /dashboard/admin/data 并点击 `tab-market-margin`，Then `margin-sync-panel` 渲染，起止日期输入默认近 1 年（断言 startDate = 今天−364、endDate = 今天）。
2. **触发同步→轮询→计数→历史**：When 填写合法起止日点 `margin-sync-start-button`，Then 发起 `POST /admin/init/margin` 且 body 为 `{start_date, end_date}`（snake_case）；mock 状态序列 running→completed 下 `margin-sync-progress` 先出现后消失；终态后三类计数（`margin-sync-success-count` 等）显示 fixture 值；`margin-sync-records` 列表出现该条任务。
3. **前端校验拦截**：Given 起止倒置 / 结束日在未来 / 跨度 > 10 年，Then 按钮禁用 + `margin-sync-validation-error` 行内提示，且断言网络零调用（mock 请求计数=0）。
4. **失败日展开与未处理提示**：Given 终态 result 含 1 个 failed 日与 unprocessedDates，When 点击 `margin-sync-date-result-{date}` 行，Then 展开显示失败状态与截断原因；`margin-sync-unprocessed-dates` 提示块可见。

## Task 列表

| # | Task | 维度 | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| 1 | useTaskStatus.ts TaskData.result 字段（MarginTaskResult） | frontend | done | camelCase 契约（TaskData 泛型参数化，默认 MarketMetricsTaskResult 兼容 16 期既有消费方） |
| 2 | adminApi.initMargin | frontend | done | snake_case body |
| 3 | MarginSyncPanel 创建/轮询/进度/三类计数区 | frontend | done | 2s 轮询 + 默认近 1 年 |
| 4 | dateResults 展开（状态+截断 reason）+ unprocessedDates 提示 | frontend | done | 两融无四类计数 |
| 5 | 记录区分页与互斥交互 | frontend | done | fetcher SWR |
| 6 | data/page.tsx Tab 接入 | frontend | done | tab-market-margin |
| 7 | jest 组件测试 | frontend | done | tests/margin/ |
| 8 | E2E 用例 + mock + spec（red 证据） | frontend | done | 先 red 后实现（red 证据 2026-08-14；green 见 evidence） |

## 验收标准

### 前端验收

- [x] AC-7 Tab 进入：管理员数据管理页出现"融资融券"tab，点击后同步面板渲染，日期输入默认近 1 年
- [x] 前端拦截：起止倒置 / 未来结束日 / 跨度 >10 年三种输入按钮禁用且不发请求（jest + E2E 断言网络零调用）
- [x] AC-7 面板闭环：创建成功（body snake_case）→ 轮询显示进度 → 终态显示成功/跳过/失败三类计数（E2E 用状态序列 mock 断言）
- [x] 展开某失败日期显示状态与截断原因；`unprocessedDates` 非空时有独立提示
- [x] 互斥：已有 pending/running 时按钮禁用 + 提示；后端拒绝（success=false）时展示返回 message；非管理员无入口（页面本身在 admin 布局内）
- [x] 记录列表按 createdAt 倒序、分页可用、状态列正确渲染五态
- [x] 取消：running 中点取消 → "取消中"过渡 → 终态 cancelled 后释放按钮
- [x] `pnpm exec tsc --noEmit`、`pnpm run lint`、`pnpm build`、jest、E2E 全部通过
- [x] E2E-TDD：`margin-sync.spec.ts` red/green 证据齐备，存 `docs/e2e/evidence/plan-08-e2e-{red|green}-{date}.md`

## 验证命令

```bash
cd web

# 1. 类型 / lint / 构建
pnpm exec tsc --noEmit && pnpm run lint && pnpm build

# 2. 组件测试
pnpm test -- tests/margin/MarginSyncPanel.test.tsx

# 3. E2E（mock 模式）
pnpm test:e2e -- tests/e2e/margin-sync.spec.ts

# 4. 既有面板回归（确认 useTaskStatus / data 页同文件编辑未破坏 16 期面板）
pnpm test -- tests/margin/ tests/market-metrics/
pnpm test:e2e -- tests/e2e/market-metrics-sync.spec.ts
```

## 交接上下文

- **spec 章节**: REQ-8（同步面板）、任务清单 T8
- **相关代码**: `web/src/components/market-metrics/MarketMetricsSyncPanel.tsx`（L1-679 全量对照母本：TASK_TYPE 常量 L44、默认日期 L95-98、useTaskStatus L164-170、前端校验 L174-181、互斥判定 L184-192、displayResult 优先级 L200-203、dateResults 展开 L243-262、记录区 L553-654）、`web/src/hooks/useTaskStatus.ts`（TaskData L14-28）、`web/src/app/dashboard/admin/data/page.tsx`（Tab 枚举 L15-22、按钮 L106-116、挂载 L127）、`web/src/lib/api.ts`（initMarketMetrics L649-653 范式）
- **契约 / 数据对象**: `MarginTaskResult`（plan-04 §交接上下文约定：`{successCount, skippedCount, failedCount, dateResults: [{tradeDate, status, reason?}], unprocessedDates}` camelCase 直消费）——本面板与 plan-04/05 三方契约一致
- **下游消费方**: 无（终端展示功能）
- **实现级补充项**: 默认近 1 年（16 期为近 30 日）来自 spec 边界"历史范围=近1年"的澄清结论；dateResults 展开仅状态+原因（无四类计数）来自 plan-03"两融无参与集合概念"裁定——均非新造 AC

## 风险与边界

- **执行顺序**: 按 Task 列表顺序执行；与 plan-07 共享 `marginTypes.ts`/`api.ts`，必须串行在 plan-07 之后
- **验证失败排查方向**: E2E mock 未命中查 URL 与 page 参数；轮询不推进查 useTaskStatus 的 enabled/taskId 传值；计数不显示查 result 键是否 camelCase
- **允许修改的额外文件**: 无
- **暂停条件**: 若 plan-05 实际交付的 result 键与 camelCase 契约不符导致类型冲突，暂停并回改写入侧（不得在前端放宽类型为 any 或私加转换层）
- **风险备注**: result 可能很大（1 年 ≈ 240+ 交易日 × 3 字段）——dateResults 列表沿用 16 期"默认渲染最近 50 条 + 加载更多"懒加载，避免一次性 DOM 爆炸

### 前端边界场景

| 场景 | 处理方式 | 状态 |
| --- | --- | --- |
| 创建请求被后端互斥拒绝 | 展示 message，按钮保持可用态 | done |
| 轮询期间网络错误 | isError 展示 + refetch 恢复 | done |
| result 为 null（任务未终态） | 隐藏日期结果区（本地 running 显示占位块） | done |
| unprocessedDates 非空 | 独立提示块 | done |
| 空记录列表 | 空态文案 | done |
| dateResults 超过 50 条 | 默认渲染 50 条 + "加载更多"懒加载 | done |
