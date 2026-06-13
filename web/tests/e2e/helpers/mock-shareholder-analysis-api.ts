import { Page } from '@playwright/test'

/**
 * Mock helpers for shareholder analysis page E2E tests (plan-04)
 *
 * 后端用户侧 API（plan-02，baseURL 已含 /api/v1）：
 * - GET /api/v1/shareholder-analysis/overview            — 监控组概览
 * - GET /api/v1/shareholder-analysis/summary             — 汇总统计 + 变动趋势
 * - GET /api/v1/shareholder-analysis/industry-distribution — 行业分布
 * - GET /api/v1/shareholder-analysis/holdings            — 分页持仓列表（含退出股票）
 *
 * 参照 mock-fund-api.ts / mock-shareholder-api.ts 模式：
 * - URL 匹配用 URL.pathname 精确匹配（避免 glob 歧义）
 * - test data factory 用 camelCase（架构 §7.6 + plan-02 §7 契约）
 * - 多个 helper 在同一 URL 注册时，非自己负责的方法/参数必须用 route.fallback()
 *   转交，避免 LIFO 短路（参照 mock-shareholder-api.ts 注释）
 * - handler 内按 URLSearchParams 解析 industry/change_direction/page 决定返回哪份 fixture
 *
 * 外层契约（plan-02 green 已验证，server/src/api/v1/shareholder_analysis.py）：
 *   { success: true, data: {...} }
 * 故所有 mock 用 { success: true, data } 包裹，前端 hook 读 res.data.data。
 */

// ---------- URL Matching Helpers ----------

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

// ---------- Types (架构 §7.2) ----------

export interface GroupOverview {
  groupId: number
  groupName: string
  description: string | null
  stockCount: number
  increaseCount: number
  decreaseCount: number
  newCount: number
  exitCount: number
}

export interface OverviewData {
  reportPeriods: string[]
  currentPeriod: string
  hasPrevPeriod: boolean
  groups: GroupOverview[]
}

export interface SummaryData {
  summary: {
    stockCount: number
    totalHoldAmount: number
    avgHoldFloatRatio: number
  }
  trend: {
    increaseCount: number
    decreaseCount: number
    newCount: number
    exitCount: number
  }
  hasPrevPeriod: boolean
}

export interface IndustryItem {
  industry: string
  stockCount: number
  percentage: number
}

export interface IndustryDistributionData {
  distribution: IndustryItem[]
}

export interface HoldingItem {
  symbol: string
  stockName: string
  totalHoldAmount: number
  totalHoldFloatRatio: number
  changeDirection: 'increase' | 'decrease' | 'new' | 'unchanged' | 'exit' | null
  industries: string[]
}

export interface HoldingsData {
  holdings: HoldingItem[]
  total: number
}

// 响应体可以是静态对象或按 query 决定的工厂函数（用于筛选场景）
type OverviewResolver = (query: URLSearchParams, callIndex: number) => OverviewData
type SummaryResolver = (query: URLSearchParams, callIndex: number) => SummaryData
type IndustryDistResolver = (
  query: URLSearchParams,
  callIndex: number
) => IndustryDistributionData
type HoldingsResolver = (query: URLSearchParams, callIndex: number) => HoldingsData

// ---------- Test Data Factory ----------

/**
 * 测试用 5 个预定义股东分组概览（与 plan-03 种子数据一致）
 * 国家队/外资投行/社保基金/保险公司/私募基金
 */
export function createTestOverview(opts?: { hasPrevPeriod?: boolean }): OverviewData {
  const hasPrevPeriod = opts?.hasPrevPeriod ?? true
  return {
    reportPeriods: ['2024-12-31', '2024-09-30'],
    currentPeriod: '2024-12-31',
    hasPrevPeriod,
    groups: [
      {
        groupId: 1,
        groupName: '国家队',
        description: '汇金、证金等国家队资金',
        stockCount: 4,
        increaseCount: 1,
        decreaseCount: 1,
        newCount: 2,
        exitCount: 1,
      },
      {
        groupId: 2,
        groupName: '外资投行',
        description: '合格境外机构投资者（QFII）',
        stockCount: 2,
        increaseCount: 0,
        decreaseCount: 0,
        newCount: 1,
        exitCount: 0,
      },
      {
        groupId: 3,
        groupName: '社保基金',
        description: '全国社保基金理事会及组合',
        stockCount: 3,
        increaseCount: 1,
        decreaseCount: 0,
        newCount: 1,
        exitCount: 0,
      },
      {
        groupId: 4,
        groupName: '保险公司',
        description: '保险公司资金',
        stockCount: 5,
        increaseCount: 2,
        decreaseCount: 1,
        newCount: 1,
        exitCount: 0,
      },
      {
        groupId: 5,
        groupName: '私募基金',
        description: '知名私募基金',
        stockCount: 2,
        increaseCount: 0,
        decreaseCount: 0,
        newCount: 1,
        exitCount: 0,
      },
    ],
  }
}

/**
 * 数据未同步空状态（AC-08 / L3 降级）：overview 返回空 report_periods + 空 groups
 */
export function createTestOverviewEmpty(): OverviewData {
  return {
    reportPeriods: [],
    currentPeriod: '',
    hasPrevPeriod: false,
    groups: [],
  }
}

/**
 * 国家队汇总统计 + 变动趋势（plan-02 fixture 一致）
 */
export function createTestSummary(opts?: {
  hasPrevPeriod?: boolean
  industry?: string
  changeDirection?: string
}): SummaryData {
  const hasPrevPeriod = opts?.hasPrevPeriod ?? true
  // 默认国家队全量
  let summary = {
    stockCount: 4,
    totalHoldAmount: 2100,
    avgHoldFloatRatio: 0.42,
  }
  let trend = {
    increaseCount: 1,
    decreaseCount: 1,
    newCount: 2,
    exitCount: 1,
  }

  // 行业筛选"银行"：仅 1 只股票（601398）
  if (opts?.industry === '银行') {
    summary = { stockCount: 1, totalHoldAmount: 400, avgHoldFloatRatio: 0.05 }
  }
  // 变动方向"退出"：summary 仍展示全集（趋势不受 change_direction 影响）
  if (opts?.changeDirection === 'exit') {
    summary = { stockCount: 1, totalHoldAmount: 600, avgHoldFloatRatio: 0.05 }
  }

  // 无上期数据：趋势全 0（AC-11）
  if (!hasPrevPeriod) {
    trend = { increaseCount: 0, decreaseCount: 0, newCount: 0, exitCount: 0 }
  }

  return { summary, trend, hasPrevPeriod }
}

/**
 * 行业分布（plan-02 fixture 一致）：白酒 2 / 银行 1 / 保险 1
 */
export function createTestIndustryDistribution(): IndustryDistributionData {
  return {
    distribution: [
      { industry: '白酒', stockCount: 2, percentage: 50 },
      { industry: '银行', stockCount: 1, percentage: 25 },
      { industry: '保险', stockCount: 1, percentage: 25 },
    ],
  }
}

/**
 * 国家队持仓股票（plan-02 fixture 一致）
 * 600519 贵州茅台/increase / 000858 五粮液/decrease / 601318 中国平安/new / 601398 工商银行/new
 */
export function createTestHoldings(opts?: {
  industry?: string
  changeDirection?: string
  hasPrevPeriod?: boolean
}): HoldingsData {
  const hasPrevPeriod = opts?.hasPrevPeriod ?? true
  const all: HoldingItem[] = [
    {
      symbol: '600519',
      stockName: '贵州茅台',
      totalHoldAmount: 1000,
      totalHoldFloatRatio: 0.08,
      changeDirection: 'increase',
      industries: ['白酒'],
    },
    {
      symbol: '000858',
      stockName: '五粮液',
      totalHoldAmount: 500,
      totalHoldFloatRatio: 0.13,
      changeDirection: 'decrease',
      industries: ['白酒'],
    },
    {
      symbol: '601318',
      stockName: '中国平安',
      totalHoldAmount: 200,
      totalHoldFloatRatio: 0.01,
      changeDirection: 'new',
      industries: ['保险'],
    },
    {
      symbol: '601398',
      stockName: '工商银行',
      totalHoldAmount: 400,
      totalHoldFloatRatio: 0.05,
      changeDirection: 'new',
      industries: ['银行'],
    },
  ]

  // 退出股票（上期有本期无，持股数据为上期值）— 用于 AC-05 退出筛选
  const exitStock: HoldingItem = {
    symbol: '600000',
    stockName: '浦发银行',
    totalHoldAmount: 600,
    totalHoldFloatRatio: 0.05,
    changeDirection: 'exit',
    industries: ['银行'],
  }

  let holdings = all
  if (opts?.industry === '银行') {
    holdings = all.filter((h) => h.industries.includes('银行'))
  }
  if (opts?.changeDirection === 'exit') {
    holdings = [exitStock]
  } else if (opts?.changeDirection === 'increase') {
    holdings = all.filter((h) => h.changeDirection === 'increase')
  }

  // 无上期数据：所有 changeDirection 显示为 null（AC-11 降级）
  if (!hasPrevPeriod) {
    holdings = all.map((h) => ({ ...h, changeDirection: null }))
  }

  return { holdings, total: holdings.length }
}

/**
 * 多组联合持仓（AC-03 / US-06）：group_ids=1,2 按 symbol 去重后 5 只
 * 601398 在国家队+外资投行中重复匹配，去重后 5 只
 */
export function createMultiGroupHoldings(): HoldingsData {
  return {
    holdings: [
      {
        symbol: '600519',
        stockName: '贵州茅台',
        totalHoldAmount: 1000,
        totalHoldFloatRatio: 0.08,
        changeDirection: 'increase',
        industries: ['白酒'],
      },
      {
        symbol: '000858',
        stockName: '五粮液',
        totalHoldAmount: 500,
        totalHoldFloatRatio: 0.13,
        changeDirection: 'decrease',
        industries: ['白酒'],
      },
      {
        symbol: '601318',
        stockName: '中国平安',
        totalHoldAmount: 200,
        totalHoldFloatRatio: 0.01,
        changeDirection: 'new',
        industries: ['保险'],
      },
      {
        symbol: '601398',
        stockName: '工商银行',
        totalHoldAmount: 400,
        totalHoldFloatRatio: 0.05,
        changeDirection: 'new',
        industries: ['银行'],
      },
      {
        symbol: '600036',
        stockName: '招商银行',
        totalHoldAmount: 300,
        totalHoldFloatRatio: 0.03,
        changeDirection: 'unchanged',
        industries: ['银行'],
      },
    ],
    total: 5,
  }
}

// ---------- Mock Helpers ----------

/**
 * Mock GET /api/v1/shareholder-analysis/overview
 *
 * @param overviewOrFactory 静态 OverviewData 或按 query/callIndex 决定的工厂
 * @param responses         多次调用按序返回不同结果（用于 AC-09 切换报告期场景）
 */
export async function mockShareholderOverview(
  page: Page,
  overviewOrFactory: OverviewData | OverviewResolver,
  responses?: OverviewData[]
): Promise<void> {
  let callIndex = 0
  await page.route(
    (url) => matchApiPath(url, '/api/v1/shareholder-analysis/overview'),
    async (route) => {
      if (route.request().method() !== 'GET') {
        await route.fallback()
        return
      }
      const query = parseQuery(route.request().url())
      let data: OverviewData
      if (responses && responses.length > 0) {
        data = responses[Math.min(callIndex, responses.length - 1)]
      } else if (typeof overviewOrFactory === 'function') {
        data = overviewOrFactory(query, callIndex)
      } else {
        data = overviewOrFactory
      }
      callIndex += 1
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data }),
      })
    }
  )
}

/**
 * Mock GET /api/v1/shareholder-analysis/overview — 返回空（AC-08 空状态）
 */
export async function mockShareholderOverviewEmpty(page: Page): Promise<void> {
  await mockShareholderOverview(page, createTestOverviewEmpty())
}

/**
 * Mock GET /api/v1/shareholder-analysis/summary
 *
 * handler 内按 query 的 industry / change_direction 决定返回哪份 fixture，
 * 实现筛选联动效果（无需每个测试单独 mock）
 */
export async function mockShareholderSummary(
  page: Page,
  baseSummary: SummaryData | SummaryResolver = createTestSummary()
): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/shareholder-analysis/summary'),
    async (route) => {
      if (route.request().method() !== 'GET') {
        await route.fallback()
        return
      }
      const query = parseQuery(route.request().url())
      const industry = query.get('industry') ?? undefined
      const changeDirection = query.get('change_direction') ?? undefined
      const data: SummaryData =
        typeof baseSummary === 'function'
          ? baseSummary(query, 0)
          : createTestSummary({
              industry,
              changeDirection,
              hasPrevPeriod: baseSummary.hasPrevPeriod,
            })
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data }),
      })
    }
  )
}

/**
 * Mock GET /api/v1/shareholder-analysis/industry-distribution
 */
export async function mockShareholderIndustryDistribution(
  page: Page,
  distribution: IndustryDistributionData | IndustryDistResolver = createTestIndustryDistribution()
): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/shareholder-analysis/industry-distribution'),
    async (route) => {
      if (route.request().method() !== 'GET') {
        await route.fallback()
        return
      }
      const query = parseQuery(route.request().url())
      const data: IndustryDistributionData =
        typeof distribution === 'function' ? distribution(query, 0) : distribution
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data }),
      })
    }
  )
}

/**
 * Mock GET /api/v1/shareholder-analysis/holdings
 *
 * handler 内按 query 的 industry / change_direction / group_ids 决定返回哪份 fixture
 *
 * @param baseHoldings       默认持仓（国家队）
 * @param multiGroupHoldings 多组联合持仓（group_ids 含逗号时返回），用于 AC-03
 */
export async function mockShareholderHoldings(
  page: Page,
  baseHoldings: HoldingsData | HoldingsResolver = createTestHoldings(),
  multiGroupHoldings?: HoldingsData
): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/shareholder-analysis/holdings'),
    async (route) => {
      if (route.request().method() !== 'GET') {
        await route.fallback()
        return
      }
      const query = parseQuery(route.request().url())
      const groupIds = query.get('group_ids') ?? ''
      const industry = query.get('industry') ?? undefined
      const changeDirection = query.get('change_direction') ?? undefined
      const hasPrevPeriod = true

      let data: HoldingsData
      if (typeof baseHoldings === 'function') {
        data = baseHoldings(query, 0)
      } else if (multiGroupHoldings && groupIds.includes(',')) {
        // 多组联合 → 返回去重数据（AC-03）
        data = multiGroupHoldings
      } else {
        data = createTestHoldings({ industry, changeDirection, hasPrevPeriod })
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data }),
      })
    }
  )
}
