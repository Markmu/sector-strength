import { Page } from '@playwright/test'

/**
 * Mock helpers for ETF monitor page E2E tests
 *
 * 后端用户侧 API（baseURL 已含 /api/v1）：
 * - GET /api/v1/etf-monitor/index-rankings  — 指数排行（按 index_code 聚合 + 排序 + 分页）
 * - GET /api/v1/etf-monitor/index-detail    — 指数下 ETF 明细（展开行，按 index_code 筛）
 * - GET /api/v1/etf-monitor/trend            — 历史趋势（指数/单只ETF × 份额/净流入额 × 7/30/90日）
 * - GET /api/v1/etf-monitor/latest-date      — 最新交易日（日期选择器默认值）
 *
 * 参照 mock-sector-fund-flow-api.ts 模式：
 * - URL 匹配用 URL.pathname 精确匹配（避免 glob 歧义）
 * - test data factory 用 camelCase（与 etfMonitorTypes.ts 对齐）
 * - handler 内按 URLSearchParams 解析 sort_by/order/target_type/target_code/metric/days/trade_date
 * - query 参数保持 snake_case，响应字段 camelCase（后端 _dict_to_camel）
 *
 * 特例（架构 §7.6）：sort_by 与 metric 参数的「值」用 camelCase（netInflow /
 * shareChange / share），与后端取值一致，不要下划线化。
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

// ---------- Types (与 src/types/etfMonitorTypes.ts 对齐) ----------

export type EtfSortBy = 'netInflow' | 'shareChange' | 'share'
export type EtfOrder = 'asc' | 'desc'
export type EtfTargetType = 'index' | 'etf'
export type EtfTrendMetric = 'share' | 'netInflow'
export type EtfTrendDays = 7 | 30 | 90

export interface EtfIndexRankingItem {
  indexCode: string
  indexName: string
  etfCount: number
  totalShare: number | null
  totalShareChange: number | null
  totalNetInflow: number | null
  totalSize: number | null
}

export interface EtfIndexRankingsData {
  hasData: boolean
  tradeDate: string | null
  items: EtfIndexRankingItem[]
  total: number
  page: number
  pageSize: number
}

export interface EtfDetailItem {
  tsCode: string
  name: string
  unitNav: number | null
  share: number | null
  totalSize: number | null
  shareChange: number | null
  netInflow: number | null
  changePercent: number | null
}

export interface EtfIndexDetailData {
  hasData: boolean
  items: EtfDetailItem[]
}

export interface EtfTrendPoint {
  tradeDate: string
  value: number | null
}

export interface EtfTrendData {
  hasData: boolean
  metric: string
  unit: string
  series: EtfTrendPoint[]
}

export interface EtfLatestDateData {
  hasData: boolean
  tradeDate: string | null
}

// ---------- Test Data Factory ----------

/**
 * 默认指数排行测试数据（按 index_code 聚合，按 netInflow desc 排序）
 *
 * 3 个指数：
 * - 沪深300（000300.SH）：净流入 +12亿、份额 800 亿份、份额变化 +5 亿份
 * - 中证500（000905.SH）：净流入 -3.5亿（负值，绿色）、份额 500 亿份、份额变化 -2 亿份
 * - 创业板指（399006.SZ）：净流入 +0.8亿、份额 300 亿份、份额变化 +0.5 亿份
 */
export function createTestEtfIndexRankings(): EtfIndexRankingsData {
  const items: EtfIndexRankingItem[] = [
    {
      indexCode: '000300.SH',
      indexName: '沪深300',
      etfCount: 18,
      totalShare: 800,
      totalShareChange: 5,
      totalNetInflow: 12,
      totalSize: 560,
    },
    {
      indexCode: '000905.SH',
      indexName: '中证500',
      etfCount: 12,
      totalShare: 500,
      totalShareChange: -2,
      totalNetInflow: -3.5,
      totalSize: 300,
    },
    {
      indexCode: '399006.SZ',
      indexName: '创业板指',
      etfCount: 6,
      totalShare: 300,
      totalShareChange: 0.5,
      totalNetInflow: 0.8,
      totalSize: 120,
    },
  ]

  return {
    hasData: true,
    tradeDate: '2026-07-28',
    items,
    total: items.length,
    page: 1,
    pageSize: 20,
  }
}

/** 指数排行空数据（该日期暂无 ETF 数据 → 空态） */
export function createTestEtfIndexRankingsEmpty(): EtfIndexRankingsData {
  return {
    hasData: false,
    tradeDate: null,
    items: [],
    total: 0,
    page: 1,
    pageSize: 20,
  }
}

/**
 * 指数明细测试数据（展开指数看 ETF 明细）。
 *
 * 沪深300（000300.SH）下 2 只 ETF，按 netInflow desc 排序：
 * - 510300.SH 华泰柏瑞沪深300ETF：净流入 +6亿、份额 400 亿份、份额变化 +3 亿份
 * - 510310.SH 易方达沪深300ETF：净流入 +2亿、份额 200 亿份、份额变化 +1 亿份
 */
export function createTestEtfIndexDetail(opts?: {
  indexCode?: string
}): EtfIndexDetailData {
  const indexCode = opts?.indexCode ?? '000300.SH'

  const itemsByIndex: Record<string, EtfDetailItem[]> = {
    '000300.SH': [
      {
        tsCode: '510300.SH',
        name: '华泰柏瑞沪深300ETF',
        unitNav: 4.123,
        share: 400,
        totalSize: 1649.2,
        shareChange: 3,
        netInflow: 6,
        changePercent: 0.85,
      },
      {
        tsCode: '510310.SH',
        name: '易方达沪深300ETF',
        unitNav: 1.856,
        share: 200,
        totalSize: 371.2,
        shareChange: 1,
        netInflow: 2,
        changePercent: null,
      },
    ],
  }

  const items = itemsByIndex[indexCode] ?? [
    {
      tsCode: 'mock-001',
      name: `${indexCode}样本ETF`,
      unitNav: 1.0,
      share: 100,
      totalSize: 100,
      shareChange: 1,
      netInflow: 1,
      changePercent: null,
    },
  ]
  return { hasData: true, items }
}

/**
 * 历史趋势测试数据（份额/净流入额曲线）。
 *
 * days 参数控制序列长度（7/30/90），默认 7 日；shortHistory=true 模拟历史不足区间。
 */
export function createTestEtfTrend(opts?: {
  targetType?: EtfTargetType
  targetCode?: string
  metric?: EtfTrendMetric
  days?: EtfTrendDays
  shortHistory?: boolean
  empty?: boolean
}): EtfTrendData {
  const targetType = opts?.targetType ?? 'index'
  const metric = opts?.metric ?? 'netInflow'
  const days = opts?.days ?? 7

  if (opts?.empty) {
    return {
      hasData: false,
      metric,
      unit: metric === 'share' ? '亿份' : '亿元',
      series: [],
    }
  }

  const pointCount = opts?.shortHistory ? 3 : days
  const scale = targetType === 'etf' ? 0.1 : 1

  const baseDate = new Date('2026-07-22T00:00:00Z')
  const series: EtfTrendPoint[] = []
  for (let i = 0; i < pointCount; i++) {
    const d = new Date(baseDate)
    d.setUTCDate(d.getUTCDate() + i)
    const tradeDate = d.toISOString().slice(0, 10)

    let value: number | null
    if (metric === 'share') {
      value = Math.round((800 + i * 5) * scale * 100) / 100
    } else {
      const raw = i % 3 === 1 ? -(2 + i) : 3 + i
      value = Math.round(raw * scale * 100) / 100
    }
    series.push({ tradeDate, value })
  }

  return {
    hasData: series.length > 0,
    metric,
    unit: metric === 'share' ? '亿份' : '亿元',
    series,
  }
}

/** 最新交易日测试数据 */
export function createTestEtfLatestDate(
  tradeDate: string | null = '2026-07-28'
): EtfLatestDateData {
  return {
    hasData: tradeDate != null,
    tradeDate,
  }
}

// ---------- Mock Helpers ----------

/**
 * Mock GET /api/v1/etf-monitor/index-rankings — 指数排行
 *
 * handler 内按 query 的 sort_by/order/page/page_size/trade_date 模拟后端行为：
 * - sort_by/order：在内存内对 items 重排（模拟后端排序）
 * - page/page_size：透传（分页由真实分页场景测试，默认单页全量）
 */
export async function mockEtfIndexRankings(
  page: Page,
  data: EtfIndexRankingsData = createTestEtfIndexRankings()
): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/etf-monitor/index-rankings'),
    async (route) => {
      if (route.request().method() !== 'GET') {
        await route.fallback()
        return
      }
      const query = parseQuery(route.request().url())
      const sortBy = (query.get('sort_by') as EtfSortBy) || 'netInflow'
      const order = (query.get('order') as EtfOrder) || 'desc'

      // 调用方传空数据（hasData=false）时直接返回，不重排
      if (!data.hasData || data.items.length === 0) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true, data }),
        })
        return
      }

      const baseItems = data.items

      // 排序键映射到字段（sort_by 值 camelCase）
      const sortFieldMap: Record<EtfSortBy, keyof EtfIndexRankingItem> = {
        netInflow: 'totalNetInflow',
        shareChange: 'totalShareChange',
        share: 'totalShare',
      }
      const field = sortFieldMap[sortBy]
      const sorted = [...baseItems].sort((a, b) => {
        const av = (a[field] as number | null) ?? 0
        const bv = (b[field] as number | null) ?? 0
        return order === 'asc' ? av - bv : bv - av
      })

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            hasData: true,
            tradeDate: data.tradeDate ?? '2026-07-28',
            items: sorted,
            total: sorted.length,
            page: parseInt(query.get('page') || '1', 10),
            pageSize: parseInt(query.get('page_size') || '20', 10),
          },
        }),
      })
    }
  )
}

/** Mock index-rankings 失败（排行加载失败错误态 + 重试） */
export async function mockEtfIndexRankingsError(page: Page): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/etf-monitor/index-rankings'),
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

/** Mock index-rankings 空数据（该日期暂无 ETF 数据 → 空态） */
export async function mockEtfIndexRankingsEmpty(page: Page): Promise<void> {
  await mockEtfIndexRankings(page, createTestEtfIndexRankingsEmpty())
}

/**
 * Mock GET /api/v1/etf-monitor/index-detail — 指数明细（展开行）
 *
 * handler 内按 query 的 index_code 返回该指数下 ETF 明细。
 */
export async function mockEtfIndexDetail(
  page: Page,
  data: EtfIndexDetailData = createTestEtfIndexDetail()
): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/etf-monitor/index-detail'),
    async (route) => {
      if (route.request().method() !== 'GET') {
        await route.fallback()
        return
      }
      const query = parseQuery(route.request().url())
      const indexCode = query.get('index_code') || '000300.SH'

      const responseData = createTestEtfIndexDetail({ indexCode })

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: responseData }),
      })
    }
  )
}

/** Mock index-detail 失败（展开明细加载失败） */
export async function mockEtfIndexDetailError(page: Page): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/etf-monitor/index-detail'),
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
 * Mock GET /api/v1/etf-monitor/trend — 历史趋势曲线
 *
 * shortHistory / empty 由 query 参数控制（约定 target_code 含 '__short__' /
 * '__empty__' 标记）。
 */
export async function mockEtfTrend(
  page: Page,
  data?: EtfTrendData
): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/etf-monitor/trend'),
    async (route) => {
      if (route.request().method() !== 'GET') {
        await route.fallback()
        return
      }
      const query = parseQuery(route.request().url())
      const targetType = (query.get('target_type') as EtfTargetType) || 'index'
      const targetCode = query.get('target_code') || '000300.SH'
      const metric = (query.get('metric') as EtfTrendMetric) || 'netInflow'
      const days = (parseInt(query.get('days') || '7', 10) as EtfTrendDays) || 7

      // 调用方显式传空数据 → 空态
      if (data && !data.hasData) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true, data }),
        })
        return
      }

      const shortHistory = targetCode.includes('__short__')
      const empty = targetCode.includes('__empty__')

      const responseData = createTestEtfTrend({
        targetType,
        targetCode,
        metric,
        days,
        shortHistory,
        empty,
      })

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: responseData }),
      })
    }
  )
}

/** Mock trend 失败（趋势数据加载失败） */
export async function mockEtfTrendError(page: Page): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/etf-monitor/trend'),
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
 * Mock GET /api/v1/etf-monitor/latest-date — 最新交易日
 */
export async function mockEtfLatestDate(
  page: Page,
  tradeDate: string | null = '2026-07-28'
): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/etf-monitor/latest-date'),
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
          data: { hasData: tradeDate != null, tradeDate },
        }),
      })
    }
  )
}

/**
 * 一键安装全量默认 mock（index-rankings + index-detail + trend + latest-date），
 * 用于多数 Happy 场景。
 */
export async function installEtfMonitorMocks(page: Page): Promise<void> {
  await mockEtfIndexRankings(page)
  await mockEtfIndexDetail(page)
  await mockEtfTrend(page)
  await mockEtfLatestDate(page, '2026-07-28')
}
