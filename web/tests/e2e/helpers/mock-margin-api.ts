import { Page } from '@playwright/test'

/**
 * Mock helpers for margin panel E2E tests（第 17 期 plan-07）
 *
 * 被测 API（baseURL 已含 /api/v1，前端 endpoint 不带 /api/v1 前缀，无双前缀）：
 * - GET /api/v1/margin/trend?range=30|90|250 — 全市场融资融券趋势（plan-06 契约，plan-07 首页消费）
 *
 * 范式照抄 mock-market-metrics-api.ts（16 期 plan-07）：
 * - URL 匹配用 URL.pathname 精确匹配（matchApiPath，效果等价于 glob 拦截
 *   "任意 host + /api/v1/margin/trend + 任意 query"，避免 glob 歧义与双前缀漏拦）
 * - test data factory 字段 camelCase（与 marginTypes.ts 契约逐字段一致：
 *   tradeDate/rzye/rqye/rzmre/rzche/rqmcl/rzrqye，元/股原始值 float）
 * - handler 内按 URLSearchParams 解析 range；缺失日六指标全 null（AC-5，不补 0/前值）
 * - 响应体 { success, data } 业务包 + camelCase（后端 _dict_to_camel + Decimal→float + date→ISO）
 *
 * 宿主页稳定 mock（mockNormalDashboardPrerequisites / mockMarketMetricsTrend）不在本文件，
 * 直接复用 mock-market-metrics-api.ts 的导出，避免重复实现。
 */

// ---------- URL Matching Helpers（与 mock-market-metrics-api.ts 一致） ----------

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

// ---------- Types（与 src/types/marginTypes.ts 逐字段一致，plan-07 §1） ----------

export type MarginRange = 30 | 90 | 250

export interface MarginPoint {
  tradeDate: string
  rzye: number | null // 融资余额（元）
  rqye: number | null // 融券余额（元）
  rzmre: number | null // 融资买入额（元）
  rzche: number | null // 融资偿还额（元）
  rqmcl: number | null // 融券卖出量（股，不入图）
  rzrqye: number | null // 两融合计余额（元）
}

export interface MarginTrendData {
  latest: MarginPoint | null
  points: MarginPoint[]
  range: MarginRange
  hasMissingDates: boolean
}

// ---------- Test Data Factory ----------

/**
 * 构造 N 个交易日点（连续日，便于断言）。
 * nullDayIndices 指定哪些索引为「缺结果日」（六指标全 null，模拟缺口，AC-5）。
 *
 * 单位口径与架构一致：存储统一元/股原始值，前端显示层 ÷1e8 转亿（spec D5）。
 * - rzye：~2.1 万亿元 → 原始 2.1e12 元，每日 +100 亿元
 * - rqye：~7500 亿元 → 原始 7.5e11 元，每日 +50 亿元
 * - rzmre：~2200 亿元 → 原始 2.2e11 元，每日 +10 亿元
 * - rzche：~2100 亿元 → 原始 2.1e11 元，每日 +10 亿元
 * - rqmcl：~3.2 亿股 → 原始 3.2e9 股（不入图，仅契约保留）
 * - rzrqye = rzye + rqye（spec D2：服务层重算口径，fixture 保持一致）
 */
function buildMarginPoints(count: number, nullDayIndices: number[] = []): MarginPoint[] {
  const points: MarginPoint[] = []
  // 最后一天固定为 2026-08-13（最近结果日），向前推 count 个连续日
  const base = new Date('2026-08-13T00:00:00Z')
  for (let i = 0; i < count; i++) {
    const d = new Date(base)
    d.setUTCDate(d.getUTCDate() - (count - 1 - i))
    const tradeDate = d.toISOString().slice(0, 10)

    if (nullDayIndices.includes(i)) {
      points.push({
        tradeDate,
        rzye: null,
        rqye: null,
        rzmre: null,
        rzche: null,
        rqmcl: null,
        rzrqye: null,
      })
      continue
    }

    const rzye = 2.1e12 + i * 1e10
    const rqye = 7.5e11 + i * 5e9
    points.push({
      tradeDate,
      rzye: Math.round(rzye * 100) / 100,
      rqye: Math.round(rqye * 100) / 100,
      rzmre: Math.round((2.2e11 + i * 1e9) * 100) / 100,
      rzche: Math.round((2.1e11 + i * 1e9) * 100) / 100,
      rqmcl: Math.round((3.2e9 + i * 1e7) * 100) / 100,
      rzrqye: Math.round((rzye + rqye) * 100) / 100,
    })
  }
  return points
}

/**
 * 融资融券趋势测试数据工厂。
 *
 * - empty：latest=null、points=[]（同步未跑 → 空态）
 * - gaps：7 日轴，第 3、5 日（索引 2、4）六指标全 null → hasMissingDates=true（缺口断线）
 * - 默认：按 range 生成连续交易日满数据，hasMissingDates=false
 */
export function createTestMarginTrend(opts?: {
  range?: MarginRange
  empty?: boolean
  gaps?: boolean
}): MarginTrendData {
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
    // 7 日轴，索引 2、4 为缺口日（六指标 null，非 0）
    const nullDayIndices = [2, 4]
    const points = buildMarginPoints(7, nullDayIndices)
    const nonNull = points.filter((p) => p.rzye !== null)
    return {
      latest: nonNull.length > 0 ? nonNull[nonNull.length - 1] : null,
      points,
      range,
      hasMissingDates: true,
    }
  }

  const points = buildMarginPoints(range)
  return {
    latest: points[points.length - 1],
    points,
    range,
    hasMissingDates: false,
  }
}

// ---------- Mock Helpers（被测功能） ----------

/**
 * Mock GET /api/v1/margin/trend — 全市场融资融券趋势。
 *
 * handler 内按 query `range` 生成对应数量的交易日点；
 * 调用方可传入 fixture（empty/gaps/满数据）覆盖默认。
 */
export async function mockMarginTrend(page: Page, data?: MarginTrendData): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/margin/trend'),
    async (route) => {
      if (route.request().method() !== 'GET') {
        await route.fallback()
        return
      }
      const query = parseQuery(route.request().url())
      const range = (parseInt(query.get('range') || '30', 10) as MarginRange) || 30

      const responseData = data ?? createTestMarginTrend({ range })

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
export async function mockMarginTrendEmpty(page: Page): Promise<void> {
  await mockMarginTrend(page, createTestMarginTrend({ empty: true }))
}

/** Mock trend 部分缺口（7 日轴 2 日六指标 null，hasMissingDates=true → 断线 + 提示） */
export async function mockMarginTrendGaps(page: Page): Promise<void> {
  await mockMarginTrend(page, createTestMarginTrend({ gaps: true }))
}

/** Mock trend 失败（500 → 错误态 + 重试） */
export async function mockMarginTrendError(page: Page): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/margin/trend'),
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
export async function installMarginMocks(page: Page): Promise<void> {
  await mockMarginTrend(page)
}
