import { Page } from '@playwright/test'

/**
 * Mock helpers for ETF monitor page E2E tests (14 期 plan-05)
 *
 * 后端用户侧 API（baseURL 已含 /api/v1）：
 * - GET /api/v1/etf-monitor/index-rankings  — 指数排行（宽基/行业 × 净流入额/份额变化/份额排序 + 分页）
 * - GET /api/v1/etf-monitor/index-detail    — 指数下 ETF 明细（展开行）
 * - GET /api/v1/etf-monitor/trend            — 历史趋势（指数/单只ETF × 份额/净流入额 × 7/30/90日）
 * - GET /api/v1/etf-monitor/latest-date      — 最新交易日（日期选择器默认值）
 *
 * 参照 mock-sector-fund-flow-api.ts 模式：
 * - URL 匹配用 URL.pathname 精确匹配（避免 glob 歧义）
 * - test data factory 用 camelCase（架构 §7.2 契约 + plan-04/05 §3；etfMonitorTypes.ts）
 * - handler 内按 URLSearchParams 解析 category/sort_by/order/target_type/target_code/metric/days/trade_date 决定返回哪份 fixture
 * - query 参数保持 snake_case，响应字段 camelCase（后端 _dict_to_camel）
 *
 * 特例（架构 §7.6）：sort_by 与 metric 参数的「值」用 camelCase（netInflow /
 * shareChange / share），与后端取值一致，不要下划线化。
 *
 * 外层契约（{ success: true, data: {...} }）：前端 hook 读 res.data.data。
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

// ---------- Types (与 src/types/etfMonitorTypes.ts 对齐，架构 §7.2) ----------

export type EtfCategoryKey = 'broad' | 'industry'
export type EtfSortBy = 'netInflow' | 'shareChange' | 'share'
export type EtfOrder = 'asc' | 'desc'
export type EtfTargetType = 'index' | 'etf'
export type EtfTrendMetric = 'share' | 'netInflow'
export type EtfTrendDays = 7 | 30 | 90

export interface EtfIndexRankingItem {
  indexName: string
  category: string
  etfCount: number
  totalShare: number | null
  totalShareChange: number | null
  totalNetInflow: number | null
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
 * 默认指数排行测试数据（覆盖 TC-5.1~5.5 各场景）
 *
 * 宽基维度（broad）默认 3 行，按 netInflow desc 排序：
 * - 沪深300：净流入 +12亿（正值，红色）、份额 800 亿份、份额变化 +5 亿份
 * - 中证500：净流入 -3.5亿（负值，绿色）、份额 500 亿份、份额变化 -2 亿份
 * - 创业板指：净流入 +0.8亿、份额 300 亿份、份额变化 +0.5 亿份
 *
 * 行业维度（industry）默认 2 行，标签差异化（便于 AC-02 切换断言）：
 * - 半导体：净流入 +8亿
 * - 新能源车：净流出 -2亿
 *
 * 金额单位：netInflow 亿元、share/shareChange 亿份（与前端契约一致，直接展示）。
 * 按不同 sortBy 排序时 handler 内存重排（见 mockEtfIndexRankings）。
 */
export function createTestEtfIndexRankings(
  opts?: { category?: EtfCategoryKey }
): EtfIndexRankingsData {
  const category = opts?.category ?? 'broad'

  const itemsByType: Record<EtfCategoryKey, EtfIndexRankingItem[]> = {
    broad: [
      {
        indexName: '沪深300',
        category: 'broad',
        etfCount: 18,
        totalShare: 800,
        totalShareChange: 5,
        totalNetInflow: 12,
      },
      {
        indexName: '中证500',
        category: 'broad',
        etfCount: 12,
        totalShare: 500,
        totalShareChange: -2,
        totalNetInflow: -3.5,
      },
      {
        indexName: '创业板指',
        category: 'broad',
        etfCount: 6,
        totalShare: 300,
        totalShareChange: 0.5,
        totalNetInflow: 0.8,
      },
    ],
    industry: [
      {
        indexName: '半导体',
        category: 'industry',
        etfCount: 9,
        totalShare: 420,
        totalShareChange: 4,
        totalNetInflow: 8,
      },
      {
        indexName: '新能源车',
        category: 'industry',
        etfCount: 5,
        totalShare: 210,
        totalShareChange: -1.5,
        totalNetInflow: -2,
      },
    ],
  }

  const items = itemsByType[category]
  return {
    hasData: true,
    tradeDate: '2026-07-28',
    items,
    total: items.length,
    page: 1,
    pageSize: 20,
  }
}

/** 指数排行空数据（TC-5.4：该日期暂无 ETF 数据 → 空态） */
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
 * 指数明细测试数据（TC-5.6：展开指数看 ETF 明细）。
 *
 * 沪深300 下 2 只 ETF，按 netInflow desc 排序（与表格展开默认一致）：
 * - 510300.SH 华泰柏瑞沪深300ETF：净流入 +6亿、份额 400 亿份、份额变化 +3 亿份
 * - 510310.SH 易方达沪深300ETF：净流入 +2亿、份额 200 亿份、份额变化 +1 亿份
 *
 * changePercent 首版因数据源 fund_daily 不可用可能为 null（plan-01 §6 风险），
 * 这里给一个 null 一个有值，验证明细列容错（E2E 不要求该列有值）。
 */
export function createTestEtfIndexDetail(opts?: {
  indexName?: string
}): EtfIndexDetailData {
  const indexName = opts?.indexName ?? '沪深300'

  const itemsByIndex: Record<string, EtfDetailItem[]> = {
    沪深300: [
      {
        tsCode: '510300.SH',
        name: '华泰柏瑞沪深300ETF',
        unitNav: 4.123,
        share: 400,
        shareChange: 3,
        netInflow: 6,
        changePercent: 0.85,
      },
      {
        tsCode: '510310.SH',
        name: '易方达沪深300ETF',
        unitNav: 1.856,
        share: 200,
        shareChange: 1,
        netInflow: 2,
        changePercent: null, // 容错：首版 change_percent 可能 null
      },
    ],
  }

  const items = itemsByIndex[indexName] ?? [
    {
      tsCode: 'mock-001',
      name: `${indexName}样本ETF`,
      unitNav: 1.0,
      share: 100,
      shareChange: 1,
      netInflow: 1,
      changePercent: null,
    },
  ]
  return { hasData: true, items }
}

/**
 * 历史趋势测试数据（TC-5.8/5.9：份额/净流入额曲线）。
 *
 * 指数对象返回多日序列（按 tradeDate 升序）：
 * - share：份额单调，全正
 * - netInflow：正负交替，验证零轴基线 + 正负段色标
 *
 * 单只 ETF 对象量级小于汇总（AC-08：单只 < 汇总）。
 *
 * days 参数控制序列长度（7/30/90），默认 7 日；调用方可通过 createTestEtfTrend
 * 传 shortHistory=true 模拟历史不足区间（TC-5.9：序列点少于所选 days）。
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
  const targetCode = opts?.targetCode ?? '沪深300'
  const metric = opts?.metric ?? 'netInflow'
  const days = opts?.days ?? 7

  // 空数据（TC：该对象完全无数据 → 空态）
  if (opts?.empty) {
    return {
      hasData: false,
      metric,
      unit: metric === 'share' ? '亿份' : '亿元',
      series: [],
    }
  }

  // 历史不足区间（TC-5.9）：只返回 3 天数据（少于 days=7/30/90）
  const pointCount = opts?.shortHistory ? 3 : days

  // 指数量级 vs 单只 ETF 量级（AC-08：单只 < 汇总）
  const scale = targetType === 'etf' ? 0.1 : 1

  // 生成序列点（按 tradeDate 升序，2026-07-22 起）
  const baseDate = new Date('2026-07-22T00:00:00Z')
  const series: EtfTrendPoint[] = []
  for (let i = 0; i < pointCount; i++) {
    const d = new Date(baseDate)
    d.setUTCDate(d.getUTCDate() + i)
    const tradeDate = d.toISOString().slice(0, 10)

    let value: number | null
    if (metric === 'share') {
      // 份额单调递增、全正
      value = Math.round((800 + i * 5) * scale * 100) / 100
    } else {
      // netInflow 正负交替，验证零轴基线 + 正负段色标
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
 * handler 内按 query 的 category/sort_by/order/page/page_size/trade_date 模拟后端行为：
 * - category 切换：返回对应维度数据（broad/industry 差异化标签）
 * - sort_by/order：在内存内对 items 重排（模拟后端排序）
 * - page/page_size：透传（分页 AC-13 由真实分页场景测试，默认单页全量）
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
      const category = (query.get('category') as EtfCategoryKey) || 'broad'
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

      // 按 category 取差异化数据（若调用方传默认数据但 query category 不同，
      // 用按 category 生成的数据，保证切换维度时标签变化可断言）
      const baseItems = createTestEtfIndexRankings({ category }).items

      // 排序键映射到字段（sort_by 值 camelCase，架构 §7.6 特例）
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

/** Mock index-rankings 失败（TC-5.12：排行加载失败错误态 + 重试） */
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

/** Mock index-rankings 空数据（TC-5.4：该日期暂无 ETF 数据 → 空态） */
export async function mockEtfIndexRankingsEmpty(page: Page): Promise<void> {
  await mockEtfIndexRankings(page, createTestEtfIndexRankingsEmpty())
}

/**
 * Mock GET /api/v1/etf-monitor/index-detail — 指数明细（展开行）
 *
 * handler 内按 query 的 index_name 返回该指数下 ETF 明细。
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
      const indexName = query.get('index_name') || '沪深300'

      // 按 index_name 取差异化数据（默认展开沪深300）
      const responseData = createTestEtfIndexDetail({ indexName })

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
 * handler 内按 query 的 target_type/target_code/metric/days/end_date 返回对应序列。
 * 支持历史不足区间（shortHistory）与空数据（empty）场景：
 * - 调用方传 data.hasData=false 时直接返回空 series
 * - 否则按 targetType/metric/days 生成序列（history 充足）
 *
 * shortHistory / empty 由 query 参数控制（约定 target_code 含 '__short__' /
 * '__empty__' 标记），便于 TC-5.9 / 空态场景切换。
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
      const targetCode = query.get('target_code') || '沪深300'
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

      // 按 target_code 标记切换场景：
      // - 含 '__short__' → 历史不足区间（TC-5.9）
      // - 含 '__empty__' → 完全无数据空态
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
 * 用于多数 Happy 场景（TC-5.1/5.2/5.3/5.5/5.6/5.7/5.8/5.11）。
 *
 * 参照 installFullFundFlowMocks 范式：封装 4 端点默认成功响应。
 */
export async function installEtfMonitorMocks(page: Page): Promise<void> {
  await mockEtfIndexRankings(page)
  await mockEtfIndexDetail(page)
  await mockEtfTrend(page)
  await mockEtfLatestDate(page, '2026-07-28')
}
