import { test as base, expect } from '@playwright/test'
import {
  mockBrokerMonths,
  mockBrokerMonthsEmpty,
  mockStockRanking,
  mockBrokerList,
  mockBrokerDetail,
  mockBrokerSectorRankings,
  installBrokerFullMocks,
  createTestStockRanking,
  createTestSectorRankings,
} from './helpers/mock-broker-recommend-api'
import {
  mockTrendRanking,
  createTestTrendRanking,
  createTestTrendRankingSingleMonth,
  createTestTrendRankingPaged,
  createTestTrendRankingEmpty,
} from './helpers/mock-broker-recommend-trend-api'

const BROKER_ANALYSIS_PAGE = '/dashboard/broker-recommend-analysis'
const SEARCH_DEBOUNCE_BUFFER = 500

/**
 * 普通用户认证 fixture（复用 broker-recommend-analysis.spec.ts 范式）
 * 本项目自定义 JWT（token 存 localStorage + Cookie access_token），非 NextAuth。
 */
const userTest = base.extend<{ authedPage: void }>({
  authedPage: [
    async ({ page }, use) => {
      await page.context().addCookies([
        { name: 'access_token', value: 'test-mock-jwt-token', domain: 'localhost', path: '/' },
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
 * 趋势视图完整 mock：09 双视图 mock + 趋势榜 mock
 */
async function installTrendFullMocks(page: import('@playwright/test').Page) {
  await installBrokerFullMocks(page)
  await mockTrendRanking(page, createTestTrendRanking())
}

// ============================================================================
// plan-02：前端推荐趋势视图（第三视图 + Sparkline + 趋势榜表格）
// 覆盖 AC-01/02/05/06/08/09/10/11/12
// 当前阶段：red（趋势视图尚未实现，预期全部失败）
// ============================================================================

userTest.describe('plan-02：前端推荐趋势视图（red 阶段）', () => {
  userTest.describe('视图入口与状态（AC-01/10）', () => {
    userTest('TC-2.1 视图切换器出现"推荐趋势"第三选项 + 切换后月份选择器隐藏', async ({ page }) => {
      await installTrendFullMocks(page)
      await page.goto(BROKER_ANALYSIS_PAGE)

      // AC-01：视图切换器存在"推荐趋势"第三选项，与股票/券商平级
      const trendBtn = page.getByTestId('broker-view-trend')
      await expect(trendBtn).toBeVisible()
      await expect(trendBtn).toContainText('推荐趋势')

      // 切换前月份选择器可见（默认股票维度）
      await expect(page.getByTestId('broker-month-selector')).toBeVisible()

      // 切换到趋势视图
      await trendBtn.click()
      await expect(trendBtn).toHaveAttribute('aria-pressed', 'true')

      // AC-01：切换到趋势视图后月份选择器隐藏
      await expect(page.getByTestId('broker-month-selector')).toHaveCount(0)
    })

    userTest('TC-2.2 切到趋势隐藏板块筛选/板块分布，切回股票恢复月份选择器（AC-10）', async ({ page }) => {
      await installTrendFullMocks(page)
      await page.goto(BROKER_ANALYSIS_PAGE)

      // 默认股票维度：月份选择器 + 板块筛选 + 板块分布均可见
      await expect(page.getByTestId('broker-month-selector')).toBeVisible()
      await expect(page.getByTestId('broker-sector-type-selector')).toBeVisible()

      // 切到趋势视图
      await page.getByTestId('broker-view-trend').click()
      await expect(page.getByTestId('broker-month-selector')).toHaveCount(0)
      await expect(page.getByTestId('broker-sector-type-selector')).toHaveCount(0)
      await expect(page.getByTestId('broker-sector-filter')).toHaveCount(0)

      // AC-10：切回股票维度 → 月份选择器恢复（默认最新月）、搜索清空
      await page.getByTestId('broker-view-stock').click()
      await expect(page.getByTestId('broker-month-selector')).toBeVisible()
      await expect(page.getByTestId('broker-month-selector')).toContainText('2026-06')
      await expect(page.getByTestId('broker-search-input')).toHaveValue('')
    })

    userTest('TC-2.3 切到趋势视图清空搜索 + 回第1页（AC-10）', async ({ page }) => {
      await installTrendFullMocks(page)
      await page.goto(BROKER_ANALYSIS_PAGE)

      // 股票维度下输入搜索词
      await page.getByTestId('broker-search-input').fill('600')
      await page.waitForTimeout(SEARCH_DEBOUNCE_BUFFER)
      await expect(page.getByTestId('broker-search-input')).toHaveValue('600')

      // 切到趋势视图 → 搜索清空（AC-10）
      await page.getByTestId('broker-view-trend').click()
      await expect(page.getByTestId('broker-search-input')).toHaveValue('')
    })
  })

  userTest.describe('趋势榜展示（AC-02/03）', () => {
    userTest('TC-2.4 趋势榜按连续月数降序展示 + 四指标列（AC-02）', async ({ page }) => {
      await installTrendFullMocks(page)
      await page.goto(BROKER_ANALYSIS_PAGE)

      // 切到趋势视图
      await page.getByTestId('broker-view-trend').click()

      // AC-02：趋势榜表格渲染
      const table = page.getByTestId('broker-trend-table')
      await expect(table).toBeVisible()

      const rows = table.locator('tbody tr')
      await expect(rows.first()).toContainText('600519') // 榜首（连续月数 3 最大）

      // 连续月数降序：600519(3) → 300750(1) → 688981(1)
      await expect(rows.first()).toContainText('3') // 连续月数
      await expect(rows.nth(1)).toContainText('300750')
      await expect(rows.nth(2)).toContainText('688981')

      // 四指标列内容：连续月数 / 累计家数 / 最新月家数
      await expect(rows.first()).toContainText('12') // 累计家数
      await expect(rows.first()).toContainText('5') // 最新月家数
    })

    userTest('TC-2.5 多级排序稳定（AC-03：连续月数↓→累计家数↓→最新月家数↓）', async ({ page }) => {
      await installTrendFullMocks(page)
      await page.goto(BROKER_ANALYSIS_PAGE)
      await page.getByTestId('broker-view-trend').click()

      const rows = page.getByTestId('broker-trend-table').locator('tbody tr')
      await expect(rows).toHaveCount(3)

      // 300750 与 688981 连续月数均为 1、累计家数均为 5；
      // 最新月家数 300750=3 > 688981=1，故 300750 排前
      await expect(rows.nth(1)).toContainText('300750')
      await expect(rows.nth(2)).toContainText('688981')
    })
  })

  userTest.describe('Sparkline 渲染（AC-05/07）', () => {
    userTest('TC-2.6 每行 Sparkline 渲染（AC-05）', async ({ page }) => {
      await installTrendFullMocks(page)
      await page.goto(BROKER_ANALYSIS_PAGE)
      await page.getByTestId('broker-view-trend').click()

      // AC-05：每行 Sparkline 按 data-testid 命名渲染
      await expect(page.getByTestId('broker-trend-sparkline-600519')).toBeVisible()
      await expect(page.getByTestId('broker-trend-sparkline-300750')).toBeVisible()
      await expect(page.getByTestId('broker-trend-sparkline-688981')).toBeVisible()
    })

    userTest('TC-2.7 断档股 Sparkline 含 0 点（AC-07）', async ({ page }) => {
      await installTrendFullMocks(page)
      await page.goto(BROKER_ANALYSIS_PAGE)
      await page.getByTestId('broker-view-trend').click()

      // 300750 是断档股（2026-05 无推荐），Sparkline 应正常渲染
      const spark = page.getByTestId('broker-trend-sparkline-300750')
      await expect(spark).toBeVisible()
      // 断档股连续月数从最新月向前计到断档即停 = 1
      const rows = page.getByTestId('broker-trend-table').locator('tbody tr')
      await expect(rows.nth(1)).toContainText('300750')
      await expect(rows.nth(1)).toContainText('1') // 连续月数 1
    })
  })

  userTest.describe('行展开月度明细（AC-06）', () => {
    userTest('TC-2.8 展开按月降序展示家数与券商（前3+省略，AC-06）', async ({ page }) => {
      await installTrendFullMocks(page)
      await page.goto(BROKER_ANALYSIS_PAGE)
      await page.getByTestId('broker-view-trend').click()

      // 点击展开控件（600519 连续推荐，3 个月每月均有券商）
      await page.getByTestId('broker-trend-expand-600519').click()

      const detail = page.getByTestId('broker-trend-expand-content-600519')
      await expect(detail).toBeVisible()

      // AC-06：展开后按月降序（新→旧）展示，三行均存在
      const row0606 = page.getByTestId('broker-trend-month-row-600519-2026-06')
      const row0505 = page.getByTestId('broker-trend-month-row-600519-2026-05')
      const row0404 = page.getByTestId('broker-trend-month-row-600519-2026-04')
      await expect(row0606).toBeVisible()
      await expect(row0505).toBeVisible()
      await expect(row0404).toBeVisible()

      // AC-06 核心：每月都展示券商（按月作用域断言，避免跨月同名券商 strict mode 冲突）
      // 2026-06：5 家券商，topBrokers 前3省略（+2 家）
      await expect(row0606.getByText('中信证券')).toBeVisible()
      await expect(row0606.getByText(/\+2\s*家/)).toBeVisible()
      // 2026-05：4 家券商，topBrokers 前3省略（+1 家）
      await expect(row0505.getByText('中信证券')).toBeVisible()
      await expect(row0505.getByText(/\+1\s*家/)).toBeVisible()
      // 2026-04：3 家券商，无省略
      await expect(row0404.getByText('中信证券')).toBeVisible()
      await expect(row0404.getByText('华泰证券')).toBeVisible()
      await expect(row0404.getByText(/\+\d+\s*家/)).toHaveCount(0)

      // 再次点击收起
      await page.getByTestId('broker-trend-expand-600519').click()
      await expect(detail).toHaveCount(0)
    })

    userTest('TC-2.9 展开某月无推荐显示家数0券商"—"（AC-06）', async ({ page }) => {
      await installTrendFullMocks(page)
      await page.goto(BROKER_ANALYSIS_PAGE)
      await page.getByTestId('broker-view-trend').click()

      // 300750 是断档股，2026-05 brokerCount=0
      await page.getByTestId('broker-trend-expand-300750').click()

      const detail = page.getByTestId('broker-trend-expand-content-300750')
      await expect(detail).toBeVisible()

      // 按月降序：2026-06 → 2026-05 → 2026-04，三行均存在
      const row0606 = page.getByTestId('broker-trend-month-row-300750-2026-06')
      const row0505 = page.getByTestId('broker-trend-month-row-300750-2026-05')
      const row0404 = page.getByTestId('broker-trend-month-row-300750-2026-04')
      await expect(row0606).toBeVisible()
      await expect(row0505).toBeVisible()
      await expect(row0404).toBeVisible()

      // AC-06：2026-05 家数 0，券商列显示占位符
      await expect(row0505).toContainText('0 家')
      await expect(row0505.getByText('-', { exact: true })).toBeVisible()

      // 对比：有推荐月份不应显示"—"
      await expect(row0606.getByText('中信证券')).toBeVisible()
      await expect(row0606.getByText('-', { exact: true })).toHaveCount(0)
    })
  })

  userTest.describe('分页（AC-08）', () => {
    userTest('TC-2.10 分页 total>20 显示分页器（AC-08）', async ({ page }) => {
      await installBrokerFullMocks(page)
      await mockTrendRanking(page, createTestTrendRankingPaged())
      await page.goto(BROKER_ANALYSIS_PAGE)
      await page.getByTestId('broker-view-trend').click()

      // AC-08：total=25 > pageSize=20，分页器显示
      await expect(page.getByTestId('broker-trend-pagination')).toBeVisible()
    })

    userTest('TC-2.11 分页 total≤20 隐藏分页器（AC-08）', async ({ page }) => {
      await installTrendFullMocks(page)
      await page.goto(BROKER_ANALYSIS_PAGE)
      await page.getByTestId('broker-view-trend').click()

      // total=3 ≤ 20，分页器隐藏
      await expect(page.getByTestId('broker-trend-pagination')).toHaveCount(0)
    })
  })

  userTest.describe('搜索（AC-09）', () => {
    userTest('TC-2.12 趋势视图搜索股票命中 + 回第1页 + 清空恢复（AC-09）', async ({ page }) => {
      await installTrendFullMocks(page)
      await page.goto(BROKER_ANALYSIS_PAGE)
      await page.getByTestId('broker-view-trend').click()

      const table = page.getByTestId('broker-trend-table')
      const rows = table.locator('tbody tr')
      await expect(rows).toHaveCount(3)

      // 搜索命中（代码前缀）
      await page.getByTestId('broker-search-input').fill('600')
      await page.waitForTimeout(SEARCH_DEBOUNCE_BUFFER)
      await expect(rows).toHaveCount(1)
      await expect(rows.first()).toContainText('600519')

      // 搜索命中（名称包含）
      await page.getByTestId('broker-search-input').fill('茅台')
      await page.waitForTimeout(SEARCH_DEBOUNCE_BUFFER)
      await expect(rows).toHaveCount(1)
      await expect(rows.first()).toContainText('600519')

      // 无匹配提示
      await page.getByTestId('broker-search-input').fill('不存在的股票')
      await page.waitForTimeout(SEARCH_DEBOUNCE_BUFFER)
      await expect(page.getByText('未找到匹配结果', { exact: false })).toBeVisible()

      // 清空恢复完整榜单
      await page.getByTestId('broker-search-input').fill('')
      await page.waitForTimeout(SEARCH_DEBOUNCE_BUFFER)
      await expect(rows).toHaveCount(3)
    })
  })

  userTest.describe('单月数据降级（AC-11）', () => {
    userTest('TC-2.13 单月数据趋势榜正常 + Sparkline 单点不报错（AC-11）', async ({ page }) => {
      await installBrokerFullMocks(page)
      await mockTrendRanking(page, createTestTrendRankingSingleMonth())
      await page.goto(BROKER_ANALYSIS_PAGE)
      await page.getByTestId('broker-view-trend').click()

      const table = page.getByTestId('broker-trend-table')
      const rows = table.locator('tbody tr')
      await expect(rows).toHaveCount(1)
      await expect(rows.first()).toContainText('600519')

      // AC-11：仅一个已同步月份，连续月数均为 1
      await expect(rows.first()).toContainText('1')

      // AC-11：Sparkline 单点（values.length===1）正常渲染不报错
      await expect(page.getByTestId('broker-trend-sparkline-600519')).toBeVisible()
    })
  })

  userTest.describe('空状态（AC-12）', () => {
    userTest('TC-2.14 数据从未同步整页空状态（复用 09 hasNoData，AC-12）', async ({ page }) => {
      // months.hasData=false → 09 hasNoData 分支仅渲染标题+空状态块，
      // 不渲染视图切换器（趋势视图同样不展示）
      await mockBrokerMonthsEmpty(page)
      await mockStockRanking(page, createTestStockRanking())
      await mockBrokerSectorRankings(page, { ...createTestSectorRankings(), hasData: false })
      await mockTrendRanking(page, createTestTrendRankingEmpty())
      await page.goto(BROKER_ANALYSIS_PAGE)

      await expect(page.getByTestId('broker-page')).toBeVisible({ timeout: 15000 })
      await expect(page.getByTestId('broker-empty-state')).toBeVisible()
      await expect(page.getByText('暂无券商金股数据', { exact: false })).toBeVisible()

      // AC-12：空状态下视图切换器不渲染，趋势视图同样不展示
      await expect(page.getByTestId('broker-view-trend')).toHaveCount(0)
      await expect(page.getByTestId('broker-trend-table')).toHaveCount(0)
    })
  })
})
