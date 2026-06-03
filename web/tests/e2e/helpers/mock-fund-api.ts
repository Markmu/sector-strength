import { Page } from '@playwright/test'

/**
 * Mock helpers for fund-related E2E tests
 *
 * 所有 mock helper 集中管理，避免在 spec 文件中重复写 page.route()
 *
 * URL 匹配策略：使用 URL 对象解析后按 pathname 精确匹配，避免 glob pattern 的歧义
 */

// ---------- Types ----------

export interface FundItem {
  tsCode: string
  name: string
  management?: string
  custodian?: string
  fundType?: string
  investType?: string
  benchmark?: string
  market?: string
  foundDate?: string
  listDate?: string
  delistDate?: string
  status?: string
  hasPortfolio?: boolean
}

export interface PortfolioItem {
  fundTsCode: string
  reportPeriod: string | null
  annDate: string | null
  stockSymbol: string
  stockName: string | null
  marketValue: number | null
  amount: number | null
  stkMkvRatio: number | null
  stkFloatRatio: number | null
}

export interface ReverseLookupItem {
  fundTsCode: string
  fundName: string | null
  fundType: string | null
  management: string | null
  stockSymbol: string
  reportPeriod: string | null
  stkMkvRatio: number | null
  stkFloatRatio: number | null
  marketValue: number | null
  amount: number | null
}

export interface PortfolioData {
  items: PortfolioItem[]
  total: number
  page: number
  pageSize: number
  totalPages: number
  isPortfolioEmpty: boolean
  hasPortfolio: boolean
  latestReportPeriod: string | null
  latestAnnDate: string | null
}

export interface ReverseLookupData {
  items: ReverseLookupItem[]
  total: number
  page: number
  pageSize: number
  totalPages: number
  stockName: string | null
  reportPeriod: string | null
}

// ---------- URL Matching Helpers ----------

/**
 * 判断请求 URL 是否匹配指定的 API path
 *
 * 使用 URL 对象解析，避免 glob pattern 对 query string 中 ? 和 . 的歧义
 */
function matchApiPath(requestUrl: string, expectedPath: string): boolean {
  try {
    const url = new URL(requestUrl)
    return url.pathname === expectedPath
  } catch {
    return false
  }
}

/**
 * 判断请求 URL 的 pathname 是否以指定前缀开头
 */
function matchApiPathPrefix(requestUrl: string, expectedPrefix: string): boolean {
  try {
    const url = new URL(requestUrl)
    return url.pathname.startsWith(expectedPrefix)
  } catch {
    return false
  }
}

// ---------- Test Data Factories ----------

/** 创建测试用基金列表数据 */
export function createTestFunds(): FundItem[] {
  return [
    {
      tsCode: '510300.SH',
      name: '华泰柏瑞沪深300ETF',
      management: '华泰柏瑞基金',
      fundType: '股票型',
      investType: '被动指数型',
      benchmark: '沪深300指数',
      market: 'E',
      foundDate: '2012-05-04',
      hasPortfolio: true,
    },
    {
      tsCode: '000001.OF',
      name: '华夏成长混合',
      management: '华夏基金',
      fundType: '混合型',
      investType: '偏股混合型',
      benchmark: undefined,
      market: 'O',
      hasPortfolio: true,
    },
    {
      tsCode: '110011.OF',
      name: '易方达中小盘混合',
      management: '易方达基金',
      fundType: '混合型',
      investType: '偏股混合型',
      benchmark: undefined,
      market: 'O',
      foundDate: '2008-06-19',
      hasPortfolio: false,
    },
    {
      tsCode: '159915.SZ',
      name: '易方达创业板ETF',
      management: '易方达基金',
      fundType: '股票型',
      investType: '被动指数型',
      benchmark: '创业板指数',
      market: 'E',
      foundDate: '2011-09-20',
      hasPortfolio: true,
    },
    {
      tsCode: '001838.OF',
      name: '国泰CES半导体芯片ETF联接C',
      management: '国泰基金',
      fundType: '股票型',
      investType: '被动指数型',
      benchmark: '中华交易服务半导体芯片行业指数收益率*95%+银行活期存款利率(税后)*5%',
      market: 'O',
      foundDate: '2019-05-16',
      hasPortfolio: true,
    },
    {
      tsCode: '164906.OF',
      name: '交银中证海外中国互联网指数(QDII-LOF)',
      management: '交银施罗德基金',
      fundType: 'QDII',
      investType: undefined,
      benchmark: '中证海外中国互联网指数(人民币)收益率*95%+银行活期存款利率(税后)*5%',
      market: 'O',
      foundDate: '2015-05-27',
      hasPortfolio: true,
    },
  ]
}

/** 创建测试用持仓明细数据 */
export function createTestPortfolio(tsCode: string): PortfolioData {
  return {
    items: [
      {
        fundTsCode: tsCode,
        reportPeriod: '2025-12-31',
        annDate: '2026-03-31',
        stockSymbol: '600519.SH',
        stockName: '贵州茅台',
        marketValue: 1500000000,
        amount: 8000000,
        stkMkvRatio: 9.85,
        stkFloatRatio: 0.64,
      },
      {
        fundTsCode: tsCode,
        reportPeriod: '2025-12-31',
        annDate: '2026-03-31',
        stockSymbol: '000858.SZ',
        stockName: '五粮液',
        marketValue: 800000000,
        amount: 5000000,
        stkMkvRatio: 5.25,
        stkFloatRatio: 1.37,
      },
      {
        fundTsCode: tsCode,
        reportPeriod: '2025-12-31',
        annDate: '2026-03-31',
        stockSymbol: '601318.SH',
        stockName: '中国平安',
        marketValue: 600000000,
        amount: 10000000,
        stkMkvRatio: 3.94,
        stkFloatRatio: 0.55,
      },
      {
        fundTsCode: tsCode,
        reportPeriod: '2025-12-31',
        annDate: '2026-03-31',
        stockSymbol: '000333.SZ',
        stockName: '美的集团',
        marketValue: 450000000,
        amount: 6000000,
        stkMkvRatio: 2.95,
        stkFloatRatio: null,
      },
      {
        fundTsCode: tsCode,
        reportPeriod: '2025-12-31',
        annDate: '2026-03-31',
        stockSymbol: '600036.SH',
        stockName: '招商银行',
        marketValue: 400000000,
        amount: 9000000,
        stkMkvRatio: 2.63,
        stkFloatRatio: 0.36,
      },
    ],
    total: 5,
    page: 1,
    pageSize: 20,
    totalPages: 1,
    isPortfolioEmpty: false,
    hasPortfolio: true,
    latestReportPeriod: '2025-12-31',
    latestAnnDate: '2026-03-31',
  }
}

/** 创建测试用反查数据（按 stkMkvRatio 降序） */
export function createTestReverseLookup(): ReverseLookupData {
  return {
    items: [
      {
        fundTsCode: '110011.OF',
        fundName: '易方达中小盘混合',
        fundType: '混合型',
        management: '易方达基金',
        stockSymbol: '600519.SH',
        reportPeriod: '2025-12-31',
        stkMkvRatio: 8.12,
        stkFloatRatio: 4.16,
        marketValue: 2000000000,
        amount: 10000000,
      },
      {
        fundTsCode: '000001.OF',
        fundName: '华夏成长混合',
        fundType: '混合型',
        management: '华夏基金',
        stockSymbol: '600519.SH',
        reportPeriod: '2025-12-31',
        stkMkvRatio: 3.50,
        stkFloatRatio: 1.80,
        marketValue: 800000000,
        amount: 4000000,
      },
      {
        fundTsCode: '510300.SH',
        fundName: '华泰柏瑞沪深300ETF',
        fundType: '股票型',
        management: '华泰柏瑞基金',
        stockSymbol: '600519.SH',
        reportPeriod: '2025-12-31',
        stkMkvRatio: 1.25,
        stkFloatRatio: 0.64,
        marketValue: 1500000000,
        amount: 8000000,
      },
    ],
    total: 3,
    page: 1,
    pageSize: 20,
    totalPages: 1,
    stockName: '贵州茅台',
    reportPeriod: '2025-12-31',
  }
}

// ---------- Mock Helpers ----------

/**
 * Mock GET /api/v1/funds — 基金列表
 *
 * 支持搜索和过滤：根据 URL 参数筛选结果
 */
export async function mockFundList(
  page: Page,
  funds: FundItem[],
  total: number
): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/funds'),
    async (route) => {
      if (route.request().method() !== 'GET') {
        await route.continue()
        return
      }

      const urlObj = new URL(route.request().url())
      const search = urlObj.searchParams.get('search') || ''
      const market = urlObj.searchParams.get('market') || ''
      const fundType = urlObj.searchParams.get('fund_type') || ''
      const pageNum = parseInt(urlObj.searchParams.get('page') || '1', 10)
      const pageSize = parseInt(urlObj.searchParams.get('page_size') || '20', 10)

      // 过滤
      let filtered = [...funds]
      if (search) {
        const s = search.toLowerCase()
        filtered = filtered.filter(
          (f) =>
            f.tsCode.toLowerCase().includes(s) ||
            f.name.toLowerCase().includes(s)
        )
      }
      if (market) {
        const markets = market.split(',')
        filtered = filtered.filter((f) => f.market && markets.includes(f.market))
      }
      if (fundType) {
        const types = fundType.split(',')
        filtered = filtered.filter((f) => f.fundType && types.includes(f.fundType))
      }

      const totalFiltered = filtered.length
      const totalPages = Math.ceil(totalFiltered / pageSize)
      const start = (pageNum - 1) * pageSize
      const paged = filtered.slice(start, start + pageSize)

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            items: paged,
            total: totalFiltered,
            page: pageNum,
            pageSize,
            totalPages,
          },
        }),
      })
    }
  )
}

/**
 * Mock GET /api/v1/funds/{tsCode} — 基金详情
 */
export async function mockFundDetail(
  page: Page,
  fund: FundItem
): Promise<void> {
  const expectedPath = `/api/v1/funds/${encodeURIComponent(fund.tsCode)}`
  await page.route(
    (url) => matchApiPath(url, expectedPath),
    async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: fund,
          }),
        })
      } else {
        await route.continue()
      }
    }
  )
}

/**
 * Mock GET /api/v1/funds/{tsCode}/portfolio — 持仓明细
 */
export async function mockFundPortfolio(
  page: Page,
  tsCode: string,
  data: PortfolioData
): Promise<void> {
  const expectedPrefix = `/api/v1/funds/${encodeURIComponent(tsCode)}/portfolio`
  await page.route(
    (url) => matchApiPathPrefix(url, expectedPrefix),
    async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data,
          }),
        })
      } else {
        await route.continue()
      }
    }
  )
}

/**
 * Mock GET /api/v1/funds/reverse-lookup — 反查
 */
export async function mockReverseLookup(
  page: Page,
  data: ReverseLookupData
): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/funds/reverse-lookup'),
    async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data,
          }),
        })
      } else {
        await route.continue()
      }
    }
  )
}

/**
 * Mock 反查返回空结果
 */
export async function mockReverseLookupEmpty(page: Page): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/funds/reverse-lookup'),
    async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: {
              items: [],
              total: 0,
              page: 1,
              pageSize: 20,
              totalPages: 0,
              stockName: null,
              reportPeriod: null,
            },
          }),
        })
      } else {
        await route.continue()
      }
    }
  )
}

/**
 * Mock GET /api/v1/funds — 返回空列表
 */
export async function mockFundListEmpty(page: Page): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/funds'),
    async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: {
              items: [],
              total: 0,
              page: 1,
              pageSize: 20,
              totalPages: 0,
            },
          }),
        })
      } else {
        await route.continue()
      }
    }
  )
}

/**
 * Mock GET /api/v1/funds — 返回服务端错误
 */
export async function mockFundListError(page: Page): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/funds'),
    async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Internal Server Error' }),
        })
      } else {
        await route.continue()
      }
    }
  )
}

/**
 * Mock GET /api/v1/funds/{tsCode}/portfolio — 空持仓场景 A（hasPortfolio=false）
 */
export async function mockFundPortfolioNoData(
  page: Page,
  tsCode: string
): Promise<void> {
  const expectedPrefix = `/api/v1/funds/${encodeURIComponent(tsCode)}/portfolio`
  await page.route(
    (url) => matchApiPathPrefix(url, expectedPrefix),
    async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: {
              items: [],
              total: 0,
              page: 1,
              pageSize: 20,
              totalPages: 0,
              isPortfolioEmpty: true,
              hasPortfolio: false,
              latestReportPeriod: null,
              latestAnnDate: null,
            },
          }),
        })
      } else {
        await route.continue()
      }
    }
  )
}

/**
 * Mock GET /api/v1/funds/{tsCode}/portfolio — 空持仓场景 B（hasPortfolio=true, isPortfolioEmpty=true）
 */
export async function mockFundPortfolioNotDisclosed(
  page: Page,
  tsCode: string
): Promise<void> {
  const expectedPrefix = `/api/v1/funds/${encodeURIComponent(tsCode)}/portfolio`
  await page.route(
    (url) => matchApiPathPrefix(url, expectedPrefix),
    async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: {
              items: [],
              total: 0,
              page: 1,
              pageSize: 20,
              totalPages: 0,
              isPortfolioEmpty: true,
              hasPortfolio: true,
              latestReportPeriod: null,
              latestAnnDate: null,
            },
          }),
        })
      } else {
        await route.continue()
      }
    }
  )
}

/**
 * Mock POST /api/v1/admin/init/funds — 管理员基金基本信息同步（成功）
 */
export async function mockFundSyncSuccess(page: Page): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/admin/init/funds'),
    async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: { task_id: 'task-fund-basic-001' },
          }),
        })
      } else {
        await route.continue()
      }
    }
  )
}

/**
 * Mock POST /api/v1/admin/init/funds — 管理员基金基本信息同步（失败）
 */
export async function mockFundSyncError(page: Page): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/admin/init/funds'),
    async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Tushare 接口调用失败' }),
        })
      } else {
        await route.continue()
      }
    }
  )
}

/**
 * Mock POST /api/v1/admin/init/fund-portfolio — 管理员持仓同步（成功）
 */
export async function mockFundPortfolioSyncSuccess(page: Page): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/admin/init/fund-portfolio'),
    async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: { task_id: 'task-fund-portfolio-001' },
          }),
        })
      } else {
        await route.continue()
      }
    }
  )
}

/**
 * Mock POST /api/v1/admin/init/fund-portfolio — 管理员持仓同步（失败）
 */
export async function mockFundPortfolioSyncError(page: Page): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/admin/init/fund-portfolio'),
    async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: '报告期参数缺失' }),
        })
      } else {
        await route.continue()
      }
    }
  )
}

/**
 * Mock GET /api/v1/admin/tasks/{taskId} — 任务状态轮询（已完成）
 */
export async function mockTaskStatusCompleted(
  page: Page,
  taskId: string,
  result?: { added?: number; updated?: number; failed?: number }
): Promise<void> {
  const expectedPath = `/api/v1/admin/tasks/${taskId}`
  await page.route(
    (url) => matchApiPath(url, expectedPath),
    async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: {
              taskId,
              taskType: 'sync_fund_basic',
              status: 'completed',
              progress: 100,
              total: 100,
              percent: 100,
              params: {},
              errorMessage: null,
              retryCount: 0,
              maxRetries: 3,
              createdAt: new Date().toISOString(),
              startedAt: new Date().toISOString(),
              completedAt: new Date().toISOString(),
            },
          }),
        })
      } else {
        await route.continue()
      }
    }
  )
}

/**
 * Mock GET /api/v1/admin/tasks/{taskId} — 任务状态轮询（失败）
 */
export async function mockTaskStatusFailed(
  page: Page,
  taskId: string,
  errorMessage: string
): Promise<void> {
  const expectedPath = `/api/v1/admin/tasks/${taskId}`
  await page.route(
    (url) => matchApiPath(url, expectedPath),
    async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: {
              taskId,
              taskType: 'sync_fund_basic',
              status: 'failed',
              progress: 50,
              total: 100,
              percent: 50,
              params: {},
              errorMessage,
              retryCount: 1,
              maxRetries: 3,
              createdAt: new Date().toISOString(),
              startedAt: new Date().toISOString(),
              completedAt: null,
            },
          }),
        })
      } else {
        await route.continue()
      }
    }
  )
}

/**
 * Mock GET /api/v1/admin/tasks/{taskId} — 任务状态轮询（运行中）
 */
export async function mockTaskStatusRunning(
  page: Page,
  taskId: string
): Promise<void> {
  const expectedPath = `/api/v1/admin/tasks/${taskId}`
  await page.route(
    (url) => matchApiPath(url, expectedPath),
    async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: {
              taskId,
              taskType: 'sync_fund_basic',
              status: 'running',
              progress: 50,
              total: 100,
              percent: 50,
              params: {},
              errorMessage: null,
              retryCount: 0,
              maxRetries: 3,
              createdAt: new Date().toISOString(),
              startedAt: new Date().toISOString(),
              completedAt: null,
            },
          }),
        })
      } else {
        await route.continue()
      }
    }
  )
}
