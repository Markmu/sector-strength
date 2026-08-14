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
    // 宿主稳定（17 期补充）：量价面板内嵌融资融券图（/margin/trend），
    // 未 mock 会 401 触发竞态重定向——mock 空数据保持页面稳定
    await page.route('**/api/v1/margin/trend*', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: { latest: null, points: [], range: 30, hasMissingDates: false },
        }),
      })
    )
  })

  adminTest('TC-7.1 面板渲染于指数总览之后、走势图之前，双折线图 + 最新日期（AC-04 / FEAT-0003 AC-1/2）', async ({
    page,
  }) => {
    await installMarketMetricsMocks(page)

    // FEAT-0003：共享 watchlist mock 返回空列表会让走势/估值/权重区块整体不渲染，
    // 无法断言「面板在走势图之前」。此处覆写为非空（后注册的 route 优先），
    // 并 mock 三个子请求防止 401 竞态重定向（与宿主稳定原则一致）。
    const json = (body: unknown) => ({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(body),
    })
    await page.route('**/api/v1/index-monitor/watchlist*', (route) =>
      route.fulfill(
        json({
          success: true,
          data: { watchlist: [{ tsCode: '000300.SH', name: '沪深300' }] },
        })
      )
    )
    await page.route('**/api/v1/index-monitor/trend*', (route) =>
      route.fulfill(
        json({
          success: true,
          data: {
            series: [
              {
                tsCode: '000300.SH',
                name: '沪深300',
                points: [
                  { tradeDate: '2026-08-12', close: 4000 },
                  { tradeDate: '2026-08-13', close: 4010 },
                ],
              },
            ],
          },
        })
      )
    )
    await page.route('**/api/v1/index-monitor/valuation*', (route) =>
      route.fulfill(json({ success: true, data: { hasData: false, points: [] } }))
    )
    await page.route('**/api/v1/index-monitor/weights*', (route) =>
      route.fulfill(
        json({ success: true, data: { weights: [], concentration: null } })
      )
    )

    await page.goto(DASHBOARD)

    // 面板可见
    await expect(page.getByTestId('market-metrics-panel')).toBeVisible()

    // 「多指数走势对比」由 watchlist SWR 异步渲染，先等它出现再断言顺序
    await expect(
      page.getByRole('heading', { name: '多指数走势对比' })
    ).toBeVisible()

    // DOM 顺序（FEAT-0003 位置调整）：面板在「指数总览」标题之后、「多指数走势对比」之前
    await expectPanelRelativeToHeading(page, {
      after: { text: '指数总览' },
      before: { text: '多指数走势对比' },
    })

    // 双折线图（FEAT-0003）：成交额/平均价各一容器；旧单图与指标切换按钮已移除
    await expect(page.getByTestId('market-metrics-chart-amount')).toHaveCount(1)
    await expect(page.getByTestId('market-metrics-chart-amount')).toBeVisible()
    await expect(page.getByTestId('market-metrics-chart-price')).toHaveCount(1)
    await expect(page.getByTestId('market-metrics-chart-price')).toBeVisible()
    await expect(page.getByTestId('market-metrics-chart')).toHaveCount(0)
    expect(
      await page.getByTestId('market-metrics-metric-amountYuan').count()
    ).toBe(0)

    // 最近结果日可见（L1 降级：展示最近成功结果及其日期，非今天）
    await expect(page.getByTestId('market-metrics-latest-date')).toBeVisible()

    // 融资融券余额趋势区块存在（宿主 mock 为空数据 → 显示未同步提示）
    await expect(
      page.getByText('融资融券余额趋势')
    ).toBeVisible()
    await expect(
      page.getByTestId('market-metrics-chart-margin-empty')
    ).toBeVisible()
  })

  adminTest('TC-7.3 双折线断言：左成交额 line / 右平均价 line，无 bar series（FEAT-0003 AC-2）', async ({
    page,
  }) => {
    await installMarketMetricsMocks(page)
    await page.goto(DASHBOARD)
    await expect(page.getByTestId('market-metrics-panel')).toBeVisible()

    // 指标切换按钮组全部移除
    for (const m of ['amountYuan', 'volumeShares', 'averagePrice']) {
      expect(await page.getByTestId(`market-metrics-metric-${m}`).count()).toBe(0)
    }

    // 经 __echartsInst__ 测试钩子读两图 option：series 均为 line、名称正确、无 bar。
    // poll 到目标值为止（双图 dynamic 加载/首渲存在瞬时窗口，实例可能短暂未挂）
    const readSeries = (testid: string) =>
      page.evaluate((sel) => {
        const el = document.querySelector(sel) as
          | (HTMLDivElement & { __echartsInst__?: { getOption: () => unknown } })
          | null
        if (!el || !el.__echartsInst__) return null
        const opt = el.__echartsInst__.getOption() as {
          series: Array<{ name: string; type: string }>
        }
        return opt.series.map((s) => ({ name: s.name, type: s.type }))
      }, `[data-testid="${testid}"]`)

    await expect
      .poll(() => readSeries('market-metrics-chart-amount'), {
        message: '成交额图 echarts 实例应就绪且 series 为 line',
      })
      .toEqual([{ name: '成交额', type: 'line' }])

    await expect
      .poll(() => readSeries('market-metrics-chart-price'), {
        message: '平均价图 echarts 实例应就绪且 series 为 line',
      })
      .toEqual([{ name: '平均价', type: 'line' }])
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
    // 图表仍渲染（断线而非整体空；FEAT-0003 双图）
    await expect(page.getByTestId('market-metrics-chart-amount')).toBeVisible()
    await expect(page.getByTestId('market-metrics-chart-price')).toBeVisible()
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
    await expect(page.getByTestId('market-metrics-chart-amount')).toBeVisible()
  })
})

// ============================================================================
// 普通首页（dashboard/page.tsx 普通分支）
// ============================================================================

normalTest.describe('plan-07：普通首页市场量价面板', () => {
  normalTest.beforeEach(async ({ page }) => {
    // 宿主页稳定：market-index / heatmap / rankings，避免 401 跳 /login
    await mockNormalDashboardPrerequisites(page)
    // 宿主页稳定（17 期补充）：普通首页还挂有 MarginPanel，其 /margin/trend
    // 请求未 mock 会 401 触发竞态重定向——mock 空数据保持页面稳定
    await page.route('**/api/v1/margin/trend*', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: { latest: null, points: [], range: 30, hasMissingDates: false },
        }),
      })
    )
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
