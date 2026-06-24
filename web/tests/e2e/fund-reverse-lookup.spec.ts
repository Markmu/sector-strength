import { test as base, expect } from '@playwright/test'
import {
  mockReverseLookup,
  mockReverseLookupEmpty,
  createTestReverseLookup,
} from './helpers/mock-fund-api'

const REVERSE_LOOKUP_PAGE = '/dashboard/funds/reverse-lookup'

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

test.describe('AC-04：反查页', () => {

  test.describe('反查结果展示', () => {
    test('输入股票代码展示反查结果', async ({ page }) => {
      const lookupData = createTestReverseLookup()
      await mockReverseLookup(page, lookupData)
      await page.goto(`${REVERSE_LOOKUP_PAGE}?symbol=600519`)

      const main = page.locator('main')

      // 断言：表格可见（开发模式下可能有双重渲染，用 first）
      const table = main.locator('table').first()
      await expect(table).toBeVisible()

      // 断言：表头
      await expect(table.getByText('基金代码')).toBeVisible()
      await expect(table.getByText('基金名称')).toBeVisible()
      await expect(table.getByText('占净值比')).toBeVisible()
    })

    test('结果按占净值比降序', async ({ page }) => {
      const lookupData = createTestReverseLookup()
      // mock 数据已按 stkMkvRatio 降序排列
      await mockReverseLookup(page, lookupData)
      await page.goto(`${REVERSE_LOOKUP_PAGE}?symbol=600519`)

      const main = page.locator('main')
      const rows = main.locator('tbody tr')
      await expect(rows).toHaveCount(3)

      // 第一行应为占净值比最高的（易方达中小盘混合 8.12%）
      await expect(rows.first()).toContainText('110011.OF')
      await expect(rows.first()).toContainText('8.12%')

      // 第二行（华夏成长混合 3.50%）
      await expect(rows.nth(1)).toContainText('000001.OF')
      await expect(rows.nth(1)).toContainText('3.50%')

      // 第三行（华泰柏瑞沪深300ETF 1.25%）
      await expect(rows.nth(2)).toContainText('510300.SH')
      await expect(rows.nth(2)).toContainText('1.25%')
    })

    test('展示 stockName 和 reportPeriod 元信息', async ({ page }) => {
      const lookupData = createTestReverseLookup()
      await mockReverseLookup(page, lookupData)
      await page.goto(`${REVERSE_LOOKUP_PAGE}?symbol=600519`)

      // 断言：标题包含股票名称 — 用 heading level 1 精确匹配
      const main = page.locator('main')
      await expect(main.getByRole('heading', { level: 1 })).toContainText('贵州茅台（600519）')
      await expect(main.getByRole('heading', { level: 1 })).toContainText('反查结果')

      // 断言：副标题包含报告期
      await expect(main.getByText('最新报告期 2025-12-31')).toBeVisible()
    })

    test('结果统计展示', async ({ page }) => {
      const lookupData = createTestReverseLookup()
      await mockReverseLookup(page, lookupData)
      await page.goto(`${REVERSE_LOOKUP_PAGE}?symbol=600519`)

      // 断言：统计信息 — 限定到内容区域 div 避免匹配 DashboardHeader subtitle
      await expect(page.locator('main .max-w-7xl').getByText('共 3 只基金重仓持有')).toBeVisible()
    })

    test('展示完整的持仓数据列', async ({ page }) => {
      const lookupData = createTestReverseLookup()
      await mockReverseLookup(page, lookupData)
      await page.goto(`${REVERSE_LOOKUP_PAGE}?symbol=600519`)

      const main = page.locator('main')
      const rows = main.locator('tbody tr')
      await expect(rows).toHaveCount(3)

      // 验证第一行的完整数据
      const firstRow = rows.first()
      await expect(firstRow).toContainText('110011.OF') // 基金代码
      await expect(firstRow).toContainText('易方达中小盘混合') // 基金名称
      await expect(firstRow).toContainText('20.0 亿') // 持仓市值
      await expect(firstRow).toContainText('8.12%') // 占净值比
    })
  })

  test.describe('无结果空态', () => {
    test('无结果时展示"暂无基金披露重仓持有该股票"', async ({ page }) => {
      await mockReverseLookupEmpty(page)
      await page.goto(`${REVERSE_LOOKUP_PAGE}?symbol=999999`)

      // 断言：空态文案 — 限定到 main 区域
      const main = page.locator('main')
      await expect(main.getByText('最新一期暂无基金披露重仓持有该股票')).toBeVisible()
      await expect(main.getByText('当前报告期无占净值比 >= 1% 的基金持仓记录')).toBeVisible()
    })
  })

  test.describe('点击跳转详情页', () => {
    test('点击反查结果中的基金行跳转详情页', async ({ page }) => {
      const lookupData = createTestReverseLookup()
      await mockReverseLookup(page, lookupData)
      await page.goto(`${REVERSE_LOOKUP_PAGE}?symbol=600519`)

      const main = page.locator('main')
      const rows = main.locator('tbody tr')
      await expect(rows).toHaveCount(3)

      // 点击第一行
      await rows.first().click()

      // 断言：跳转到该基金的详情页
      await expect(page).toHaveURL(/\/dashboard\/funds\/110011\.OF/)
    })
  })

  test.describe('无 symbol 参数', () => {
    test('直接访问无 symbol 参数时展示"请输入股票代码"', async ({ page }) => {
      await page.goto(REVERSE_LOOKUP_PAGE)

      // 断言：引导文案 — 限定到 main 区域
      const main = page.locator('main')
      await expect(main.getByText('请输入股票代码', { exact: true }).first()).toBeVisible()
      await expect(main.getByText('请在基金分析页面输入股票代码进行反查')).toBeVisible()

      // 断言：返回列表按钮（是 button 元素）
      await expect(main.getByRole('button', { name: '返回列表' })).toBeVisible()
    })

    test('空 symbol 参数等同于无参数', async ({ page }) => {
      await page.goto(`${REVERSE_LOOKUP_PAGE}?symbol=`)

      // 断言：引导文案 — 限定到 main 区域
      await expect(page.locator('main').getByText('请输入股票代码', { exact: true }).first()).toBeVisible()
    })
  })

  test.describe('返回导航', () => {
    test('点击"返回基金分析"按钮回到列表页', async ({ page }) => {
      const lookupData = createTestReverseLookup()
      await mockReverseLookup(page, lookupData)
      await page.goto(`${REVERSE_LOOKUP_PAGE}?symbol=600519`)

      // 断言：返回按钮（是 button 元素，不是 link）— 限定到 main 区域
      const main = page.locator('main')
      const backButton = main.getByRole('button', { name: '返回基金分析' })
      await expect(backButton).toBeVisible()

      await backButton.click()

      // 断言：回到基金列表页
      await expect(page).toHaveURL(/\/dashboard\/funds$/)
    })

    test('无结果时返回按钮也可用', async ({ page }) => {
      await mockReverseLookupEmpty(page)
      await page.goto(`${REVERSE_LOOKUP_PAGE}?symbol=999999`)

      // 断言：返回基金分析按钮 — 限定到 main 区域
      const main = page.locator('main')
      const backButton = main.getByRole('button', { name: '返回基金分析' })
      await expect(backButton).toBeVisible()

      await backButton.click()
      await expect(page).toHaveURL(/\/dashboard\/funds$/)
    })
  })

  test.describe('面包屑导航', () => {
    test('面包屑展示仪表板 > 基金分析 > 反查', async ({ page }) => {
      const lookupData = createTestReverseLookup()
      await mockReverseLookup(page, lookupData)
      await page.goto(`${REVERSE_LOOKUP_PAGE}?symbol=600519`)

      // 面包屑在 header > nav 中，链接是 <a> 标签
      // sidebar 也有"仪表板"和"基金分析"链接，需要限定到 nav 区域
      const breadcrumbNav = page.locator('header nav')
      await expect(breadcrumbNav.getByRole('link', { name: '仪表板' })).toBeVisible()
      await expect(breadcrumbNav.getByRole('link', { name: '基金分析' })).toBeVisible()
    })
  })
})

// ============================================================================
// plan-03 / AC-05：从扎堆分析下钻（from=fund-crowd）
// 04 反查页侧 3 个场景：差异提示 + 返回扎堆分析入口 / 04 原生零影响 / 返回跳转
// 完全复用 04 反查页核心逻辑（ReverseLookupContent + useReverseLookup），
// 仅新增 `from` query 参数条件渲染分支（plan-03 Task 6）+ syncUrl 保留 from（Task 7）
// ============================================================================

test.describe('AC-05：从扎堆分析下钻（from=fund-crowd）', () => {
  test('TC-3.1 from=fund-crowd 时顶部展示差异提示与返回扎堆分析入口', async ({ page }) => {
    const lookupData = createTestReverseLookup()
    await mockReverseLookup(page, lookupData)
    // 带 from=fund-crowd query 进入（plan-03 handleReverseLookup 跳转的目标 URL）
    await page.goto(`${REVERSE_LOOKUP_PAGE}?symbol=600519&from=fund-crowd`)

    const main = page.locator('main')

    // 断言：差异提示文案可见（ADR-4 双轨下钻契约 + 架构 §7.6 命名预案）
    await expect(main.getByTestId('fund-crowd-drilldown-hint')).toBeVisible()
    await expect(main.getByTestId('fund-crowd-drilldown-hint')).toContainText(
      '扎堆统计计入全部重仓记录'
    )

    // 断言：「返回扎堆分析」入口可见（仅 from=fund-crowd 时渲染）
    await expect(main.getByTestId('back-to-fund-crowd')).toBeVisible()

    // 断言：原「返回基金分析」入口不渲染（避免用户误点回基金分析页丢失扎堆页状态）
    await expect(
      main.getByRole('button', { name: /^返回基金分析$/ })
    ).toHaveCount(0)
  })

  test('TC-3.2 无 from 参数时（04 原生入口）不渲染差异提示与返回扎堆分析', async ({ page }) => {
    const lookupData = createTestReverseLookup()
    await mockReverseLookup(page, lookupData)
    // 04 原生入口：无 from 参数（从基金分析页进入）
    await page.goto(`${REVERSE_LOOKUP_PAGE}?symbol=600519`)

    const main = page.locator('main')

    // 断言：差异提示不渲染（04 原生零影响回归）
    await expect(main.getByTestId('fund-crowd-drilldown-hint')).toHaveCount(0)
    // 断言：「返回扎堆分析」入口不渲染
    await expect(main.getByTestId('back-to-fund-crowd')).toHaveCount(0)
    // 断言：原「返回基金分析」入口正常渲染（04 原生体验不受影响）
    await expect(
      main.getByRole('button', { name: /^返回基金分析$/ })
    ).toBeVisible()
  })

  test('TC-3.3 点击返回扎堆分析跳转到扎堆分析页', async ({ page }) => {
    const lookupData = createTestReverseLookup()
    await mockReverseLookup(page, lookupData)
    await page.goto(`${REVERSE_LOOKUP_PAGE}?symbol=600519&from=fund-crowd`)

    const main = page.locator('main')
    // 点击「返回扎堆分析」入口
    await main.getByTestId('back-to-fund-crowd').click()

    // 断言：路由跳转到扎堆分析页
    await expect(page).toHaveURL(/\/dashboard\/fund-crowd-analysis/)
  })
})
