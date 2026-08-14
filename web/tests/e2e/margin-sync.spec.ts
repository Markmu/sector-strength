import { test as base, expect, type Page } from '@playwright/test'
import { mockDataStatusNormal } from './helpers/mock-api'
import {
  mockMarginSyncSuccess,
  mockMarginSyncMutex,
  mockMarginTaskPollingSequence,
  mockMarginSyncRecords,
  createTestMarginResult,
  createTestSyncRecord,
  FAILED_DAY_REASON,
} from './helpers/mock-margin-sync-api'

/**
 * 数据管理融资融券同步面板 E2E spec（第 17 期 plan-08）
 *
 * 本文件由 test-e2e skill 在 plan-08 red-e2e 阶段创建，覆盖 AC-7（同步面板：
 * 进度/明细/历史记录）+ 前端校验拦截 + 互斥交互，对应 plan-08 §实现规格-5 的
 * 4 条 Given/When/Then 场景。
 *
 * 被测功能：数据管理页新增「融资融券」Tab + MarginSyncPanel（plan-08 Task 3/6）：
 * - data/page.tsx 增加 data-testid="tab-market-margin"（置于「市场量价」之后）
 * - MarginSyncPanel：日期输入（默认近 1 年）+ 前端校验 + 创建 + 2s 轮询 + 终态三类计数
 *   + dateResults 展开（状态 + 截断 reason，无 16 期四类计数）+ unprocessedDates 提示
 *   + 记录分页 + 互斥交互
 *
 * red 阶段：Tab 与 MarginSyncPanel 均未创建 →
 * 所有用例因 `tab-market-margin` / `margin-sync-*` data-testid 不存在而预期失败。
 *
 * 认证：复用 market-metrics-sync.spec.ts / admin-etf-sync.spec.ts 范式——本项目自定义
 * JWT（token 存 localStorage + Cookie access_token），非 NextAuth。isAdmin =
 * user.role === 'admin'（AuthContext）。本 spec 用 admin 角色（数据管理页在 admin 布局内）。
 *
 * 宿主页稳定：数据管理页默认 Tab 为「数据状态」（DataStatusPanel），它会请求
 * /api/v1/admin/data/status。用 mock token 打真实后端会被 401 拒绝触发
 * handleUnauthorizedRedirect 跳 /login。故 beforeEach 装 mockDataStatusNormal（既有约定）
 * 让宿主页稳定，失败原因落在「Tab/组件未实现」而非环境错误。
 */

const ADMIN_DATA_PAGE = '/dashboard/admin/data'

/**
 * 扩展 test fixture：在每个测试前注入管理员认证（沿用 market-metrics-sync 范式）。
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
 * 切到「融资融券」Tab（green 阶段有效；red 阶段 tab 不存在，由调用方首个断言失败）。
 */
async function openMarginTab(page: Page) {
  await page.getByTestId('tab-market-margin').click()
}

/** 本地时区 YYYY-MM-DD（与组件 formatLocalDate 同口径，默认近 1 年断言用） */
function toLocalISODate(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

test.describe('plan-08：数据管理融资融券同步面板', () => {
  test.beforeEach(async ({ page }) => {
    // 宿主页稳定：默认「数据状态」Tab 请求 /admin/data/status，避免 401 跳 /login
    await mockDataStatusNormal(page)
  })

  // --------------------------------------------------------------------------
  // TC-8.1 Tab 进入 + 默认近 1 年（场景 1）
  // --------------------------------------------------------------------------
  test('TC-8.1 数据管理页新增「融资融券」Tab，点击后渲染面板且默认近 1 年', async ({ page }) => {
    await mockMarginSyncRecords(page, [])
    await page.goto(ADMIN_DATA_PAGE)

    // Tab 可见（文案「融资融券」）
    await expect(page.getByTestId('tab-market-margin')).toBeVisible()
    await expect(page.getByTestId('tab-market-margin')).toHaveText(/融资融券/)

    // 点击切到面板
    await openMarginTab(page)

    // 面板可见 + 两个日期输入 + 开始同步按钮
    const panel = page.getByTestId('margin-sync-panel')
    await expect(panel).toBeVisible()
    await expect(panel.getByLabel('开始日期')).toBeVisible()
    await expect(panel.getByLabel('结束日期')).toBeVisible()
    await expect(panel.getByTestId('margin-sync-start-button')).toBeVisible()

    // 默认近 1 年：startDate = 今天−364、endDate = 今天（16 期为近 30 日，此处不同）
    const today = new Date()
    const yearAgo = new Date(today)
    yearAgo.setDate(yearAgo.getDate() - 364)
    await expect(panel.getByLabel('开始日期')).toHaveValue(toLocalISODate(yearAgo))
    await expect(panel.getByLabel('结束日期')).toHaveValue(toLocalISODate(today))
  })

  // --------------------------------------------------------------------------
  // TC-8.2 触发同步→轮询→终态三类计数→历史记录（场景 2，AC-7）
  // --------------------------------------------------------------------------
  test('TC-8.2 合法创建（body snake_case）→ 轮询进度先现后隐 → 终态三类计数 → 记录列表出现该任务', async ({
    page,
  }) => {
    const taskId = 'task-margin-sync-001'
    const result = createTestMarginResult({ successDays: 2, failedDays: 1 })
    await mockMarginSyncSuccess(page, taskId)

    // 状态化记录列表：任务终态前面板拉到空列表；终态回调 refreshRecords 后出现该任务
    // （母本范式：useTaskStatus 终态回调里 refreshRecords()）
    let marginTaskTerminal = false
    await mockMarginTaskPollingSequence(page, taskId, {
      runningCalls: 3,
      result,
      onTerminal: () => {
        marginTaskTerminal = true
      },
    })
    const completedRecord = createTestSyncRecord({ taskId, status: 'completed', result })
    await page.route(
      (url) => {
        if (url.pathname !== '/api/v1/admin/tasks') return false
        return url.searchParams.get('task_types') === 'sync_market_margin'
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
              tasks: marginTaskTerminal ? [completedRecord] : [],
              total: marginTaskTerminal ? 1 : 0,
              page: 1,
            },
          }),
        })
      }
    )

    await page.goto(ADMIN_DATA_PAGE)
    await openMarginTab(page)

    const panel = page.getByTestId('margin-sync-panel')
    // 填合法起止日并开始同步
    await panel.getByLabel('开始日期').fill('2026-07-15')
    await panel.getByLabel('结束日期').fill('2026-08-13')

    // 捕获 POST init 请求（断言 body snake_case）
    const initRequestPromise = page.waitForRequest(
      (req) =>
        req.method() === 'POST' && new URL(req.url()).pathname === '/api/v1/admin/init/margin'
    )
    await panel.getByTestId('margin-sync-start-button').click()
    const initRequest = await initRequestPromise
    expect(JSON.parse(initRequest.postData() ?? '{}')).toEqual({
      start_date: '2026-07-15',
      end_date: '2026-08-13',
    })

    // 轮询：running 期间进度区可见，终态后隐藏（mock 序列 3 次 running 后 completed）
    await expect(panel.getByTestId('margin-sync-progress')).toBeVisible()
    await expect(panel.getByTestId('margin-sync-progress')).toBeHidden()

    // 终态：三类计数与 fixture 一致
    await expect(panel.getByTestId('margin-sync-success-count')).toHaveText(
      String(result.successCount)
    )
    await expect(panel.getByTestId('margin-sync-skipped-count')).toHaveText(
      String(result.skippedCount)
    )
    await expect(panel.getByTestId('margin-sync-failed-count')).toHaveText(
      String(result.failedCount)
    )

    // 记录列表出现该条任务（终态回调 refreshRecords 后，taskId 前 8 位可见）
    const recordsTable = panel.getByTestId('margin-sync-records')
    await expect(recordsTable).toBeVisible()
    await expect(recordsTable).toContainText(taskId.slice(0, 8))
  })

  // --------------------------------------------------------------------------
  // TC-8.3 前端校验拦截-起止倒置（场景 3）
  // --------------------------------------------------------------------------
  test('TC-8.3 起止倒置：按钮禁用且不发请求', async ({ page }) => {
    await mockMarginSyncSuccess(page, 'should-not-be-called')
    await mockMarginSyncRecords(page, [])
    await page.goto(ADMIN_DATA_PAGE)
    await openMarginTab(page)

    const panel = page.getByTestId('margin-sync-panel')
    // 监听 POST init 请求（应零调用）
    let initCalls = 0
    page.on('request', (req) => {
      if (req.method() === 'POST' && new URL(req.url()).pathname === '/api/v1/admin/init/margin') {
        initCalls += 1
      }
    })

    // 倒置：start > end
    await panel.getByLabel('开始日期').fill('2026-08-10')
    await panel.getByLabel('结束日期').fill('2026-08-01')

    // 按钮禁用 + 行内错误提示
    await expect(panel.getByTestId('margin-sync-start-button')).toBeDisabled()
    await expect(panel.getByTestId('margin-sync-validation-error')).toBeVisible()
    // 零调用（前端拦截不发请求）
    await expect.poll(() => initCalls, { message: 'init 请求应为 0' }).toBe(0)
  })

  // --------------------------------------------------------------------------
  // TC-8.4 前端校验拦截-未来结束日（场景 3）
  // --------------------------------------------------------------------------
  test('TC-8.4 未来结束日：按钮禁用且不发请求', async ({ page }) => {
    await mockMarginSyncSuccess(page, 'should-not-be-called')
    await mockMarginSyncRecords(page, [])
    await page.goto(ADMIN_DATA_PAGE)
    await openMarginTab(page)

    const panel = page.getByTestId('margin-sync-panel')
    let initCalls = 0
    page.on('request', (req) => {
      if (req.method() === 'POST' && new URL(req.url()).pathname === '/api/v1/admin/init/margin') {
        initCalls += 1
      }
    })

    // 未来结束日
    await panel.getByLabel('开始日期').fill('2026-08-01')
    await panel.getByLabel('结束日期').fill('2099-12-31')

    await expect(panel.getByTestId('margin-sync-start-button')).toBeDisabled()
    await expect(panel.getByTestId('margin-sync-validation-error')).toBeVisible()
    await expect.poll(() => initCalls, { message: 'init 请求应为 0' }).toBe(0)
  })

  // --------------------------------------------------------------------------
  // TC-8.5 前端校验拦截-跨度超 10 年（场景 3）
  // --------------------------------------------------------------------------
  test('TC-8.5 跨度超 10 年：按钮禁用且不发请求', async ({ page }) => {
    await mockMarginSyncSuccess(page, 'should-not-be-called')
    await mockMarginSyncRecords(page, [])
    await page.goto(ADMIN_DATA_PAGE)
    await openMarginTab(page)

    const panel = page.getByTestId('margin-sync-panel')
    let initCalls = 0
    page.on('request', (req) => {
      if (req.method() === 'POST' && new URL(req.url()).pathname === '/api/v1/admin/init/margin') {
        initCalls += 1
      }
    })

    // 跨度 > 10 年
    await panel.getByLabel('开始日期').fill('2000-01-01')
    await panel.getByLabel('结束日期').fill('2026-08-13')

    await expect(panel.getByTestId('margin-sync-start-button')).toBeDisabled()
    await expect(panel.getByTestId('margin-sync-validation-error')).toBeVisible()
    await expect.poll(() => initCalls, { message: 'init 请求应为 0' }).toBe(0)
  })

  // --------------------------------------------------------------------------
  // TC-8.6 失败日展开与未处理提示（场景 4，AC-7）
  // --------------------------------------------------------------------------
  test('TC-8.6 点开某失败日期显示状态与截断原因；unprocessedDates 非空时独立提示块可见', async ({
    page,
  }) => {
    const result = createTestMarginResult({
      successDays: 1,
      failedDays: 1,
      unprocessedDates: ['2026-08-10', '2026-08-11'],
    })
    const failedDate = result.dateResults.find((d) => d.status === 'failed')!
    const completedRecord = createTestSyncRecord({
      taskId: 'task-margin-completed',
      status: 'completed',
      result,
    })
    await mockMarginSyncRecords(page, [completedRecord])
    await page.goto(ADMIN_DATA_PAGE)
    await openMarginTab(page)

    const panel = page.getByTestId('margin-sync-panel')
    const list = panel.getByTestId('margin-sync-date-result-list')
    await expect(list).toBeVisible()

    // 点击失败日期行展开
    const failedRow = panel.getByTestId(`margin-sync-date-result-${failedDate.tradeDate}`)
    await failedRow.click()

    // 展开后显示失败状态与截断原因（含前缀片段，不含末尾完整片段——截断 100 字符）
    await expect(failedRow).toContainText(/失败/)
    await expect(failedRow).toContainText(FAILED_DAY_REASON.slice(0, 50))
    await expect(failedRow).not.toContainText(FAILED_DAY_REASON.slice(-20))

    // 两融无 16 期 expected/daily/suspended/final 四类计数
    await expect(panel).not.toContainText('应参与')
    await expect(panel).not.toContainText('全天停牌')

    // unprocessedDates 非空：独立提示块可见且含未处理日期
    const hint = panel.getByTestId('margin-sync-unprocessed-dates')
    await expect(hint).toBeVisible()
    await expect(hint).toContainText('2026-08-10')
  })

  // --------------------------------------------------------------------------
  // TC-8.7 互斥禁用（任务运行中禁用触发按钮）
  // --------------------------------------------------------------------------
  test('TC-8.7 已有同类任务运行时创建按钮禁用并提示', async ({ page }) => {
    // 记录列表含 1 条 running 同步任务 → 面板 recordsHaveRunning → 按钮禁用 + 提示
    const runningRecord = createTestSyncRecord({
      taskId: 'task-margin-running',
      status: 'running',
      progress: 3,
      total: 10,
      result: null,
    })
    await mockMarginSyncRecords(page, [runningRecord])
    await page.goto(ADMIN_DATA_PAGE)
    await openMarginTab(page)

    const panel = page.getByTestId('margin-sync-panel')
    await expect(panel.getByTestId('margin-sync-start-button')).toBeDisabled()
    await expect(panel.getByTestId('margin-sync-mutex-hint')).toBeVisible()
  })

  // --------------------------------------------------------------------------
  // TC-8.8 后端互斥拒绝时展示 message（AC-3 前端侧兜底）
  // --------------------------------------------------------------------------
  test('TC-8.8 后端互斥拒绝时展示返回 message', async ({ page }) => {
    const mutexMsg = '已有融资融券同步任务正在运行，请等待当前任务完成'
    await mockMarginSyncMutex(page, mutexMsg)
    await mockMarginSyncRecords(page, [])
    await page.goto(ADMIN_DATA_PAGE)
    await openMarginTab(page)

    const panel = page.getByTestId('margin-sync-panel')
    await panel.getByLabel('开始日期').fill('2026-07-15')
    await panel.getByLabel('结束日期').fill('2026-08-13')
    await panel.getByTestId('margin-sync-start-button').click()

    // AdminApiClient 对 success=false 抛错 → 面板展示 message
    await expect(panel.getByTestId('margin-sync-validation-error')).toContainText(mutexMsg)
  })

  // --------------------------------------------------------------------------
  // TC-8.9 记录分页（task_types=sync_market_margin；倒序/分页/五态）
  // --------------------------------------------------------------------------
  test('TC-8.9 记录列表按 createdAt 倒序、分页可用、状态列渲染五态', async ({ page }) => {
    const records = [
      createTestSyncRecord({
        taskId: 'task-margin-003',
        status: 'completed',
        createdAt: '2026-08-13T10:00:00.000Z',
        params: { start_date: '2026-08-01', end_date: '2026-08-13' },
        result: createTestMarginResult(),
      }),
      createTestSyncRecord({
        taskId: 'task-margin-002',
        status: 'failed',
        errorMessage: 'Tushare 限流',
        createdAt: '2026-08-12T10:00:00.000Z',
        params: { start_date: '2026-07-01', end_date: '2026-08-13' },
        result: createTestMarginResult({ successDays: 5, failedDays: 3 }),
      }),
      createTestSyncRecord({
        taskId: 'task-margin-001',
        status: 'cancelled',
        createdAt: '2026-08-11T10:00:00.000Z',
        params: { start_date: '2026-06-01', end_date: '2026-08-13' },
        result: createTestMarginResult({
          successDays: 2,
          failedDays: 0,
          unprocessedDates: ['2026-08-09'],
        }),
      }),
    ]
    await mockMarginSyncRecords(page, records, { total: 25, page: 1 })
    await page.goto(ADMIN_DATA_PAGE)
    await openMarginTab(page)

    const panel = page.getByTestId('margin-sync-panel')
    const recordsTable = panel.getByTestId('margin-sync-records')
    await expect(recordsTable).toBeVisible()

    // 状态徽章：completed / failed / cancelled 三态可见（五态中至少三态）
    await expect(recordsTable.getByText('已完成', { exact: true })).toBeVisible()
    await expect(recordsTable.getByText('失败', { exact: true })).toBeVisible()
    await expect(recordsTable.getByText('已取消', { exact: true })).toBeVisible()

    // 按 createdAt 倒序：最新记录（2026-08-13，params start 2026-08-01）在最前
    const body = await recordsTable.innerText()
    expect(body.indexOf('2026-08-01')).toBeGreaterThanOrEqual(0)
    expect(body.indexOf('2026-08-01')).toBeLessThan(body.indexOf('2026-07-01'))
    expect(body.indexOf('2026-07-01')).toBeLessThan(body.indexOf('2026-06-01'))

    // 分页「下一页」可见（total=25 > page_size=20）
    await expect(panel.getByTestId('margin-sync-records-next-page')).toBeVisible()
  })
})
