import { Page } from '@playwright/test'

/**
 * Mock helpers for fund crowd analysis page E2E tests (plan-02)
 *
 * 后端用户侧 API（plan-01，baseURL 已含 /api/v1）：
 * - GET /api/v1/fund-crowd-analysis/rankings                — 扎堆度排行榜（含环比 + 搜索 + 分页）
 * - GET /api/v1/fund-crowd-analysis/industry-distribution   — 行业分布（按扎堆股数量占比）
 *
 * 参照 mock-shareholder-analysis-api.ts 模式：
 * - URL 匹配用 URL.pathname 精确匹配（避免 glob 歧义）
 * - test data factory 用 camelCase（架构 §7.6 + plan-02 §3 契约）
 * - 多个 helper 在同一 URL 注册时，非自己负责的方法用 route.fallback() 转交，避免 LIFO 短路
 * - handler 内按 URLSearchParams 解析 scope/search/page 决定返回哪份 fixture
 *
 * 外层契约（plan-01 green 已验证，server/src/api/v1/fund_crowd_analysis.py）：
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

// ---------- Types (与 lib/api.ts CrowdRanking* / CrowdIndustry* 对齐，架构 §7.2) ----------

export type CrowdScope = 'active' | 'all'

export interface CrowdRankingItemData {
  stockSymbol: string
  stockName: string | null
  industries: string[]
  fundCount: number
  totalFloatRatio: number | null
  fundCountChange: number | null
  totalFloatRatioChange: number | null
  isNew: boolean | null
}

export interface CrowdRankingsData {
  hasData: boolean
  currentPeriod: string | null
  prevPeriod: string | null
  hasPrevPeriod: boolean
  items: CrowdRankingItemData[]
  total: number
  page: number
  pageSize: number
}

export interface CrowdIndustryItemData {
  industry: string
  stockCount: number
  percentage: number
  totalFloatRatio: number
}

export interface CrowdIndustryDistributionData {
  hasData: boolean
  currentPeriod: string | null
  distribution: CrowdIndustryItemData[]
}

// ---------- Test Data Factory ----------

/**
 * 默认排行榜测试数据（覆盖 AC-01/02/03 各场景）
 *
 * - 600519 贵州茅台：基金数 286，环比 +12（抱团加强，绿色 ↑）
 * - 300750 宁德时代：基金数 198，环比 -8（抱团瓦解，红色 ↓）
 * - 688981 中芯国际：isNew=true（新进，AC-03）
 *
 * @param opts.hasPrevPeriod 默认 true；false 时所有 change 字段与 isNew 统一 null（AC-06）
 */
export function createTestCrowdRankings(opts?: {
  hasPrevPeriod?: boolean
}): CrowdRankingsData {
  const hasPrevPeriod = opts?.hasPrevPeriod ?? true
  return {
    hasData: true,
    currentPeriod: '2025-12-31',
    prevPeriod: hasPrevPeriod ? '2025-09-30' : null,
    hasPrevPeriod,
    items: [
      {
        stockSymbol: '600519',
        stockName: '贵州茅台',
        industries: ['食品饮料'],
        fundCount: 286,
        totalFloatRatio: 8.2,
        fundCountChange: hasPrevPeriod ? 12 : null,
        totalFloatRatioChange: hasPrevPeriod ? 0.8 : null,
        isNew: hasPrevPeriod ? false : null,
      },
      {
        stockSymbol: '300750',
        stockName: '宁德时代',
        industries: ['电力设备'],
        fundCount: 198,
        totalFloatRatio: 5.4,
        fundCountChange: hasPrevPeriod ? -8 : null,
        totalFloatRatioChange: hasPrevPeriod ? -1.1 : null,
        isNew: hasPrevPeriod ? false : null,
      },
      {
        stockSymbol: '688981',
        stockName: '中芯国际',
        industries: ['电子'],
        fundCount: 45,
        totalFloatRatio: 3.1,
        fundCountChange: null,
        totalFloatRatioChange: null,
        // AC-06：hasPrevPeriod=false 时后端 isNew=null（避免与 true 新进标识混淆）
        isNew: hasPrevPeriod ? true : null,
      },
    ],
    total: 3,
    page: 1,
    pageSize: 20,
  }
}

/** AC-07 空状态：持仓数据未同步 */
export function createTestCrowdRankingsEmpty(): CrowdRankingsData {
  return {
    hasData: false,
    currentPeriod: null,
    prevPeriod: null,
    hasPrevPeriod: false,
    items: [],
    total: 0,
    page: 1,
    pageSize: 20,
  }
}

/** 行业分布测试数据（AC-04） */
export function createTestCrowdIndustryDistribution(): CrowdIndustryDistributionData {
  return {
    hasData: true,
    currentPeriod: '2025-12-31',
    distribution: [
      { industry: '食品饮料', stockCount: 32, percentage: 16.0, totalFloatRatio: 12.5 },
      { industry: '电力设备', stockCount: 28, percentage: 14.0, totalFloatRatio: 9.8 },
      { industry: '银行', stockCount: 20, percentage: 10.0, totalFloatRatio: 7.2 },
    ],
  }
}

/** 行业分布空数据（AC-04 边界） */
export function createTestCrowdIndustryDistributionEmpty(): CrowdIndustryDistributionData {
  return {
    hasData: true,
    currentPeriod: '2025-12-31',
    distribution: [],
  }
}

// ---------- Mock Helpers ----------

/**
 * Mock GET /api/v1/fund-crowd-analysis/rankings — 排行榜
 *
 * handler 内按 query 的 scope/search 模拟后端过滤：
 * - scope=all 时 fundCount 翻倍（模拟纳入被动型）
 * - search 命中时仅返回匹配项（代码前缀 OR 名称包含，不区分大小写）
 */
export async function mockCrowdRankings(
  page: Page,
  data: CrowdRankingsData = createTestCrowdRankings()
): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/fund-crowd-analysis/rankings'),
    async (route) => {
      if (route.request().method() !== 'GET') {
        await route.fallback()
        return
      }
      const query = parseQuery(route.request().url())
      const scope = (query.get('scope') as CrowdScope) || 'active'
      const search = query.get('search') || ''

      let items = [...data.items]
      // scope=all 模拟：fundCount 翻倍（被动型纳入）
      if (scope === 'all') {
        items = items.map((it) => ({ ...it, fundCount: it.fundCount * 2 }))
      }
      // search 过滤（代码前缀 OR 名称包含，不区分大小写）
      if (search) {
        const s = search.toLowerCase()
        items = items.filter(
          (it) =>
            it.stockSymbol.toLowerCase().startsWith(s) ||
            (it.stockName ?? '').toLowerCase().includes(s)
        )
      }
      const total = items.length
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: { ...data, items, total },
        }),
      })
    }
  )
}

/** Mock rankings 空状态（AC-07：持仓数据未同步） */
export async function mockCrowdRankingsEmpty(page: Page): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/fund-crowd-analysis/rankings'),
    async (route) => {
      if (route.request().method() !== 'GET') {
        await route.fallback()
        return
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: createTestCrowdRankingsEmpty() }),
      })
    }
  )
}

/** Mock GET /api/v1/fund-crowd-analysis/industry-distribution — 行业分布 */
export async function mockCrowdIndustryDistribution(
  page: Page,
  data: CrowdIndustryDistributionData = createTestCrowdIndustryDistribution()
): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/fund-crowd-analysis/industry-distribution'),
    async (route) => {
      if (route.request().method() !== 'GET') {
        await route.fallback()
        return
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data }),
      })
    }
  )
}

/** Mock industry-distribution 空数据（AC-04 边界） */
export async function mockCrowdIndustryDistributionEmpty(page: Page): Promise<void> {
  await mockCrowdIndustryDistribution(page, createTestCrowdIndustryDistributionEmpty())
}
