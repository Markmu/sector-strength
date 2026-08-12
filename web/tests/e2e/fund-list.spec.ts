import { test as base, expect } from '@playwright/test'
import {
  mockFundList,
  mockFundListEmpty,
  mockFundListError,
  mockFundDetail,
  mockFundPortfolio,
  mockReverseLookup,
  createTestFunds,
  createTestPortfolio,
  createTestReverseLookup,
  type FundItem,
} from './helpers/mock-fund-api'

const FUND_LIST_PAGE = '/dashboard/funds'

/**
 * 扩展 test fixture：在每个测试前注入认证 cookie
 * bypass Next.js middleware 的路由保护
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

test.describe('AC-01/02：基金列表页', () => {

  test.describe('页面加载与基本展示', () => {
    test('页面加载展示搜索框、过滤面板、列表表格', async ({ page }) => {
      const funds = createTestFunds()
      await mockFundList(page, funds, funds.length)
      await page.goto(FUND_LIST_PAGE)

      // 断言：搜索栏可见（基金搜索 + 股票反查两个输入框）— 用 getByRole 避免多匹配
      const main = page.locator('main')
      const fundSearchInputs = main.getByPlaceholder('输入基金代码或名称')
      await expect(fundSearchInputs.first()).toBeVisible()
      const reverseSearchInput = main.getByPlaceholder('按股票反查')
      await expect(reverseSearchInput).toBeVisible()

      // 断言：过滤面板可见（市场 + 基金类型两个分区标题）— 限定到 main 区域
      await expect(main.getByText('市场', { exact: true })).toBeVisible()
      await expect(main.getByText('类型', { exact: true }).first()).toBeVisible()

      // 断言：表格可见，包含表头
      const table = main.locator('table').first()
      await expect(table).toBeVisible()
      await expect(table.getByText('代码')).toBeVisible()
      await expect(table.getByText('名称')).toBeVisible()
      await expect(table.getByText('操作')).toBeVisible()
    })
  })

  test.describe('搜索功能', () => {
    test('输入关键字搜索基金，列表筛选结果', async ({ page }) => {
      const funds = createTestFunds()
      await mockFundList(page, funds, funds.length)
      await mockFundDetail(page, funds[0])
      await mockFundPortfolio(page, funds[0].tsCode, createTestPortfolio(funds[0].tsCode))
      await page.goto(FUND_LIST_PAGE)

      // 等待表格加载
      await expect(page.locator('main tbody tr')).toHaveCount(funds.length)

      // 输入搜索关键字 — 限定到 main 区域
      const searchInput = page.locator('main').getByPlaceholder('输入基金代码或名称')
      await searchInput.fill('沪深300')

      // 等待 debounce (300ms) + 渲染
      await expect(page.locator('main tbody tr')).toHaveCount(1)
      await expect(page.locator('main tbody')).toContainText('510300.SH')
      await expect(page.locator('main tbody')).toContainText('华泰柏瑞沪深300ETF')
    })

    test('搜索无结果展示空态文案', async ({ page }) => {
      const funds = createTestFunds()
      await mockFundList(page, funds, funds.length)
      await mockFundDetail(page, funds[0])
      await mockFundPortfolio(page, funds[0].tsCode, createTestPortfolio(funds[0].tsCode))
      await page.goto(FUND_LIST_PAGE)

      // 等待加载完成
      await expect(page.locator('main tbody tr')).toHaveCount(funds.length)

      // 搜索不存在的关键字 — 限定到 main 区域
      const searchInput = page.locator('main').getByPlaceholder('输入基金代码或名称')
      await searchInput.fill('不存在的基金XYZ')

      // 断言：空态文案
      await expect(page.locator('main').getByText('未找到匹配基金')).toBeVisible()
      await expect(page.locator('main').getByText('请调整搜索词或清除过滤项')).toBeVisible()
    })
  })

  test.describe('市场过滤', () => {
    test('勾选场内 ETF 过滤', async ({ page }) => {
      const funds = createTestFunds()
      await mockFundList(page, funds, funds.length)
      await mockReverseLookup(page, createTestReverseLookup())
      await page.goto(FUND_LIST_PAGE)

      await expect(page.locator('main tbody tr')).toHaveCount(funds.length)

      // 勾选"场内 ETF" — Checkbox 使用 label + input，getByLabel 可匹配
      await page.getByLabel('场内 ETF').check()

      // 断言：仅场内基金 (market=E)
      await expect(page.locator('main tbody tr')).toHaveCount(2)
      await expect(page.locator('main tbody')).toContainText('510300.SH')
      await expect(page.locator('main tbody')).toContainText('159915.SZ')
    })

    test('勾选场外过滤', async ({ page }) => {
      const funds = createTestFunds()
      await mockFundList(page, funds, funds.length)
      await page.goto(FUND_LIST_PAGE)

      await expect(page.locator('main tbody tr')).toHaveCount(funds.length)

      // 勾选"场外"
      await page.getByLabel('场外').check()

      // 断言：仅场外基金 (market=O)
      await expect(page.locator('main tbody tr')).toHaveCount(4)
      await expect(page.locator('main tbody')).toContainText('000001.OF')
      await expect(page.locator('main tbody')).toContainText('110011.OF')
    })
  })

  test.describe('基金类型过滤', () => {
    test('勾选股票型过滤', async ({ page }) => {
      const funds = createTestFunds()
      await mockFundList(page, funds, funds.length)
      await page.goto(FUND_LIST_PAGE)

      await expect(page.locator('main tbody tr')).toHaveCount(funds.length)

      // 勾选"股票型"
      await page.getByLabel('股票型').check()

      // 断言：仅股票型基金
      await expect(page.locator('main tbody tr')).toHaveCount(3)
      await expect(page.locator('main tbody')).toContainText('510300.SH')
      await expect(page.locator('main tbody')).toContainText('159915.SZ')
      await expect(page.locator('main tbody')).toContainText('001838.OF')
    })

    test('勾选 QDII 过滤', async ({ page }) => {
      const funds = createTestFunds()
      await mockFundList(page, funds, funds.length)
      await page.goto(FUND_LIST_PAGE)

      await expect(page.locator('main tbody tr')).toHaveCount(funds.length)

      // 勾选"QDII"
      await page.getByLabel('QDII').check()

      // 断言：仅 QDII 基金
      await expect(page.locator('main tbody tr')).toHaveCount(1)
      await expect(page.locator('main tbody')).toContainText('164906.OF')
    })

    test('勾选混合型过滤', async ({ page }) => {
      const funds = createTestFunds()
      await mockFundList(page, funds, funds.length)
      await page.goto(FUND_LIST_PAGE)

      await expect(page.locator('main tbody tr')).toHaveCount(funds.length)

      // 勾选"混合型"
      await page.getByLabel('混合型').check()

      // 断言：仅混合型基金
      await expect(page.locator('main tbody tr')).toHaveCount(2)
      await expect(page.locator('main tbody')).toContainText('000001.OF')
      await expect(page.locator('main tbody')).toContainText('110011.OF')
    })
  })

  test.describe('搜索与过滤组合', () => {
    test('搜索 + 市场过滤组合筛选', async ({ page }) => {
      const funds = createTestFunds()
      await mockFundList(page, funds, funds.length)
      await page.goto(FUND_LIST_PAGE)

      await expect(page.locator('main tbody tr')).toHaveCount(funds.length)

      // 先搜索"易方达" — 限定到 main 区域
      const searchInput = page.locator('main').getByPlaceholder('输入基金代码或名称')
      await searchInput.fill('易方达')
      await expect(page.locator('main tbody tr')).toHaveCount(2)

      // 搜索建议层会覆盖后方筛选项，键盘关闭后再操作筛选。
      await searchInput.press('Escape')

      // 再勾选"场内 ETF"
      await page.getByLabel('场内 ETF').check()

      // 断言：场内的易方达基金
      await expect(page.locator('main tbody tr')).toHaveCount(1)
      await expect(page.locator('main tbody')).toContainText('159915.SZ')
    })
  })

  test.describe('列表空态', () => {
    test('列表为空展示"暂无基金数据"', async ({ page }) => {
      await mockFundListEmpty(page)
      await page.goto(FUND_LIST_PAGE)

      // 断言：空态文案
      await expect(page.locator('main').getByText('暂无基金数据')).toBeVisible()
      await expect(page.locator('main').getByText('请管理员先在管理后台执行同步')).toBeVisible()
    })
  })

  test.describe('hasPortfolio 标记', () => {
    test('hasPortfolio=false 的基金标注"暂无数据"', async ({ page }) => {
      const funds = createTestFunds()
      await mockFundList(page, funds, funds.length)
      await page.goto(FUND_LIST_PAGE)

      await expect(page.locator('main tbody tr')).toHaveCount(funds.length)

      // 110011.OF 的 hasPortfolio=false
      const row = page.locator('main tr').filter({ hasText: '110011.OF' })
      await expect(row).toBeVisible()
      await expect(row.getByText('暂无数据')).toBeVisible()

      // 510300.SH 的 hasPortfolio=true，不应有"暂无数据"标记
      const row2 = page.locator('main tr').filter({ hasText: '510300.SH' })
      await expect(row2).toBeVisible()
      await expect(row2.getByText('暂无数据')).not.toBeVisible()
    })
  })

  test.describe('点击跳转', () => {
    test('点击基金行跳转详情页', async ({ page }) => {
      const funds = createTestFunds()
      await mockFundList(page, funds, funds.length)
      await mockFundDetail(page, funds[0])
      await mockFundPortfolio(page, funds[0].tsCode, createTestPortfolio(funds[0].tsCode))
      await page.goto(FUND_LIST_PAGE)

      await expect(page.locator('main tbody tr')).toHaveCount(funds.length)

      // 点击 510300.SH 所在行
      const row = page.locator('main tr').filter({ hasText: '510300.SH' })
      await row.click()

      // 断言：跳转到详情页（URL 含 . 不被截断）
      await expect(page).toHaveURL(/\/dashboard\/funds\/510300\.SH/)
    })

    test('点击详情按钮跳转详情页', async ({ page }) => {
      const funds = createTestFunds()
      await mockFundList(page, funds, funds.length)
      await mockFundDetail(page, funds[0])
      await mockFundPortfolio(page, funds[0].tsCode, createTestPortfolio(funds[0].tsCode))
      await page.goto(FUND_LIST_PAGE)

      await expect(page.locator('main tbody tr')).toHaveCount(funds.length)

      // 点击 510300.SH 行内的"详情"按钮
      const row = page.locator('main tr').filter({ hasText: '510300.SH' })
      await row.getByRole('button', { name: '详情' }).click()

      // 断言：跳转到详情页
      await expect(page).toHaveURL(/\/dashboard\/funds\/510300\.SH/)
    })
  })

  test.describe('股票反查入口', () => {
    test('在反查输入框中输入股票代码并回车，跳转反查页', async ({ page }) => {
      const funds = createTestFunds()
      await mockFundList(page, funds, funds.length)
      await mockReverseLookup(page, createTestReverseLookup())
      await page.route('**/api/v1/stocks/search**', (route) => route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            items: [{ symbol: '600519', name: '贵州茅台' }],
            total: 1,
            page: 1,
            page_size: 10,
            total_pages: 1,
          },
        }),
      }))
      await page.goto(FUND_LIST_PAGE)

      // 等待页面加载 — 限定到 main 区域
      await expect(page.locator('main').getByPlaceholder('按股票反查')).toBeVisible()

      // 输入股票代码 — 限定到 main 区域避免 strict mode
      const reverseInput = page.locator('main').getByPlaceholder('按股票反查')
      await reverseInput.fill('600519')

      // 回车立即搜索，再从建议列表确认目标股票。
      await reverseInput.press('Enter')
      await page.getByRole('button', { name: /600519.*贵州茅台/ }).click()

      // 当前列表页以内嵌反查模式承载结果。
      await expect(page).toHaveURL(/\/dashboard\/funds\?symbol=600519/)
    })
  })

  test.describe('分页功能', () => {
    test('分页控件在数据超过一页时展示', async ({ page }) => {
      // 创建超过一页的数据（25条 > 20条/页）
      const funds: FundItem[] = Array.from({ length: 25 }, (_, i) => ({
        tsCode: `${String(i + 1).padStart(6, '0')}.OF`,
        name: `测试基金${i + 1}`,
        fundType: '股票型',
        market: 'O',
        hasPortfolio: true,
      }))
      await mockFundList(page, funds, funds.length)
      await page.goto(FUND_LIST_PAGE)

      // 等待表格加载
      await expect(page.locator('main tbody tr')).toHaveCount(20)

      // 断言：分页信息可见 — 限定到 main 区域
      await expect(page.locator('main').getByText('第 1 / 2 页')).toBeVisible()
      await expect(page.locator('main').getByText('共 25 条')).toBeVisible()

      // 断言：下一页按钮
      const nextButton = page.locator('main').getByRole('button', { name: '下一页' })
      await expect(nextButton).toBeVisible()
      await expect(nextButton).toBeEnabled()

      // 点击下一页
      await nextButton.click()

      // 断言：第二页数据
      await expect(page.locator('main tbody tr')).toHaveCount(5)
      await expect(page.locator('main').getByText('第 2 / 2 页')).toBeVisible()
    })
  })

  test.describe('结果统计', () => {
    test('无搜索条件时展示"共 N 只基金"', async ({ page }) => {
      const funds = createTestFunds()
      await mockFundList(page, funds, funds.length)
      await page.goto(FUND_LIST_PAGE)

      // 断言：统计文案 — 限定到 main 区域
      await expect(page.locator('main').getByText(`共 ${funds.length} 只基金`)).toBeVisible()
    })

    test('有搜索条件时展示"找到 N 只匹配基金"', async ({ page }) => {
      const funds = createTestFunds()
      await mockFundList(page, funds, funds.length)
      await page.goto(FUND_LIST_PAGE)

      await expect(page.locator('main tbody tr')).toHaveCount(funds.length)

      // 搜索 — 限定到 main 区域
      const searchInput = page.locator('main').getByPlaceholder('输入基金代码或名称')
      await searchInput.fill('ETF')

      // 断言：匹配文案
      await expect(page.locator('main').getByText('找到 3 只匹配基金')).toBeVisible()
    })
  })

  test.describe('加载错误态', () => {
    test('API 返回 500 展示错误态', async ({ page }) => {
      await mockFundListError(page)
      await page.goto(FUND_LIST_PAGE)

      // 断言：错误态
      await expect(page.locator('main').getByText('加载失败，请重试')).toBeVisible()
      await expect(page.locator('main').getByText('网络请求异常')).toBeVisible()
    })
  })
})
