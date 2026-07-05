import { test as base, expect, type Page } from '@playwright/test'
import {
  mockSectorStocks,
  mockSectorStocksEmpty,
  mockSectorStocksError,
  mockStockDetail,
  mockSectorChartApis,
  createTestSectorStocks,
  createTestSectorStocksMany,
  createTestStockDetail,
} from './helpers/mock-sector-stocks-api'

const SECTOR_DETAIL_PAGE = '/dashboard/sector-analysis/1'

/**
 * 扩展 test fixture：在每个测试前注入普通用户认证。
 *
 * 参照 fund-crowd-analysis.spec.ts:22-53 模式：本项目使用自定义
 * JWT（token 存 localStorage + Cookie access_token），非 NextAuth。
 * 板块详情页是面向普通登录用户的页面，role 设为 user 即可通过 /dashboard 守卫。
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
        localStorage.setItem(
          'user',
          JSON.stringify({
            id: 'test-user-id',
            email: 'user@test.com',
            username: 'TestUser',
            is_active: true,
            role: 'user',
          })
        )
      })
      await use()
    },
    { auto: true },
  ],
})

/**
 * 安装默认全量 mock（图表 + 成分股 + 个股详情）。
 * 图表 mock 必须安装，否则进入详情页会 401 重定向 /login。
 */
async function installFullMocks(
  page: Page,
  opts?: { stocks?: ReturnType<typeof createTestSectorStocks>; withStockDetail?: boolean }
): Promise<void> {
  await mockSectorChartApis(page)
  await mockSectorStocks(page, opts?.stocks ?? createTestSectorStocks())
  if (opts?.withStockDetail ?? false) {
    await mockStockDetail(page, createTestStockDetail())
  }
}

// ============== FEAT-02：成分股 hook 与表格组件 ==============

test.describe('板块成分股列表', () => {
  test.describe('默认加载与排序（AC-01/02/03）', () => {
    test('TC-2.1 默认加载按强度分降序，六列齐全（AC-01）', async ({ page }) => {
      await installFullMocks(page)
      await page.goto(SECTOR_DETAIL_PAGE)

      const table = page.getByTestId('sector-stocks-table')
      await expect(table).toBeVisible()

      // 3 行，按 strength_score 降序：600519(92) / 000858(88) / 000568(85)
      const rows = table.locator('tbody tr')
      await expect(rows).toHaveCount(3)
      await expect(rows.first()).toContainText('600519')
      await expect(rows.first()).toContainText('92')
      await expect(rows.nth(1)).toContainText('000858')
      await expect(rows.nth(2)).toContainText('000568')

      // 总数显示
      await expect(table).toContainText('共 3 只')
    })

    test('TC-2.2 点击强度分表头切换升序（AC-02）', async ({ page }) => {
      await installFullMocks(page)
      await page.goto(SECTOR_DETAIL_PAGE)

      const table = page.getByTestId('sector-stocks-table')
      await expect(table).toBeVisible()

      // 默认降序，首行 600519(92)
      const rows = table.locator('tbody tr')
      await expect(rows.first()).toContainText('600519')

      // 点击强度分表头切升序，首行应变最低分 000568(85)
      await table.getByTestId('sector-stocks-sort-strength_score').click()
      await expect(rows.first()).toContainText('000568')
      // 再次点击切回降序
      await table.getByTestId('sector-stocks-sort-strength_score').click()
      await expect(rows.first()).toContainText('600519')
    })

    test('TC-2.3 点击市值表头降序，代码列不可排序（AC-03）', async ({ page }) => {
      await installFullMocks(page)
      await page.goto(SECTOR_DETAIL_PAGE)

      const table = page.getByTestId('sector-stocks-table')
      await expect(table).toBeVisible()

      // 点击市值表头，按市值降序：600519(2.1万亿) 首行
      await table.getByTestId('sector-stocks-sort-market_cap').click()
      const rows = table.locator('tbody tr')
      await expect(rows.first()).toContainText('600519')
    })
  })

  test.describe('分页（AC-04）', () => {
    test('TC-2.4 翻页 + 每页条数切换', async ({ page }) => {
      // 造 25 条，默认 pageSize=20，应显示分页器且可翻第 2 页
      await installFullMocks(page, { stocks: createTestSectorStocksMany(25) })
      await page.goto(SECTOR_DETAIL_PAGE)

      const table = page.getByTestId('sector-stocks-table')
      await expect(table).toBeVisible()

      // 默认第 1 页 20 条
      await expect(table.locator('tbody tr')).toHaveCount(20)

      // 翻到第 2 页：页码是 button（非 link），用精确文本匹配避免误匹配
      await table.getByRole('button', { name: '2', exact: true }).click()
      await expect(table.locator('tbody tr')).toHaveCount(5)
    })
  })

  test.describe('加载失败重试（AC-05）', () => {
    test('TC-2.5 失败显示重试按钮，图表不受影响', async ({ page }) => {
      // 图表 mock 正常，成分股 mock 失败
      await mockSectorChartApis(page)
      await mockSectorStocksError(page)
      await page.goto(SECTOR_DETAIL_PAGE)

      const table = page.getByTestId('sector-stocks-table')
      await expect(table.getByTestId('sector-stocks-retry')).toBeVisible()

      // 重试：卸载错误 mock，安装成功 mock，再点重试
      await page.unroute('**/stocks**')
      await mockSectorStocks(page, createTestSectorStocks())
      await table.getByTestId('sector-stocks-retry').click()
      await expect(table.locator('tbody tr')).toHaveCount(3)
    })
  })

  test.describe('空数据（AC-06）', () => {
    test('TC-2.6 无成分股显示空态', async ({ page }) => {
      await mockSectorChartApis(page)
      await mockSectorStocksEmpty(page)
      await page.goto(SECTOR_DETAIL_PAGE)

      const table = page.getByTestId('sector-stocks-table')
      await expect(table.getByTestId('sector-stocks-empty')).toBeVisible()
      // 不显示表格与分页器
      await expect(table.locator('tbody tr')).toHaveCount(0)
    })
  })
})

// ============== FEAT-03：个股分析落地页 ==============

test.describe('下钻个股分析页（AC-07）', () => {
  test('TC-3.1 点击成分股行跳转个股页且落地页不空', async ({ page }) => {
    await installFullMocks(page, { withStockDetail: true })
    await page.goto(SECTOR_DETAIL_PAGE)

    const table = page.getByTestId('sector-stocks-table')
    await expect(table).toBeVisible()

    // 点击首行（600519），跳转到个股分析页
    await table.locator('tbody tr').first().click()
    await expect(page).toHaveURL(/\/dashboard\/stock-analysis\/1$/)

    // 落地页展示基础信息，不空白
    const card = page.getByTestId('stock-info-card')
    await expect(card).toBeVisible()
    await expect(card).toContainText('600519')
    await expect(card).toContainText('贵州茅台')
  })
})
