import { test as base, expect } from '@playwright/test'
import {
  mockFundList,
  mockFundDetail,
  mockFundPortfolio,
  mockFundPortfolioNoData,
  mockFundPortfolioNotDisclosed,
  createTestFunds,
  createTestPortfolio,
  type FundItem,
} from './helpers/mock-fund-api'

/**
 * 扩展 test fixture：在每个测试前注入认证 cookie
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

test.describe('AC-03/05：基金详情页', () => {

  // 测试用基金
  const testFund: FundItem = createTestFunds()[0] // 510300.SH

  test.describe('基本信息卡片', () => {
    test('详情页展示基金基本信息', async ({ page }) => {
      await mockFundDetail(page, testFund)
      await mockFundPortfolio(page, testFund.tsCode, createTestPortfolio(testFund.tsCode))
      await page.goto(`/dashboard/funds/${encodeURIComponent(testFund.tsCode)}`)

      // 断言：基金名称和代码 — 限定到 main 区域
      const main = page.locator('main')
      // h1 在 DashboardHeader 中显示基金名称
      await expect(main.getByRole('heading', { name: '华泰柏瑞沪深300ETF', level: 1 })).toBeVisible()
      // subtitle 在 DashboardHeader 中显示代码
      await expect(main.locator('header').getByText('510300.SH')).toBeVisible()

      // 断言：类型信息
      await expect(main.getByText('股票型 / 被动指数型')).toBeVisible()

      // 断言：管理人
      await expect(main.getByText('华泰柏瑞基金')).toBeVisible()

      // 断言：成立日期
      await expect(main.getByText('2012-05-04')).toBeVisible()

      // 断言：跟踪标的
      await expect(main.getByText('沪深300指数')).toBeVisible()

      // 断言：市场标签（场内）
      await expect(main.getByText('场内')).toBeVisible()
    })

    test('跟踪标的为空时显示占位符', async ({ page }) => {
      const fundNoBenchmark: FundItem = {
        ...testFund,
        tsCode: '000002.OF',
        benchmark: undefined,
      }
      await mockFundDetail(page, fundNoBenchmark)
      await mockFundPortfolio(page, fundNoBenchmark.tsCode, createTestPortfolio(fundNoBenchmark.tsCode))
      await page.goto(`/dashboard/funds/${encodeURIComponent(fundNoBenchmark.tsCode)}`)

      const main = page.locator('main')
      // 找到 "跟踪标的" 标签所在的父容器
      const benchmarkLabel = main.getByText('跟踪标的', { exact: true })
      await expect(benchmarkLabel).toBeVisible()
      // 同一行的内容值显示占位符
      const benchmarkContainer = benchmarkLabel.locator('..')
      await expect(benchmarkContainer.getByText('-', { exact: true })).toBeVisible()
    })
  })

  test.describe('持仓明细表格', () => {
    test('持仓明细按占净值比降序展示', async ({ page }) => {
      await mockFundDetail(page, testFund)
      const portfolio = createTestPortfolio(testFund.tsCode)
      await mockFundPortfolio(page, testFund.tsCode, portfolio)
      await page.goto(`/dashboard/funds/${encodeURIComponent(testFund.tsCode)}`)

      // 断言：持仓表格可见 — 限定到 main 区域
      const main = page.locator('main')
      const table = main.locator('table').first()
      await expect(table).toBeVisible()

      // 断言：表头完整
      await expect(table.getByText('股票代码')).toBeVisible()
      await expect(table.getByText('名称')).toBeVisible()
      await expect(table.getByText('持仓市值')).toBeVisible()
      await expect(table.getByText('持股数')).toBeVisible()
      await expect(table.getByText('占净值比')).toBeVisible()
      await expect(table.getByText('占流通比')).toBeVisible()

      // 断言：持仓数据按占净值比降序（mock 数据已排序）
      const rows = main.locator('tbody tr')
      await expect(rows).toHaveCount(5)

      // 第一行应为占净值比最高的（贵州茅台 9.85%）
      await expect(rows.first()).toContainText('600519.SH')
      await expect(rows.first()).toContainText('9.85%')

      // 第二行（五粮液 5.25%）
      await expect(rows.nth(1)).toContainText('000858.SZ')
      await expect(rows.nth(1)).toContainText('5.25%')
    })

    test('持仓明细列完整展示', async ({ page }) => {
      await mockFundDetail(page, testFund)
      await mockFundPortfolio(page, testFund.tsCode, createTestPortfolio(testFund.tsCode))
      await page.goto(`/dashboard/funds/${encodeURIComponent(testFund.tsCode)}`)

      const main = page.locator('main')
      const rows = main.locator('tbody tr')
      await expect(rows).toHaveCount(5)

      // 验证第一行的完整列数据
      const firstRow = rows.first()
      await expect(firstRow).toContainText('600519.SH') // 股票代码
      await expect(firstRow).toContainText('贵州茅台') // 股票名称
      await expect(firstRow).toContainText('15.0 亿') // 持仓市值
      await expect(firstRow).toContainText('9.85%') // 占净值比
      await expect(firstRow).toContainText('0.64%') // 占流通比
    })

    test('占流通比为 null 时显示占位符', async ({ page }) => {
      await mockFundDetail(page, testFund)
      await mockFundPortfolio(page, testFund.tsCode, createTestPortfolio(testFund.tsCode))
      await page.goto(`/dashboard/funds/${encodeURIComponent(testFund.tsCode)}`)

      const main = page.locator('main')
      const rows = main.locator('tbody tr')
      await expect(rows).toHaveCount(5)

      // 第四行（美的集团 stkFloatRatio=null）
      const fourthRow = rows.nth(3)
      await expect(fourthRow).toContainText('000333.SZ')
      await expect(fourthRow).toContainText('2.95%')
      // 占流通比那列应该显示 "—"
      // 同一行有两个 "—"（stockName 和 stkFloatRatio 都可能显示 —）
      await expect(fourthRow).toContainText('-')
    })
  })

  test.describe('全部持仓展开', () => {
    test('"全部持仓"展开按钮在数据超过默认页面大小时显示', async ({ page }) => {
      await mockFundDetail(page, testFund)
      const portfolio = createTestPortfolio(testFund.tsCode)
      // 模拟 total > 当前 items.length 的场景
      portfolio.total = 30
      await mockFundPortfolio(page, testFund.tsCode, portfolio)
      await page.goto(`/dashboard/funds/${encodeURIComponent(testFund.tsCode)}`)

      // 断言：展开按钮可见 — 限定到 main 区域
      await expect(page.locator('main').getByRole('button', { name: /全部持仓/ })).toBeVisible()
      // 持仓标题中显示 "共 30 条"
      await expect(page.locator('main').getByText('持仓明细（共 30 条）')).toBeVisible()
    })
  })

  test.describe('空态场景 A（hasPortfolio=false）', () => {
    test('展示"暂无最新持仓数据（数据源未收录）"', async ({ page }) => {
      const fundNoPortfolio: FundItem = {
        ...testFund,
        tsCode: '110011.OF',
        hasPortfolio: false,
      }
      await mockFundDetail(page, fundNoPortfolio)
      await mockFundPortfolioNoData(page, fundNoPortfolio.tsCode)
      await page.goto(`/dashboard/funds/${encodeURIComponent(fundNoPortfolio.tsCode)}`)

      const main = page.locator('main')

      // 断言：空态文案（场景 A）
      await expect(main.getByText('暂无最新持仓数据')).toBeVisible()
      await expect(main.getByText('数据源未收录该基金')).toBeVisible()

      // 断言：返回列表按钮 — 限定到空态卡片区域避免匹配顶部的返回列表按钮
      const emptyStateCard = main.locator('.bg-card').filter({ hasText: '暂无最新持仓数据' })
      await expect(emptyStateCard.getByRole('button', { name: '返回列表' })).toBeVisible()

      // 断言：不显示"触发同步"按钮（场景 A 只有"返回列表"按钮，没有"触发同步"链接）
      await expect(main.getByRole('link', { name: '触发同步' })).not.toBeVisible()
    })
  })

  test.describe('空态场景 B（hasPortfolio=true, isPortfolioEmpty=true）', () => {
    test('展示"暂无最新一期持仓数据"和"触发同步"按钮', async ({ page }) => {
      const fundWithPortfolio: FundItem = {
        ...testFund,
        tsCode: '510300.SH',
        hasPortfolio: true,
      }
      await mockFundDetail(page, fundWithPortfolio)
      await mockFundPortfolioNotDisclosed(page, fundWithPortfolio.tsCode)
      await page.goto(`/dashboard/funds/${encodeURIComponent(fundWithPortfolio.tsCode)}`)

      const main = page.locator('main')

      // 断言：空态文案（场景 B）
      await expect(main.getByText('暂无最新一期持仓数据')).toBeVisible()
      await expect(main.getByText('当前报告期尚未披露')).toBeVisible()

      // 断言：返回列表按钮 — 限定到空态卡片区域避免匹配顶部的返回列表按钮
      const emptyStateCard = main.locator('.bg-card').filter({ hasText: '暂无最新一期持仓数据' })
      await expect(emptyStateCard.getByRole('button', { name: '返回列表' })).toBeVisible()

      // 断言："触发同步"链接 — EmptyPortfolioState 场景 B 中是 <a> 标签
      const syncLink = main.getByRole('link', { name: '触发同步' })
      await expect(syncLink).toBeVisible()
      // 验证链接指向管理页面
      await expect(syncLink).toHaveAttribute('href', '/dashboard/admin/fund-init')
    })
  })

  test.describe('返回列表', () => {
    test('点击"返回列表"按钮跳转到基金列表页', async ({ page }) => {
      const funds = createTestFunds()
      await mockFundList(page, funds, funds.length)
      await mockFundDetail(page, testFund)
      await mockFundPortfolio(page, testFund.tsCode, createTestPortfolio(testFund.tsCode))
      await page.goto(`/dashboard/funds/${encodeURIComponent(testFund.tsCode)}`)

      // 断言：顶部"返回列表"按钮（是 button 元素，不是 link）— 有多个"返回列表"，取第一个
      const main = page.locator('main')
      const backButton = main.getByRole('button', { name: '返回列表' }).first()
      await expect(backButton).toBeVisible()

      await backButton.click()

      // 断言：跳转回列表页
      await expect(page).toHaveURL(/\/dashboard\/funds$/)
    })
  })

  test.describe('URL 含 `.` 正确解析', () => {
    test('510300.SH 在 URL 中不被截断', async ({ page }) => {
      const fund: FundItem = {
        tsCode: '510300.SH',
        name: '华泰柏瑞沪深300ETF',
        fundType: '股票型',
        market: 'E',
        hasPortfolio: true,
      }
      await mockFundDetail(page, fund)
      await mockFundPortfolio(page, fund.tsCode, createTestPortfolio(fund.tsCode))

      // 直接访问带 . 的 URL
      await page.goto(`/dashboard/funds/${encodeURIComponent('510300.SH')}`)

      const main = page.locator('main')
      // 断言：页面正确渲染，基金代码正确展示
      await expect(main.locator('header').getByText('510300.SH')).toBeVisible()
      await expect(main.getByRole('heading', { name: '华泰柏瑞沪深300ETF', level: 1 })).toBeVisible()

      // 断言：URL 仍然包含完整代码
      expect(page.url()).toContain('510300.SH')
    })

    test('159915.SZ URL 解析正确', async ({ page }) => {
      const fund: FundItem = {
        tsCode: '159915.SZ',
        name: '易方达创业板ETF',
        fundType: '股票型',
        market: 'E',
        hasPortfolio: true,
      }
      await mockFundDetail(page, fund)
      await mockFundPortfolio(page, fund.tsCode, createTestPortfolio(fund.tsCode))

      await page.goto(`/dashboard/funds/${encodeURIComponent('159915.SZ')}`)

      const main = page.locator('main')
      await expect(main.locator('header').getByText('159915.SZ')).toBeVisible()
      await expect(main.getByRole('heading', { name: '易方达创业板ETF', level: 1 })).toBeVisible()
    })
  })

  test.describe('持仓报告期标题', () => {
    test('展示报告期和公告日期信息', async ({ page }) => {
      await mockFundDetail(page, testFund)
      await mockFundPortfolio(page, testFund.tsCode, createTestPortfolio(testFund.tsCode))
      await page.goto(`/dashboard/funds/${encodeURIComponent(testFund.tsCode)}`)

      // 断言：报告期信息 — 限定到 main 区域
      const main = page.locator('main')
      await expect(main.getByText('最新报告期 2025-12-31')).toBeVisible()
      await expect(main.getByText('公告日 2026-03-31')).toBeVisible()
      await expect(main.getByText('持仓明细（共 5 条）')).toBeVisible()
    })
  })

  test.describe('面包屑导航', () => {
    test('面包屑展示仪表板 > 基金分析 > 基金名称', async ({ page }) => {
      await mockFundDetail(page, testFund)
      await mockFundPortfolio(page, testFund.tsCode, createTestPortfolio(testFund.tsCode))
      await page.goto(`/dashboard/funds/${encodeURIComponent(testFund.tsCode)}`)

      // 断言：面包屑层级 — 面包屑在 header > nav 中，链接是 <a> 标签
      // sidebar 也有"仪表板"和"基金分析"链接，需要限定到 nav 区域
      const breadcrumbNav = page.locator('header nav')
      await expect(breadcrumbNav.getByRole('link', { name: '仪表板' })).toBeVisible()
      await expect(breadcrumbNav.getByRole('link', { name: '基金分析' })).toBeVisible()
    })
  })
})
