import { Page } from '@playwright/test'

/**
 * Mock helpers for shareholder group admin E2E tests
 *
 * 参照 mock-fund-api.ts 模式：
 * - URL 匹配用 URL.pathname 精确匹配（避免 glob pattern 歧义）
 * - test data factory 用 camelCase（对齐 plan-01 GroupListItem 契约 + 架构 §7.6 命名规则）
 * - 命名 mockXxxSuccess / mockXxxError / mockXxxList
 *
 * 后端 Admin API（plan-01）：/api/v1/admin/shareholder-groups
 * - GET    /                  分组列表
 * - POST   /                  新增
 * - PATCH  /{id}              编辑
 * - DELETE /{id}              删除
 * - GET    /preview           匹配预览
 *
 * 注意：plan-01 实际 response 是否包 { success, data } 外层由后端实现决定，
 * 本 helpers 按 admin-fund-sync.mockFundSyncSuccess 的 { success: true, data } 模式编写，
 * green 阶段如发现外层不同再调整，不影响 red 阶段结论。
 *
 * 重要：当多个 helper 在同一 URL 注册（如 list GET + create POST）时，Playwright 按
 * LIFO 顺序调用 handler（后注册的先执行）。非本方法处理时必须用 route.fallback()
 * 转交下一个 handler，而非 route.continue()（后者直接把请求发到网络，会跳过其它 handler，
 * 导致先注册的 list GET mock 被 create POST handler 的 continue() 短路 → ERR_CONNECTION_REFUSED）。
 *
 * 注：被测组件用 ref 防止 React StrictMode 在 dev 下对 useEffect 的双重调用导致初始
 * 列表重复请求，因此本 helper 的 callIndex 序列能正确对应"初始加载 / 操作后刷新"两次调用。
 */

// ---------- Types ----------

export interface ShareholderGroupItem {
  id: number
  name: string
  description: string | null
  isSystem: boolean
  ruleCount: number
  matchedStockCount: number
  keywords: string[]
}

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

function matchApiPathPrefix(requestUrl: URL | string, expectedPrefix: string): boolean {
  return toPathname(requestUrl).startsWith(expectedPrefix)
}

// ---------- Test Data Factory ----------

/**
 * 创建测试用 5 个预定义股东分组（与 plan-01 Alembic 种子数据一致）
 *
 * 来源：plan-01 green 证据 test_list_returns_predefined_groups
 * 组名：国家队 / 外资投行 / 社交基金 / 保险公司 / 私募基金
 */
export function createTestShareholderGroups(): ShareholderGroupItem[] {
  return [
    {
      id: 1,
      name: '国家队',
      description: '汇金、证金等国家队资金',
      isSystem: true,
      ruleCount: 3,
      matchedStockCount: 42,
      keywords: ['中央汇金', '中国证金', '国家集成电路产业投资基金'],
    },
    {
      id: 2,
      name: '外资投行',
      description: '合格境外机构投资者（QFII）',
      isSystem: true,
      ruleCount: 4,
      matchedStockCount: 28,
      keywords: ['瑞士银行', '摩根大通', '摩根士丹利', '高盛'],
    },
    {
      id: 3,
      name: '社保基金',
      description: '全国社保基金理事会及组合',
      isSystem: true,
      ruleCount: 2,
      matchedStockCount: 35,
      keywords: ['全国社保基金'],
    },
    {
      id: 4,
      name: '保险公司',
      description: '保险公司资金',
      isSystem: true,
      ruleCount: 3,
      matchedStockCount: 51,
      keywords: ['中国人寿', '中国平安人寿', '泰康人寿'],
    },
    {
      id: 5,
      name: '私募基金',
      description: '知名私募基金',
      isSystem: true,
      ruleCount: 2,
      matchedStockCount: 19,
      keywords: ['高瓴', '景林'],
    },
  ]
}

/**
 * 新建 QFII 分组（新增后的列表项，供 TC-1.4 / TC-1.8 使用）
 */
export function createQFiiGroup(): ShareholderGroupItem {
  return {
    id: 100,
    name: 'QFII',
    description: '合格境外机构投资者',
    isSystem: false,
    ruleCount: 2,
    matchedStockCount: 28,
    keywords: ['瑞士银行', '摩根大通'],
  }
}

// ---------- Mock Helpers ----------

/**
 * Mock GET /api/v1/admin/shareholder-groups — 分组列表
 *
 * 支持多次调用返回不同结果：通过 listResponses 数组按调用序号返回，
 * 用于"操作前/操作后列表变化"场景（如新增后、删除后刷新列表）
 *
 * @param listResponses 按调用顺序的列表数据数组；超出索引时返回最后一个
 */
export async function mockShareholderGroupsList(
  page: Page,
  listResponses: ShareholderGroupItem[][]
): Promise<void> {
  let callIndex = 0
  await page.route(
    (url) => matchApiPath(url, '/api/v1/admin/shareholder-groups'),
    async (route) => {
      if (route.request().method() !== 'GET') {
        await route.fallback()
        return
      }
      const data = listResponses[Math.min(callIndex, listResponses.length - 1)] ?? []
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
 * Mock GET /api/v1/admin/shareholder-groups — 列表接口返回 500
 */
export async function mockShareholderGroupsListError(page: Page): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/admin/shareholder-groups'),
    async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Internal Server Error' }),
        })
      } else {
        await route.fallback()
      }
    }
  )
}

/**
 * Mock POST /api/v1/admin/shareholder-groups — 新增分组成功
 */
export async function mockShareholderGroupCreate(
  page: Page,
  created?: ShareholderGroupItem
): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/admin/shareholder-groups'),
    async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: created ?? createQFiiGroup(),
          }),
        })
      } else {
        await route.fallback()
      }
    }
  )
}

/**
 * Mock POST /api/v1/admin/shareholder-groups — 组名重复返回 400
 */
export async function mockShareholderGroupCreateConflict(page: Page): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/admin/shareholder-groups'),
    async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({ detail: '组名已存在' }),
        })
      } else {
        await route.fallback()
      }
    }
  )
}

/**
 * Mock PATCH /api/v1/admin/shareholder-groups/{id} — 编辑分组成功
 */
export async function mockShareholderGroupUpdate(
  page: Page,
  updated?: ShareholderGroupItem
): Promise<void> {
  const prefix = '/api/v1/admin/shareholder-groups/'
  await page.route(
    (url) => {
      const path = toPathname(url)
      return path.startsWith(prefix) && !path.startsWith(`${prefix}preview`)
    },
    async (route) => {
      if (route.request().method() === 'PATCH') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: updated ?? createTestShareholderGroups()[0],
          }),
        })
      } else {
        await route.fallback()
      }
    }
  )
}

/**
 * Mock DELETE /api/v1/admin/shareholder-groups/{id} — 删除分组成功
 */
export async function mockShareholderGroupDelete(page: Page): Promise<void> {
  const prefix = '/api/v1/admin/shareholder-groups/'
  await page.route(
    (url) => {
      const path = toPathname(url)
      return path.startsWith(prefix) && !path.startsWith(`${prefix}preview`)
    },
    async (route) => {
      if (route.request().method() === 'DELETE') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true, data: { id: 100 } }),
        })
      } else {
        await route.fallback()
      }
    }
  )
}

/**
 * Mock GET /api/v1/admin/shareholder-groups/preview — 匹配预览
 *
 * 注意：本 helper 用 matchApiPathPrefix 捕获 /preview 前缀，会同时匹配
 * /preview-breakdown 路径。spec 中如同时使用 mockShareholderGroupPreview
 * 和 mockShareholderGroupPreviewBreakdown，必须先注册本 helper、后注册
 * PreviewBreakdown —— LIFO 让精确匹配的 PreviewBreakdown 先命中。
 */
export async function mockShareholderGroupPreview(
  page: Page,
  matchedStockCount: number = 3
): Promise<void> {
  await page.route(
    (url) => matchApiPathPrefix(url, '/api/v1/admin/shareholder-groups/preview'),
    async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            data: { matchedStockCount },
          }),
        })
      } else {
        await route.fallback()
      }
    }
  )
}

// ---------- plan-02 helpers ----------

/**
 * 测试用"社保"分组（plan-02 场景 1~4 用，多关键词场景）
 *
 * 跟随 createQFiiGroup() 无参工厂风格；返回固定实例
 */
export function createSocialGroup(): ShareholderGroupItem {
  return {
    id: 1,
    name: '社保',
    description: '全国社保基金测试组',
    isSystem: false,
    ruleCount: 2,
    matchedStockCount: 5,
    keywords: ['全国社保', '社保基金'],
  }
}

/**
 * 测试用"社保"分组变体（plan-02 场景 5 用，含空关键词 + 0 匹配关键词）
 *
 * keywords: ['全国社保', '', '无匹配关键词']
 *  - index 0：正常匹配（2 只）
 *  - index 1：空关键词 → AC-08 不显示股数和按钮
 *  - index 2：0 匹配 → AC-09 按钮置灰
 */
export function createSocialGroupWithEmptyAndZero(): ShareholderGroupItem {
  return {
    id: 1,
    name: '社保',
    description: '场景 5 边界测试组',
    isSystem: false,
    ruleCount: 3,
    matchedStockCount: 2,
    keywords: ['全国社保', '', '无匹配关键词'],
  }
}

/**
 * Mock GET /api/v1/admin/shareholder-groups/preview-breakdown — 逐关键词股数
 *
 * 注意：spec 中必须先注册 mockShareholderGroupPreview（前缀匹配 /preview），
 * 再注册本 helper（精确匹配 /preview-breakdown）—— LIFO 让精确匹配先命中。
 */
export async function mockShareholderGroupPreviewBreakdown(
  page: Page,
  items: Array<{ keyword: string; matchedStockCount: number | null }>
): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/admin/shareholder-groups/preview-breakdown'),
    async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true, data: { items } }),
        })
      } else {
        await route.fallback()
      }
    }
  )
}

/**
 * Mock GET /api/v1/admin/shareholder-groups/preview-breakdown — 失败（默认 500）
 */
export async function mockShareholderGroupPreviewBreakdownError(
  page: Page,
  status: number = 500
): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/admin/shareholder-groups/preview-breakdown'),
    async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Internal Server Error' }),
        })
      } else {
        await route.fallback()
      }
    }
  )
}

/**
 * Mock GET /api/v1/admin/shareholder-groups/preview-breakdown — 按调用次数返回不同结果
 *
 * 场景 3（AC-06 实时刷新）用：第一次（初始加载）与第二次（修改关键词后）返回不同股数。
 * 参照 mockShareholderGroupsList 的 callIndex 模式（line 147-168）
 */
export async function mockShareholderGroupPreviewBreakdownSequence(
  page: Page,
  itemsList: Array<Array<{ keyword: string; matchedStockCount: number | null }>>
): Promise<void> {
  let callIndex = 0
  await page.route(
    (url) => matchApiPath(url, '/api/v1/admin/shareholder-groups/preview-breakdown'),
    async (route) => {
      if (route.request().method() !== 'GET') {
        await route.fallback()
        return
      }
      const items = itemsList[Math.min(callIndex, itemsList.length - 1)] ?? []
      callIndex += 1
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: { items } }),
      })
    }
  )
}

/**
 * Mock GET /api/v1/admin/shareholder-groups/keyword-matches — 关键词明细
 */
export async function mockShareholderGroupKeywordMatches(
  page: Page,
  data: {
    items: Array<{ symbol: string; stockName: string | null; holderName: string }>
    total: number
    page: number
    pageSize: number
  }
): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/admin/shareholder-groups/keyword-matches'),
    async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true, data }),
        })
      } else {
        await route.fallback()
      }
    }
  )
}

/**
 * Mock GET /api/v1/admin/shareholder-groups/keyword-matches — 失败（默认 500）
 */
export async function mockShareholderGroupKeywordMatchesError(
  page: Page,
  status: number = 500
): Promise<void> {
  await page.route(
    (url) => matchApiPath(url, '/api/v1/admin/shareholder-groups/keyword-matches'),
    async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Internal Server Error' }),
        })
      } else {
        await route.fallback()
      }
    }
  )
}

/**
 * Mock GET /api/v1/admin/shareholder-groups/{id} — 单条详情（编辑页按 id 加载）
 *
 * 匹配 prefix 之后为纯数字 id 的路径（排除 preview / preview-breakdown /
 * keyword-matches 等静态段），仅处理 GET。
 */
export async function mockShareholderGroupDetail(
  page: Page,
  group: ShareholderGroupItem
): Promise<void> {
  const prefix = '/api/v1/admin/shareholder-groups/'
  await page.route(
    (url) => {
      const path = toPathname(url)
      if (!path.startsWith(prefix)) return false
      const rest = path.slice(prefix.length)
      // 只匹配 /{数字id}，排除 preview / preview-breakdown / keyword-matches 等静态段
      return /^\d+$/.test(rest)
    },
    async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true, data: group }),
        })
      } else {
        await route.fallback()
      }
    }
  )
}
