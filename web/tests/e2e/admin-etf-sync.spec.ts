import { test as base, expect } from '@playwright/test'
import {
  mockEtfBasicSyncSuccess,
  mockEtfBasicSyncError,
  mockEtfDailySyncSuccess,
  mockEtfDailySyncConcurrent,
  mockEtfDailySyncError,
  mockEtfHistorySyncSuccess,
  mockEtfTaskStatusCompleted,
  mockEtfTaskStatusRunning,
  mockEtfTaskStatusFailed,
  mockEtfSyncRecords,
} from './helpers/mock-etf-sync-api'

const ADMIN_ETF_PAGE = '/dashboard/admin/etf-init'

/**
 * 扩展 test fixture：在每个测试前注入管理员认证（沿用 admin-fund-sync 范式）
 */
const test = base.extend<{ authedPage: void }>({
  authedPage: [async ({ page }, use) => {
    await page.context().addCookies([{
      name: 'access_token',
      value: 'test-mock-jwt-token',
      domain: 'localhost',
      path: '/',
    }])
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
  }, { auto: true }],
})

test.describe('ETF 数据同步面板（第 14 期 plan-03 admin UI）', () => {

  test.describe('面板展示', () => {
    test('管理员可见 ETF 同步面板双卡片', async ({ page }) => {
      await mockEtfSyncRecords(page)
      await page.goto(ADMIN_ETF_PAGE)

      const main = page.locator('main')

      // 断言：页面标题
      await expect(main.getByRole('heading', { name: 'ETF 数据同步' })).toBeVisible()

      // 断言：基础信息同步卡片
      await expect(main.getByText('ETF 基础信息同步')).toBeVisible()
      await expect(main.getByRole('button', { name: '手动同步' })).toBeVisible()

      // 断言：当日采集卡片
      await expect(main.getByText('ETF 当日份额采集')).toBeVisible()
      await expect(main.getByRole('button', { name: '手动采集' })).toBeVisible()

      // 断言：历史回填卡片
      await expect(main.getByText('ETF 历史数据回填')).toBeVisible()
      await expect(main.getByRole('button', { name: '开始回填' })).toBeDisabled()

      // 断言：起止日期输入框
      await expect(main.getByLabel('开始日期')).toBeVisible()
      await expect(main.getByLabel('结束日期')).toBeVisible()

      // 断言：同步记录区
      await expect(main.getByRole('heading', { name: '同步记录' })).toBeVisible()
      await expect(main.getByText('暂无同步记录')).toBeVisible()
    })

    test('侧边栏有 ETF 数据同步导航项', async ({ page }) => {
      await mockEtfSyncRecords(page)
      await page.goto(ADMIN_ETF_PAGE)

      // 断言：侧边栏导航项存在并指向正确路由
      const navLink = page.getByRole('link', { name: /ETF 数据同步/ }).first()
      await expect(navLink).toBeVisible()
    })
  })

  test.describe('基础信息同步', () => {
    test('点击"手动同步"触发同步并完成', async ({ page }) => {
      const taskId = 'task-etf-basic-001'
      await mockEtfBasicSyncSuccess(page, taskId)
      await mockEtfTaskStatusCompleted(page, taskId, 'sync_etf_basic')
      await mockEtfSyncRecords(page)
      await page.goto(ADMIN_ETF_PAGE)

      const main = page.locator('main')
      // 限定到基础信息卡片：main 内首个「手动同步」按钮
      const syncButton = main.getByRole('button', { name: '手动同步' }).first()
      await syncButton.click()

      // 断言：成功 toast
      await expect(main.getByText('ETF 基础信息同步完成')).toBeVisible()
    })

    test('同步失败展示错误 toast', async ({ page }) => {
      await mockEtfBasicSyncError(page)
      await mockEtfSyncRecords(page)
      await page.goto(ADMIN_ETF_PAGE)

      const main = page.locator('main')
      const syncButton = main.getByRole('button', { name: '手动同步' }).first()
      await syncButton.click()

      // 断言：错误 toast
      await expect(main.getByText(/创建同步任务失败/)).toBeVisible()
    })
  })

  test.describe('当日份额采集', () => {
    test('点击"手动采集"触发同步并完成', async ({ page }) => {
      const taskId = 'task-etf-daily-001'
      await mockEtfDailySyncSuccess(page, taskId)
      await mockEtfTaskStatusCompleted(page, taskId, 'sync_etf_daily')
      await mockEtfSyncRecords(page)
      await page.goto(ADMIN_ETF_PAGE)

      const main = page.locator('main')
      const syncButton = main.getByRole('button', { name: '手动采集' })
      await syncButton.click()

      // 断言：成功 toast
      await expect(main.getByText('ETF 当日份额采集完成')).toBeVisible()
    })

    test('采集失败展示错误 toast', async ({ page }) => {
      await mockEtfDailySyncError(page)
      await mockEtfSyncRecords(page)
      await page.goto(ADMIN_ETF_PAGE)

      const main = page.locator('main')
      const syncButton = main.getByRole('button', { name: '手动采集' })
      await syncButton.click()

      // 断言：错误 toast
      await expect(main.getByText(/创建采集任务失败/)).toBeVisible()
    })

    test('并发保护拦截展示提示', async ({ page }) => {
      // 并发保护返回 success=false 但 HTTP 200，data 为 null
      await mockEtfDailySyncConcurrent(page)
      await mockEtfSyncRecords(page)
      await page.goto(ADMIN_ETF_PAGE)

      const main = page.locator('main')
      const syncButton = main.getByRole('button', { name: '手动采集' })
      await syncButton.click()

      // 断言：AdminApiClient 对 success=false 抛错，触发失败 toast
      await expect(main.getByText(/创建采集任务失败/)).toBeVisible()
    })

    test('采集运行中按钮显示进度', async ({ page }) => {
      const taskId = 'task-etf-daily-001'
      await mockEtfDailySyncSuccess(page, taskId)
      await mockEtfTaskStatusRunning(page, taskId, 'sync_etf_daily')
      // 预置一条 running 记录，使同步记录表展示"运行中"状态
      await mockEtfSyncRecords(page, [
        {
          taskId,
          taskType: 'sync_etf_daily',
          status: 'running',
          progress: 50,
          total: 100,
          params: {},
          errorMessage: null,
          createdAt: new Date().toISOString(),
        },
      ])
      await page.goto(ADMIN_ETF_PAGE)

      const main = page.locator('main')
      const syncButton = main.getByRole('button', { name: '手动采集' })
      await syncButton.click()

      // 断言：按钮变为采集中状态并禁用
      await expect(main.getByRole('button', { name: /采集/ })).toBeDisabled()

      // 断言：同步记录出现"运行中"状态
      await expect(main.getByText('运行中', { exact: true })).toBeVisible()
    })
  })

  test.describe('历史数据回填', () => {
    test('未选日期时按钮禁用', async ({ page }) => {
      await mockEtfSyncRecords(page)
      await page.goto(ADMIN_ETF_PAGE)

      const main = page.locator('main')
      // 开始回填按钮在未填日期时禁用
      await expect(main.getByRole('button', { name: '开始回填' })).toBeDisabled()
    })

    test('选择日期后可触发回填并完成', async ({ page }) => {
      const taskId = 'task-etf-history-001'
      await mockEtfHistorySyncSuccess(page, taskId)
      await mockEtfTaskStatusCompleted(page, taskId, 'backfill_etf_history')
      await mockEtfSyncRecords(page)
      await page.goto(ADMIN_ETF_PAGE)

      const main = page.locator('main')

      // 填入起止日期
      await main.getByLabel('开始日期').fill('2026-01-01')
      await main.getByLabel('结束日期').fill('2026-01-31')

      // 按钮变为可用
      const fillButton = main.getByRole('button', { name: '开始回填' })
      await expect(fillButton).toBeEnabled()
      await fillButton.click()

      // 断言：成功 toast
      await expect(main.getByText('ETF 历史数据回填完成')).toBeVisible()
    })

    test('任务执行失败展示失败状态', async ({ page }) => {
      const taskId = 'task-etf-history-001'
      await mockEtfHistorySyncSuccess(page, taskId)
      await mockEtfTaskStatusFailed(page, taskId, '日期范围超出上限', 'backfill_etf_history')
      await mockEtfSyncRecords(page)
      await page.goto(ADMIN_ETF_PAGE)

      const main = page.locator('main')

      await main.getByLabel('开始日期').fill('2026-01-01')
      await main.getByLabel('结束日期').fill('2026-01-31')
      await main.getByRole('button', { name: '开始回填' }).click()

      // 断言：失败 toast
      await expect(main.getByText(/回填失败/)).toBeVisible()
    })
  })

  test.describe('同步记录列表', () => {
    test('展示已有 ETF 同步历史', async ({ page }) => {
      const now = new Date().toISOString()
      await mockEtfSyncRecords(page, [
        {
          taskId: 'task-etf-basic-old',
          taskType: 'sync_etf_basic',
          status: 'completed',
          progress: 1806,
          total: 1806,
          params: {},
          errorMessage: null,
          createdAt: now,
        },
        {
          taskId: 'task-etf-daily-old',
          taskType: 'sync_etf_daily',
          status: 'completed',
          progress: 1608,
          total: 1608,
          params: {},
          errorMessage: null,
          createdAt: now,
        },
        {
          taskId: 'task-etf-history-old',
          taskType: 'backfill_etf_history',
          status: 'failed',
          progress: 5,
          total: 30,
          params: { start_date: '2026-01-01', end_date: '2026-01-30' },
          errorMessage: 'Tushare 限流',
          createdAt: now,
        },
      ])
      await page.goto(ADMIN_ETF_PAGE)

      const main = page.locator('main')

      // 断言：两条记录的任务类型显示名
      await expect(main.getByText('ETF 当日份额采集').first()).toBeVisible()
      await expect(main.getByText('ETF 历史数据回填').first()).toBeVisible()

      // 断言：历史回填记录展示日期参数
      await expect(main.getByText('2026-01-01 ~ 2026-01-30')).toBeVisible()

      // 断言：失败记录的错误详情
      await expect(main.getByText('Tushare 限流')).toBeVisible()
    })
  })
})
