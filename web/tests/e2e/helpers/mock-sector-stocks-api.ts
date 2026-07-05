import { Page } from '@playwright/test'

/**
 * Mock helpers for sector stocks E2E tests (plan-04 / 需求 11-板块成分股列表)
 *
 * 后端用户侧 API（baseURL 已含 /api/v1）：
 * - GET /api/v1/sectors/{sector_id}/stocks  — 板块成分股列表（排序 + 分页）
 * - GET /api/v1/stocks/{stock_id}           — 个股详情（plan-03 落地页）
 * - GET /api/v1/sectors/{sector_id}/strength-history — 板块强度历史（详情页图表，避免 401）
 * - GET /api/v1/sectors/{sector_id}/ma-history        — 板块均线历史（详情页图表，避免 401）
 *
 * 参照 mock-fund-crowd-api.ts 模式：
 * - URL 匹配用 URL.pathname 精确匹配
 * - 多 helper 同 URL 注册时用 route.fallback() 避免 LIFO 短路
 * - handler 内按 query 排序/分页模拟后端
 *
 * 字段命名：snake_case（对齐后端真实输出，与 mock-fund-crowd-api 的 camelCase 不同！）
 * 外层契约：{ success: true, data: {...} }，前端 hook 读 res.data.data。
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

/** 匹配 path 是否形如 /api/v1/sectors/{id}/stocks */
function matchSectorStocksPath(requestUrl: URL | string): boolean {
  return /^\/api\/v1\/sectors\/\d+\/stocks$/.test(toPathname(requestUrl))
}

/** 匹配 path 是否形如 /api/v1/stocks/{id} */
function matchStockDetailPath(requestUrl: URL | string): boolean {
  return /^\/api\/v1\/stocks\/\d+$/.test(toPathname(requestUrl))
}

/** 匹配板块强度/均线历史（图表 mock，避免 401） */
function matchSectorHistoryPath(requestUrl: URL | string, suffix: string): boolean {
  return new RegExp(`^/api/v1/sectors/\\d+/${suffix}$`).test(toPathname(requestUrl))
}

// ---------- Types (snake_case，对齐后端真实输出) ----------

export interface SectorStockItemData {
  id: string
  symbol: string
  name: string
  current_price: number | null
  market_cap: number | null
  strength_score: number | null
  trend_direction: number | null // 1=上升, 0=横盘, -1=下降
}

export interface SectorStocksData {
  items: SectorStockItemData[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface StockDetailData {
  id: string
  symbol: string
  name: string
  current_price: number | null
  market_cap: number | null
  strength_score: number | null
  trend_direction: number | null
}

// ---------- Test Data Factories ----------

const BASE_STOCKS: SectorStockItemData[] = [
  {
    id: '1',
    symbol: '600519',
    name: '贵州茅台',
    current_price: 1680,
    market_cap: 2.1e12,
    strength_score: 92,
    trend_direction: 1,
  },
  {
    id: '2',
    symbol: '000858',
    name: '五粮液',
    current_price: 156,
    market_cap: 6.1e11,
    strength_score: 88,
    trend_direction: 1,
  },
  {
    id: '3',
    symbol: '000568',
    name: '泸州老窖',
    current_price: 220,
    market_cap: 3.2e11,
    strength_score: 85,
    trend_direction: -1,
  },
]

/** 默认 3 只，按 strength_score 降序 */
export function createTestSectorStocks(): SectorStocksData {
  return {
    items: BASE_STOCKS,
    total: BASE_STOCKS.length,
    page: 1,
    page_size: 20,
    total_pages: 1,
  }
}

/** 造 total 条数据用于分页测试（AC-04）。每条按序生成，strength_score 递减。 */
export function createTestSectorStocksMany(total: number): SectorStocksData {
  const items: SectorStockItemData[] = Array.from({ length: total }, (_, i) => ({
    id: String(i + 1),
    symbol: String(600000 + i),
    name: `测试股${i + 1}`,
    current_price: 100 + i,
    market_cap: 1e9 * (total - i),
    strength_score: Math.max(10, 100 - i),
    trend_direction: i % 3 === 0 ? 1 : i % 3 === 1 ? -1 : 0,
  }))
  return {
    items,
    total,
    page: 1,
    page_size: 20,
    total_pages: Math.max(1, Math.ceil(total / 20)),
  }
}

/** 空成分股（AC-06） */
export function createTestSectorStocksEmpty(): SectorStocksData {
  return { items: [], total: 0, page: 1, page_size: 20, total_pages: 0 }
}

/** 个股详情测试数据（AC-07，对应首行 600519） */
export function createTestStockDetail(): StockDetailData {
  return { ...BASE_STOCKS[0] }
}

// ---------- Mock Helpers ----------

/**
 * Mock GET /api/v1/sectors/{sector_id}/stocks — 成分股列表。
 *
 * handler 内按 query 的 sort_by/sort_order/page/page_size 模拟后端排序与分页。
 */
export async function mockSectorStocks(
  page: Page,
  data: SectorStocksData = createTestSectorStocks()
): Promise<void> {
  await page.route(
    (url) => matchSectorStocksPath(url),
    async (route) => {
      if (route.request().method() !== 'GET') {
        await route.fallback()
        return
      }
      const query = parseQuery(route.request().url())
      // 排序（sortBy 限定为数值字段，避免字符串索引）
      const numericKeys = ['strength_score', 'market_cap', 'current_price'] as const
      const sortBy = numericKeys.includes(query.get('sort_by') as (typeof numericKeys)[number])
        ? (query.get('sort_by') as (typeof numericKeys)[number])
        : 'strength_score'
      const sortOrder = query.get('sort_order') === 'asc' ? 'asc' : 'desc'
      const pageNum = parseInt(query.get('page') || '1', 10) || 1
      const pageSize = parseInt(query.get('page_size') || '20', 10) || 20

      let items = [...data.items]
      items.sort((a, b) => {
        const av = a[sortBy] ?? -Infinity
        const bv = b[sortBy] ?? -Infinity
        return sortOrder === 'desc' ? bv - av : av - bv
      })
      const total = items.length
      // 分页
      const start = (pageNum - 1) * pageSize
      const paged = items.slice(start, start + pageSize)

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            items: paged,
            total,
            page: pageNum,
            page_size: pageSize,
            total_pages: Math.max(0, Math.ceil(total / pageSize)),
          },
        }),
      })
    }
  )
}

/** Mock 成分股接口返回空（AC-06） */
export async function mockSectorStocksEmpty(page: Page): Promise<void> {
  await mockSectorStocks(page, createTestSectorStocksEmpty())
}

/** Mock 成分股接口返回 500（AC-05） */
export async function mockSectorStocksError(page: Page): Promise<void> {
  await page.route(
    (url) => matchSectorStocksPath(url),
    async (route) => {
      if (route.request().method() !== 'GET') {
        await route.fallback()
        return
      }
      await route.fulfill({ status: 500, contentType: 'application/json', body: '{}' })
    }
  )
}

/** Mock GET /api/v1/stocks/{stock_id} — 个股详情（AC-07） */
export async function mockStockDetail(
  page: Page,
  data: StockDetailData = createTestStockDetail()
): Promise<void> {
  await page.route(
    (url) => matchStockDetailPath(url),
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

/**
 * Mock 板块详情页的图表接口 + 板块选择器接口。
 *
 * 进入 /dashboard/sector-analysis/{id} 会同时请求：
 * - strength-history / ma-history（图表）
 * - /sectors（板块选择器填充，详情页 page.tsx:54 挂载即调）
 * 不 mock 任一接口会 401 → 触发 handleUnauthorizedRedirect → 跳 /login，导致 fixture 失效。
 * 返回最小数据集即可。
 */
export async function mockSectorChartApis(page: Page): Promise<void> {
  const handler = async (route: import('@playwright/test').Route) => {
    if (route.request().method() !== 'GET') {
      await route.fallback()
      return
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        sector_id: '1',
        sector_name: '测试板块',
        data: [],
      }),
    })
  }
  await page.route((url) => matchSectorHistoryPath(url, 'strength-history'), handler)
  await page.route((url) => matchSectorHistoryPath(url, 'ma-history'), handler)
  // 板块选择器列表（详情页挂载即调用，返回 1 个板块避免 401）
  await page.route(
    (url) => toPathname(url) === '/api/v1/sectors',
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
            items: [
              { id: '1', code: 'BK0001', name: '测试板块', type: 'industry' },
            ],
            total: 1,
            page: 1,
            page_size: 100,
          },
        }),
      })
    }
  )
}
