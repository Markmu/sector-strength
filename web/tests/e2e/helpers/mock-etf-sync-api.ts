import { Page } from '@playwright/test'

/**
 * Mock helpers for ETF 数据同步 admin E2E tests（第 14 期 plan-03 admin UI）
 *
 * 拦截 admin 同步端点，不依赖真实后端。
 * URL 匹配策略：用 URL 对象解析后按 pathname + query 精确匹配，避免 glob 歧义。
 */

// ---------- URL Matching Helpers ----------

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
    return new URL(requestUrl).searchParams
  }
  return requestUrl.searchParams
}

// ---------- ETF 当日份额采集 Mocks ----------

/**
 * Mock POST /api/v1/admin/init/etf-daily — ETF 当日采集（成功）
 */
export async function mockEtfDailySyncSuccess(
  page: Page,
  taskId = 'task-etf-daily-001'
): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/admin/init/etf-daily'),
    async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: { task_id: taskId },
            message: 'ETF 当日采集任务已创建',
          }),
        })
      } else {
        await route.fallback()
      }
    }
  )
}

/**
 * Mock POST /api/v1/admin/init/etf-daily — ETF 当日采集（并发保护拦截）
 */
export async function mockEtfDailySyncConcurrent(page: Page): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/admin/init/etf-daily'),
    async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: false,
            data: null,
            message: '已有 ETF 当日采集任务正在运行，请等待当前任务完成',
          }),
        })
      } else {
        await route.fallback()
      }
    }
  )
}

/**
 * Mock POST /api/v1/admin/init/etf-daily — ETF 当日采集（失败）
 */
export async function mockEtfDailySyncError(page: Page): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/admin/init/etf-daily'),
    async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Tushare 接口调用失败' }),
        })
      } else {
        await route.fallback()
      }
    }
  )
}

// ---------- ETF 历史数据回填 Mocks ----------

/**
 * Mock POST /api/v1/admin/init/etf-history — ETF 历史回填（成功）
 */
export async function mockEtfHistorySyncSuccess(
  page: Page,
  taskId = 'task-etf-history-001'
): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/admin/init/etf-history'),
    async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: { task_id: taskId },
            message: 'ETF 历史回填任务已创建',
          }),
        })
      } else {
        await route.fallback()
      }
    }
  )
}

// ---------- 任务状态轮询 Mocks ----------

/**
 * Mock GET /api/v1/admin/tasks/{taskId} — 任务状态（已完成）
 */
export async function mockEtfTaskStatusCompleted(
  page: Page,
  taskId: string,
  taskType: 'sync_etf_daily' | 'backfill_etf_history' = 'sync_etf_daily'
): Promise<void> {
  const expectedPath = `/api/v1/admin/tasks/${taskId}`
  await page.route((url) => matchApiPath(url, expectedPath), async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            taskId,
            taskType,
            status: 'completed',
            progress: 100,
            total: 100,
            percent: 100,
            params: {},
            errorMessage: null,
            retryCount: 0,
            maxRetries: 3,
            createdAt: new Date().toISOString(),
            startedAt: new Date().toISOString(),
            completedAt: new Date().toISOString(),
          },
        }),
      })
    } else {
      await route.fallback()
    }
  })
}

/**
 * Mock GET /api/v1/admin/tasks/{taskId} — 任务状态（运行中）
 */
export async function mockEtfTaskStatusRunning(
  page: Page,
  taskId: string,
  taskType: 'sync_etf_daily' | 'backfill_etf_history' = 'sync_etf_daily'
): Promise<void> {
  const expectedPath = `/api/v1/admin/tasks/${taskId}`
  await page.route((url) => matchApiPath(url, expectedPath), async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            taskId,
            taskType,
            status: 'running',
            progress: 50,
            total: 100,
            percent: 50,
            params: {},
            errorMessage: null,
            retryCount: 0,
            maxRetries: 3,
            createdAt: new Date().toISOString(),
            startedAt: new Date().toISOString(),
            completedAt: null,
          },
        }),
      })
    } else {
      await route.fallback()
    }
  })
}

/**
 * Mock GET /api/v1/admin/tasks/{taskId} — 任务状态（失败）
 */
export async function mockEtfTaskStatusFailed(
  page: Page,
  taskId: string,
  errorMessage: string,
  taskType: 'sync_etf_daily' | 'backfill_etf_history' = 'sync_etf_daily'
): Promise<void> {
  const expectedPath = `/api/v1/admin/tasks/${taskId}`
  await page.route((url) => matchApiPath(url, expectedPath), async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            taskId,
            taskType,
            status: 'failed',
            progress: 50,
            total: 100,
            percent: 50,
            params: {},
            errorMessage,
            retryCount: 1,
            maxRetries: 3,
            createdAt: new Date().toISOString(),
            startedAt: new Date().toISOString(),
            completedAt: null,
          },
        }),
      })
    } else {
      await route.fallback()
    }
  })
}

// ---------- 同步记录列表 Mock ----------

/**
 * Mock GET /api/v1/admin/tasks?task_types=sync_etf_daily,backfill_etf_history — 同步记录列表
 *
 * EtfSyncPanel 用固定 SWR key 查询该端点。
 */
export async function mockEtfSyncRecords(
  page: Page,
  records: Array<Record<string, unknown>> = []
): Promise<void> {
  await page.route(
    (url) => {
      if (!matchApiPath(url, '/api/v1/admin/tasks')) return false
      return parseQuery(url).get('task_types') === 'sync_etf_daily,backfill_etf_history'
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
          data: { tasks: records, total: records.length, page: 1 },
        }),
      })
    }
  )
}
