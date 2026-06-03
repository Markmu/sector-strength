import { test as base, expect } from '@playwright/test'
import {
  mockFundSyncSuccess,
  mockFundSyncError,
  mockFundPortfolioSyncSuccess,
  mockFundPortfolioSyncError,
  mockTaskStatusCompleted,
  mockTaskStatusFailed,
  mockTaskStatusRunning,
} from './helpers/mock-fund-api'

const ADMIN_FUND_PAGE = '/dashboard/admin/fund-init'

/**
 * 扩展 test fixture：在每个测试前注入管理员认证
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

test.describe('AC-06/07：管理员基金同步面板', () => {

  test.describe('面板展示', () => {
    test('管理员可见基金同步面板', async ({ page }) => {
      await page.goto(ADMIN_FUND_PAGE)

      const main = page.locator('main')

      // 断言：基金同步标题 — 限定到 main 区域，sidebar 也有"基金同步"导航项
      // header 中的 h1 "基金同步" 在 main 内
      await expect(main.getByText('基金同步')).toBeVisible()

      // 断言：基金基本信息同步区
      await expect(main.getByText('基金基本信息同步')).toBeVisible()
      await expect(main.getByRole('button', { name: '手动同步' })).toBeVisible()

      // 断言：基金持仓明细同步区
      await expect(main.getByText('基金持仓明细同步')).toBeVisible()

      // 断言：同步记录区 — 使用 heading 避免匹配 "暂无同步记录" 文案
      await expect(main.getByRole('heading', { name: '同步记录' })).toBeVisible()
      await expect(main.getByText('暂无同步记录')).toBeVisible()
    })

    test('持仓同步区有报告期选择下拉框', async ({ page }) => {
      await page.goto(ADMIN_FUND_PAGE)

      const main = page.locator('main')

      // 断言：报告期选择下拉 — 限定到 main 区域
      const periodSelect = main.locator('select')
      await expect(periodSelect).toBeVisible()
      // option 在 select 未展开时 hidden，改用 toHaveText 验证选项值
      await expect(periodSelect.locator('option').first()).toHaveText('选择报告期')

      // 断言：同步指定报告期按钮
      await expect(main.getByRole('button', { name: '同步指定报告期' })).toBeVisible()

      // 断言：同步最新季度快捷按钮
      await expect(main.getByRole('button', { name: /同步最新季度/ })).toBeVisible()
    })
  })

  test.describe('手动同步基金基本信息', () => {
    test('点击"手动同步"按钮触发同步', async ({ page }) => {
      const taskId = 'task-fund-basic-001'
      await mockFundSyncSuccess(page)
      await mockTaskStatusCompleted(page, taskId)
      await page.goto(ADMIN_FUND_PAGE)

      const main = page.locator('main')

      // 点击手动同步
      const syncButton = main.getByRole('button', { name: '手动同步' })
      await expect(syncButton).toBeVisible()
      await syncButton.click()

      // 断言：同步记录表新增一条记录 — 限定到 table 避免匹配 h3 标题，用 first 避免双重渲染
      await expect(main.locator('table').first().getByText('基金基本信息').first()).toBeVisible()

      // 断言：toast 成功通知
      await expect(main.getByText('基金基本信息同步完成')).toBeVisible()
    })

    test('同步中按钮 disabled 且显示"同步中..."', async ({ page }) => {
      const taskId = 'task-fund-basic-001'
      await mockFundSyncSuccess(page)
      await mockTaskStatusRunning(page, taskId)
      await page.goto(ADMIN_FUND_PAGE)

      const main = page.locator('main')

      // 点击手动同步
      const syncButton = main.getByRole('button', { name: '手动同步' })
      await syncButton.click()

      // 断言：按钮变为同步中状态
      await expect(main.getByRole('button', { name: '同步中...' })).toBeVisible()
      await expect(main.getByRole('button', { name: '同步中...' })).toBeDisabled()

      // 断言：同步记录有 "运行中" 状态（StatusBadge 中的精确文本）
      await expect(main.getByText('运行中', { exact: true })).toBeVisible()
    })
  })

  test.describe('同步完成统计', () => {
    test('同步完成后展示成功 toast', async ({ page }) => {
      const taskId = 'task-fund-basic-001'
      await mockFundSyncSuccess(page)
      await mockTaskStatusCompleted(page, taskId)
      await page.goto(ADMIN_FUND_PAGE)

      const main = page.locator('main')

      const syncButton = main.getByRole('button', { name: '手动同步' })
      await syncButton.click()

      // 断言：成功 toast
      await expect(main.getByText('基金基本信息同步完成')).toBeVisible()

      // 断言：同步记录中新增条目
      await expect(main.getByText('已完成')).toBeVisible()
    })
  })

  test.describe('同步失败处理', () => {
    test('同步失败弹窗展示错误原因', async ({ page }) => {
      // mock 创建任务失败
      await mockFundSyncError(page)
      await page.goto(ADMIN_FUND_PAGE)

      const main = page.locator('main')

      const syncButton = main.getByRole('button', { name: '手动同步' })
      await syncButton.click()

      // 断言：错误 toast
      await expect(main.getByText(/创建同步任务失败/)).toBeVisible()
    })

    test('任务执行失败展示失败状态', async ({ page }) => {
      const taskId = 'task-fund-basic-001'
      await mockFundSyncSuccess(page)
      await mockTaskStatusFailed(page, taskId, '数据获取超时，请重试')
      await page.goto(ADMIN_FUND_PAGE)

      const main = page.locator('main')

      const syncButton = main.getByRole('button', { name: '手动同步' })
      await syncButton.click()

      // 断言：失败 toast
      await expect(main.getByText(/同步失败/)).toBeVisible()

      // 断言：同步记录中有失败条目（StatusBadge 中的精确文本）
      await expect(main.getByText('失败', { exact: true })).toBeVisible()
    })
  })

  test.describe('持仓同步', () => {
    test('选择报告期并点击同步', async ({ page }) => {
      const taskId = 'task-fund-portfolio-001'
      await mockFundPortfolioSyncSuccess(page)
      await mockTaskStatusCompleted(page, taskId)
      await page.goto(ADMIN_FUND_PAGE)

      const main = page.locator('main')

      // 选择报告期 — 限定到 main 区域
      const periodSelect = main.locator('select')
      // 选择第一个非空选项
      const options = periodSelect.locator('option')
      const optionCount = await options.count()
      if (optionCount > 1) {
        await periodSelect.selectOption({ index: 1 })
      }

      // 点击同步指定报告期
      const syncButton = main.getByRole('button', { name: '同步指定报告期' })
      await expect(syncButton).toBeEnabled()
      await syncButton.click()

      // 断言：同步记录表新增持仓记录 — 限定到 table 避免匹配标题，用 first 避免双重渲染
      await expect(main.locator('table').first().getByText('基金持仓').first()).toBeVisible()
    })

    test('未选择报告期时同步按钮 disabled', async ({ page }) => {
      await page.goto(ADMIN_FUND_PAGE)

      const main = page.locator('main')

      // 断言：同步按钮初始 disabled
      const syncButton = main.getByRole('button', { name: '同步指定报告期' })
      await expect(syncButton).toBeDisabled()
    })

    test('点击"同步最新季度"快捷按钮触发同步', async ({ page }) => {
      const taskId = 'task-fund-portfolio-001'
      await mockFundPortfolioSyncSuccess(page)
      await mockTaskStatusCompleted(page, taskId)
      await page.goto(ADMIN_FUND_PAGE)

      const main = page.locator('main')

      // 点击"同步最新季度"
      const quickSyncButton = main.getByRole('button', { name: /同步最新季度/ })
      await expect(quickSyncButton).toBeVisible()
      await quickSyncButton.click()

      // 断言：同步记录表新增记录 — 限定到 table 避免匹配标题，用 first 避免双重渲染
      await expect(main.locator('table').first().getByText('基金持仓').first()).toBeVisible()
    })

    test('持仓同步失败展示错误', async ({ page }) => {
      await mockFundPortfolioSyncError(page)
      await page.goto(ADMIN_FUND_PAGE)

      const main = page.locator('main')

      // 选择报告期
      const periodSelect = main.locator('select')
      const options = periodSelect.locator('option')
      const optionCount = await options.count()
      if (optionCount > 1) {
        await periodSelect.selectOption({ index: 1 })
      }

      // 点击同步
      const syncButton = main.getByRole('button', { name: '同步指定报告期' })
      await syncButton.click()

      // 断言：错误 toast
      await expect(main.getByText(/创建同步任务失败/)).toBeVisible()
    })
  })

  test.describe('同步记录表', () => {
    test('同步记录表展示时间、任务、报告期、结果、详情', async ({ page }) => {
      const taskId = 'task-fund-basic-001'
      await mockFundSyncSuccess(page)
      await mockTaskStatusCompleted(page, taskId)
      await page.goto(ADMIN_FUND_PAGE)

      const main = page.locator('main')

      // 触发一次同步
      await main.getByRole('button', { name: '手动同步' }).click()

      // 断言：同步记录表有表头 — 限定到 main 区域，用 first 避免双重渲染
      const table = main.locator('table').first()
      await expect(table.getByText('时间')).toBeVisible()
      await expect(table.getByText('任务')).toBeVisible()
      await expect(table.getByText('报告期')).toBeVisible()
      await expect(table.getByText('结果')).toBeVisible()
      await expect(table.getByText('详情')).toBeVisible()

      // 断言：记录行存在 — 同步流程会添加 running + completed 两条记录，取 first
      await expect(table.getByText('基金基本信息').first()).toBeVisible()
    })
  })

  test.describe('同步互斥', () => {
    test('一个同步运行中时，其他同步按钮 disabled', async ({ page }) => {
      const taskId = 'task-fund-basic-001'
      await mockFundSyncSuccess(page)
      await mockTaskStatusRunning(page, taskId)
      await page.goto(ADMIN_FUND_PAGE)

      const main = page.locator('main')

      // 触发基本信息同步
      const basicSyncButton = main.getByRole('button', { name: '手动同步' })
      await basicSyncButton.click()

      // 断言：基本信息同步按钮 disabled
      await expect(main.getByRole('button', { name: '同步中...' })).toBeDisabled()

      // 断言：持仓同步按钮也 disabled（isAnySyncRunning=true）
      const portfolioSyncButton = main.getByRole('button', { name: '同步指定报告期' })
      await expect(portfolioSyncButton).toBeDisabled()

      // 断言：同步最新季度按钮 disabled
      const quickSyncButton = main.getByRole('button', { name: /同步最新季度/ })
      await expect(quickSyncButton).toBeDisabled()
    })
  })
})
