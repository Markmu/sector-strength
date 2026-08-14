import { Page } from '@playwright/test'

/**
 * Mock helpers for 市场量价同步面板 admin E2E tests（第 16 期 plan-08）
 *
 * 被测 API（baseURL 已含 /api/v1，AdminApiClient 提取 json.data）：
 * - POST /api/v1/admin/init/market-metrics（成功/互斥拒绝/校验拒绝）
 * - GET  /api/v1/admin/tasks/{task_id}（轮询序列 running→completed，带 result fixture）
 * - GET  /api/v1/admin/tasks?task_types=sync_market_metrics&page=1&page_size=20（同步记录列表）
 *
 * 范式照抄 mock-etf-sync-api.ts 与 mock-market-metrics-api.ts：
 * - URL 匹配用 URL.pathname 精确匹配（matchApiPath，避免 glob 歧义、host 无关）
 * - test data factory 字段 camelCase（与 marketMetricsTypes.ts / 架构 §7.2 对齐）
 * - handler 内按 URLSearchParams 解析 task_types；query 名 snake_case 与后端 Query 一致
 * - 响应体 `{ success, data, message? }` 业务包；result 键全 camelCase（plan-05 handler 构造即 camelCase，
 *   to_dict() 原样透传，前端直消费、无二次键转换）
 * - 非目标方法用 route.fallback() 放行（避免吞掉其他 panel 的请求）
 *
 * 后端契约（已上线，见 plan-08「环境事实」）：
 * - POST init body snake_case（start_date/end_date），返回 ApiResponse data.task_id
 * - GET task list query snake_case（task_types/page/page_size），fetcher 解包
 * - GET task detail：TaskData camelCase + result: MarketMetricsTaskResult camelCase
 *
 * 注意：宿主页（数据管理页默认「数据状态」Tab，DataStatusPanel）请求 /admin/data/status，
 * 用 mock token 打真实后端会 401 触发 handleUnauthorizedRedirect 跳 /login。
 * 该宿主 mock 不在本文件，spec 内复用 mock-api.ts 的 mockDataStatusNormal（同宿主页既有约定）。
 */

// ---------- URL Matching Helpers（与 mock-etf-sync-api.ts 一致） ----------

function toPathname(requestUrl: URL | string): string {
  if (typeof requestUrl === 'string') {
    try {
      return new URL(requestUrl).pathname
    } catch {
      return ''
    }
  }
  return requestUrl.pathname
}

function matchApiPath(requestUrl: URL | string, expectedPath: string): boolean {
  return toPathname(requestUrl) === expectedPath
}

function parseQuery(requestUrl: URL | string): URLSearchParams {
  if (typeof requestUrl === 'string') {
    try {
      return new URL(requestUrl).searchParams
    } catch {
      return new URLSearchParams()
    }
  }
  return requestUrl.searchParams
}

// ---------- Types（与 src/types/marketMetricsTypes.ts / 架构 §7.2 逐字段一致，plan-08 §1） ----------

export type SyncMarketMetricsTaskType = 'sync_market_metrics'
export type MarketMetricsDateStatus = 'success' | 'failed'

export interface MarketMetricsDateResult {
  tradeDate: string
  status: MarketMetricsDateStatus
  expected: number
  daily: number
  suspended: number
  final: number
  reason?: string
}

export interface MarketMetricsTaskResult {
  successCount: number
  skippedCount: number
  failedCount: number
  dateResults: MarketMetricsDateResult[]
  unprocessedDates: string[]
}

/** 任务状态（与 useTaskStatus TaskData 对齐，含 nullable result） */
export interface MarketMetricsTaskData {
  taskId: string
  taskType: SyncMarketMetricsTaskType
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress: number
  total: number
  percent: number
  params?: Record<string, unknown> | null
  errorMessage?: string | null
  retryCount: number
  maxRetries: number
  createdAt: string
  startedAt?: string | null
  completedAt?: string | null
  result?: MarketMetricsTaskResult | null
}

const TASK_TYPE = 'sync_market_metrics' as const

// ---------- Test Data Factory ----------

/**
 * 构造 MarketMetricsTaskResult。
 * - successDays/failedDays 控制两类日期数量；failed 自带非空 reason（截断展示验证）
 * - unprocessedDates 默认空（完整处理范围）；传入则模拟取消/超时/重启恢复
 * 四类计数口径与架构 §6 一致：expected = daily + suspended +（其它缺失，此处 daily+suspended ≈ expected-缺失）
 */
export function createTestMarketMetricsResult(opts?: {
  successDays?: number
  failedDays?: number
  skippedCount?: number
  unprocessedDates?: string[]
}): MarketMetricsTaskResult {
  const successDays = opts?.successDays ?? 2
  const failedDays = opts?.failedDays ?? 1
  const dateResults: MarketMetricsDateResult[] = []

  // 最近结果日锚定 2026-08-13，向前推连续交易日
  const base = new Date('2026-08-13T00:00:00Z')
  let offset = 0
  const iso = (d: Date) => d.toISOString().slice(0, 10)
  const stepBack = () => {
    const d = new Date(base)
    d.setUTCDate(d.getUTCDate() - offset)
    offset += 1
    return iso(d)
  }

  for (let i = 0; i < successDays; i++) {
    // 成功日：四类计数自洽（daily + suspended = expected，final = daily）
    const daily = 5180 + i
    const suspended = 24 + (i % 5)
    dateResults.push({
      tradeDate: stepBack(),
      status: 'success',
      expected: daily + suspended,
      daily,
      suspended,
      final: daily,
    })
  }
  for (let i = 0; i < failedDays; i++) {
    // 失败日：四类计数部分缺失（final=0），reason 非空（截断展示验证）
    const daily = 4100 + i
    const suspended = 18 + (i % 4)
    dateResults.push({
      tradeDate: stepBack(),
      status: 'failed',
      expected: daily + suspended + 120,
      daily,
      suspended,
      final: 0,
      reason:
        '完整性校验失败：daily_count + suspended_count 与 expected 不一致，缺失 120 只（ts_code 样本：000001.SZ/000002.SZ/...）',
    })
  }

  return {
    successCount: successDays,
    skippedCount: opts?.skippedCount ?? 8, // 非交易日（自然日 - 交易日）
    failedCount: failedDays,
    dateResults,
    unprocessedDates: opts?.unprocessedDates ?? [],
  }
}

/** 构造一条同步记录（用于记录列表 mock，携带 camelCase result）。 */
export function createTestSyncRecord(opts: {
  taskId?: string
  status?: MarketMetricsTaskData['status']
  progress?: number
  total?: number
  result?: MarketMetricsTaskResult | null
  errorMessage?: string | null
  params?: Record<string, unknown>
  createdAt?: string
}): MarketMetricsTaskData {
  const status = opts.status ?? 'completed'
  const progress = opts.progress ?? 10
  const total = opts.total ?? 10
  const now = opts.createdAt ?? new Date().toISOString()
  return {
    taskId: opts.taskId ?? 'task-mm-sync-001',
    taskType: TASK_TYPE,
    status,
    progress,
    total,
    percent: total > 0 ? Math.round((progress / total) * 100) : 0,
    params: opts.params ?? { start_date: '2026-07-15', end_date: '2026-08-13' },
    errorMessage: opts.errorMessage ?? null,
    retryCount: 0,
    maxRetries: 0,
    createdAt: now,
    startedAt: now,
    completedAt:
      status === 'completed' || status === 'failed' || status === 'cancelled' ? now : null,
    result: opts.result !== undefined ? opts.result : createTestMarketMetricsResult(),
  }
}

// ---------- Mock Helpers：创建入口 ----------

/**
 * Mock POST /api/v1/admin/init/market-metrics — 创建成功。
 * body 接受 snake_case start_date/end_date（user_input），返回 ApiResponse data.task_id。
 */
export async function mockMarketMetricsSyncSuccess(
  page: Page,
  taskId = 'task-mm-sync-001'
): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/admin/init/market-metrics'),
    async (route) => {
      if (route.request().method() !== 'POST') {
        await route.fallback()
        return
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: { task_id: taskId },
          message: '市场量价同步任务已创建',
        }),
      })
    }
  )
}

/**
 * Mock POST /api/v1/admin/init/market-metrics — 互斥拒绝（后端二次拒绝）。
 * success=false、HTTP 200、data=null；AdminApiClient 对 success=false 抛错，前端展示 message。
 */
export async function mockMarketMetricsSyncMutex(
  page: Page,
  message = '已有市场量价同步任务正在运行，请等待当前任务完成'
): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/admin/init/market-metrics'),
    async (route) => {
      if (route.request().method() !== 'POST') {
        await route.fallback()
        return
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: false,
          data: null,
          message,
        }),
      })
    }
  )
}

/**
 * Mock POST /api/v1/admin/init/market-metrics — 校验拒绝（后端二次校验，如零交易日）。
 * success=false、HTTP 200、data=null；前端展示 message。
 */
export async function mockMarketMetricsSyncValidationReject(
  page: Page,
  message = '日期范围无效：零交易日或跨度超出上限'
): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/admin/init/market-metrics'),
    async (route) => {
      if (route.request().method() !== 'POST') {
        await route.fallback()
        return
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: false,
          data: null,
          message,
        }),
      })
    }
  )
}

// ---------- Mock Helpers：任务状态轮询 ----------

/**
 * Mock GET /api/v1/admin/tasks/{task_id} — 轮询序列 running→completed。
 *
 * useTaskStatus 默认 2s 轮询：首次立即 GET（running，progress/total + percent），
 * 后续每次 GET 推进 progress，第 runningCalls 次后返回 completed（带 result fixture）。
 *
 * 与 mock-etf-sync-api.ts 固定状态 mock 不同，此 helper 用闭包计数器模拟状态推进，
 * 以验证 AC-02 轮询→终态闭环（plan-08 §3：2s 轮询 + 终态三类计数）。
 *
 * @param runningCalls 返回 running 的次数（含首次），其后返回 completed
 */
export async function mockMarketMetricsTaskPollingSequence(
  page: Page,
  taskId: string,
  opts?: {
    runningCalls?: number
    total?: number
    result?: MarketMetricsTaskResult
  }
): Promise<void> {
  const runningCalls = opts?.runningCalls ?? 2
  const total = opts?.total ?? 10
  const result = opts?.result ?? createTestMarketMetricsResult()
  const expectedPath = `/api/v1/admin/tasks/${taskId}`
  let callCount = 0
  const now = new Date().toISOString()

  await page.route((url) => matchApiPath(url, expectedPath), async (route) => {
    if (route.request().method() !== 'GET') {
      await route.fallback()
      return
    }
    callCount += 1
    const isCompleted = callCount > runningCalls
    const progress = isCompleted ? total : Math.min(callCount * 3, total - 1)

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        data: {
          taskId,
          taskType: TASK_TYPE,
          status: isCompleted ? 'completed' : 'running',
          progress,
          total,
          percent: total > 0 ? Math.round((progress / total) * 100) : 0,
          params: { start_date: '2026-07-15', end_date: '2026-08-13' },
          errorMessage: null,
          retryCount: 0,
          maxRetries: 0,
          createdAt: now,
          startedAt: now,
          completedAt: isCompleted ? now : null,
          result: isCompleted ? result : null,
        },
      }),
    })
  })
}

/**
 * Mock GET /api/v1/admin/tasks/{task_id} — 固定 completed + 自定义 result。
 * 供记录列表/失败日期展开等需要稳定终态数据的用例使用。
 */
export async function mockMarketMetricsTaskCompletedWithResult(
  page: Page,
  taskId: string,
  result: MarketMetricsTaskResult | null = createTestMarketMetricsResult()
): Promise<void> {
  const expectedPath = `/api/v1/admin/tasks/${taskId}`
  const now = new Date().toISOString()
  await page.route((url) => matchApiPath(url, expectedPath), async (route) => {
    if (route.request().method() !== 'GET') {
      await route.fallback()
      return
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        data: {
          taskId,
          taskType: TASK_TYPE,
          status: 'completed',
          progress: 10,
          total: 10,
          percent: 100,
          params: { start_date: '2026-07-15', end_date: '2026-08-13' },
          errorMessage: null,
          retryCount: 0,
          maxRetries: 0,
          createdAt: now,
          startedAt: now,
          completedAt: now,
          result,
        },
      }),
    })
  })
}

// ---------- Mock Helpers：同步记录列表 ----------

/**
 * Mock GET /api/v1/admin/tasks?task_types=sync_market_metrics&page=1&page_size=20 — 同步记录列表。
 *
 * MarketMetricsSyncPanel 用固定 SWR key 查询该端点（范式同 IndexSyncPanel RECORDS_SWR_KEY）。
 * fetcher 解包外层 data，此处返回 { tasks, total, page }；每条 record 携带 camelCase result。
 */
export async function mockMarketMetricsSyncRecords(
  page: Page,
  records: MarketMetricsTaskData[] = [],
  opts?: { total?: number; page?: number }
): Promise<void> {
  await page.route(
    (url) => {
      if (!matchApiPath(url, '/api/v1/admin/tasks')) return false
      const q = parseQuery(url)
      return q.get('task_types') === TASK_TYPE
    },
    async (route) => {
      if (route.request().method() !== 'GET') {
        await route.fallback()
        return
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            tasks: records,
            total: opts?.total ?? records.length,
            page: opts?.page ?? 1,
          },
        }),
      })
    }
  )
}

// ---------- 一键安装 ----------

/**
 * 一键安装默认 mock：POST init 成功 + 轮询序列 running→completed（带 result）+ 空记录列表。
 * 用于 TC-8.2 合法创建→轮询→终态闭环。
 */
export async function installMarketMetricsSyncMocks(page: Page): Promise<void> {
  const taskId = 'task-mm-sync-001'
  await mockMarketMetricsSyncSuccess(page, taskId)
  await mockMarketMetricsTaskPollingSequence(page, taskId)
  await mockMarketMetricsSyncRecords(page, [])
}
