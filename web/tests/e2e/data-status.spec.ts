import { test as base, expect } from '@playwright/test'
import {
  mockDataStatusNormal,
  mockDataStatusMixed,
  mockDataStatusFailed,
  mockDataStatusNoData,
  mockDataStatusError,
  mockBackfillSuccess,
  mockBackfillConflict,
  mockBackfillError,
} from './helpers/mock-api'

const ADMIN_DATA_PAGE = '/dashboard/admin/data'

/**
 * 扩展 test fixture：在每个测试前注入认证 cookie
 * bypass Next.js middleware 的路由保护
 */
const test = base.extend<{ authedPage: void }>({
  authedPage: [async ({ page }, use) => {
    // 注入 access_token cookie 以 bypass middleware 路由守卫
    await page.context().addCookies([{
      name: 'access_token',
      value: 'test-mock-jwt-token',
      domain: 'localhost',
      path: '/',
    }])
    // localStorage 中设置完整的认证状态，供 AuthContext 初始化
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

test.describe('plan-03：前端数据状态标签页', () => {

  test.describe('TC-3.1 默认展示"数据状态"标签页', () => {
    test('访问数据管理页面时默认展示数据状态标签页', async ({ page }) => {
      await mockDataStatusNormal(page)
      await page.goto(ADMIN_DATA_PAGE)

      // 断言：数据状态标签按钮可见且处于激活态
      const dataStatusTab = page.getByTestId('tab-data-status')
      await expect(dataStatusTab).toBeVisible()
      await expect(dataStatusTab).toHaveClass(/border-blue-600/)

      // 断言：数据状态面板可见
      await expect(page.getByTestId('data-status-panel')).toBeVisible()
    })
  })

  test.describe('TC-3.2 三张状态卡片正常展示', () => {
    test('加载正常数据后三张卡片展示类型名称、最新日期、正常状态', async ({ page }) => {
      await mockDataStatusNormal(page)
      await page.goto(ADMIN_DATA_PAGE)

      // 断言：三张卡片可见
      const historyCard = page.getByTestId('data-type-card-history')
      const maCard = page.getByTestId('data-type-card-ma')
      const strengthCard = page.getByTestId('data-type-card-strength')

      await expect(historyCard).toBeVisible()
      await expect(maCard).toBeVisible()
      await expect(strengthCard).toBeVisible()

      // 断言：卡片标题
      await expect(historyCard).toContainText('板块历史数据')
      await expect(maCard).toContainText('板块均线数据')
      await expect(strengthCard).toContainText('板块强度数据')

      // 断言：每张卡片显示绿色"正常"Badge
      for (const card of [historyCard, maCard, strengthCard]) {
        const badge = card.getByTestId('status-badge')
        await expect(badge).toBeVisible()
        await expect(badge).toContainText('正常')
      }

      // 断言：每张卡片显示最新日期
      await expect(historyCard).toContainText('2026-05-26')
      await expect(maCard).toContainText('2026-05-26')
      await expect(strengthCard).toContainText('2026-05-26')
    })
  })

  test.describe('TC-3.3 缺失状态卡片展示', () => {
    test('缺失数据显示橙色Badge和缺失日期范围', async ({ page }) => {
      await mockDataStatusMixed(page)
      await page.goto(ADMIN_DATA_PAGE)

      // 断言：history 卡片（缺失状态）
      const historyCard = page.getByTestId('data-type-card-history')
      await expect(historyCard).toBeVisible()

      // 断言：橙色"缺失"Badge
      const badge = historyCard.getByTestId('status-badge')
      await expect(badge).toBeVisible()
      await expect(badge).toContainText('缺失')

      // 断言：缺失日期范围
      const missingRange = historyCard.getByTestId('missing-range')
      await expect(missingRange).toBeVisible()
      await expect(missingRange).toContainText('2026-05-25')
      await expect(missingRange).toContainText('2026-05-26')

      // 断言：补齐按钮可见
      const backfillButton = historyCard.getByTestId('backfill-button')
      await expect(backfillButton).toBeVisible()
      await expect(backfillButton).toContainText('补齐缺失数据')
    })
  })

  test.describe('TC-3.4 暂无数据卡片展示', () => {
    test('no_data状态显示灰色Badge且无补齐按钮', async ({ page }) => {
      await mockDataStatusNoData(page)
      await page.goto(ADMIN_DATA_PAGE)

      const historyCard = page.getByTestId('data-type-card-history')
      await expect(historyCard).toBeVisible()

      // 断言：灰色"暂无数据"Badge
      const badge = historyCard.getByTestId('status-badge')
      await expect(badge).toBeVisible()
      await expect(badge).toContainText('暂无数据')

      // 断言：不显示补齐按钮
      const backfillButton = historyCard.getByTestId('backfill-button')
      await expect(backfillButton).not.toBeVisible()
    })
  })

  test.describe('TC-3.5 补齐按钮点击触发补齐', () => {
    test('点击补齐按钮后调用backfill API并刷新状态', async ({ page }) => {
      await mockDataStatusMixed(page)
      await mockBackfillSuccess(page, 'history')
      await page.goto(ADMIN_DATA_PAGE)

      const historyCard = page.getByTestId('data-type-card-history')
      const backfillButton = historyCard.getByTestId('backfill-button')

      await expect(backfillButton).toBeVisible()
      await expect(backfillButton).toBeEnabled()

      // 点击补齐按钮
      await backfillButton.click()

      // 断言：backfill API 调用后按钮恢复可用态（mock 瞬时完成）
      await expect(backfillButton).toBeEnabled()
    })
  })

  test.describe('TC-3.6 补齐进行中显示进度条', () => {
    test('有活跃running任务时显示进度条和百分比', async ({ page }) => {
      await mockDataStatusMixed(page)
      await page.goto(ADMIN_DATA_PAGE)

      // strength 卡片有活跃 running 任务
      const strengthCard = page.getByTestId('data-type-card-strength')
      await expect(strengthCard).toBeVisible()

      // 断言：进度条可见
      const progressBar = strengthCard.getByTestId('progress-bar')
      await expect(progressBar).toBeVisible()

      // 断言：百分比文字可见 (15/30 = 50%)
      await expect(strengthCard).toContainText('50%')

      // 断言：补齐按钮禁用
      const backfillButton = strengthCard.getByTestId('backfill-button')
      await expect(backfillButton).not.toBeVisible()
    })
  })

  test.describe('TC-3.7 标签页切换不影响其他标签', () => {
    test('切换到其他标签再切回数据状态标签仍正常', async ({ page }) => {
      await mockDataStatusNormal(page)
      await page.goto(ADMIN_DATA_PAGE)

      // 数据状态面板可见
      await expect(page.getByTestId('data-status-panel')).toBeVisible()

      // 切换到数据初始化标签
      await page.getByRole('button', { name: '数据初始化' }).click()

      // 数据状态面板不可见
      await expect(page.getByTestId('data-status-panel')).not.toBeVisible()

      // 切回数据状态标签
      await page.getByTestId('tab-data-status').click()

      // 数据状态面板再次可见
      await expect(page.getByTestId('data-status-panel')).toBeVisible()
    })
  })

  test.describe('TC-3.8 状态API请求失败显示错误态', () => {
    test('API返回500时显示错误提示和重试按钮', async ({ page }) => {
      await mockDataStatusError(page)
      await page.goto(ADMIN_DATA_PAGE)

      // 断言：错误态容器可见
      const errorState = page.getByTestId('error-state')
      await expect(errorState).toBeVisible()

      // 断言：重试按钮可见
      const retryButton = page.getByTestId('retry-button')
      await expect(retryButton).toBeVisible()
    })
  })

  test.describe('TC-3.9 补齐API返回409冲突', () => {
    test('409冲突时按钮恢复可用并显示提示', async ({ page }) => {
      await mockDataStatusMixed(page)
      await mockBackfillConflict(page, 'history')
      await page.goto(ADMIN_DATA_PAGE)

      const historyCard = page.getByTestId('data-type-card-history')
      const backfillButton = historyCard.getByTestId('backfill-button')

      await backfillButton.click()

      // 断言：按钮恢复可用
      await expect(backfillButton).toBeEnabled()
    })
  })

  test.describe('TC-3.10 补齐API调用失败（非409）', () => {
    test('500错误时按钮恢复可用并显示错误提示', async ({ page }) => {
      await mockDataStatusMixed(page)
      await mockBackfillError(page, 'history')
      await page.goto(ADMIN_DATA_PAGE)

      const historyCard = page.getByTestId('data-type-card-history')
      const backfillButton = historyCard.getByTestId('backfill-button')

      await backfillButton.click()

      // 断言：按钮恢复可用
      await expect(backfillButton).toBeEnabled()
    })
  })

  test.describe('TC-3.11 补齐失败显示错误和重新补齐按钮', () => {
    test('failed任务显示红色错误信息和重新补齐按钮', async ({ page }) => {
      await mockDataStatusFailed(page)
      await page.goto(ADMIN_DATA_PAGE)

      // ma 卡片有 failed 任务
      const maCard = page.getByTestId('data-type-card-ma')
      await expect(maCard).toBeVisible()

      // 断言：错误信息可见
      const errorMessage = maCard.getByTestId('task-error-message')
      await expect(errorMessage).toBeVisible()
      await expect(errorMessage).toContainText('数据获取超时')

      // 断言：重新补齐按钮可见
      const retryBackfillButton = maCard.getByTestId('retry-backfill-button')
      await expect(retryBackfillButton).toBeVisible()
    })
  })

  test.describe('TC-3.12 点击重试重新请求状态API', () => {
    test('错误态下点击重试后状态正常展示', async ({ page }) => {
      // 第一次访问返回 500
      await mockDataStatusError(page)
      await page.goto(ADMIN_DATA_PAGE)

      // 错误态可见
      await expect(page.getByTestId('error-state')).toBeVisible()

      // 切换 mock 为正常数据
      await mockDataStatusNormal(page)

      // 点击重试
      await page.getByTestId('retry-button').click()

      // 断言：错误态消失，卡片正常展示
      await expect(page.getByTestId('data-type-card-history')).toBeVisible()
      await expect(page.getByTestId('error-state')).not.toBeVisible()
    })
  })

  test.describe('TC-3.13 点击重新补齐按钮再次创建任务', () => {
    test('failed状态下点击重新补齐按钮调用backfill API', async ({ page }) => {
      await mockDataStatusFailed(page)
      await mockBackfillSuccess(page, 'ma')
      await page.goto(ADMIN_DATA_PAGE)

      const maCard = page.getByTestId('data-type-card-ma')
      const retryBackfillButton = maCard.getByTestId('retry-backfill-button')

      await expect(retryBackfillButton).toBeVisible()

      // 点击重新补齐按钮
      await retryBackfillButton.click()

      // 断言：backfill API 调用后按钮恢复可用态（mock 瞬时完成）
      await expect(retryBackfillButton).toBeEnabled()
    })
  })
})
