import { Page } from '@playwright/test'

/**
 * Mock helpers for market metrics panel E2E tests（第 16 期 plan-07）
 *
 * 用户侧 API（baseURL 已含 /api/v1，前端 endpoint 不带 /api/v1 前缀）：
 * - GET /api/v1/market-metrics/trend?range=30|90|250 — 市场量价趋势（plan-06 契约，plan-07 首页消费）
 *
 * 范式照抄 mock-etf-monitor-api.ts：
 * - URL 匹配用 URL.pathname 精确匹配（matchApiPath，避免 glob 歧义、host 无关）
 * - test data factory 字段 camelCase（与 marketMetricsTypes.ts 对齐）
 * - handler 内按 URLSearchParams 解析 range；query 名 snake_case 与后端 Query 一致
 * - 响应体 `{ success, data }` 业务包 + camelCase（后端 _dict_to_camel + Decimal→float + date→ISO）
 *
 * 另含「宿主页稳定 mock」（mockIndexMonitorOverview/Watchlist、mockNormalDashboardPrerequisites）：
 * 这些不是被测功能，仅为让管理员/普通首页宿主组件（IndexMonitorPage / 板块热力图 / 排名等）
 * 不因 mock token 被真实后端 401 拒绝而触发 handleUnauthorizedRedirect 跳 /login，从而保证
 * red 阶段失败原因落在「MarketMetricsPanel 组件未实现」而非环境错误。
 */

// ---------- URL Matching Helpers（与 mock-etf-monitor-api.ts 一致） ----------

function toPathname(requestUrl: URL | string): string {
  if (typeof requestUrl === 'string') {
    try {
      return new URL(requestUrl).pathname
    } catch {
      return ''
    }
  }
  return requestUrl.pathname
}

function matchApiPath(requestUrl: URL | string, expectedPath: string): boolean {
  return toPathname(requestUrl) === expectedPath
}

function parseQuery(requestUrl: URL | string): URLSearchParams {
  if (typeof requestUrl === 'string') {
    try {
      return new URL(requestUrl).searchParams
    } catch {
      return new URLSearchParams()
    }
  }
  return requestUrl.searchParams
}

// ---------- Types（与 src/types/marketMetricsTypes.ts 逐字段一致，plan-07 §1） ----------

export type MarketMetricRange = 30 | 90 | 250
export type MetricKey = 'amountYuan' | 'volumeShares' | 'averagePrice'

export interface MarketMetricPoint {
  tradeDate: string
  volumeShares: number | null
  amountYuan: number | null
  averagePrice: number | null
  finalStockCount: number | null
  suspendedStockCount: number | null
}

export interface MarketMetricsTrendData {
  latest: MarketMetricPoint | null
  points: MarketMetricPoint[]
  range: MarketMetricRange
  hasMissingDates: boolean
}

// ---------- Test Data Factory ----------

/**
 * 构造 N 个交易日点（连续日，便于断言）。
 * nullDayIndices 指定哪些索引为「缺结果日」（三指标全 null，模拟缺口）。
 *
 * 单位口径与架构一致：存储统一股/元，前端显示层 ÷1e8 转亿。
 * - volumeShares：~720 亿股 → 原始 7.2e9 股
 * - amountYuan：~8200 亿元 → 原始 8.2e11 元
 * - averagePrice：~11.38 元（2 位小数）
 */
function buildPoints(
  count: number,
  nullDayIndices: number[] = []
): MarketMetricPoint[] {
  const points: MarketMetricPoint[] = []
  // 最后一天固定为 2026-08-13（最近结果日），向前推 count 个连续日
  const base = new Date('2026-08-13T00:00:00Z')
  for (let i = 0; i < count; i++) {
    const d = new Date(base)
    d.setUTCDate(d.getUTCDate() - (count - 1 - i))
    const tradeDate = d.toISOString().slice(0, 10)

    if (nullDayIndices.includes(i)) {
      points.push({
        tradeDate,
        volumeShares: null,
        amountYuan: null,
        averagePrice: null,
        finalStockCount: null,
        suspendedStockCount: null,
      })
      continue
    }

    points.push({
      tradeDate,
      volumeShares: Math.round((7.2e9 + i * 1e7) * 100) / 100,
      amountYuan: Math.round((8.2e11 + i * 2e9) * 100) / 100,
      averagePrice: Math.round((11.38 + i * 0.01) * 100) / 100,
      finalStockCount: 5200 + (i % 5),
      suspendedStockCount: 22 + (i % 7),
    })
  }
  return points
}

/**
 * 市场量价趋势测试数据工厂。
 *
 * - empty：latest=null、points=[]（同步未跑 → 空态）
 * - gaps：7 日轴，第 3、5 日（索引 2、4）缺结果 → hasMissingDates=true（缺口断线）
 * - 默认：按 range 生成连续交易日满数据，hasMissingDates=false
 */
export function createTestMarketMetricsTrend(opts?: {
  range?: MarketMetricRange
  empty?: boolean
  gaps?: boolean
}): MarketMetricsTrendData {
  const range = opts?.range ?? 30

  if (opts?.empty) {
    return {
      latest: null,
      points: [],
      range,
      hasMissingDates: false,
    }
  }

  if (opts?.gaps) {
    // 7 日轴，索引 2、4 为缺口日（null，非 0）
    const nullDayIndices = [2, 4]
    const points = buildPoints(7, nullDayIndices)
    const nonNull = points.filter((p) => p.volumeShares !== null)
    return {
      latest: nonNull.length > 0 ? nonNull[nonNull.length - 1] : null,
      points,
      range,
      hasMissingDates: true,
    }
  }

  const points = buildPoints(range)
  return {
    latest: points[points.length - 1],
    points,
    range,
    hasMissingDates: false,
  }
}

// ---------- Mock Helpers（被测功能） ----------

/**
 * Mock GET /api/v1/market-metrics/trend — 市场量价趋势。
 *
 * handler 内按 query `range` 生成对应数量的交易日点；
 * 调用方可传入 fixture（empty/gaps/满数据）覆盖默认。
 */
export async function mockMarketMetricsTrend(
  page: Page,
  data?: MarketMetricsTrendData
): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/market-metrics/trend'),
    async (route) => {
      if (route.request().method() !== 'GET') {
        await route.fallback()
        return
      }
      const query = parseQuery(route.request().url())
      const range = (parseInt(query.get('range') || '30', 10) as MarketMetricRange) || 30

      const responseData = data ?? createTestMarketMetricsTrend({ range })

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: { ...responseData, range },
        }),
      })
    }
  )
}

/** Mock trend 全空（latest=null、points=[] → 空态） */
export async function mockMarketMetricsTrendEmpty(page: Page): Promise<void> {
  await mockMarketMetricsTrend(page, createTestMarketMetricsTrend({ empty: true }))
}

/** Mock trend 部分缺口（7 日轴 2 日 null，hasMissingDates=true → 断线 + 提示） */
export async function mockMarketMetricsTrendGaps(page: Page): Promise<void> {
  await mockMarketMetricsTrend(page, createTestMarketMetricsTrend({ gaps: true }))
}

/** Mock trend 失败（500 → 错误态 + 重试） */
export async function mockMarketMetricsTrendError(page: Page): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/market-metrics/trend'),
    async (route) => {
      if (route.request().method() !== 'GET') {
        await route.fallback()
        return
      }
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal Server Error' }),
      })
    }
  )
}

/**
 * 一键安装满数据 mock（默认 range 响应），用于多数 Happy 场景。
 */
export async function installMarketMetricsMocks(page: Page): Promise<void> {
  await mockMarketMetricsTrend(page)
}

// ---------- 宿主页稳定 mock（非被测功能，避免 401 重定向） ----------
// 管理员首页 IndexMonitorPage 会请求 index-monitor overview/watchlist；
// 普通首页会请求 market-index/heatmap/rankings。
// 这些 endpoint 用 mock token 打真实后端会被 401 拒绝 → handleUnauthorizedRedirect 跳 /login，
// 导致 red 失败原因落在环境错误而非「组件未实现」。此处返回最小合法数据让宿主页稳定。

/** Mock GET /api/v1/index-monitor/overview — 管理员首页指数总览（返回 1 只指数，让 IndexOverviewCards 渲染「指数总览」） */
export async function mockIndexMonitorOverview(page: Page): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/index-monitor/overview'),
    async (route) => {
      if (route.request().method() !== 'GET') {
        await route.fallback()
        return
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            tradeDate: '2026-08-13',
            indices: [
              {
                tsCode: '000300.SH',
                name: '沪深300',
                close: 3900.52,
                pctChg: 0.85,
                amount: 250000000000,
                peTtm: 12.3,
              },
            ],
          },
        }),
      })
    }
  )
}

/** Mock GET /api/v1/index-monitor/watchlist — 关注清单（空数组，宿主稳定即可） */
export async function mockIndexMonitorWatchlist(page: Page): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/index-monitor/watchlist'),
    async (route) => {
      if (route.request().method() !== 'GET') {
        await route.fallback()
        return
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: { watchlist: [] },
        }),
      })
    }
  )
}

/**
 * Mock 普通首页宿主页依赖（market-index / heatmap / rankings），
 * 避免 useMarketIndex/useSectorHeatmapData/useSectorRanking/useStockRanking 的
 * 请求 401 触发 handleUnauthorizedRedirect。返回最小合法数据。
 */
export async function mockNormalDashboardPrerequisites(page: Page): Promise<void> {
  // 市场强度指数（useMarketIndex → fetcher，host 无关）
  await page.route(
    (url) => matchApiPath(url, '/api/v1/market-index'),
    async (route) => {
      if (route.request().method() !== 'GET') {
        await route.fallback()
        return
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: { index: {}, stats: {}, trend: [] },
        }),
      })
    }
  )

  // 板块热力图（useSectorHeatmapData → heatmapApi，Zod 校验通过即用空 sectors）
  await page.route(
    (url) => matchApiPath(url, '/api/v1/heatmap'),
    async (route) => {
      if (route.request().method() !== 'GET') {
        await route.fallback()
        return
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: { sectors: [], timestamp: '2026-08-13T15:00:00.000Z' },
        }),
      })
    }
  )

  // 板块 / 个股排名（useSectorRanking / useStockRanking → fetcher）
  for (const sub of ['sectors', 'stocks']) {
    await page.route(
      (url) => matchApiPath(url, `/api/v1/rankings/${sub}`),
      async (route) => {
        if (route.request().method() !== 'GET') {
          await route.fallback()
          return
        }
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true, data: [], total: 0 }),
        })
      }
    )
  }
}
