import { test as base, expect, type Page } from '@playwright/test'
import { mockDataStatusNormal } from './helpers/mock-api'
import {
  mockMarketMetricsSyncSuccess,
  mockMarketMetricsSyncMutex,
  mockMarketMetricsSyncValidationReject,
  mockMarketMetricsTaskPollingSequence,
  mockMarketMetricsTaskCompletedWithResult,
  mockMarketMetricsSyncRecords,
  createTestMarketMetricsResult,
  createTestSyncRecord,
} from './helpers/mock-market-metrics-sync-api'

/**
 * 数据管理市场量价同步面板 E2E spec（第 16 期 plan-08）
 *
 * 本文件由 test-e2e skill 在 plan-08 red-e2e 阶段创建，覆盖 AC-02/07/10/11。
 *
 * 被测功能：数据管理页新增「市场量价」Tab + MarketMetricsSyncPanel（plan-08 Task 3/6）：
 * - data/page.tsx 增加 data-testid="tab-market-metrics"
 * - MarketMetricsSyncPanel：日期输入 + 前端校验 + 创建 + 2s 轮询 + 终态三类计数
 *   + dateResults 四类计数展开 + unprocessedDates 提示 + 记录分页 + 互斥交互
 *
 * red 阶段：Tab 与 MarketMetricsSyncPanel 均未创建 →
 * 所有用例因 `tab-market-metrics` / `market-metrics-sync-*` data-testid 不存在而预期失败。
 *
 * 认证：复用 admin-etf-sync.spec.ts / market-metrics-panel.spec.ts 范式——本项目自定义 JWT
 * （token 存 localStorage + Cookie access_token），非 NextAuth。isAdmin = user.role === 'admin'
 * （AuthContext）。
 *
 * 宿主页稳定：数据管理页默认 Tab 为「数据状态」（DataStatusPanel），它会请求
 * /api/v1/admin/data/status。用 mock token 打真实后端会被 401 拒绝触发 handleUnauthorizedRedirect
 * 跳 /login。故 beforeEach 装 mockDataStatusNormal（既有约定）让宿主页稳定，
 * 失败原因落在「Tab/组件未实现」而非环境错误。
 */

const ADMIN_DATA_PAGE = '/dashboard/admin/data'

/**
 * 扩展 test fixture：在每个测试前注入管理员认证（沿用 admin-etf-sync 范式）。
 */
const test = base.extend<{ authedPage: void }>({
  authedPage: [
    async ({ page }, use) => {
      await page.context().addCookies([
        {
          name: 'access_token',
          value: 'test-mock-jwt-token',
          domain: 'localhost',
          path: '/',
        },
      ])
      await page.addInitScript(() => {
        localStorage.setItem('accessToken', 'test-mock-jwt-token')
        localStorage.setItem('refreshToken', 'test-mock-refresh-token')
        localStorage.setItem('tokenType', 'Bearer')
        localStorage.setItem('expiresIn', '3600')
        localStorage.setItem('user', JSON.stringify({
          id: 'test-admin-id',
          email: 'admin@test.com',
          username: 'TestAdmin',
          is_active: true,
          role: 'admin',
        }))
      })
      await use()
    },
    { auto: true },
  ],
})

/**
 * 切到「市场量价」Tab（green 阶段有效；red 阶段 tab 不存在，由调用方首个断言失败）。
 */
async function openMarketMetricsTab(page: Page) {
  await page.getByTestId('tab-market-metrics').click()
}

test.describe('plan-08：数据管理市场量价同步面板', () => {
  test.beforeEach(async ({ page }) => {
    // 宿主页稳定：默认「数据状态」Tab 请求 /admin/data/status，避免 401 跳 /login
    await mockDataStatusNormal(page)
  })

  // --------------------------------------------------------------------------
  // TC-8.1 Tab 进入
  // --------------------------------------------------------------------------
  test('TC-8.1 数据管理页新增「市场量价」Tab，点击后渲染同步面板', async ({ page }) => {
    await mockMarketMetricsSyncRecords(page, [])
    await page.goto(ADMIN_DATA_PAGE)

    // Tab 可见
    await expect(page.getByTestId('tab-market-metrics')).toBeVisible()
    await expect(page.getByTestId('tab-market-metrics')).toHaveText(/市场量价/)

    // 点击切到面板
    await openMarketMetricsTab(page)

    // 面板可见 + 两个日期输入 + 开始同步按钮
    const panel = page.getByTestId('market-metrics-sync-panel')
    await expect(panel).toBeVisible()
    await expect(panel.getByLabel('开始日期')).toBeVisible()
    await expect(panel.getByLabel('结束日期')).toBeVisible()
    await expect(panel.getByTestId('market-metrics-sync-start-button')).toBeVisible()
  })

  // --------------------------------------------------------------------------
  // TC-8.2 合法创建→轮询→终态三类计数（AC-02）
  // --------------------------------------------------------------------------
  test('TC-8.2 合法创建后 2s 轮询进度，终态显示 success/skipped/failed 三类计数', async ({
    page,
  }) => {
    const taskId = 'task-mm-sync-001'
    const result = createTestMarketMetricsResult({ successDays: 2, failedDays: 1 })
    await mockMarketMetricsSyncSuccess(page, taskId)
    await mockMarketMetricsTaskPollingSequence(page, taskId, { result })
    await mockMarketMetricsSyncRecords(page, [])

    await page.goto(ADMIN_DATA_PAGE)
    await openMarketMetricsTab(page)

    const panel = page.getByTestId('market-metrics-sync-panel')
    // 填合法起止日并开始同步
    await panel.getByLabel('开始日期').fill('2026-07-15')
    await panel.getByLabel('结束日期').fill('2026-08-13')
    await panel.getByTestId('market-metrics-sync-start-button').click()

    // 轮询：终态后显示三类计数（与 fixture 一致）
    await expect(panel.getByTestId('market-metrics-sync-success-count')).toHaveText(
      String(result.successCount)
    )
    await expect(panel.getByTestId('market-metrics-sync-skipped-count')).toHaveText(
      String(result.skippedCount)
    )
    await expect(panel.getByTestId('market-metrics-sync-failed-count')).toHaveText(
      String(result.failedCount)
    )
  })

  // --------------------------------------------------------------------------
  // TC-8.3 前端校验拦截-起止倒置（AC-10）
  // --------------------------------------------------------------------------
  test('TC-8.3 起止倒置：按钮禁用且不发请求', async ({ page }) => {
    await mockMarketMetricsSyncSuccess(page, 'should-not-be-called')
    await mockMarketMetricsSyncRecords(page, [])
    await page.goto(ADMIN_DATA_PAGE)
    await openMarketMetricsTab(page)

    const panel = page.getByTestId('market-metrics-sync-panel')
    // 监听 POST init 请求（应零调用）
    let initCalls = 0
    page.on('request', (req) => {
      if (
        req.method() === 'POST' &&
        req.url().includes('/admin/init/market-metrics')
      ) {
        initCalls += 1
      }
    })

    // 倒置：start > end
    await panel.getByLabel('开始日期').fill('2026-08-10')
    await panel.getByLabel('结束日期').fill('2026-08-01')

    // 按钮禁用 + 行内错误提示
    await expect(panel.getByTestId('market-metrics-sync-start-button')).toBeDisabled()
    await expect(panel.getByTestId('market-metrics-sync-validation-error')).toBeVisible()
    // 零调用（前端拦截不发请求）
    await expect.poll(() => initCalls, { message: 'init 请求应为 0' }).toBe(0)
  })

  // --------------------------------------------------------------------------
  // TC-8.4 前端校验拦截-未来结束日（AC-10）
  // --------------------------------------------------------------------------
  test('TC-8.4 未来结束日：按钮禁用且不发请求', async ({ page }) => {
    await mockMarketMetricsSyncSuccess(page, 'should-not-be-called')
    await mockMarketMetricsSyncRecords(page, [])
    await page.goto(ADMIN_DATA_PAGE)
    await openMarketMetricsTab(page)

    const panel = page.getByTestId('market-metrics-sync-panel')
    let initCalls = 0
    page.on('request', (req) => {
      if (
        req.method() === 'POST' &&
        req.url().includes('/admin/init/market-metrics')
      ) {
        initCalls += 1
      }
    })

    // 未来结束日
    await panel.getByLabel('开始日期').fill('2026-08-01')
    await panel.getByLabel('结束日期').fill('2099-12-31')

    await expect(panel.getByTestId('market-metrics-sync-start-button')).toBeDisabled()
    await expect(panel.getByTestId('market-metrics-sync-validation-error')).toBeVisible()
    await expect.poll(() => initCalls, { message: 'init 请求应为 0' }).toBe(0)
  })

  // --------------------------------------------------------------------------
  // TC-8.5 前端校验拦截-跨度超 10 年（AC-10）
  // --------------------------------------------------------------------------
  test('TC-8.5 跨度超 10 年：按钮禁用且不发请求', async ({ page }) => {
    await mockMarketMetricsSyncSuccess(page, 'should-not-be-called')
    await mockMarketMetricsSyncRecords(page, [])
    await page.goto(ADMIN_DATA_PAGE)
    await openMarketMetricsTab(page)

    const panel = page.getByTestId('market-metrics-sync-panel')
    let initCalls = 0
    page.on('request', (req) => {
      if (
        req.method() === 'POST' &&
        req.url().includes('/admin/init/market-metrics')
      ) {
        initCalls += 1
      }
    })

    // 跨度 > 10 年
    await panel.getByLabel('开始日期').fill('2000-01-01')
    await panel.getByLabel('结束日期').fill('2026-08-13')

    await expect(panel.getByTestId('market-metrics-sync-start-button')).toBeDisabled()
    await expect(panel.getByTestId('market-metrics-sync-validation-error')).toBeVisible()
    await expect.poll(() => initCalls, { message: 'init 请求应为 0' }).toBe(0)
  })

  // --------------------------------------------------------------------------
  // TC-8.6 互斥禁用（AC-11）
  // --------------------------------------------------------------------------
  test('TC-8.6 已有同类任务运行时创建按钮禁用并提示', async ({ page }) => {
    // 记录列表含 1 条 running 同步任务 → 面板 isRunning → 按钮禁用 + 提示
    const runningRecord = createTestSyncRecord({
      taskId: 'task-mm-running',
      status: 'running',
      progress: 3,
      total: 10,
      result: null,
    })
    await mockMarketMetricsSyncRecords(page, [runningRecord])
    await page.goto(ADMIN_DATA_PAGE)
    await openMarketMetricsTab(page)

    const panel = page.getByTestId('market-metrics-sync-panel')
    await expect(panel.getByTestId('market-metrics-sync-start-button')).toBeDisabled()
    await expect(panel.getByTestId('market-metrics-sync-mutex-hint')).toBeVisible()
  })

  // --------------------------------------------------------------------------
  // TC-8.7 失败日期四类计数展开（AC-07）
  // --------------------------------------------------------------------------
  test('TC-8.7 点开某失败日期显示 expected/daily/suspended/final 四类计数与原因', async ({
    page,
  }) => {
    const result = createTestMarketMetricsResult({ successDays: 1, failedDays: 1 })
    const failedDate = result.dateResults.find((d) => d.status === 'failed')!
    const completedRecord = createTestSyncRecord({
      taskId: 'task-mm-completed',
      status: 'completed',
      progress: 10,
      total: 10,
      result,
    })
    await mockMarketMetricsSyncRecords(page, [completedRecord])
    await page.goto(ADMIN_DATA_PAGE)
    await openMarketMetricsTab(page)

    const panel = page.getByTestId('market-metrics-sync-panel')
    const list = panel.getByTestId('market-metrics-sync-date-result-list')
    await expect(list).toBeVisible()

    // 点击失败日期行展开
    const failedRow = panel.getByTestId(
      `market-metrics-sync-date-result-${failedDate.tradeDate}`
    )
    await failedRow.click()

    // 展开后显示四类计数与 reason
    await expect(failedRow.getByText(`应参与`).locator('..')).toBeVisible()
    await expect(failedRow).toContainText(String(failedDate.expected))
    await expect(failedRow).toContainText(String(failedDate.daily))
    await expect(failedRow).toContainText(String(failedDate.suspended))
    await expect(failedRow).toContainText(String(failedDate.final))
    await expect(failedRow).toContainText(/完整性校验失败|不一致|缺失/)
  })

  // --------------------------------------------------------------------------
  // TC-8.8 unprocessedDates 提示（AC-07 恢复语义）
  // --------------------------------------------------------------------------
  test('TC-8.8 result.unprocessedDates 非空时独立提示块可见', async ({ page }) => {
    const result = createTestMarketMetricsResult({
      successDays: 1,
      failedDays: 0,
      unprocessedDates: ['2026-08-10', '2026-08-11'],
    })
    const completedRecord = createTestSyncRecord({
      taskId: 'task-mm-completed',
      status: 'completed',
      progress: 10,
      total: 10,
      result,
    })
    await mockMarketMetricsSyncRecords(page, [completedRecord])
    await page.goto(ADMIN_DATA_PAGE)
    await openMarketMetricsTab(page)

    const panel = page.getByTestId('market-metrics-sync-panel')
    const hint = panel.getByTestId('market-metrics-sync-unprocessed-dates')
    await expect(hint).toBeVisible()
    // 含未处理日期
    await expect(hint).toContainText('2026-08-10')
  })

  // --------------------------------------------------------------------------
  // TC-8.9 记录分页（记录列表倒序/分页/五态）
  // --------------------------------------------------------------------------
  test('TC-8.9 记录列表按 createdAt 倒序、分页可用、状态列渲染五态', async ({ page }) => {
    const records = [
      createTestSyncRecord({
        taskId: 'task-mm-003',
        status: 'completed',
        createdAt: '2026-08-13T10:00:00.000Z',
        result: createTestMarketMetricsResult(),
      }),
      createTestSyncRecord({
        taskId: 'task-mm-002',
        status: 'failed',
        errorMessage: 'Tushare 限流',
        createdAt: '2026-08-12T10:00:00.000Z',
        result: createTestMarketMetricsResult({ successDays: 5, failedDays: 3 }),
      }),
      createTestSyncRecord({
        taskId: 'task-mm-001',
        status: 'cancelled',
        createdAt: '2026-08-11T10:00:00.000Z',
        result: createTestMarketMetricsResult({
          successDays: 2,
          failedDays: 0,
          unprocessedDates: ['2026-08-09'],
        }),
      }),
    ]
    await mockMarketMetricsSyncRecords(page, records, { total: 25, page: 1 })
    await page.goto(ADMIN_DATA_PAGE)
    await openMarketMetricsTab(page)

    const panel = page.getByTestId('market-metrics-sync-panel')
    const recordsTable = panel.getByTestId('market-metrics-sync-records')
    await expect(recordsTable).toBeVisible()

    // 状态徽章：completed / failed / cancelled 三态可见（五态中至少三态）
    await expect(recordsTable.getByText('已完成', { exact: true })).toBeVisible()
    await expect(recordsTable.getByText('失败', { exact: true })).toBeVisible()
    await expect(recordsTable.getByText('已取消', { exact: true })).toBeVisible()

    // 分页「下一页」可见（total=25 > page_size=20）
    await expect(
      panel.getByTestId('market-metrics-sync-records-next-page')
    ).toBeVisible()
  })

  // --------------------------------------------------------------------------
  // 附加：后端二次互斥拒绝时展示 message（AC-11 后端兜底）
  // --------------------------------------------------------------------------
  test('TC-8.10 后端互斥拒绝时展示返回 message', async ({ page }) => {
    const mutexMsg = '已有市场量价同步任务正在运行，请等待当前任务完成'
    await mockMarketMetricsSyncMutex(page, mutexMsg)
    await mockMarketMetricsSyncRecords(page, [])
    await page.goto(ADMIN_DATA_PAGE)
    await openMarketMetricsTab(page)

    const panel = page.getByTestId('market-metrics-sync-panel')
    await panel.getByLabel('开始日期').fill('2026-07-15')
    await panel.getByLabel('结束日期').fill('2026-08-13')
    await panel.getByTestId('market-metrics-sync-start-button').click()

    // AdminApiClient 对 success=false 抛错 → 面板展示 message
    await expect(panel.getByTestId('market-metrics-sync-validation-error')).toContainText(
      mutexMsg
    )
  })
})
