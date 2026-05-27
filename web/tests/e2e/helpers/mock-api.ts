import { Page } from '@playwright/test'

/**
 * Mock helpers for data status E2E tests
 *
 * 所有 mock helper 集中管理，避免在 spec 文件中重复写 page.route()
 */

// ---------- Types ----------

export interface DataTypeStatus {
  type: 'history' | 'ma' | 'strength'
  label: string
  latest_date: string | null
  status: 'normal' | 'missing' | 'no_data'
  missing_range: { start: string; end: string } | null
  active_task: {
    task_id: string
    status: 'pending' | 'running' | 'completed' | 'failed'
    progress: number
    total: number
    error_message: string | null
  } | null
}

export interface DataStatusResponse {
  success: boolean
  data: {
    items: DataTypeStatus[]
  }
}

// ---------- Mock Helpers ----------

/** Mock GET /api/v1/admin/data/status — 返回三类数据正常状态 */
export async function mockDataStatusNormal(page: Page): Promise<void> {
  await page.route('**/api/v1/admin/data/status', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            items: [
              {
                type: 'history',
                label: '板块历史数据',
                latest_date: '2026-05-26',
                status: 'normal',
                missing_range: null,
                active_task: null,
              },
              {
                type: 'ma',
                label: '板块均线数据',
                latest_date: '2026-05-26',
                status: 'normal',
                missing_range: null,
                active_task: null,
              },
              {
                type: 'strength',
                label: '板块强度数据',
                latest_date: '2026-05-26',
                status: 'normal',
                missing_range: null,
                active_task: null,
              },
            ],
          },
        }),
      })
    } else {
      await route.continue()
    }
  })
}

/** Mock GET /api/v1/admin/data/status — 返回混合状态（含缺失和活跃任务） */
export async function mockDataStatusMixed(page: Page): Promise<void> {
  await page.route('**/api/v1/admin/data/status', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            items: [
              {
                type: 'history',
                label: '板块历史数据',
                latest_date: '2026-05-24',
                status: 'missing',
                missing_range: { start: '2026-05-25', end: '2026-05-26' },
                active_task: null,
              },
              {
                type: 'ma',
                label: '板块均线数据',
                latest_date: '2026-05-26',
                status: 'normal',
                missing_range: null,
                active_task: null,
              },
              {
                type: 'strength',
                label: '板块强度数据',
                latest_date: '2026-05-24',
                status: 'missing',
                missing_range: { start: '2026-05-25', end: '2026-05-26' },
                active_task: {
                  task_id: 'task-strength-001',
                  status: 'running',
                  progress: 15,
                  total: 30,
                  error_message: null,
                },
              },
            ],
          },
        }),
      })
    } else {
      await route.continue()
    }
  })
}

/** Mock GET /api/v1/admin/data/status — 返回失败状态 */
export async function mockDataStatusFailed(page: Page): Promise<void> {
  await page.route('**/api/v1/admin/data/status', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            items: [
              {
                type: 'history',
                label: '板块历史数据',
                latest_date: '2026-05-24',
                status: 'missing',
                missing_range: { start: '2026-05-25', end: '2026-05-26' },
                active_task: null,
              },
              {
                type: 'ma',
                label: '板块均线数据',
                latest_date: '2026-05-24',
                status: 'missing',
                missing_range: { start: '2026-05-25', end: '2026-05-26' },
                active_task: {
                  task_id: 'task-ma-failed-001',
                  status: 'failed',
                  progress: 10,
                  total: 30,
                  error_message: '数据获取超时，请重试',
                },
              },
              {
                type: 'strength',
                label: '板块强度数据',
                latest_date: '2026-05-26',
                status: 'normal',
                missing_range: null,
                active_task: null,
              },
            ],
          },
        }),
      })
    } else {
      await route.continue()
    }
  })
}

/** Mock GET /api/v1/admin/data/status — 返回 no_data 状态 */
export async function mockDataStatusNoData(page: Page): Promise<void> {
  await page.route('**/api/v1/admin/data/status', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            items: [
              {
                type: 'history',
                label: '板块历史数据',
                latest_date: null,
                status: 'no_data',
                missing_range: null,
                active_task: null,
              },
              {
                type: 'ma',
                label: '板块均线数据',
                latest_date: null,
                status: 'no_data',
                missing_range: null,
                active_task: null,
              },
              {
                type: 'strength',
                label: '板块强度数据',
                latest_date: null,
                status: 'no_data',
                missing_range: null,
                active_task: null,
              },
            ],
          },
        }),
      })
    } else {
      await route.continue()
    }
  })
}

/** Mock GET /api/v1/admin/data/status — 返回服务端错误 */
export async function mockDataStatusError(page: Page): Promise<void> {
  await page.route('**/api/v1/admin/data/status', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal Server Error' }),
      })
    } else {
      await route.continue()
    }
  })
}

/** Mock POST /api/v1/admin/data/backfill/{type} — 返回成功 */
export async function mockBackfillSuccess(page: Page, type: string): Promise<void> {
  await page.route(`**/api/v1/admin/data/backfill/${type}`, async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: { task_id: `task-${type}-001` },
        }),
      })
    } else {
      await route.continue()
    }
  })
}

/** Mock POST /api/v1/admin/data/backfill/{type} — 返回 409 冲突 */
export async function mockBackfillConflict(page: Page, type: string): Promise<void> {
  await page.route(`**/api/v1/admin/data/backfill/${type}`, async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 409,
        contentType: 'application/json',
        body: JSON.stringify({ detail: '已有任务在执行中' }),
      })
    } else {
      await route.continue()
    }
  })
}

/** Mock POST /api/v1/admin/data/backfill/{type} — 返回服务端错误 */
export async function mockBackfillError(page: Page, type: string): Promise<void> {
  await page.route(`**/api/v1/admin/data/backfill/${type}`, async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal Server Error' }),
      })
    } else {
      await route.continue()
    }
  })
}
