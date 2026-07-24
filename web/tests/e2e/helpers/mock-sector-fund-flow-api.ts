import { Page } from '@playwright/test'

/**
 * Mock helpers for sector fund flow page E2E tests (plan-03)
 *
 * 后端用户侧 API（baseURL 已含 /api/v1）：
 * - GET /api/v1/sector-fund-flow/rankings      — 资金流排行榜（最新采样点）
 * - GET /api/v1/sector-fund-flow/timeseries    — 盘中变化曲线（按板块名分组）
 * - GET /api/v1/sector-fund-flow/latest-date   — 最新交易日
 *
 * 参照 mock-fund-crowd-api.ts 模式：
 * - URL 匹配用 URL.pathname 精确匹配（避免 glob 歧义）
 * - test data factory 用 camelCase（架构 §7.2 契约 + plan-03 §3）
 * - handler 内按 URLSearchParams 解析 sector_type/sort_by/order/sector_names 决定返回哪份 fixture
 * - query 参数保持 snake_case，响应字段 camelCase（后端 _dict_to_camel）
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

// ---------- Types (与 src/types/fundFlowTypes.ts 对齐，架构 §7.2) ----------

export type SectorTypeKey = 'industry' | 'concept' | 'region'
export type FundFlowSortBy = 'net_inflow' | 'inflow' | 'outflow'
export type FundFlowOrder = 'asc' | 'desc'

export interface FundFlowRankingItemData {
  rank: number
  sectorName: string
  sectorId: number | null
  changePercent: number | null
  inflow: number | null
  outflow: number | null
  netInflow: number | null
  companyCount: number | null
  leadingStock: string | null
  leadingStockChange: number | null
  currentPrice: number | null
}

export interface FundFlowRankingsData {
  hasData: boolean
  tradeDate: string | null
  items: FundFlowRankingItemData[]
  total: number
  page: number
  pageSize: number
}

export interface FundFlowSeriesPointData {
  sampleTime: string
  netInflow: number | null
}

export interface FundFlowSeriesItemData {
  sectorName: string
  data: FundFlowSeriesPointData[]
}

export interface FundFlowTimeseriesData {
  hasData: boolean
  tradeDate: string | null
  series: FundFlowSeriesItemData[]
}

export interface FundFlowLatestDateData {
  latestDate: string | null
}

// ---------- Test Data Factory ----------

/**
 * 默认排行榜测试数据（覆盖 TC1/TC2/TC3/TC4 各场景）
 *
 * 维度（industry）默认 3 行，按 net_inflow desc 排序：
 * - 半导体：净额 +12亿（净流入，红色）
 * - 证券：净额 -3.5亿（净流出，绿色）
 * - 银行：净额 +0.8亿
 *
 * 金额单位为元（后端原始口径），前端会换算成亿/万展示。
 * industry 行的 sectorId 非 null（可跳转强度页）；concept 行全部 null（验证不可跳转）。
 */
export function createTestFundFlowRankings(
  opts?: { sectorType?: SectorTypeKey }
): FundFlowRankingsData {
  const sectorType = opts?.sectorType ?? 'industry'
  const YI = 1e8

  const itemsByType: Record<SectorTypeKey, FundFlowRankingItemData[]> = {
    industry: [
      {
        rank: 1,
        sectorName: '半导体',
        sectorId: 101,
        changePercent: 3.21,
        inflow: 15 * YI,
        outflow: 3 * YI,
        netInflow: 12 * YI,
        companyCount: 120,
        leadingStock: '中芯国际',
        leadingStockChange: 5.4,
        currentPrice: 88.5,
      },
      {
        rank: 2,
        sectorName: '证券',
        sectorId: 102,
        changePercent: -1.05,
        inflow: 4 * YI,
        outflow: 7.5 * YI,
        netInflow: -3.5 * YI,
        companyCount: 50,
        leadingStock: '中信证券',
        leadingStockChange: -2.1,
        currentPrice: 22.3,
      },
      {
        rank: 3,
        sectorName: '银行',
        sectorId: 103,
        changePercent: 0.32,
        inflow: 5 * YI,
        outflow: 4.2 * YI,
        netInflow: 0.8 * YI,
        companyCount: 42,
        leadingStock: '招商银行',
        leadingStockChange: 0.85,
        currentPrice: 35.6,
      },
    ],
    concept: [
      {
        rank: 1,
        sectorName: '新能源',
        sectorId: null, // 概念板块未匹配 sectors 表 → 不可跳转
        changePercent: 2.1,
        inflow: 10 * YI,
        outflow: 2 * YI,
        netInflow: 8 * YI,
        companyCount: 80,
        leadingStock: '宁德时代',
        leadingStockChange: 4.2,
        currentPrice: 210.0,
      },
      {
        rank: 2,
        sectorName: '芯片',
        sectorId: null,
        changePercent: -0.8,
        inflow: 3 * YI,
        outflow: 6 * YI,
        netInflow: -3 * YI,
        companyCount: 60,
        leadingStock: '韦尔股份',
        leadingStockChange: -1.5,
        currentPrice: 95.2,
      },
    ],
    region: [
      {
        rank: 1,
        sectorName: '贵州',
        sectorId: null,
        changePercent: 1.2,
        inflow: 8 * YI,
        outflow: 2 * YI,
        netInflow: 6 * YI,
        companyCount: 30,
        leadingStock: '贵州茅台',
        leadingStockChange: 1.8,
        currentPrice: 1680.0,
      },
    ],
  }

  const items = itemsByType[sectorType]
  return {
    hasData: true,
    tradeDate: '2026-07-24',
    items,
    total: items.length,
    page: 1,
    pageSize: 20,
  }
}

/** 排行榜空数据（TC：该日期暂无资金流数据） */
export function createTestFundFlowRankingsEmpty(): FundFlowRankingsData {
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
 * 盘中变化曲线测试数据（TC5：叠加曲线）
 *
 * industry 维度返回 半导体 + 证券 两条曲线，采样点为交易时段（09:30 ~ 15:00 间），
 * 数值单位为元（前端换算成亿）。半导体全程净流入为正，证券全程净流出为负，
 * 便于断言曲线渲染与图例。
 */
export function createTestFundFlowTimeseries(
  opts?: { sectorNames?: string[]; sectorType?: SectorTypeKey }
): FundFlowTimeseriesData {
  const sectorType = opts?.sectorType ?? 'industry'
  const YI = 1e8

  const fullSeriesByType: Record<SectorTypeKey, FundFlowSeriesItemData[]> = {
    industry: [
      {
        sectorName: '半导体',
        data: [
          { sampleTime: '2026-07-24T09:30:00', netInflow: 3 * YI },
          { sampleTime: '2026-07-24T10:30:00', netInflow: 7 * YI },
          { sampleTime: '2026-07-24T14:00:00', netInflow: 12 * YI },
        ],
      },
      {
        sectorName: '证券',
        data: [
          { sampleTime: '2026-07-24T09:30:00', netInflow: -1 * YI },
          { sampleTime: '2026-07-24T10:30:00', netInflow: -2.5 * YI },
          { sampleTime: '2026-07-24T14:00:00', netInflow: -3.5 * YI },
        ],
      },
      {
        sectorName: '银行',
        data: [
          { sampleTime: '2026-07-24T09:30:00', netInflow: 0.2 * YI },
          { sampleTime: '2026-07-24T10:30:00', netInflow: 0.5 * YI },
          { sampleTime: '2026-07-24T14:00:00', netInflow: 0.8 * YI },
        ],
      },
    ],
    concept: [
      {
        sectorName: '新能源',
        data: [
          { sampleTime: '2026-07-24T09:30:00', netInflow: 2 * YI },
          { sampleTime: '2026-07-24T14:00:00', netInflow: 8 * YI },
        ],
      },
      {
        sectorName: '芯片',
        data: [
          { sampleTime: '2026-07-24T09:30:00', netInflow: -0.5 * YI },
          { sampleTime: '2026-07-24T14:00:00', netInflow: -3 * YI },
        ],
      },
    ],
    region: [
      {
        sectorName: '贵州',
        data: [
          { sampleTime: '2026-07-24T09:30:00', netInflow: 1.5 * YI },
          { sampleTime: '2026-07-24T14:00:00', netInflow: 6 * YI },
        ],
      },
    ],
  }

  const fullSeries = fullSeriesByType[sectorType] ?? []
  // 若调用方指定 sectorNames，仅返回这些板块的曲线（模拟后端按 sector_names 过滤）
  const names = opts?.sectorNames
  const series =
    names && names.length > 0
      ? fullSeries.filter((s) => names.includes(s.sectorName))
      : fullSeries

  return {
    hasData: series.length > 0,
    tradeDate: '2026-07-24',
    series,
  }
}

/** 盘中变化空数据（TC：无采样数据空态） */
export function createTestFundFlowTimeseriesEmpty(): FundFlowTimeseriesData {
  return {
    hasData: false,
    tradeDate: null,
    series: [],
  }
}

/** 最新交易日测试数据 */
export function createTestFundFlowLatestDate(
  latestDate: string | null = '2026-07-24'
): FundFlowLatestDateData {
  return { latestDate }
}

// ---------- Mock Helpers ----------

/**
 * Mock GET /api/v1/sector-fund-flow/rankings — 排行榜
 *
 * handler 内按 query 的 sector_type/sort_by/order 模拟后端排序与维度过滤：
 * - sector_type 切换：返回对应维度数据（industry/concept/region 差异化标签）
 * - sort_by/order：在内存内对 items 重排（模拟后端排序）
 */
export async function mockFundFlowRankings(
  page: Page,
  data: FundFlowRankingsData = createTestFundFlowRankings()
): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/sector-fund-flow/rankings'),
    async (route) => {
      if (route.request().method() !== 'GET') {
        await route.fallback()
        return
      }
      const query = parseQuery(route.request().url())
      const sectorType = (query.get('sector_type') as SectorTypeKey) || 'industry'
      const sortBy = (query.get('sort_by') as FundFlowSortBy) || 'net_inflow'
      const order = (query.get('order') as FundFlowOrder) || 'desc'

      // 调用方传空数据（hasData=false）时直接返回，不重排
      if (!data.hasData || data.items.length === 0) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true, data }),
        })
        return
      }

      // 按 sector_type 取差异化数据（若 data 是默认 industry 数据但 query 是 concept，
      // 用按 type 生成的数据，保证切换维度时标签变化可断言）
      const baseItems =
        sectorType === (data as FundFlowRankingsData & { _originType?: string })._originType
          ? data.items
          : createTestFundFlowRankings({ sectorType }).items

      // 排序键映射到字段
      const sortFieldMap: Record<FundFlowSortBy, keyof FundFlowRankingItemData> = {
        net_inflow: 'netInflow',
        inflow: 'inflow',
        outflow: 'outflow',
      }
      const field = sortFieldMap[sortBy]
      const sorted = [...baseItems].sort((a, b) => {
        const av = (a[field] as number | null) ?? 0
        const bv = (b[field] as number | null) ?? 0
        return order === 'asc' ? av - bv : bv - av
      })
      // 重排 rank
      const reRanked = sorted.map((it, idx) => ({ ...it, rank: idx + 1 }))

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            hasData: true,
            tradeDate: data.tradeDate ?? '2026-07-24',
            items: reRanked,
            total: reRanked.length,
            page: parseInt(query.get('page') || '1', 10),
            pageSize: parseInt(query.get('page_size') || '20', 10),
          },
        }),
      })
    }
  )
}

/** Mock rankings 失败（TC6：排行榜加载失败错误态） */
export async function mockFundFlowRankingsError(page: Page): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/sector-fund-flow/rankings'),
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

/** Mock rankings 空数据（该日期暂无资金流数据） */
export async function mockFundFlowRankingsEmpty(page: Page): Promise<void> {
  await mockFundFlowRankings(page, createTestFundFlowRankingsEmpty())
}

/**
 * Mock GET /api/v1/sector-fund-flow/timeseries — 盘中变化曲线
 *
 * handler 内按 query 的 sector_names（逗号分隔）+ sector_type 返回对应曲线。
 * sector_names 为空时后端约定返回空 series（hasData=false）。
 */
export async function mockFundFlowTimeseries(
  page: Page,
  data: FundFlowTimeseriesData = createTestFundFlowTimeseries()
): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/sector-fund-flow/timeseries'),
    async (route) => {
      if (route.request().method() !== 'GET') {
        await route.fallback()
        return
      }
      const query = parseQuery(route.request().url())
      const sectorType = (query.get('sector_type') as SectorTypeKey) || 'industry'
      const sectorNamesRaw = query.get('sector_names') || ''
      const sectorNames = sectorNamesRaw
        ? sectorNamesRaw.split(',').filter(Boolean)
        : []

      // 调用方传空数据（hasData=false）时直接返回
      if (!data.hasData) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true, data }),
        })
        return
      }

      const responseData = createTestFundFlowTimeseries({
        sectorNames,
        sectorType,
      })

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: responseData }),
      })
    }
  )
}

/** Mock timeseries 失败（盘中变化数据加载失败） */
export async function mockFundFlowTimeseriesError(page: Page): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/sector-fund-flow/timeseries'),
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

/** Mock timeseries 空数据（无采样数据空态） */
export async function mockFundFlowTimeseriesEmpty(page: Page): Promise<void> {
  await mockFundFlowTimeseries(page, createTestFundFlowTimeseriesEmpty())
}

/**
 * Mock GET /api/v1/sector-fund-flow/latest-date — 最新交易日
 */
export async function mockFundFlowLatestDate(
  page: Page,
  latestDate: string | null = '2026-07-24'
): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/sector-fund-flow/latest-date'),
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
          data: { latestDate },
        }),
      })
    }
  )
}

/**
 * 一键安装全量默认 mock（rankings + timeseries + latest-date），用于多数 Happy 场景。
 */
export async function installFullFundFlowMocks(page: Page): Promise<void> {
  await mockFundFlowRankings(page)
  await mockFundFlowTimeseries(page)
  await mockFundFlowLatestDate(page, '2026-07-24')
}
