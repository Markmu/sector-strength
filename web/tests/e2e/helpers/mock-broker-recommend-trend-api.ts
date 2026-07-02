import { Page } from '@playwright/test'

/**
 * Mock helpers for broker recommend trend view E2E tests (plan-02, 10 期)
 *
 * 趋势视图用户侧 API（plan-01 提供，baseURL 已含 /api/v1）：
 * - GET /api/v1/broker-recommend-analysis/trend-ranking — 持续推荐趋势榜
 *
 * 范式参照 mock-broker-recommend-api.ts：
 * - URL 匹配用 URL.pathname 精确匹配（避免 glob 歧义）
 * - test data factory 用 camelCase（架构 §7.2 + plan-02 §实现规格 #1 契约）
 * - handler 内按 URLSearchParams 解析 search/page/page_size 决定返回哪份 fixture
 * - 多个 helper 在同一路径注册时，非自己负责的方法用 route.fallback() 放行
 *
 * 外层契约：{ success: true, data: TrendRankingResponse }（前端 hook 读 res.data.data）
 *
 * data-testid 对齐 plan-02 §实现规格 #4：
 * - broker-trend-table / broker-trend-expand-{symbol} / broker-trend-expand-content-{symbol}
 * - broker-trend-pagination / broker-trend-sparkline-{symbol}
 */

// ---------- URL Matching Helpers（范式照搬 mock-broker-recommend-api.ts） ----------

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

// ---------- Types（与 lib/api.ts TrendRankingItem 对齐，架构 §7.2，camelCase） ----------

export interface TrendMonthPoint {
  month: string
  brokerCount: number
}

export interface TrendMonthBroker {
  month: string
  brokerCount: number
  topBrokers: string[]
}

export interface TrendRankingItem {
  symbol: string
  name: string | null
  industries: string[]
  consecutiveMonths: number
  cumulativeBrokerCount: number
  latestMonthBrokerCount: number
  monthlySeries: TrendMonthPoint[]
  monthlyBrokers: TrendMonthBroker[]
}

export interface TrendRankingData {
  hasData: boolean
  total: number
  page: number
  pageSize: number
  items: TrendRankingItem[]
}

// ---------- Test Data Factory ----------

/**
 * 多月趋势榜测试数据（AC-02/03/05/06/07/08）
 *
 * 场景设计：
 * - 600519：3 个月连续推荐（窗口全覆盖，连续月数 3）— 榜首
 * - 300750：连续推荐但中间断档（2026-05 无推荐，断档股 AC-07）— 连续月数从最新月向前计到断档即停 = 1
 * - 688981：仅 1 家券商推荐（验证 topBrokers 前3省略边界）
 *
 * 多级排序（AC-03）：连续月数↓ → 累计家数↓ → 最新月家数↓ → 代码↑
 */
export function createTestTrendRanking(): TrendRankingData {
  return {
    hasData: true,
    total: 3,
    page: 1,
    pageSize: 20,
    items: [
      {
        symbol: '600519',
        name: '贵州茅台',
        industries: ['食品饮料'],
        consecutiveMonths: 3,
        cumulativeBrokerCount: 12,
        latestMonthBrokerCount: 5,
        // 旧→新升序（Sparkline 横轴旧→新）
        monthlySeries: [
          { month: '2026-04', brokerCount: 3 },
          { month: '2026-05', brokerCount: 4 },
          { month: '2026-06', brokerCount: 5 },
        ],
        monthlyBrokers: [
          { month: '2026-06', brokerCount: 5, topBrokers: ['中信证券', '中金公司', '国泰君安', '华泰证券', '招商证券'] },
          { month: '2026-05', brokerCount: 4, topBrokers: ['中信证券', '中金公司', '国泰君安', '招商证券'] },
          { month: '2026-04', brokerCount: 3, topBrokers: ['中信证券', '中金公司', '华泰证券'] },
        ],
      },
      {
        // 断档股（AC-07）：2026-05 无推荐（brokerCount=0），连续月数从最新月 2026-06 向前计到断档即停 = 1
        symbol: '300750',
        name: '宁德时代',
        industries: ['电力设备'],
        consecutiveMonths: 1,
        cumulativeBrokerCount: 5,
        latestMonthBrokerCount: 3,
        monthlySeries: [
          { month: '2026-04', brokerCount: 2 },
          { month: '2026-05', brokerCount: 0 }, // 断档点（Sparkline 含 0 点 AC-05）
          { month: '2026-06', brokerCount: 3 },
        ],
        monthlyBrokers: [
          { month: '2026-06', brokerCount: 3, topBrokers: ['中信证券', '中金公司', '华泰证券'] },
          { month: '2026-05', brokerCount: 0, topBrokers: [] }, // 某月无券商 → 家数 0 / 券商"—"（AC-06）
          { month: '2026-04', brokerCount: 2, topBrokers: ['中金公司', '华泰证券'] },
        ],
      },
      {
        // 多级排序末位：连续月数 1（与 300750 同）→ 累计家数 5（与 300750 同）→ 最新月家数 1 < 3 → 排在 300750 后
        symbol: '688981',
        name: '中芯国际',
        industries: ['电子'],
        consecutiveMonths: 1,
        cumulativeBrokerCount: 5,
        latestMonthBrokerCount: 1,
        monthlySeries: [
          { month: '2026-06', brokerCount: 1 },
        ],
        monthlyBrokers: [
          { month: '2026-06', brokerCount: 1, topBrokers: ['中信证券'] },
        ],
      },
    ],
  }
}

/**
 * 单月趋势榜测试数据（AC-11 降级）
 * - 仅一个月已同步，连续月数均为 1
 * - Sparkline 单点（values.length===1）不报错
 */
export function createTestTrendRankingSingleMonth(): TrendRankingData {
  return {
    hasData: true,
    total: 1,
    page: 1,
    pageSize: 20,
    items: [
      {
        symbol: '600519',
        name: '贵州茅台',
        industries: ['食品饮料'],
        consecutiveMonths: 1,
        cumulativeBrokerCount: 5,
        latestMonthBrokerCount: 5,
        monthlySeries: [{ month: '2026-06', brokerCount: 5 }],
        monthlyBrokers: [
          { month: '2026-06', brokerCount: 5, topBrokers: ['中信证券', '中金公司', '国泰君安', '华泰证券', '招商证券'] },
        ],
      },
    ],
  }
}

/**
 * 分页测试数据（AC-08）：25 条 > 20，分页器应显示
 */
export function createTestTrendRankingPaged(): TrendRankingData {
  const items: TrendRankingItem[] = Array.from({ length: 25 }, (_, i) => ({
    symbol: String(600000 + i).padStart(6, '0'),
    name: `股票${i + 1}`,
    industries: ['测试行业'],
    consecutiveMonths: 1,
    cumulativeBrokerCount: 1,
    latestMonthBrokerCount: 1,
    monthlySeries: [{ month: '2026-06', brokerCount: 1 }],
    monthlyBrokers: [{ month: '2026-06', brokerCount: 1, topBrokers: ['中信证券'] }],
  }))
  return {
    hasData: true,
    total: 25,
    page: 1,
    pageSize: 20,
    items,
  }
}

/**
 * 空状态趋势榜测试数据（AC-12）：hasData=false，无 items
 */
export function createTestTrendRankingEmpty(): TrendRankingData {
  return {
    hasData: false,
    total: 0,
    page: 1,
    pageSize: 20,
    items: [],
  }
}

// ---------- Mock Helpers ----------

/**
 * Mock GET /api/v1/broker-recommend-analysis/trend-ranking
 *
 * 支持 search 过滤 + page 分页：
 * - search：按 symbol 前缀或 name 包含过滤
 * - page：服务端分页（mock 简化：仅返回 page=1 的前 pageSize 条，total 为过滤后总数）
 */
export async function mockTrendRanking(
  page: Page,
  data: TrendRankingData = createTestTrendRanking()
): Promise<void> {
  await page.route(
    (url) =>
      matchApiPath(url, '/api/v1/broker-recommend-analysis/trend-ranking'),
    async (route) => {
      if (route.request().method() !== 'GET') {
        await route.fallback()
        return
      }
      const query = parseQuery(route.request().url())
      const search = query.get('search') || ''
      const pageNum = Number(query.get('page') || '1')

      let items = [...data.items] as TrendRankingItem[]
      if (search) {
        const s = search.toLowerCase()
        items = items.filter(
          (it) =>
            it.symbol.toLowerCase().startsWith(s) ||
            (it.name ?? '').toLowerCase().includes(s)
        )
      }
      const total = items.length
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: { ...data, items, total, page: pageNum },
        }),
      })
    }
  )
}
