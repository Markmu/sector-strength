import { test as base, expect } from '@playwright/test'
import {
  mockBrokerMonths,
  mockBrokerMonthsEmpty,
  mockStockRanking,
  mockBrokerList,
  mockBrokerDetail,
  mockBrokerRecommendSyncSuccess,
  mockBrokerRecommendSyncError,
  mockBrokerTaskStatusCompleted,
  mockBrokerTaskStatusFailed,
  mockBrokerSyncRecords,
  mockBrokerSectorRankings,
  installBrokerFullMocks,
  createTestStockRanking,
  createTestBrokerDetail,
  createTestSectorRankings,
} from './helpers/mock-broker-recommend-api'

const BROKER_ANALYSIS_PAGE = '/dashboard/broker-recommend-analysis'
const DATA_MANAGEMENT_PAGE = '/dashboard/admin/data'

/**
 * 普通用户认证 fixture（复用 fund-crowd-analysis.spec.ts 范式）
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
 * 管理员认证 fixture（复用 admin-fund-sync.spec.ts 范式）
 */
const adminTest = base.extend<{ authedPage: void }>({
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
            id: 'test-admin-id',
            email: 'admin@test.com',
            username: 'TestAdmin',
            is_active: true,
            role: 'admin',
          })
        )
      })
      await use()
    },
    { auto: true },
  ],
})

const SEARCH_DEBOUNCE_BUFFER = 500

/**
 * 数据管理页 catch-all mock：未匹配的 /api/v1/admin/* GET 请求返回空成功，
 * 避免页面加载时其他 tab 的面板（DataStatusPanel 等）发起未 mock 请求触发 401 重定向。
 * 仅用于 admin 数据管理页测试，不拦截已注册的 broker mock（route 注册顺序 LIFO，
 * broker mock 更具体且先注册，会优先匹配）。
 */
async function mockAdminCatchAll(page: import('@playwright/test').Page) {
  await page.route('**/api/v1/admin/**', async (route) => {
    if (route.request().method() !== 'GET') {
      await route.fallback()
      return
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ success: true, data: { tasks: [], total: 0 } }),
    })
  })
}

// ============================================================================
// 用户侧券商金股分析页（AC-01 ~ AC-14）
// ============================================================================

userTest.describe('plan-03：券商每月荐股分析页（用户侧）', () => {
  userTest.describe('入口与菜单（AC-01）', () => {
    userTest('TC-3.1 侧边栏"券商每月荐股"菜单项并进入页面', async ({ page }) => {
      await installBrokerFullMocks(page)
      // 直接访问 broker 页（侧边栏在所有 dashboard 页都渲染），验证菜单存在
      await page.goto(BROKER_ANALYSIS_PAGE)
      await expect(page.getByTestId('broker-page')).toBeVisible()

      const menuLink = page.getByRole('link', { name: '券商每月荐股' })
      await expect(menuLink).toBeVisible()
      await menuLink.click()

      await expect(page).toHaveURL(/\/dashboard\/broker-recommend-analysis/)
    })
  })

  userTest.describe('股票维度排行榜（AC-02/03/06/07）', () => {
    userTest('TC-3.2 默认股票维度·最新月排行榜（家数降序，前 3 家省略）', async ({ page }) => {
      await installBrokerFullMocks(page)
      await page.goto(BROKER_ANALYSIS_PAGE)

      await expect(page.getByTestId('broker-view-stock')).toHaveAttribute('aria-pressed', 'true')

      const rows = page.locator('[data-testid="broker-ranking-table"] tbody tr')
      await expect(rows).toHaveCount(3)
      await expect(rows.first()).toContainText('600519')
      await expect(rows.first()).toContainText('5')
      await expect(rows.nth(1)).toContainText('300750')
      await expect(rows.nth(2)).toContainText('688981')

      const firstRow = rows.first()
      await expect(firstRow.getByText('中信证券')).toBeVisible()
      await expect(firstRow.getByText('中金公司')).toBeVisible()
      await expect(firstRow.getByText('国泰君安')).toBeVisible()
      await expect(firstRow.getByText(/\+2\s*家/)).toBeVisible()
    })

    userTest('TC-3.3 行展开全部推荐券商（预加载无 loading）', async ({ page }) => {
      await installBrokerFullMocks(page)
      await page.goto(BROKER_ANALYSIS_PAGE)

      const rows = page.locator('[data-testid="broker-ranking-table"] tbody tr')
      await expect(rows).toHaveCount(3)

      await page.getByTestId('broker-expand-688981').click()

      // 展开内容在独立行（colSpan），用 page 级 testid 定位
      // 688981 仅 1 家券商（中信证券），展开显示全部推荐券商（不再显示理由）
      const detail = page.getByTestId('broker-expand-content-688981')
      await expect(detail).toBeVisible()
      await expect(detail.getByText('中信证券')).toBeVisible()

      await page.getByTestId('broker-expand-688981').click()
      await expect(detail).toHaveCount(0)
    })

    userTest('TC-3.4 分页 total≤20 隐藏分页器', async ({ page }) => {
      await installBrokerFullMocks(page)
      await page.goto(BROKER_ANALYSIS_PAGE)

      await expect(page.locator('[data-testid="broker-ranking-table"] tbody tr')).toHaveCount(3)
      await expect(page.getByTestId('broker-pagination')).toHaveCount(0)
    })
  })

  userTest.describe('板块分布排行榜（行业/概念/地域，各 Top5）', () => {
    userTest('TC-3.SE.1 三类型板块排行榜展示，按股票数降序', async ({ page }) => {
      await installBrokerFullMocks(page)
      await page.goto(BROKER_ANALYSIS_PAGE)

      // 板块排行榜容器可见
      await expect(page.getByTestId('broker-sector-rankings')).toBeVisible()
      // 三类型卡片均渲染
      await expect(page.getByTestId('broker-sector-card-industry')).toBeVisible()
      await expect(page.getByTestId('broker-sector-card-concept')).toBeVisible()
      await expect(page.getByTestId('broker-sector-card-region')).toBeVisible()

      // 行业维度 Top1 = 食品饮料（12 只）
      const industryCard = page.getByTestId('broker-sector-card-industry')
      await expect(
        industryCard.getByText('食品饮料', { exact: false })
      ).toBeVisible()
      await expect(industryCard.getByText('12 只')).toBeVisible()
    })

    userTest('TC-3.SE.2 跟随月份切换联动（空状态隐藏区块）', async ({ page }) => {
      // 从未同步 → 整页空状态，板块排行榜区块不渲染
      await mockBrokerMonthsEmpty(page)
      await mockStockRanking(page, createTestStockRanking())
      await mockBrokerSectorRankings(page)
      await page.goto(BROKER_ANALYSIS_PAGE)
      await expect(page.getByTestId('broker-page')).toBeVisible({ timeout: 15000 })
      await expect(page.getByTestId('broker-empty-state')).toBeVisible()
      await expect(page.getByTestId('broker-sector-rankings')).toHaveCount(0)
    })
  })

  userTest.describe('股票维度排行榜板块筛选（行业/概念/地域）', () => {
    userTest('TC-3.SF.1 行业板块筛选生效（选食品饮料只剩 600519）', async ({ page }) => {
      await installBrokerFullMocks(page)
      await page.goto(BROKER_ANALYSIS_PAGE)

      // 默认显示全部 3 只
      const rows = page.locator('[data-testid="broker-ranking-table"] tbody tr')
      await expect(rows).toHaveCount(3)

      // 板块筛选器可见（仅股票维度）
      await expect(page.getByTestId('broker-sector-type-selector')).toBeVisible()
      await expect(page.getByTestId('broker-sector-filter')).toBeVisible()

      // 选"食品饮料"→ 只剩 600519
      await page.getByTestId('broker-sector-filter').click()
      await page.getByRole('option', { name: '食品饮料' }).click()
      await expect(rows).toHaveCount(1)
      await expect(rows.first()).toContainText('600519')
    })

    userTest('TC-3.SF.2 切换板块类型清空板块名（行业→概念）', async ({ page }) => {
      await installBrokerFullMocks(page)
      await page.goto(BROKER_ANALYSIS_PAGE)

      // 行业维度选"食品饮料"
      await page.getByTestId('broker-sector-filter').click()
      await page.getByRole('option', { name: '食品饮料' }).click()
      await expect(page.getByTestId('broker-sector-filter')).toContainText('食品饮料')

      // 切到概念维度 → 板块名清空（显示"全部概念"）
      await page.getByTestId('broker-sector-type-concept').click()
      await expect(page.getByTestId('broker-sector-filter')).toContainText('全部概念')

      // 恢复全部 3 只
      await expect(
        page.locator('[data-testid="broker-ranking-table"] tbody tr')
      ).toHaveCount(3)
    })

    userTest('TC-3.SF.3 券商维度筛选器隐藏', async ({ page }) => {
      await installBrokerFullMocks(page)
      await page.goto(BROKER_ANALYSIS_PAGE)

      // 切到券商维度
      await page.getByTestId('broker-view-broker').click()

      // 板块筛选器隐藏（仅股票维度生效）
      await expect(page.getByTestId('broker-sector-type-selector')).toHaveCount(0)
      await expect(page.getByTestId('broker-sector-filter')).toHaveCount(0)
    })
  })

  userTest.describe('券商维度分组反查（AC-04）', () => {
    userTest('TC-3.5 券商维度分组 + 推荐股票数 + 不改变月份', async ({ page }) => {
      await installBrokerFullMocks(page)
      await page.goto(BROKER_ANALYSIS_PAGE)

      await page.getByTestId('broker-view-broker').click()
      await expect(page.getByTestId('broker-view-broker')).toHaveAttribute('aria-pressed', 'true')
      await expect(page.getByTestId('broker-view-stock')).toHaveAttribute('aria-pressed', 'false')

      const groups = page.locator('[data-testid="broker-group-list"] [data-testid^="broker-broker-"]')
      await expect(groups).toHaveCount(2)
      await expect(groups.first()).toContainText('中信证券')
      await expect(groups.first()).toContainText('3')
      await expect(groups.nth(1)).toContainText('中金公司')

      await expect(page.getByTestId('broker-month-selector')).toContainText('2026-06')
    })
  })

  userTest.describe('月份切换（AC-05/14）', () => {
    userTest('TC-3.6 月份切换清搜索词 + 回第 1 页 + 保持视图', async ({ page }) => {
      await installBrokerFullMocks(page)
      await page.goto(BROKER_ANALYSIS_PAGE)

      await page.getByTestId('broker-search-input').fill('600')
      await page.waitForTimeout(SEARCH_DEBOUNCE_BUFFER)
      await expect(page.getByTestId('broker-search-input')).toHaveValue('600')

      // MonthSelector 为原生 select，用 selectOption 选 2026-04（mock 返回空）
      await page.locator('[data-testid="broker-month-selector"] select').selectOption('2026-04-01')

      await expect(page.getByTestId('broker-search-input')).toHaveValue('')
      await expect(page.getByTestId('broker-view-stock')).toHaveAttribute('aria-pressed', 'true')

      await expect(page.getByText('所选月份暂无数据', { exact: false })).toBeVisible()
    })
  })

  userTest.describe('空状态（AC-09）', () => {
    userTest('TC-3.7 从未同步展示整页空状态', async ({ page }) => {
      // 仅 mock months 为空 + stock-ranking + sector-rankings
      // （monthsLoading 期间 enabled 暂为 true，sector-rankings 请求可能先发出，需 mock 防 401）
      await mockBrokerMonthsEmpty(page)
      await mockStockRanking(page, createTestStockRanking())
      await mockBrokerSectorRankings(page, { ...createTestSectorRankings(), hasData: false })
      await page.goto(BROKER_ANALYSIS_PAGE)
      await expect(page.getByTestId('broker-page')).toBeVisible({ timeout: 15000 })

      await expect(page.getByTestId('broker-empty-state')).toBeVisible()
      await expect(page.getByText('暂无券商金股数据', { exact: false })).toBeVisible()
      await expect(page.getByTestId('broker-ranking-table')).toHaveCount(0)
    })
  })

  userTest.describe('股票搜索（AC-11）', () => {
    userTest('TC-3.8 股票搜索命中 + 无结果提示 + 清空恢复', async ({ page }) => {
      await installBrokerFullMocks(page)
      await page.goto(BROKER_ANALYSIS_PAGE)

      const rows = page.locator('[data-testid="broker-ranking-table"] tbody tr')
      await expect(rows).toHaveCount(3)

      await page.getByTestId('broker-search-input').fill('600')
      await page.waitForTimeout(SEARCH_DEBOUNCE_BUFFER)
      await expect(rows).toHaveCount(1)
      await expect(rows.first()).toContainText('600519')

      await page.getByTestId('broker-search-input').fill('茅台')
      await page.waitForTimeout(SEARCH_DEBOUNCE_BUFFER)
      await expect(rows).toHaveCount(1)

      await page.getByTestId('broker-search-input').fill('不存在的股票')
      await page.waitForTimeout(SEARCH_DEBOUNCE_BUFFER)
      await expect(page.getByText('未找到匹配结果', { exact: false })).toBeVisible()

      await page.getByTestId('broker-search-input').fill('')
      await page.waitForTimeout(SEARCH_DEBOUNCE_BUFFER)
      await expect(rows).toHaveCount(3)
    })
  })

  userTest.describe('券商搜索（AC-12）', () => {
    userTest('TC-3.9 券商搜索命中 + 无结果提示', async ({ page }) => {
      await installBrokerFullMocks(page)
      await page.goto(BROKER_ANALYSIS_PAGE)

      await page.getByTestId('broker-view-broker').click()

      const groups = page.locator('[data-testid="broker-group-list"] [data-testid^="broker-broker-"]')
      await expect(groups).toHaveCount(2)

      await page.getByTestId('broker-search-input').fill('中信')
      await page.waitForTimeout(SEARCH_DEBOUNCE_BUFFER)
      await expect(groups).toHaveCount(1)
      await expect(groups.first()).toContainText('中信证券')

      await page.getByTestId('broker-search-input').fill('不存在的券商')
      await page.waitForTimeout(SEARCH_DEBOUNCE_BUFFER)
      await expect(page.getByText('未找到匹配结果', { exact: false })).toBeVisible()
    })
  })

  userTest.describe('券商维度展开懒加载（AC-13）', () => {
    userTest('TC-3.10 展开懒加载骨架 → 明细', async ({ page }) => {
      await installBrokerFullMocks(page)
      await page.goto(BROKER_ANALYSIS_PAGE)

      await page.getByTestId('broker-view-broker').click()
      await page.getByTestId('broker-broker-中信证券').click()

      const detail = page.locator('[data-testid="broker-detail-content-中信证券"]')
      await expect(detail).toBeVisible()
      await expect(detail.getByText('600519')).toBeVisible()
      await expect(detail.getByText('688981')).toBeVisible()
    })

    userTest('TC-3.11 懒加载失败"加载失败，请重试"可重试', async ({ page }) => {
      await mockBrokerMonths(page)
      await mockStockRanking(page, createTestStockRanking())
      await mockBrokerList(page)
      await mockBrokerDetail(page, createTestBrokerDetail(), { fail: true })
      await mockBrokerSectorRankings(page)
      await page.goto(BROKER_ANALYSIS_PAGE)

      await page.getByTestId('broker-view-broker').click()
      await page.getByTestId('broker-broker-中信证券').click()

      const detail = page.locator('[data-testid="broker-detail-content-中信证券"]')
      await expect(detail.getByText('加载失败，请重试', { exact: false })).toBeVisible()

      await mockBrokerDetail(page, createTestBrokerDetail())
      await detail.getByRole('button', { name: /重试|重新加载/ }).click()
      await expect(detail.getByText('600519')).toBeVisible()
    })
  })

  userTest.describe('状态重置（AC-14）', () => {
    userTest('TC-3.12 切视图清搜索词 + 回第 1 页', async ({ page }) => {
      await installBrokerFullMocks(page)
      await page.goto(BROKER_ANALYSIS_PAGE)

      await page.getByTestId('broker-search-input').fill('600')
      await page.waitForTimeout(SEARCH_DEBOUNCE_BUFFER)
      await expect(page.getByTestId('broker-search-input')).toHaveValue('600')

      await page.getByTestId('broker-view-broker').click()
      await expect(page.getByTestId('broker-search-input')).toHaveValue('')

      await page.getByTestId('broker-search-input').fill('中信')
      await page.waitForTimeout(SEARCH_DEBOUNCE_BUFFER)

      await page.getByTestId('broker-view-stock').click()
      await expect(page.getByTestId('broker-search-input')).toHaveValue('')
    })
  })
})

// ============================================================================
// 管理员券商金股同步面板（AC-08-ui-1 ~ ui-5）
// ============================================================================

adminTest.describe('plan-03：管理员券商金股同步面板（数据管理 tab，AC-08-ui-1~5）', () => {
  adminTest.describe('入口与面板展示（AC-08-ui-1/ui-2）', () => {
    adminTest('TC-3.13 数据管理页"券商金股同步"tab 可见并切换', async ({ page }) => {
      await mockAdminCatchAll(page)
      await mockBrokerRecommendSyncSuccess(page)
      await mockBrokerSyncRecords(page)
      await page.goto(DATA_MANAGEMENT_PAGE)
      await expect(page.locator('main')).toBeVisible({ timeout: 15000 })

      // AC-08-ui-1：数据管理页存在"券商金股同步"tab
      const tab = page.getByTestId('tab-broker-recommend')
      await expect(tab).toBeVisible()
      // 点击切换到该 tab，面板渲染（h3 标题）
      await tab.click()
      const main = page.locator('main')
      await expect(
        main.getByRole('heading', { level: 3, name: '券商金股同步' })
      ).toBeVisible()
    })

    adminTest('TC-3.14 月份选择器选月份 + 点击同步创建任务', async ({ page }) => {
      const taskId = 'task-broker-recommend-001'
      await mockAdminCatchAll(page)
      await mockBrokerRecommendSyncSuccess(page, taskId)
      await mockBrokerTaskStatusCompleted(page, taskId)
      await mockBrokerSyncRecords(page)
      await page.goto(DATA_MANAGEMENT_PAGE)
      await page.getByTestId('tab-broker-recommend').click()

      const main = page.locator('main')
      const monthSelect = main.locator('select')
      await expect(monthSelect).toBeVisible()

      const options = monthSelect.locator('option')
      const optionCount = await options.count()
      if (optionCount > 1) {
        await monthSelect.selectOption({ index: 1 })
      }

      const syncButton = main.getByRole('button', { name: '同步', exact: true })
      await expect(syncButton).toBeEnabled()
      await syncButton.click()

      await expect(main.getByText('券商金股同步完成', { exact: false })).toBeVisible({ timeout: 15000 })
    })
  })

  adminTest.describe('同步进度与失败（AC-08-ui-3/ui-5）', () => {
    adminTest('TC-3.15 任务执行失败展示失败 Toast', async ({ page }) => {
      const taskId = 'task-broker-recommend-001'
      await mockAdminCatchAll(page)
      await mockBrokerRecommendSyncSuccess(page, taskId)
      await mockBrokerTaskStatusFailed(page, taskId, 'Tushare 接口调用失败')
      await mockBrokerSyncRecords(page)
      await page.goto(DATA_MANAGEMENT_PAGE)
      await page.getByTestId('tab-broker-recommend').click()

      const main = page.locator('main')
      const monthSelect = main.locator('select')
      const options = monthSelect.locator('option')
      const optionCount = await options.count()
      if (optionCount > 1) {
        await monthSelect.selectOption({ index: 1 })
      }
      await main.getByRole('button', { name: '同步', exact: true }).click()

      await expect(main.getByText(/同步失败/)).toBeVisible()
    })

    adminTest('TC-3.16 创建任务接口失败展示错误 Toast', async ({ page }) => {
      await mockAdminCatchAll(page)
      await mockBrokerRecommendSyncError(page)
      await mockBrokerSyncRecords(page)
      await page.goto(DATA_MANAGEMENT_PAGE)
      await page.getByTestId('tab-broker-recommend').click()

      const main = page.locator('main')
      const monthSelect = main.locator('select')
      const options = monthSelect.locator('option')
      const optionCount = await options.count()
      if (optionCount > 1) {
        await monthSelect.selectOption({ index: 1 })
      }
      await main.getByRole('button', { name: '同步', exact: true }).click()

      await expect(main.getByText(/创建同步任务失败/)).toBeVisible()
    })
  })
})
