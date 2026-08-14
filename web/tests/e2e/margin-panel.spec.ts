import { test as base, expect, type Page } from '@playwright/test'
import {
  createTestMarginTrend,
  installMarginMocks,
  mockMarginTrend,
  mockMarginTrendEmpty,
  mockMarginTrendGaps,
  mockMarginTrendError,
} from './helpers/mock-margin-api'
import {
  mockMarketMetricsTrend,
  mockNormalDashboardPrerequisites,
} from './helpers/mock-market-metrics-api'

/**
 * 首页融资融券面板 E2E spec（第 17 期 plan-07）
 *
 * 本文件由 test-e2e skill 在 plan-07 red-e2e 阶段创建，覆盖 AC-6（面板渲染/范围切换）
 * 与缺口/空态/错误重试，对应 plan-07 §实现规格-5 的 4 条 Given/When/Then 场景。
 *
 * 被测功能：MarginPanel 组件（plan-07 Task 3），仅插入普通用户首页
 * （dashboard/page.tsx 非管理员分支，MarketMetricsPanel 之后）。管理员首页
 * IndexMonitorPage 分支不在 spec REQ-7 范围内（不动、不测）。
 *
 * red 阶段：MarginPanel 组件尚未创建、dashboard 未插入面板 →
 * 所有用例因 `margin-panel` 等 data-testid 不存在而预期失败。
 *
 * 认证：复用 market-metrics-panel.spec.ts 范式——本项目自定义 JWT（token 存
 * localStorage + Cookie access_token），非 NextAuth。仅用 user 角色 fixture
 * （面板只挂非管理员分支）。
 *
 * 宿主页稳定：普通首页会请求 market-index/heatmap/rankings（16 期 helper
 * mockNormalDashboardPrerequisites），且相邻 MarketMetricsPanel 会请求
 * /market-metrics/trend。这些请求用 mock token 打真实后端会被 401 拒绝触发
 * handleUnauthorizedRedirect 跳 /login。故 beforeEach 一并 mock 让页面稳定，
 * 失败原因落在「MarginPanel 组件未实现」而非环境错误。
 */

const DASHBOARD = '/dashboard'

/** legend 4 项（AC-6，顺序即 ECharts option legend.data） */
const LEGEND_ITEMS = ['融资余额', '两融合计余额', '融券余额', '融资买入额']
/** 双 Y 轴分轴（AC-6）：左轴（yAxisIndex 0）万亿级 rzye+rzrqye、右轴（1）千亿级 rqye+rzmre */
const LEFT_AXIS_SERIES = ['融资余额', '两融合计余额']
const RIGHT_AXIS_SERIES = ['融券余额', '融资买入额']

// ---------- 认证 fixture（仅 user：面板只挂非管理员分支） ----------

const normalTest = base.extend<{ authedPage: void }>({
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

// ---------- 断言工具 ----------

/** 与 MarginPanel formatBillion 同式（显示层 ÷1e8 转亿，zh-CN 2 位小数） */
function formatBillion(val: number | null): string {
  if (val === null || val === undefined) return '—'
  return (val / 1e8).toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

/**
 * 断言 DOM 顺序（AC-6 布局）：margin-panel 在 market-metrics-panel 之后、
 * 「市场强度指数」标题之前。用 compareDocumentPosition 判定，比布局坐标稳定。
 */
async function expectMarginPanelOrder(page: Page): Promise<void> {
  const rel = await page.evaluate(() => {
    const market = document.querySelector('[data-testid="market-metrics-panel"]')
    const margin = document.querySelector('[data-testid="margin-panel"]')
    if (!market || !margin) return { found: 'missing-panel' as const }
    const headings = Array.from(document.querySelectorAll('h2, h3'))
    const strength = headings.find((h) => (h.textContent || '').includes('市场强度指数'))
    if (!strength) return { found: 'missing-strength-heading' as const }
    return {
      found: 'ok' as const,
      // market 在 margin 之前 = PRECEDING(2)
      afterMetrics:
        (margin.compareDocumentPosition(market) & Node.DOCUMENT_POSITION_PRECEDING) !== 0,
      // strength 在 margin 之后 = FOLLOWING(4)
      beforeStrength:
        (margin.compareDocumentPosition(strength) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0,
    }
  })
  expect(rel.found, 'market-metrics-panel 与 margin-panel 均应存在').toBe('ok')
  expect(rel.found === 'ok' && rel.afterMetrics, 'margin-panel 应在 market-metrics-panel 之后').toBe(
    true
  )
  expect(
    rel.found === 'ok' && rel.beforeStrength,
    'margin-panel 应在「市场强度指数」之前'
  ).toBe(true)
}

interface ChartSeriesInfo {
  name: string
  type: string
  yAxisIndex: number
  connectNulls: boolean
  data: Array<number | null>
}

/**
 * 读取 margin-chart 容器上 ECharts 实例的 option（legend / series）。
 *
 * 依赖 implementer 在 onChartReady 时将实例挂到容器 DOM（__echartsInst__ 测试钩子，
 * 见用例文档）：ECharts canvas 文案（legend）与 series 数据无法从 DOM 断言——
 * 实例注册表在 echarts 模块闭包内，window.echarts 不存在。
 */
async function readChartOption(
  page: Page
): Promise<{ legend: string[] | null; series: ChartSeriesInfo[] } | null> {
  return page.evaluate(() => {
    const el = document.querySelector('[data-testid="margin-chart"]') as
      | (HTMLElement & { __echartsInst__?: { getOption: () => unknown } })
      | null
    const inst = el?.__echartsInst__
    if (!el || !inst) return null
    const opt = inst.getOption() as {
      legend?: Array<{ data?: string[] }> | { data?: string[] }
      series?: Array<Record<string, unknown>>
    }
    const legend = Array.isArray(opt.legend)
      ? (opt.legend[0]?.data ?? null)
      : (opt.legend?.data ?? null)
    const series = ((opt.series ?? []) as Array<Record<string, unknown>>).map((s) => ({
      name: String(s.name),
      type: String(s.type),
      yAxisIndex: Number(s.yAxisIndex ?? 0),
      connectNulls: Boolean(s.connectNulls),
      data: (s.data ?? []) as Array<number | null>,
    }))
    return { legend: legend ?? null, series }
  })
}

// ============================================================================
// 普通首页（dashboard/page.tsx 非管理员分支，MarketMetricsPanel 之后）
// ============================================================================

normalTest.describe('plan-07：普通首页融资融券面板', () => {
  normalTest.beforeEach(async ({ page }) => {
    // 宿主页稳定：
    // - market-index / heatmap / rankings（避免 401 跳 /login）
    // - 相邻 16 期 MarketMetricsPanel 的 /market-metrics/trend（非被测功能，稳定即可）
    await mockNormalDashboardPrerequisites(page)
    await mockMarketMetricsTrend(page)
  })

  normalTest('TC-7.1 面板渲染：market-metrics 之后 + 4 卡片（亿元）+ 双 Y 轴 legend（AC-6）', async ({
    page,
  }) => {
    await installMarginMocks(page)
    await page.goto(DASHBOARD)

    // 面板可见 + DOM 顺序（在 market-metrics-panel 之后、市场强度之前）
    await expect(page.getByTestId('margin-panel')).toBeVisible()
    await expectMarginPanelOrder(page)

    // 最近结果日（L1 降级：最近成功结果及其日期，非今天）
    const trend = createTestMarginTrend({ range: 30 })
    const latest = trend.latest!
    await expect(page.getByTestId('margin-latest-date')).toContainText(latest.tradeDate)

    // 4 张最新值卡片：值 = fixture ÷1e8（zh-CN 2 位小数）+ 亿元标签
    const cards: Array<{ testid: string; label: string; value: number | null }> = [
      { testid: 'margin-card-rzye', label: '融资余额', value: latest.rzye },
      { testid: 'margin-card-rqye', label: '融券余额', value: latest.rqye },
      { testid: 'margin-card-rzrqye', label: '两融合计余额', value: latest.rzrqye },
      { testid: 'margin-card-rzmre', label: '融资买入额', value: latest.rzmre },
    ]
    for (const c of cards) {
      const card = page.getByTestId(c.testid)
      await expect(card).toBeVisible()
      await expect(card).toContainText(c.label)
      await expect(card).toContainText(formatBillion(c.value))
      await expect(card).toContainText('亿元')
    }

    // 默认范围 30 active
    await expect(page.getByTestId('margin-range-30')).toHaveAttribute('aria-pressed', 'true')
    await expect(page.getByTestId('margin-range-90')).toHaveAttribute('aria-pressed', 'false')

    // ECharts：单实例容器 + canvas 可见
    await expect(page.getByTestId('margin-chart')).toHaveCount(1)
    await expect(
      page.locator('[data-testid="margin-chart"] canvas').first()
    ).toBeVisible()

    // legend 恰为 4 项；4 条 series 全 line / connectNulls:false / 双 Y 轴分轴正确
    const chart = await readChartOption(page)
    expect(chart, '应能读取 ECharts 实例（margin-chart 容器 __echartsInst__ 钩子）').not.toBeNull()
    expect(chart!.legend).toEqual(LEGEND_ITEMS)
    expect(chart!.series).toHaveLength(4)
    const byName = new Map(chart!.series.map((s) => [s.name, s]))
    for (const s of chart!.series) {
      expect(s.type, `${s.name} 应为 line`).toBe('line')
      expect(s.connectNulls, `${s.name} 应 connectNulls:false`).toBe(false)
      expect(s.data, `${s.name} 应有 30 个点`).toHaveLength(trend.points.length)
    }
    for (const name of LEFT_AXIS_SERIES) {
      expect(byName.get(name)?.yAxisIndex, `${name} 应在左轴（yAxisIndex 0）`).toBe(0)
    }
    for (const name of RIGHT_AXIS_SERIES) {
      expect(byName.get(name)?.yAxisIndex, `${name} 应在右轴（yAxisIndex 1）`).toBe(1)
    }
  })

  normalTest('TC-7.2 范围切换 30/90/250：发起对应 range 请求且无整页刷新（AC-6）', async ({
    page,
  }) => {
    const marginRequests: string[] = []
    page.on('request', (req) => {
      if (req.url().includes('/api/v1/margin/trend')) marginRequests.push(req.url())
    })

    await installMarginMocks(page)
    await page.goto(DASHBOARD)
    await expect(page.getByTestId('margin-panel')).toBeVisible()

    // 标记 window：后续交互若发生整页刷新，标记即丢失
    await page.evaluate(() => {
      ;(window as unknown as Record<string, unknown>).__marginE2eNoReload = 'alive'
    })

    // 点 90：等待 range=90 请求命中
    const req90 = page.waitForRequest(
      (r) => r.url().includes('/api/v1/margin/trend') && r.url().includes('range=90')
    )
    await page.getByTestId('margin-range-90').click()
    await req90
    await expect(page.getByTestId('margin-range-90')).toHaveAttribute('aria-pressed', 'true')

    // 点 250：等待 range=250 请求命中
    const req250 = page.waitForRequest(
      (r) => r.url().includes('/api/v1/margin/trend') && r.url().includes('range=250')
    )
    await page.getByTestId('margin-range-250').click()
    await req250

    // 初始 30 + 显式切换 90 / 250 均发起过请求
    expect(marginRequests.some((u) => u.includes('range=30'))).toBe(true)
    expect(marginRequests.some((u) => u.includes('range=90'))).toBe(true)
    expect(marginRequests.some((u) => u.includes('range=250'))).toBe(true)

    // 无整页刷新：URL 不变 + window 标记仍在
    await expect(page).toHaveURL(/\/dashboard/)
    expect(
      await page.evaluate(
        () => (window as unknown as Record<string, unknown>).__marginE2eNoReload
      )
    ).toBe('alive')
  })

  normalTest('TC-7.3 缺口断线：缺失日六指标 null 非 0 + 提示可见（AC-5/AC-6）', async ({
    page,
  }) => {
    await mockMarginTrendGaps(page)
    await page.goto(DASHBOARD)

    await expect(page.getByTestId('margin-panel')).toBeVisible()
    // 缺口提示可见
    await expect(page.getByTestId('margin-missing-hint')).toBeVisible()
    await expect(page.getByTestId('margin-missing-hint')).toContainText('部分日期无数据')
    // 图表仍渲染（断线而非整体空）
    await expect(
      page.locator('[data-testid="margin-chart"] canvas').first()
    ).toBeVisible()

    // series 数据：缺口索引为 null 而非 0（null 点未被填充）
    const chart = await readChartOption(page)
    expect(chart, '应能读取 ECharts 实例（margin-chart 容器 __echartsInst__ 钩子）').not.toBeNull()

    const gapTrend = createTestMarginTrend({ gaps: true })
    const nullIdx = gapTrend.points
      .map((p, i) => (p.rzye === null ? i : -1))
      .filter((i) => i >= 0)
    expect(nullIdx, '缺口 fixture 应恰含 2 个 null 日').toEqual([2, 4])

    expect(chart!.series).toHaveLength(4)
    for (const s of chart!.series) {
      expect(s.data, `${s.name} 应有 7 个点`).toHaveLength(gapTrend.points.length)
      for (const idx of nullIdx) {
        expect(
          s.data[idx],
          `${s.name}[${idx}] 缺失日应为 null（不补 0/前值）`
        ).toBeNull()
      }
      // 不出现 0 值点（null 未被填充为 0；factory 数值均为正数）
      expect(
        s.data.filter((v) => v === 0),
        `${s.name} 不应含 0 值点`
      ).toHaveLength(0)
    }
  })

  normalTest('TC-7.4 空态：latest=null 纯文案，普通用户无数据管理链接', async ({ page }) => {
    await mockMarginTrendEmpty(page)
    await page.goto(DASHBOARD)

    await expect(page.getByTestId('margin-panel')).toBeVisible()
    // 空态容器可见 + 纯文案
    await expect(page.getByTestId('margin-empty')).toBeVisible()
    await expect(page.getByTestId('margin-empty')).toContainText(/尚未同步|暂无/)
    // 普通用户无「前往数据管理」链接
    await expect(page.getByTestId('margin-empty-admin-link')).toHaveCount(0)
  })

  normalTest('TC-7.5 加载失败重试：仅重发 margin trend，不影响相邻 market-metrics 面板', async ({
    page,
  }) => {
    // 请求计数（监听全部请求，区分 margin trend / market-metrics trend）
    const counts = { marginTrend: 0, marketMetricsTrend: 0 }
    page.on('request', (req) => {
      const u = req.url()
      if (u.includes('/api/v1/margin/trend')) counts.marginTrend += 1
      if (u.includes('/api/v1/market-metrics/trend')) counts.marketMetricsTrend += 1
    })

    // margin trend 返回 500 → 错误态
    await mockMarginTrendError(page)
    await page.goto(DASHBOARD)

    await expect(page.getByTestId('margin-error')).toBeVisible()
    await expect(page.getByTestId('margin-retry')).toBeVisible()

    const marginBeforeRetry = counts.marginTrend
    const marketBeforeRetry = counts.marketMetricsTrend

    // 切 margin trend 为 200 后点重试 → 仅重发 margin trend
    await mockMarginTrend(page)
    await page.getByTestId('margin-retry').click()

    await expect
      .poll(() => counts.marginTrend, { message: 'margin trend 请求计数应 +1' })
      .toBe(marginBeforeRetry + 1)
    // 相邻 market-metrics 面板请求计数不变（局部 mutate，不刷新整页/相邻面板）
    await expect
      .poll(() => counts.marketMetricsTrend, {
        message: 'market-metrics trend 请求计数不应增加',
      })
      .toBe(marketBeforeRetry)

    // 重试后图表恢复渲染
    await expect(
      page.locator('[data-testid="margin-chart"] canvas').first()
    ).toBeVisible()
  })
})
