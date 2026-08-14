import { test as base, expect, type Page } from '@playwright/test'
import {
  installMarketMetricsMocks,
  mockMarketMetricsTrend,
  mockMarketMetricsTrendEmpty,
  mockMarketMetricsTrendGaps,
  mockMarketMetricsTrendError,
  mockIndexMonitorOverview,
  mockIndexMonitorWatchlist,
  mockNormalDashboardPrerequisites,
} from './helpers/mock-market-metrics-api'

/**
 * 首页市场量价面板 E2E spec（第 16 期 plan-07）
 *
 * 本文件由 test-e2e skill 在 plan-07 red-e2e 阶段创建，覆盖 AC-04/05/06/12。
 *
 * 被测功能：MarketMetricsPanel 组件（plan-07 Task 3），插入两套首页：
 * - 管理员首页（IndexMonitorPage，关键指数区之前）
 * - 普通首页（dashboard/page.tsx，快捷入口后、市场强度前）
 *
 * red 阶段：MarketMetricsPanel 组件尚未创建，两套首页未插入面板 →
 * 所有用例因 `market-metrics-panel` 等 data-testid 不存在而预期失败。
 *
 * 认证：复用 etf-monitor.spec.ts / admin-etf-sync.spec.ts 范式——本项目自定义 JWT
 * （token 存 localStorage + Cookie access_token），非 NextAuth。isAdmin = user.role === 'admin'
 * （AuthContext）。通过两套 fixture 分别注入 admin / user 角色。
 *
 * 宿主页稳定：管理员首页 IndexMonitorPage 会请求 index-monitor overview/watchlist；
 * 普通首页会请求 market-index/heatmap/rankings。这些请求用 mock token 打真实后端会被
 * 401 拒绝触发 handleUnauthorizedRedirect 跳 /login。故 beforeEach 装宿主 mock 让页面稳定，
 * 失败原因落在「组件未实现」而非环境错误。
 */

const DASHBOARD = '/dashboard'

// ---------- 认证 fixture（admin / user 两套） ----------

function createAuthedTest(role: 'admin' | 'user') {
  return base.extend<{ authedPage: void }>({
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
        await page.addInitScript((r) => {
          localStorage.setItem('accessToken', 'test-mock-jwt-token')
          localStorage.setItem('refreshToken', 'test-mock-refresh-token')
          localStorage.setItem('tokenType', 'Bearer')
          localStorage.setItem('expiresIn', '3600')
          localStorage.setItem(
            'user',
            JSON.stringify({
              id: r === 'admin' ? 'test-admin-id' : 'test-user-id',
              email: r === 'admin' ? 'admin@test.com' : 'user@test.com',
              username: r === 'admin' ? 'TestAdmin' : 'TestUser',
              is_active: true,
              role: r,
            })
          )
        }, role)
        await use()
      },
      { auto: true },
    ],
  })
}

const adminTest = createAuthedTest('admin')
const normalTest = createAuthedTest('user')

// ---------- DOM 顺序断言工具 ----------

/**
 * 断言「面板在关键区块之前/之后」（AC-04 布局顺序）。
 * 用 compareDocumentPosition 判定 DOM 顺序，比布局坐标更稳定。
 *
 * @param beforeSelector 先出现的 CSS 选择器（如 [data-testid="market-metrics-panel"]）
 * @param afterRole / afterText 后出现的标题文本（如「指数总览」）
 */
async function expectPanelRelativeToHeading(
  page: Page,
  opts: {
    before?: { text: string } // panel 应在该标题之前
    after?: { text: string } // panel 应在该标题之后
  }
) {
  const rel = await page.evaluate(
    ({ beforeText, afterText }) => {
      const panel = document.querySelector('[data-testid="market-metrics-panel"]')
      if (!panel) return { found: 'no-panel' as const }
      const headings = Array.from(document.querySelectorAll('h2, h3, a'))
      // 注意：before 与 after 需在同一遍里都计算（原实现 beforeText 分支提前 return，
      // 导致同时传 before+after 时 afterOk 恒为 undefined）。此处改为顺序累加结果。
      const result: { found: string; beforeOk?: boolean; afterOk?: boolean } = {
        found: 'ok',
      }
      if (beforeText) {
        const target = headings.find((h) =>
          (h.textContent || '').includes(beforeText)
        )
        if (!target) return { found: 'no-before-target' as const }
        // DOCUMENT_POSITION_FOLLOWING(4) = target 在 panel 之后 → panel 在 target 之前
        result.beforeOk =
          (panel.compareDocumentPosition(target) &
            Node.DOCUMENT_POSITION_FOLLOWING) !==
          0
      }
      if (afterText) {
        const target = headings.find((h) =>
          (h.textContent || '').includes(afterText)
        )
        if (!target) return { found: 'no-after-target' as const }
        // panel 应在 target 之后 = target 在 panel 之前 = DOCUMENT_POSITION_PRECEDING(2)
        result.afterOk =
          (panel.compareDocumentPosition(target) &
            Node.DOCUMENT_POSITION_PRECEDING) !==
          0
      }
      return result
    },
    {
      beforeText: opts.before?.text ?? null,
      afterText: opts.after?.text ?? null,
    }
  )
  expect(rel.found, 'market-metrics-panel 应存在').toBe('ok')
  if (opts.before) {
    expect(rel.beforeOk, `面板应在「${opts.before.text}」之前`).toBe(true)
  }
  if (opts.after) {
    expect(rel.afterOk, `面板应在「${opts.after.text}」之后`).toBe(true)
  }
}

// ============================================================================
// 管理员首页（IndexMonitorPage）
// ============================================================================

adminTest.describe('plan-07：管理员首页市场量价面板', () => {
  adminTest.beforeEach(async ({ page }) => {
    // 宿主页稳定：
    // - index-monitor overview/watchlist 让 IndexOverviewCards 渲染「指数总览」（TC-7.1 DOM 顺序）
    // - normal-dashboard（market-index/heatmap/rankings）：AuthContext 首帧 user=null →
    //   isAdmin=false → /dashboard 短暂渲染普通分支并发起这些请求；用 mock token 打真实后端
    //   会 401 触发 handleUnauthorizedRedirect 跳 /login。一并 mock 避免竞态重定向。
    await mockIndexMonitorOverview(page)
    await mockIndexMonitorWatchlist(page)
    await mockNormalDashboardPrerequisites(page)
  })

  adminTest('TC-7.1 面板渲染于关键指数区之前，默认成交额柱图 + 最新日期（AC-04）', async ({
    page,
  }) => {
    await installMarketMetricsMocks(page)
    await page.goto(DASHBOARD)

    // 面板可见
    await expect(page.getByTestId('market-metrics-panel')).toBeVisible()

    // DOM 顺序：面板在「指数总览」标题之前
    await expectPanelRelativeToHeading(page, { before: { text: '指数总览' } })

    // 默认成交额柱图：单实例 ECharts 容器可见
    await expect(page.getByTestId('market-metrics-chart')).toHaveCount(1)
    await expect(page.getByTestId('market-metrics-chart')).toBeVisible()

    // 最近结果日可见（L1 降级：展示最近成功结果及其日期，非今天）
    await expect(page.getByTestId('market-metrics-latest-date')).toBeVisible()
  })

  adminTest('TC-7.3 三指标切换：成交额柱→成交量柱→平均价折线（AC-04）', async ({
    page,
  }) => {
    await installMarketMetricsMocks(page)
    await page.goto(DASHBOARD)
    await expect(page.getByTestId('market-metrics-panel')).toBeVisible()

    // 默认成交额 active
    await expect(page.getByTestId('market-metrics-metric-amountYuan')).toHaveAttribute(
      'aria-pressed',
      'true'
    )

    // 切成交量（柱图）
    await page.getByTestId('market-metrics-metric-volumeShares').click()
    await expect(page.getByTestId('market-metrics-chart')).toHaveCount(1)
    await expect(
      page.getByTestId('market-metrics-metric-volumeShares')
    ).toHaveAttribute('aria-pressed', 'true')
    await expect(page.getByTestId('market-metrics-metric-amountYuan')).toHaveAttribute(
      'aria-pressed',
      'false'
    )

    // 切平均价（折线）
    await page.getByTestId('market-metrics-metric-averagePrice').click()
    await expect(page.getByTestId('market-metrics-chart')).toHaveCount(1)
    await expect(
      page.getByTestId('market-metrics-metric-averagePrice')
    ).toHaveAttribute('aria-pressed', 'true')
  })

  adminTest('TC-7.4 30/90/250 范围切换：发起对应 range 请求且无整页刷新（AC-05）', async ({
    page,
  }) => {
    await installMarketMetricsMocks(page)
    await page.goto(DASHBOARD)
    await expect(page.getByTestId('market-metrics-panel')).toBeVisible()

    // 点 90：等待 range=90 请求命中
    const req90 = page.waitForRequest(
      (req) =>
        req.url().includes('/market-metrics/trend') &&
        req.url().includes('range=90')
    )
    await page.getByTestId('market-metrics-range-90').click()
    await req90
    // 无整页刷新：URL 不变
    await expect(page).toHaveURL(/\/dashboard/)

    // 点 250：等待 range=250 请求命中
    const req250 = page.waitForRequest(
      (req) =>
        req.url().includes('/market-metrics/trend') &&
        req.url().includes('range=250')
    )
    await page.getByTestId('market-metrics-range-250').click()
    await req250
    await expect(page).toHaveURL(/\/dashboard/)

    // 切回 30
    const req30 = page.waitForRequest(
      (req) =>
        req.url().includes('/market-metrics/trend') &&
        req.url().includes('range=30')
    )
    await page.getByTestId('market-metrics-range-30').click()
    await req30
    await expect(page).toHaveURL(/\/dashboard/)
  })

  adminTest('TC-7.5 缺口断线：部分日期无数据提示可见（AC-06）', async ({ page }) => {
    await mockMarketMetricsTrendGaps(page)
    await page.goto(DASHBOARD)

    // 缺口提示可见
    await expect(page.getByTestId('market-metrics-missing-hint')).toBeVisible()
    // 图表仍渲染（断线而非整体空）
    await expect(page.getByTestId('market-metrics-chart')).toBeVisible()
  })

  adminTest('TC-7.6 空态-管理员：显示「前往数据管理」链接', async ({ page }) => {
    await mockMarketMetricsTrendEmpty(page)
    await page.goto(DASHBOARD)

    // 空态容器可见 + 管理员链接可见，指向数据管理
    await expect(page.getByTestId('market-metrics-empty')).toBeVisible()
    const link = page.getByTestId('market-metrics-empty-admin-link')
    await expect(link).toBeVisible()
    await expect(link).toHaveAttribute('href', '/dashboard/admin/data')
  })

  adminTest('TC-7.8 加载失败重试：仅局部 mutate 重发 trend，不影响指数区（AC-12）', async ({
    page,
  }) => {
    // 请求计数（监听全部请求，区分 trend / index-monitor overview）
    const counts = { trend: 0, overview: 0 }
    page.on('request', (req) => {
      const u = req.url()
      if (u.includes('/market-metrics/trend')) counts.trend += 1
      if (u.includes('/index-monitor/overview')) counts.overview += 1
    })

    // trend 返回 500 → 错误态
    await mockMarketMetricsTrendError(page)
    await page.goto(DASHBOARD)

    await expect(page.getByTestId('market-metrics-error')).toBeVisible()
    await expect(page.getByTestId('market-metrics-retry')).toBeVisible()

    const trendBeforeRetry = counts.trend
    const overviewBeforeRetry = counts.overview

    // 切 trend 为 200 后点重试 → 仅重发 trend
    await mockMarketMetricsTrend(page)
    await page.getByTestId('market-metrics-retry').click()

    // 等待新的 trend 请求命中（计数 +1）
    await expect
      .poll(() => counts.trend, { message: 'trend 请求计数应 +1' })
      .toBe(trendBeforeRetry + 1)
    // index-monitor overview 计数不变（局部 mutate，不刷新整页/指数区）
    await expect
      .poll(() => counts.overview, { message: 'overview 请求计数不应增加' })
      .toBe(overviewBeforeRetry)

    // 重试后图表恢复渲染
    await expect(page.getByTestId('market-metrics-chart')).toBeVisible()
  })
})

// ============================================================================
// 普通首页（dashboard/page.tsx 普通分支）
// ============================================================================

normalTest.describe('plan-07：普通首页市场量价面板', () => {
  normalTest.beforeEach(async ({ page }) => {
    // 宿主页稳定：market-index / heatmap / rankings，避免 401 跳 /login
    await mockNormalDashboardPrerequisites(page)
  })

  normalTest('TC-7.2 面板渲染于快捷入口后、市场强度之前（AC-04）', async ({ page }) => {
    await installMarketMetricsMocks(page)
    await page.goto(DASHBOARD)

    // 面板可见
    await expect(page.getByTestId('market-metrics-panel')).toBeVisible()

    // DOM 顺序：面板在「基金分析」快捷入口之后、「市场强度指数」之前
    await expectPanelRelativeToHeading(page, {
      after: { text: '基金分析' },
      before: { text: '市场强度指数' },
    })
  })

  normalTest('TC-7.7 空态-普通用户：显示纯文案，无链接', async ({ page }) => {
    await mockMarketMetricsTrendEmpty(page)
    await page.goto(DASHBOARD)

    // 空态容器可见
    await expect(page.getByTestId('market-metrics-empty')).toBeVisible()
    // 普通用户无「前往数据管理」链接
    await expect(page.getByTestId('market-metrics-empty-admin-link')).toHaveCount(0)
  })
})
