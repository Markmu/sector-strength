import { Page } from '@playwright/test'

/**
 * Mock helpers for broker recommend analysis page E2E tests (plan-03, 09 期)
 *
 * 后端用户侧 API（plan-02，baseURL 已含 /api/v1）：
 * - GET /api/v1/broker-recommend-analysis/months         — 月份列表 + 是否有数据
 * - GET /api/v1/broker-recommend-analysis/stock-ranking  — 股票维度排行
 * - GET /api/v1/broker-recommend-analysis/broker-list    — 券商维度分组
 * - GET /api/v1/broker-recommend-analysis/broker-detail  — 券商明细懒加载
 *
 * 管理员同步 API（plan-01）：
 * - POST /api/v1/admin/init/broker-recommend              — 触发同步任务（返回 task_id）
 * - GET  /api/v1/admin/tasks/{taskId}                     — 任务状态轮询
 *
 * 参照 mock-fund-crowd-api.ts / mock-fund-api.ts 模式：
 * - URL 匹配用 URL.pathname 精确匹配（避免 glob 歧义）
 * - test data factory 用 camelCase（架构 §7.2 + plan-03 §1 契约）
 * - 多个 helper 在同一路径注册时，非自己负责的方法用 route.fallback() 放行
 * - handler 内按 URLSearchParams 解析 search/month/broker 决定返回哪份 fixture
 *
 * 外层契约：{ success: true, data: {...} }（前端 hook 读 res.data.data）
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

// ---------- Types (与 lib/api.ts Broker* 对齐，架构 §7.2，camelCase) ----------

export interface BrokerStockRankingItem {
  symbol: string
  name: string | null
  industries: string[]
  brokerCount: number
  brokers: { broker: string; reasons: string[] }[]
}

export interface BrokerGroupItem {
  broker: string
  stockCount: number
}

export interface BrokerDetailItem {
  symbol: string
  name: string | null
  reasons: string[]
}

export interface BrokerRankingData {
  hasData: boolean
  month: string | null
  total: number
  page: number
  pageSize: number
  items: unknown[]
}

export interface BrokerMonthsData {
  hasData: boolean
  months: string[]
}

export interface BrokerDetailData {
  items: BrokerDetailItem[]
}

// ---------- Test Data Factory ----------

export function createTestBrokerMonths(): BrokerMonthsData {
  // 后端 month 字段为 Date.isoformat()（YYYY-MM-01），mock 用同一格式
  return {
    hasData: true,
    months: ['2026-06-01', '2026-05-01', '2026-04-01'],
  }
}

export function createTestBrokerMonthsEmpty(): BrokerMonthsData {
  return {
    hasData: false,
    months: [],
  }
}

/** 600519(5家,前3省略+2家) / 300750(3家) / 688981(1家,2 reasons 不丢弃) */
export function createTestStockRanking(): BrokerRankingData {
  return {
    hasData: true,
    month: '2026-06',
    total: 3,
    page: 1,
    pageSize: 20,
    items: [
      {
        symbol: '600519',
        name: '贵州茅台',
        industries: ['食品饮料'],
        brokerCount: 5,
        brokers: [
          { broker: '中信证券', reasons: ['业绩超预期', '高端白酒龙头'] },
          { broker: '中金公司', reasons: ['估值修复'] },
          { broker: '国泰君安', reasons: ['消费复苏受益'] },
          { broker: '华泰证券', reasons: ['品牌壁垒'] },
          { broker: '招商证券', reasons: ['渠道优势'] },
        ],
      },
      {
        symbol: '300750',
        name: '宁德时代',
        industries: ['电力设备'],
        brokerCount: 3,
        brokers: [
          { broker: '中信证券', reasons: ['新能源景气'] },
          { broker: '中金公司', reasons: ['海外扩张'] },
          { broker: '华泰证券', reasons: ['储能放量'] },
        ],
      },
      {
        symbol: '688981',
        name: '中芯国际',
        industries: ['电子'],
        brokerCount: 1,
        brokers: [{ broker: '中信证券', reasons: ['国产替代加速', '产能扩张'] }],
      },
    ] as BrokerStockRankingItem[],
  }
}

export function createTestBrokerList(): BrokerRankingData {
  return {
    hasData: true,
    month: '2026-06',
    total: 2,
    page: 1,
    pageSize: 20,
    items: [
      { broker: '中信证券', stockCount: 3 },
      { broker: '中金公司', stockCount: 2 },
    ] as BrokerGroupItem[],
  }
}

export function createTestBrokerDetail(): BrokerDetailData {
  return {
    items: [
      { symbol: '600519', name: '贵州茅台', reasons: ['业绩超预期', '高端白酒龙头'] },
      { symbol: '300750', name: '宁德时代', reasons: ['新能源景气'] },
      { symbol: '688981', name: '中芯国际', reasons: ['国产替代加速', '产能扩张'] },
    ],
  }
}

export function createTestStockRankingMonthEmpty(): BrokerRankingData {
  return {
    hasData: true,
    month: '2026-04',
    total: 0,
    page: 1,
    pageSize: 20,
    items: [],
  }
}

// ---------- Mock Helpers ----------

export async function mockBrokerMonths(
  page: Page,
  data: BrokerMonthsData = createTestBrokerMonths()
): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/broker-recommend-analysis/months'),
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

export async function mockBrokerMonthsEmpty(page: Page): Promise<void> {
  await mockBrokerMonths(page, createTestBrokerMonthsEmpty())
}

export async function mockStockRanking(
  page: Page,
  data: BrokerRankingData = createTestStockRanking()
): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/broker-recommend-analysis/stock-ranking'),
    async (route) => {
      if (route.request().method() !== 'GET') {
        await route.fallback()
        return
      }
      const query = parseQuery(route.request().url())
      const search = query.get('search') || ''
      const month = query.get('month') || ''

      if (month === '2026-04-01') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: createTestStockRankingMonthEmpty(),
          }),
        })
        return
      }

      let items = [...data.items] as BrokerStockRankingItem[]
      // 板块过滤（sector_name 有值时按 industries 包含匹配）
      const sectorName = query.get('sector_name') || ''
      if (sectorName) {
        items = items.filter((it) => it.industries.includes(sectorName))
      }
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
        body: JSON.stringify({ success: true, data: { ...data, items, total } }),
      })
    }
  )
}

export async function mockBrokerList(
  page: Page,
  data: BrokerRankingData = createTestBrokerList()
): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/broker-recommend-analysis/broker-list'),
    async (route) => {
      if (route.request().method() !== 'GET') {
        await route.fallback()
        return
      }
      const query = parseQuery(route.request().url())
      const search = query.get('search') || ''

      let items = [...data.items] as BrokerGroupItem[]
      if (search) {
        const s = search.toLowerCase()
        items = items.filter((it) => it.broker.toLowerCase().includes(s))
      }
      const total = items.length
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: { ...data, items, total } }),
      })
    }
  )
}

export async function mockBrokerDetail(
  page: Page,
  data: BrokerDetailData = createTestBrokerDetail(),
  opts?: { fail?: boolean }
): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/broker-recommend-analysis/broker-detail'),
    async (route) => {
      if (route.request().method() !== 'GET') {
        await route.fallback()
        return
      }
      if (opts?.fail) {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'broker-detail 接口调用失败' }),
        })
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

// ---------- Admin Sync Mocks ----------

/**
 * Mock GET /api/v1/admin/tasks?task_types=sync_broker_recommend — 同步记录列表
 *
 * BrokerRecommendSyncPanel 用固定 SWR key 查询该端点。
 */
export async function mockBrokerSyncRecords(
  page: Page,
  records: Array<Record<string, unknown>> = []
): Promise<void> {
  await page.route(
    (url) => {
      if (!matchApiPath(url, '/api/v1/admin/tasks')) return false
      return parseQuery(url).get('task_types') === 'sync_broker_recommend'
    },
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
          data: { tasks: records, total: records.length, page: 1 },
        }),
      })
    }
  )
}

export async function mockBrokerRecommendSyncSuccess(
  page: Page,
  taskId = 'task-broker-recommend-001'
): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/admin/init/broker-recommend'),
    async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true, data: { task_id: taskId } }),
        })
      } else {
        await route.fallback()
      }
    }
  )
}

export async function mockBrokerRecommendSyncError(page: Page): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/admin/init/broker-recommend'),
    async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Tushare 接口调用失败' }),
        })
      } else {
        await route.fallback()
      }
    }
  )
}

export async function mockBrokerTaskStatusCompleted(
  page: Page,
  taskId: string
): Promise<void> {
  const expectedPath = `/api/v1/admin/tasks/${taskId}`
  await page.route((url) => matchApiPath(url, expectedPath), async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            taskId,
            taskType: 'sync_broker_recommend',
            status: 'completed',
            progress: 100,
            total: 100,
            percent: 100,
            params: { month: '202606' },
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
      await route.fallback()
    }
  })
}

export async function mockBrokerTaskStatusFailed(
  page: Page,
  taskId: string,
  errorMessage: string
): Promise<void> {
  const expectedPath = `/api/v1/admin/tasks/${taskId}`
  await page.route((url) => matchApiPath(url, expectedPath), async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            taskId,
            taskType: 'sync_broker_recommend',
            status: 'failed',
            progress: 50,
            total: 100,
            percent: 50,
            params: { month: '202606' },
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
      await route.fallback()
    }
  })
}

export interface BrokerSectorRankingItem {
  sectorName: string
  stockCount: number
  percentage: number
}

export interface BrokerSectorRankingsData {
  hasData: boolean
  month: string | null
  industry: BrokerSectorRankingItem[]
  concept: BrokerSectorRankingItem[]
  region: BrokerSectorRankingItem[]
}

/** 三类型板块排行榜测试数据（行业/概念/地域各 Top3，验证降序+省略） */
export function createTestSectorRankings(): BrokerSectorRankingsData {
  return {
    hasData: true,
    month: '2026-06',
    industry: [
      { sectorName: '食品饮料', stockCount: 12, percentage: 60.0 },
      { sectorName: '电力设备', stockCount: 8, percentage: 40.0 },
      { sectorName: '银行', stockCount: 6, percentage: 30.0 },
    ],
    concept: [
      { sectorName: '白酒', stockCount: 10, percentage: 50.0 },
      { sectorName: '新能源', stockCount: 7, percentage: 35.0 },
    ],
    region: [
      { sectorName: '贵州', stockCount: 12, percentage: 60.0 },
      { sectorName: '广东', stockCount: 5, percentage: 25.0 },
    ],
  }
}

/** Mock GET /api/v1/broker-recommend-analysis/sector-rankings */
export async function mockBrokerSectorRankings(
  page: Page,
  data: BrokerSectorRankingsData = createTestSectorRankings()
): Promise<void> {
  await page.route(
    (url) =>
      matchApiPath(url, '/api/v1/broker-recommend-analysis/sector-rankings'),
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

export async function installBrokerFullMocks(page: Page): Promise<void> {
  await mockBrokerMonths(page, createTestBrokerMonths())
  await mockStockRanking(page, createTestStockRanking())
  await mockBrokerList(page, createTestBrokerList())
  await mockBrokerDetail(page, createTestBrokerDetail())
  await mockBrokerSectorRankings(page, createTestSectorRankings())
}
