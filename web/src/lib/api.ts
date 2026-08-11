import { z } from 'zod'
import { handleUnauthorizedRedirect } from './authRedirect'
import type { SectorType, SectorStocksResponse } from '@/types/sectorTypes'

// API 基础配置
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// 普通客户端使用的基础URL（需要加上 /api 前缀）
const API_BASE_WITH_PREFIX = `${API_BASE_URL}/api/v1`

// API 响应类型定义
export const ApiResponseSchema = z.object({
  error: z.optional(z.object({
    type: z.string(),
    message: z.string(),
    status_code: z.number(),
  })),
})

export type ApiResponse<T = any> = z.infer<typeof ApiResponseSchema> & {
  data?: T
}

// 请求选项
interface RequestInit {
  method?: string
  headers?: Record<string, string>
  body?: any
  params?: Record<string, any>
}

// API 客户端类
export class ApiClient {
  protected baseURL: string
  protected defaultHeaders: Record<string, string>

  constructor(baseURL: string = API_BASE_WITH_PREFIX) {
    this.baseURL = baseURL
    this.defaultHeaders = {
      'Content-Type': 'application/json',
    }
  }

  // 获取认证头
  protected getAuthHeaders(): Record<string, string> {
    // 从 localStorage 获取认证信息
    if (typeof window === 'undefined') return {}

    const accessToken = localStorage.getItem('accessToken')
    const tokenType = localStorage.getItem('tokenType') || 'Bearer'

    if (!accessToken) return {}

    return {
      'Authorization': `${tokenType} ${accessToken}`,
    }
  }

  protected async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const { method = 'GET', headers = {}, body, params } = options

    const url = new URL(`${this.baseURL}${endpoint}`)
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value === undefined || value === null) return
        // 数组：使用重复同名 key（?k=a&k=b），FastAPI 的 list[str] Query 会自动收集
        if (Array.isArray(value)) {
          if (value.length === 0) return
          value.forEach((item) => {
            if (item !== undefined && item !== null) {
              url.searchParams.append(key, String(item))
            }
          })
        } else {
          url.searchParams.append(key, String(value))
        }
      })
    }

    const authHeaders = this.getAuthHeaders()

    const config: RequestInit = {
      method,
      headers: {
        ...this.defaultHeaders,
        ...authHeaders,  // 添加认证头
        ...headers,
      },
    }

    if (body && method !== 'GET') {
      config.body = JSON.stringify(body)
    }

    try {
      const response = await fetch(url.toString(), config)
      const data = await response.json()

      if (!response.ok) {
        // 401 认证失败特殊处理
        if (response.status === 401) {
          console.error('Authentication failed:', data.error?.message || data.detail || '认证失败')
          handleUnauthorizedRedirect()
        }
        throw new Error(data.error?.message || data.detail || `HTTP error! status: ${response.status}`)
      }

      return { data }
    } catch (error) {
      console.error('API request failed:', error)
      throw error
    }
  }

  // GET 请求
  async get<T>(endpoint: string, params?: Record<string, any>): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'GET', params })
  }

  // POST 请求
  async post<T>(endpoint: string, body?: any, params?: Record<string, any>): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'POST', body, params })
  }

  // PUT 请求
  async put<T>(endpoint: string, body?: any): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'PUT', body })
  }

  // DELETE 请求
  async delete<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'DELETE' })
  }
}

// 创建默认 API 客户端实例
export const apiClient = new ApiClient()

// 健康检查 API
export const healthApi = {
  getHealth: () => apiClient.get<{ status: string; environment: string; version: string }>('/health'),
  getDatabaseHealth: () => apiClient.get<{ status: string; database: string }>('/health/db'),
}

// 股票 API
export interface StockSearchResponse {
  items: Array<{ symbol: string; name: string }>
  total: number
  page: number
  page_size: number
  total_pages: number
}

export const stocksApi = {
  getStocks: (params?: { skip?: number; limit?: number }) =>
    apiClient.get<any[]>('/stocks', params),
  getStock: (stockId: string) => apiClient.get<any>(`/stocks/${stockId}`),
  searchStocks: (keyword: string, params?: { page?: number; pageSize?: number }) =>
    apiClient.get<{
      success: boolean
      data: StockSearchResponse
    }>('/stocks/search', {
      keyword,
      page: params?.page || 1,
      page_size: params?.pageSize || 10,
    }),
}

// 板块 API
export const sectorsApi = {
  getSectors: (params?: {
    page?: number
    page_size?: number
    sector_type?: string
    level?: string
    min_strength_score?: number
    max_strength_score?: number
  }) =>
    apiClient.get<{
      success: boolean
      data: {
        items: Array<any>
        total: number
        page: number
        page_size: number
      }
    }>('/sectors', params),
  getSector: (sectorId: number) => apiClient.get<any>(`/sectors/${sectorId}`),
  getSectorStocks: (
    sectorId: number,
    params?: { page?: number; page_size?: number; sort_by?: string; sort_order?: string }
  ) =>
    apiClient.get<SectorStocksResponse>(`/sectors/${sectorId}/stocks`, params),
  searchSectors: (keyword: string, params?: { sector_type?: string; limit?: number }) =>
    apiClient.get<{
      success: boolean
      data: Array<{
        id: number
        code: string
        name: string
        type: string
        label: string
        value: number
      }>
    }>('/sectors/search', { keyword, ...params }),
  // 按板块名精确查询 sector_id（资金流页跳转用，避免 JOIN sectors 导致重复）
  lookupSectorByName: (name: string, sectorType: string) =>
    apiClient.get<{
      success: boolean
      data: { sector_id: number; sector_name: string } | null
    }>('/sectors/lookup-by-name', { name, sector_type: sectorType }),
  // 获取板块强度历史数据 (用于图表)
  getSectorStrengthHistory: (sectorId: number, params?: { start_date?: string; end_date?: string }) =>
    apiClient.get<{
      sector_id: string
      sector_name: string
      data: Array<{
        date: string
        score: number | null
        current_price: number | null
      }>
    }>(`/sectors/${sectorId}/strength-history`, params),
  // 获取板块均线历史数据 (用于图表)
  getSectorMAHistory: (sectorId: number, params?: { start_date?: string; end_date?: string }) =>
    apiClient.get<{
      sector_id: string
      sector_name: string
      data: Array<{
        date: string
        current_price: number | null
        ma5: number | null
        ma10: number | null
        ma20: number | null
        ma30: number | null
        ma60: number | null
        ma90: number | null
        ma120: number | null
        ma240: number | null
      }>
    }>(`/sectors/${sectorId}/ma-history`, params),
}

// 强度数据 API
export const strengthApi = {
  getStrength: (params?: {
    sector_id?: string
    stock_id?: string
    period?: string
    date_from?: string
    date_to?: string
    skip?: number
    limit?: number
  }) => apiClient.get<any[]>('/strength', params),
  getLatestStrength: (params?: { sector_id?: string; period?: string }) =>
    apiClient.get<any[]>('/strength/latest', params),
}

// 用户资料 API
export const userApi = {
  // 获取用户资料
  getProfile: () => apiClient.get<any>('/user/profile'),

  // 更新用户资料
  updateProfile: (data: {
    display_name?: string
    timezone?: string
    language?: string
  }) => apiClient.put<any>('/user/profile', data),

  // 获取用户偏好设置
  getPreferences: () => apiClient.get<any>('/user/preferences'),

  // 更新用户偏好设置
  updatePreferences: (data: {
    email_notifications?: boolean
    push_notifications?: boolean
    marketing_emails?: boolean
  }) => apiClient.put<any>('/user/preferences', data),

  // 更改密码
  changePassword: (data: {
    current_password: string
    new_password: string
  }) => apiClient.post<any>('/user/change-password', data),

  // 获取活跃会话
  getSessions: () => apiClient.get<any>('/user/sessions'),

  // 终止特定会话
  terminateSession: (sessionId: string) =>
    apiClient.delete<any>(`/user/sessions/${sessionId}`),

  // 终止所有其他会话
  terminateAllOtherSessions: () =>
    apiClient.delete<any>('/user/sessions/all'),

  // 停用账户
  deactivateAccount: () => apiClient.post<any>('/user/deactivate'),

  // 删除账户
  deleteAccount: () => apiClient.delete<any>('/user/account'),
}

// 热力图 API
export const heatmapApi = {
  getHeatmap: (params?: { sector_type?: string; level?: string }) =>
    apiClient.get<any>('/heatmap', params),
}

// 基金 API
export interface FundListParams {
  search?: string
  market?: string[]
  fundType?: string[]
  page?: number
  pageSize?: number
}

export interface Fund {
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

export interface FundListResponse {
  items: Fund[]
  total: number
  page: number
  pageSize: number
  totalPages: number
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
  stkMkvRatioChange: number | null
  amountChange: number | null
  marketValueChange: number | null
  isNew: boolean | null
}

export interface PortfolioResponse {
  items: PortfolioItem[]
  total: number
  page: number
  pageSize: number
  totalPages: number
  isPortfolioEmpty: boolean
  hasPortfolio: boolean
  latestReportPeriod: string | null
  latestAnnDate: string | null
  prevReportPeriod: string | null
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

export interface ReverseLookupResponse {
  items: ReverseLookupItem[]
  total: number
  page: number
  pageSize: number
  totalPages: number
  stockName: string | null
  reportPeriod: string | null
}

export const fundsApi = {
  getFunds: (params: FundListParams = {}) =>
    apiClient.get<{
      success: boolean
      data: FundListResponse
    }>('/funds', {
      search: params.search || undefined,
      market: params.market || undefined,
      fund_type: params.fundType || undefined,
      page: params.page || 1,
      page_size: params.pageSize || 20,
    }),

  getFund: (tsCode: string) =>
    apiClient.get<{
      success: boolean
      data: Fund
    }>(`/funds/${encodeURIComponent(tsCode)}`),

  getFundPortfolio: (tsCode: string, params?: { page?: number; pageSize?: number }) =>
    apiClient.get<{
      success: boolean
      data: PortfolioResponse
    }>(`/funds/${encodeURIComponent(tsCode)}/portfolio`, {
      page: params?.page || 1,
      page_size: params?.pageSize || 20,
    }),

  reverseLookup: (symbol: string, params?: {
    page?: number
    pageSize?: number
    fundType?: string[]
    market?: string[]
    fundSearch?: string
  }) =>
    apiClient.get<{
      success: boolean
      data: ReverseLookupResponse
    }>('/funds/reverse-lookup', {
      symbol,
      page: params?.page || 1,
      page_size: params?.pageSize || 20,
      fund_type: params?.fundType || undefined,
      market: params?.market || undefined,
      fund_search: params?.fundSearch || undefined,
    }),
}

// 管理员 API
// 创建专用的管理员 API 客户端，继承 ApiClient（已自动携带认证令牌）
class AdminApiClient extends ApiClient {
  constructor() {
    super(`${API_BASE_WITH_PREFIX}`)
  }

  protected async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const { method = 'GET', headers = {}, body, params } = options

    const url = new URL(`${this.baseURL}${endpoint}`)
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value === undefined || value === null) return
        // 数组：使用重复同名 key（?k=a&k=b），FastAPI 的 list[str] Query 会自动收集
        if (Array.isArray(value)) {
          if (value.length === 0) return
          value.forEach((item) => {
            if (item !== undefined && item !== null) {
              url.searchParams.append(key, String(item))
            }
          })
        } else {
          url.searchParams.append(key, String(value))
        }
      })
    }

    const authHeaders = this.getAuthHeaders()

    // 检查是否有有效 token
    if (Object.keys(authHeaders).length === 0 && endpoint.includes('/admin/')) {
      console.warn('Admin API request without authentication token')
    }

    const config: RequestInit = {
      method,
      headers: {
        ...this.defaultHeaders,
        ...authHeaders,  // 已由父类提供
        ...headers,
      },
    }

    if (body && method !== 'GET') {
      config.body = JSON.stringify(body)
    }

    try {
      const response = await fetch(url.toString(), config)

      // 检查响应状态
      if (!response.ok) {
        const json = await response.json().catch(() => ({}))
        const errorMsg = json.error?.message || json.detail || json.message || `HTTP error! status: ${response.status}`

        // 认证失败的特殊处理
        if (response.status === 401) {
          console.error('Authentication failed:', errorMsg)
          handleUnauthorizedRedirect()
        }

        throw new Error(errorMsg)
      }

      const json = await response.json()

      // 提取嵌套的 data 字段
      return { data: json.data }
    } catch (error) {
      console.error('API request failed:', endpoint, error)
      throw error
    }
  }

  // GET 请求
  async get<T>(endpoint: string, params?: Record<string, any>): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'GET', params })
  }

  // POST 请求
  async post<T>(endpoint: string, body?: any, params?: Record<string, any>): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'POST', body, params })
  }

  // PATCH 请求
  async patch<T>(endpoint: string, body?: any, params?: Record<string, any>): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'PATCH', body, params })
  }

  // DELETE 请求
  async delete<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'DELETE' })
  }
}

const adminApiClient = new AdminApiClient()

// 导出 adminApiClient 供其他模块使用
export { adminApiClient }

export const adminApi = {
  // 调度器管理
  getSchedulerStatus: () => adminApiClient.get<{ is_running: boolean; jobs: any }>('/admin/data/scheduler/status'),
  startScheduler: () => adminApiClient.post<any>('/admin/data/scheduler/start'),
  stopScheduler: () => adminApiClient.post<any>('/admin/data/scheduler/stop'),
  triggerJob: (jobId: string) => adminApiClient.post<any>(`/admin/data/scheduler/trigger/${jobId}`),

  // 数据质量
  checkDataQuality: () => adminApiClient.get<any>('/admin/data/quality/check'),

  // 缓存管理
  getCacheStats: () => adminApiClient.get<any>('/admin/data/cache/stats'),
  clearCache: (pattern?: string) => adminApiClient.post<any>('/admin/data/cache/clear', undefined, { pattern }),

  // 系统健康
  getSystemHealth: () => adminApiClient.get<any>('/admin/data/health'),

  // 用户管理
  listUsers: (params?: { q?: string; page?: number; pageSize?: number }) =>
    adminApiClient.get<{
      items: Array<{
        id: string
        email: string
        username: string | null
        role: 'admin' | 'user'
        isActive: boolean
        createdAt: string
        lastLoginAt: string | null
      }>
      total: number
      page: number
      pageSize: number
      totalPages: number
    }>('/admin/users', {
      q: params?.q || undefined,
      page: params?.page,
      pageSize: params?.pageSize,
    }),
  getUserStats: () =>
    adminApiClient.get<{
      total: number
      byRole: { admin: number; user: number }
      byStatus: { active: number; banned: number }
    }>('/admin/users/stats'),
  updateUser: (userId: string, data: { username?: string }) =>
    adminApiClient.patch<any>(`/admin/users/${userId}`, data),
  updateUserRole: (userId: string, role: 'admin' | 'user') =>
    adminApiClient.patch<any>(`/admin/users/${userId}/role`, { role }),
  updateUserStatus: (userId: string, isActive: boolean) =>
    adminApiClient.patch<any>(`/admin/users/${userId}/status`, { isActive }),

  // 基金数据同步
  initFundBasic: () =>
    adminApiClient.post<{task_id: string}>('/admin/init/funds'),
  initFundPortfolio: (period: string) =>
    adminApiClient.post<{task_id: string}>('/admin/init/fund-portfolio', { period }),
  initStockTop10Holders: (period: string) =>
    adminApiClient.post<{task_id: string}>('/admin/init/top10-holders', { period }),
  // 券商月度金股同步（09 期 plan-01/03，month 为 YYYYMM）
  initBrokerRecommend: (month: string) =>
    adminApiClient.post<{task_id: string}>('/admin/init/broker-recommend', { month }),
  // ETF 当日份额/净值采集（第 14 期 plan-03，无参数）
  initEtfDaily: () =>
    adminApiClient.post<{task_id: string}>('/admin/init/etf-daily'),
  // ETF 基础信息同步（拉取全市场 ETF 清单并归类跟踪指数/分类，无参数）
  initEtfBasic: () =>
    adminApiClient.post<{task_id: string}>('/admin/init/etf-basic'),
  // ETF 历史数据回填（第 14 期 plan-02，start_date/end_date 为 YYYY-MM-DD）
  initEtfHistory: (start_date: string, end_date: string) =>
    adminApiClient.post<{task_id: string}>('/admin/init/etf-history', { start_date, end_date }),
  // 关键指数同步（第 15 期 plan-02）
  // 指数基础信息同步（全量拉取 index_basic，预置 14 只关注指数）
  initIndexBasic: () =>
    adminApiClient.post<{task_id: string}>('/admin/init/index-basic'),
  // 指数历史数据回填（start_date/end_date 为 YYYY-MM-DD）
  initIndexHistory: (start_date: string, end_date: string) =>
    adminApiClient.post<{task_id: string}>('/admin/init/index-history', { start_date, end_date }),
  // 指数当日行情/估值/权重采集（无参数，复用 collector._update_index_daily）
  initIndexDaily: () =>
    adminApiClient.post<{task_id: string}>('/admin/init/index-daily'),
  // 涨停专题三表同步（起止都留空=最新交易日；都填=日期范围，YYYY-MM-DD）
  initLimit: (start_date?: string, end_date?: string) =>
    adminApiClient.post<{task_id: string}>(
      '/admin/init/limit',
      start_date && end_date ? { start_date, end_date } : {},
    ),

  // 股东监控组管理（plan-03 / plan-01 后端契约）
  // 后端 ApiResponse 包 { success, data, message }，AdminApiClient.request 已提取 data 字段
  getShareholderGroups: () =>
    adminApiClient.get<Array<ShareholderGroupListItem>>('/admin/shareholder-groups'),
  // 单条详情（编辑页按 id 独立加载，URL 可刷新/可分享）
  getShareholderGroup: (id: number) =>
    adminApiClient.get<ShareholderGroupListItem>(`/admin/shareholder-groups/${id}`),
  createShareholderGroup: (data: { name: string; description?: string; keywords: string[] }) =>
    adminApiClient.post<ShareholderGroupListItem>('/admin/shareholder-groups', data),
  updateShareholderGroup: (
    id: number,
    data: { name?: string; description?: string; keywords?: string[] }
  ) => adminApiClient.patch<ShareholderGroupListItem>(`/admin/shareholder-groups/${id}`, data),
  deleteShareholderGroup: (id: number) =>
    adminApiClient.delete<null>(`/admin/shareholder-groups/${id}`),
  previewShareholderGroupMatch: (keywords: string, excludeGroupId?: number) => {
    const params: Record<string, string> = { keywords }
    if (excludeGroupId) params['exclude_group_id'] = String(excludeGroupId)
    // 手动拼到 endpoint（AdminApiClient 的 params 用 url.searchParams，
    // 这里 keywords 是逗号分隔字符串，直接走 endpoint 拼接与 mock 的 URL 匹配一致）
    const search = new URLSearchParams(params).toString()
    return adminApiClient.get<{ matchedStockCount: number }>(
      `/admin/shareholder-groups/preview?${search}`
    )
  },
  // 逐关键词股数（plan-01 / plan-02）
  // 后端 ApiResponse 包 { success, data, message }，data.items[].matchedStockCount: number | null
  previewShareholderGroupMatchBreakdown: (
    keywords: string[],
    excludeGroupId?: number
  ) => {
    const params: Record<string, string> = {
      keywords: keywords.join(','),
    }
    if (excludeGroupId) params['exclude_group_id'] = String(excludeGroupId)
    // 与现有 previewShareholderGroupMatch 一致风格：手动 URLSearchParams 拼 endpoint，
    // 便于 E2E mock 用 pathname + search 精确匹配。
    // query 参数用 snake_case（exclude_group_id），不经 Pydantic alias 转换
    const search = new URLSearchParams(params).toString()
    return adminApiClient.get<{
      items: Array<{ keyword: string; matchedStockCount: number | null }>
    }>(`/admin/shareholder-groups/preview-breakdown?${search}`)
  },
  // 关键词匹配明细（plan-01 / plan-02）
  // 注意：query 参数 snake_case（page_size / exclude_group_id），response 才 camelCase
  listShareholderGroupKeywordMatches: (
    keyword: string,
    params: { page?: number; pageSize?: number; excludeGroupId?: number }
  ) => {
    const query: Record<string, string> = { keyword }
    if (params.page) query['page'] = String(params.page)
    if (params.pageSize) query['page_size'] = String(params.pageSize)
    if (params.excludeGroupId) query['exclude_group_id'] = String(params.excludeGroupId)
    const search = new URLSearchParams(query).toString()
    return adminApiClient.get<{
      items: Array<{ symbol: string; stockName: string | null; holderName: string }>
      total: number
      page: number
      pageSize: number
    }>(`/admin/shareholder-groups/keyword-matches?${search}`)
  },
}

// 导出任务状态类型供组件使用
export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'

// 股东监控组列表项（plan-01 / plan-03 契约，camelCase）
export interface ShareholderGroupListItem {
  id: number
  name: string
  description: string | null
  isSystem: boolean
  ruleCount: number
  matchedStockCount: number
  keywords: string[]
}

// 异步任务 API
export const tasksApi = {
  // 任务类型定义
  TaskType: {
    INIT_SECTORS: 'init_sectors',
    INIT_STOCKS: 'init_stocks',
    INIT_HISTORICAL_DATA: 'init_historical_data',
    INIT_SECTOR_HISTORICAL_DATA: 'init_sector_historical_data',
    INIT_SECTOR_STOCKS: 'init_sector_stocks',
    BACKFILL_BY_DATE: 'backfill_by_date',
    BACKFILL_BY_RANGE: 'backfill_by_range',
    SYNC_FUND_BASIC: 'sync_fund_basic',
    SYNC_FUND_PORTFOLIO: 'sync_fund_portfolio',
    SYNC_TOP10_HOLDERS: 'sync_top10_holders',
    SYNC_ETF_DAILY: 'sync_etf_daily',
    BACKFILL_ETF_HISTORY: 'backfill_etf_history',
    SYNC_ETF_BASIC: 'sync_etf_basic',
    SYNC_INDEX_BASIC: 'sync_index_basic',
    BACKFILL_INDEX_HISTORY: 'backfill_index_history',
    SYNC_INDEX_DAILY: 'sync_index_daily',
  } as const,

  // 任务状态定义
  TaskStatus: {
    PENDING: 'pending',
    RUNNING: 'running',
    COMPLETED: 'completed',
    FAILED: 'failed',
    CANCELLED: 'cancelled',
  } as const,

  // 获取已注册的任务类型
  getRegisteredTasks: () =>
    adminApiClient.get<string[]>('/admin/tasks/registered'),

  // 创建任务
  createTask: (data: {
    task_type: string
    params?: Record<string, any>
    max_retries?: number
    timeout_seconds?: number
  }) =>
    adminApiClient.post<{
      taskId: string
      taskType: string
      status: TaskStatus
      progress: number
      total: number
      percent: number
      createdAt: string
    }>('/admin/tasks', data),

  // 获取任务列表
  listTasks: (params?: {
    status?: string
    task_type?: string
    task_types?: string
    page?: number
    page_size?: number
  }) =>
    adminApiClient.get<{
      tasks: Array<{
        taskId: string
        taskType: string
        status: TaskStatus
        progress: number
        total: number
        percent: number
        params?: Record<string, any>
        errorMessage?: string
        retryCount: number
        maxRetries: number
        createdAt: string
        startedAt?: string
        completedAt?: string
      }>
      total: number
      page: number
    }>('/admin/tasks', params),

  // 获取任务详情
  getTask: (taskId: string) =>
    adminApiClient.get<{
      taskId: string
      taskType: string
      status: TaskStatus
      progress: number
      total: number
      percent: number
      params?: Record<string, any>
      errorMessage?: string
      retryCount: number
      maxRetries: number
      createdAt: string
      startedAt?: string
      completedAt?: string
    }>(`/admin/tasks/${taskId}`),

  // 取消任务
  cancelTask: (taskId: string) =>
    adminApiClient.post<{ taskId: string; cancelled: boolean }>(`/admin/tasks/${taskId}/cancel`),

  // 获取任务日志
  getTaskLogs: (taskId: string, params?: {
    level?: string
    page?: number
    page_size?: number
  }) =>
    adminApiClient.get<{
      logs: Array<{
        id: number
        taskId: string
        level: string
        message: string
        createdAt: string
      }>
      total: number
      page: number
    }>(`/admin/tasks/${taskId}/logs`, params),

  // 获取任务统计
  getTaskStats: () =>
    adminApiClient.get<{
      pending: number
      running: number
      completed: number
      failed: number
      cancelled: number
      total: number
    }>('/admin/tasks/stats/summary'),
}

// 股东分析面板 API（plan-04 / plan-02 后端用户侧 API）
// apiClient.baseURL 已含 /api/v1（见上方 API_BASE_WITH_PREFIX），路径不再带 /v1，避免双前缀
// 后端契约（plan-02 §7 / 架构 §7.2）：外层 { success: true, data: {...} }，camelCase
export interface ShareholderGroupOverview {
  groupId: number
  groupName: string
  description: string | null
  stockCount: number
  increaseCount: number
  decreaseCount: number
  newCount: number
  exitCount: number
}

export interface ShareholderOverviewResponse {
  reportPeriods: string[]
  currentPeriod: string
  hasPrevPeriod: boolean
  groups: ShareholderGroupOverview[]
}

export interface ShareholderSummary {
  stockCount: number
  totalHoldAmount: number
  avgHoldFloatRatio: number
}

export interface ShareholderTrend {
  increaseCount: number
  decreaseCount: number
  newCount: number
  exitCount: number
}

export interface ShareholderSummaryResponse {
  summary: ShareholderSummary
  trend: ShareholderTrend
  hasPrevPeriod: boolean
}

export interface ShareholderIndustryItem {
  industry: string
  stockCount: number
  percentage: number
}

export interface ShareholderIndustryDistributionResponse {
  distribution: ShareholderIndustryItem[]
}

export type ShareholderChangeDirection =
  | 'increase'
  | 'decrease'
  | 'new'
  | 'unchanged'
  | 'exit'
  | null

export interface ShareholderHoldingItem {
  symbol: string
  stockName: string
  totalHoldAmount: number
  totalHoldFloatRatio: number
  changeDirection: ShareholderChangeDirection
  industries: string[]
}

export interface ShareholderHoldingsResponse {
  holdings: ShareholderHoldingItem[]
  total: number
}

export interface ShareholderHolderItem {
  holderName: string
}

export interface ShareholderHolderSearchResponse {
  holders: ShareholderHolderItem[]
  total: number
}

export const shareholderAnalysisApi = {
  getOverview: (params?: { report_period?: string }) => {
    const query = params?.report_period
      ? `?report_period=${params.report_period}`
      : ''
    return apiClient.get<{
      success: boolean
      data: ShareholderOverviewResponse
    }>(`/shareholder-analysis/overview${query}`)
  },
  getSummary: (params: {
    group_ids?: string
    holder_name?: string
    report_period: string
    industry?: string
    change_direction?: string
  }) => {
    const query = new URLSearchParams({
      report_period: params.report_period,
    })
    if (params.group_ids) query.append('group_ids', params.group_ids)
    if (params.holder_name) query.append('holder_name', params.holder_name)
    if (params.industry) query.append('industry', params.industry)
    if (params.change_direction)
      query.append('change_direction', params.change_direction)
    return apiClient.get<{
      success: boolean
      data: ShareholderSummaryResponse
    }>(`/shareholder-analysis/summary?${query}`)
  },
  getIndustryDistribution: (params: {
    group_ids?: string
    holder_name?: string
    report_period: string
    change_direction?: string
  }) => {
    const query = new URLSearchParams({
      report_period: params.report_period,
    })
    if (params.group_ids) query.append('group_ids', params.group_ids)
    if (params.holder_name) query.append('holder_name', params.holder_name)
    if (params.change_direction)
      query.append('change_direction', params.change_direction)
    return apiClient.get<{
      success: boolean
      data: ShareholderIndustryDistributionResponse
    }>(`/shareholder-analysis/industry-distribution?${query}`)
  },
  getHoldings: (params: {
    group_ids?: string
    holder_name?: string
    report_period: string
    industry?: string
    change_direction?: string
    page?: number
    pageSize?: number
  }) => {
    // query key 用 snake_case（后端 Query 参数约定，to_camel 不作用于 query）
    const query = new URLSearchParams({
      report_period: params.report_period,
      page: String(params.page || 1),
      page_size: String(params.pageSize || 20),
    })
    if (params.group_ids) query.append('group_ids', params.group_ids)
    if (params.holder_name) query.append('holder_name', params.holder_name)
    if (params.industry) query.append('industry', params.industry)
    if (params.change_direction)
      query.append('change_direction', params.change_direction)
    return apiClient.get<{
      success: boolean
      data: ShareholderHoldingsResponse
    }>(`/shareholder-analysis/holdings?${query}`)
  },
  searchHolders: (params: {
    keyword: string
    page?: number
    pageSize?: number
  }) => {
    const query = new URLSearchParams({
      keyword: params.keyword,
      page: String(params.page || 1),
      page_size: String(params.pageSize || 20),
    })
    return apiClient.get<{
      success: boolean
      data: ShareholderHolderSearchResponse
    }>(`/shareholder-analysis/holders/search?${query}`)
  },
}

// ===================== 基金扎堆分析（08 plan-02）=====================

/**
 * 基金扎堆度分析前端契约（架构 §7.2 / plan-01 §3 #3）。
 * 字段全部 camelCase（后端 to_camel + _dict_to_camel 转换）；query 参数保持 snake_case。
 */
export type CrowdScope = 'active' | 'all'

export interface CrowdRankingItem {
  stockSymbol: string
  stockName: string | null
  industries: string[]
  fundCount: number
  fundCountChange: number | null
  /** 三态：true（新进）/ false（正常环比）/ null（hasPrevPeriod=false 时后端统一 null） */
  isNew: boolean | null
}

export interface CrowdRankingsResponse {
  hasData: boolean
  currentPeriod: string | null
  prevPeriod: string | null
  hasPrevPeriod: boolean
  items: CrowdRankingItem[]
  total: number
  page: number
  pageSize: number
}

export interface CrowdIndustryItem {
  industry: string
  stockCount: number
  percentage: number
}

export interface CrowdIndustryDistributionResponse {
  hasData: boolean
  currentPeriod: string | null
  /** 占比分母：当前报告期+口径下全部基金持仓的不同股票总数 */
  totalStockCount: number
  distribution: CrowdIndustryItem[]
}

/**
 * apiClient.baseURL 已含 /api/v1（见上方 API_BASE_WITH_PREFIX，line 8），
 * endpoint 不再带 /v1，避免双前缀（与 shareholderAnalysisApi / fundsApi 一致）。
 *
 * query 参数 snake_case（FastAPI Query 不经 alias 转换，参照 fundsApi.reverseLookup line 415-432）：
 * pageSize 入参 → 写 query 时必须转 page_size。
 */
export const fundCrowdAnalysisApi = {
  // 扎堆度排行榜（AC-01/02/03/06/07/08）
  getRankings: (params: {
    scope: CrowdScope
    sectorType?: SectorType
    sectorName?: string
    search?: string
    page?: number
    pageSize?: number
  }) =>
    apiClient.get<{
      success: boolean
      data: CrowdRankingsResponse
    }>('/fund-crowd-analysis/rankings', {
      scope: params.scope,
      search: params.search || undefined,
      page: params.page || 1,
      page_size: params.pageSize || 20,
      sector_type: params.sectorType,
      sector_name: params.sectorName,
    }),

  // 行业分布（AC-04）
  getIndustryDistribution: (params: { scope: CrowdScope; sectorType?: SectorType }) =>
    apiClient.get<{
      success: boolean
      data: CrowdIndustryDistributionResponse
    }>('/fund-crowd-analysis/industry-distribution', {
      scope: params.scope,
      sector_type: params.sectorType,
    }),
}

// ===================== 板块资金流（13 期 plan-03）=====================
//
// apiClient.baseURL 已含 /api/v1（见上方 API_BASE_WITH_PREFIX，line 9），
// endpoint 不再带 /api/v1，避免双前缀（与 fundCrowdAnalysisApi 一致）。
//
// 契约（plan-02 §3 / 架构 §7.3，dev-plan-check 已验证）：
// - query 参数 snake_case：sector_type / trade_date / sort_by / order / page / page_size / sector_names
// - 响应外层 { success, data }，data 内字段经后端 _dict_to_camel 转 camelCase
// - apiClient.get 泛型 T 必须写 `{ success: boolean; data: 业务对象 }`（与 fundCrowdAnalysisApi
//   line 1049 一致），否则 hook 层 res.data 取值类型撒谎 + 运行时 undefined。
import type {
  FundFlowRankingsData,
  FundFlowTimeseriesData,
  FundFlowLatestDateData,
  FundFlowSortBy,
  FundFlowOrder,
} from '@/types/fundFlowTypes'

export type { FundFlowSortBy, FundFlowOrder }

/**
 * 板块资金流查询 API（排行 / 盘中变化曲线 / 最新交易日）。
 * 类型定义见 types/fundFlowTypes.ts（camelCase 业务对象）。
 */
export const sectorFundFlowApi = {
  // 资金流排行榜（最新采样点）（AC-01/02/03/04/10/12）
  getRankings: (params: {
    sectorType?: SectorType
    tradeDate?: string | null
    sortBy?: FundFlowSortBy
    order?: FundFlowOrder
    page?: number
    pageSize?: number
  }) =>
    apiClient.get<{ success: boolean; data: FundFlowRankingsData }>(
      '/sector-fund-flow/rankings',
      {
        sector_type: params.sectorType,
        trade_date: params.tradeDate || undefined,
        sort_by: params.sortBy,
        order: params.order,
        page: params.page || 1,
        page_size: params.pageSize || 20,
      }
    ),

  // 盘中变化曲线（按板块名分组）（AC-06/07/08）
  getTimeseries: (params: {
    sectorNames: string[]
    sectorType?: SectorType
    tradeDate?: string | null
  }) =>
    apiClient.get<{ success: boolean; data: FundFlowTimeseriesData }>(
      '/sector-fund-flow/timeseries',
      {
        // 后端 sector_names 为逗号分隔字符串；空数组走 undefined 避免 ?sector_names=
        sector_names:
          params.sectorNames.length > 0 ? params.sectorNames.join(',') : undefined,
        sector_type: params.sectorType,
        trade_date: params.tradeDate || undefined,
      }
    ),

  // 最新交易日（AC 隐含：日期选择器默认值 + 历史回看）
  getLatestDate: (params: { sectorType?: SectorType }) =>
    apiClient.get<{ success: boolean; data: FundFlowLatestDateData }>(
      '/sector-fund-flow/latest-date',
      {
        sector_type: params.sectorType,
      }
    ),
}

// ============== 券商月度金股分析 API（09 期 plan-03）==============
//
// apiClient.baseURL 已含 /api/v1（见上方 API_BASE_WITH_PREFIX），
// endpoint 不再带 /v1，避免双前缀（与 fundCrowdAnalysisApi 一致）。
// query 参数 snake_case（page_size），响应输出 camelCase（后端 to_camel）。

export type BrokerView = 'stock' | 'broker' | 'trend'

export interface BrokerBrief {
  broker: string
  /** 同券商多条理由聚合，去空去重不丢弃（ADR-3） */
  reasons: string[]
}

export interface BrokerStockRankingItem {
  symbol: string
  name: string | null
  industries: string[]
  /** 推荐券商家数（COUNT DISTINCT broker，按券商名称去重） */
  brokerCount: number
  /** 全部推荐券商及理由（预加载，展开用） */
  brokers: BrokerBrief[]
}

export interface BrokerGroupItem {
  broker: string
  /** 本月推荐股票数 */
  stockCount: number
}

export interface BrokerDetailItem {
  symbol: string
  name: string | null
  /** 推荐理由数组（同 symbol 多记录合并去空去重，不丢弃） */
  reasons: string[]
}

export interface BrokerRankingResponse {
  hasData: boolean
  /** 当前月份（ISO 字符串 YYYY-MM-01），null 表示无数据 */
  month: string | null
  total: number
  page: number
  pageSize: number
  items: BrokerStockRankingItem[] | BrokerGroupItem[]
}

export interface BrokerMonthsResponse {
  hasData: boolean
  months: string[]
}

export interface BrokerDetailResponse {
  items: BrokerDetailItem[]
}

// 板块排行榜（行业/概念/地域，各 Top5）
export interface BrokerSectorRankingItem {
  sectorName: string
  stockCount: number
  percentage: number
}

export interface BrokerSectorRankingsResponse {
  hasData: boolean
  month: string | null
  industry: BrokerSectorRankingItem[]
  concept: BrokerSectorRankingItem[]
  region: BrokerSectorRankingItem[]
}

// ===================== 推荐趋势（10 期 plan-02）=====================
//
// 跨月聚合"持续推荐"趋势榜契约（架构 §7.2，camelCase）。
// 字段全部 camelCase（后端 to_camel + _dict_to_camel 转换）；query 参数保持 snake_case。
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
  /** 连续被推荐月数（从全局最新已同步月份向前沿 months 序列不间断计数，遇断档即停） */
  consecutiveMonths: number
  /** 累计券商家数（窗口内所有月份去重券商总数） */
  cumulativeBrokerCount: number
  /** 最新月家数（= 09 同月股票维度 brokerCount，口径一致） */
  latestMonthBrokerCount: number
  /** 月度家数走势序列（旧→新升序，含 0 断档点） */
  monthlySeries: TrendMonthPoint[]
  /** 各月推荐券商明细（预加载，展开用，新→旧降序） */
  monthlyBrokers: TrendMonthBroker[]
}

export interface TrendRankingResponse {
  hasData: boolean
  total: number
  page: number
  pageSize: number
  items: TrendRankingItem[]
}

export const brokerRecommendApi = {
  // 月份列表（AC-05/09）
  getMonths: () =>
    apiClient.get<{ success: boolean; data: BrokerMonthsResponse }>(
      '/broker-recommend-analysis/months'
    ),

  // 股票维度排行（AC-02/03/06/07/10/11）
  getStockRanking: (params: {
    month?: string
    search?: string
    page?: number
    pageSize?: number
    sectorType?: string
    sectorName?: string
  }) =>
    apiClient.get<{ success: boolean; data: BrokerRankingResponse }>(
      '/broker-recommend-analysis/stock-ranking',
      {
        month: params.month || undefined,
        search: params.search || undefined,
        page: params.page || 1,
        page_size: params.pageSize || 20,
        sector_type: params.sectorType || undefined,
        sector_name: params.sectorName || undefined,
      }
    ),

  // 券商维度分组（AC-04/06/07/12）
  getBrokerList: (params: {
    month?: string
    search?: string
    page?: number
    pageSize?: number
  }) =>
    apiClient.get<{ success: boolean; data: BrokerRankingResponse }>(
      '/broker-recommend-analysis/broker-list',
      {
        month: params.month || undefined,
        search: params.search || undefined,
        page: params.page || 1,
        page_size: params.pageSize || 20,
      }
    ),

  // 券商明细懒加载（AC-13）
  getBrokerDetail: (params: { month: string; broker: string }) =>
    apiClient.get<{ success: boolean; data: BrokerDetailResponse }>(
      '/broker-recommend-analysis/broker-detail',
      { month: params.month, broker: params.broker }
    ),

  // 板块排行榜（行业/概念/地域，各 Top5）
  getSectorRankings: (params: { month?: string }) =>
    apiClient.get<{ success: boolean; data: BrokerSectorRankingsResponse }>(
      '/broker-recommend-analysis/sector-rankings',
      { month: params.month || undefined }
    ),

  // 推荐趋势排行榜（10 期 plan-02，AC-02/03/05/06/07/08/09/11）
  // 跨全部已同步月份聚合，无 month 参数；query 传 snake_case（page_size）
  getTrendRanking: (params: {
    search?: string
    page?: number
    pageSize?: number
  }) =>
    apiClient.get<{ success: boolean; data: TrendRankingResponse }>(
      '/broker-recommend-analysis/trend-ranking',
      {
        ...(params.search ? { search: params.search } : {}),
        page: params.page ?? 1,
        page_size: params.pageSize ?? 20, // snake_case，FastAPI Query 不转 alias
      }
    ),
}

// ===================== ETF 监控（14 期 plan-03 查询 API / plan-04 前端客户端）=====================
//
// apiClient.baseURL 已含 /api/v1（见上方 API_BASE_WITH_PREFIX，line 9），
// endpoint 不再带 /api/v1，避免双前缀（与 sectorFundFlowApi line 1086 一致）。
//
// 契约（plan-03 §3 / 架构 §7.3，dev-plan-check 已验证）：
// - query 参数 snake_case：trade_date / sort_by / order / page / page_size /
//   index_code / target_type / target_code / metric / days / end_date
// - sort_by / metric 参数「值」用 camelCase（架构 §7.6 特例：netInflow / shareChange /
//   share），与后端取值一致，不要下划线化
// - 响应外层 { success, data }，data 内字段经后端 _dict_to_camel 转 camelCase
// - apiClient.get 泛型 T 写 `{ success: boolean; data: 业务对象 }`（与 sectorFundFlowApi
//   line 1096 一致），否则 hook 层 res.data 取值类型撒谎 + 运行时 undefined。
import type {
  EtfSortBy,
  EtfTrendMetric,
  EtfTargetType,
  EtfTrendDays,
  EtfIndexRankingsData,
  EtfIndexDetailData,
  EtfTrendData,
  EtfLatestDateData,
} from '@/types/etfMonitorTypes'
import type {
  LimitLadderData,
  LimitMultiDaysData,
  LimitListData,
  LimitLatestDateData,
  LimitType,
} from '@/types/limitTypes'
import type {
  IndexOverviewData,
  IndexTrendData,
  IndexValuationData,
  IndexWeightData,
  IndexWatchlistData,
  IndexWatchlistUpdateData,
} from '@/types/indexMonitorTypes'

export type {
  EtfSortBy,
  EtfTrendMetric,
  EtfTargetType,
  EtfTrendDays,
}

/**
 * ETF 监控查询 API（指数排行 / 指数明细 / 历史趋势 / 最新交易日）。
 * 类型定义见 types/etfMonitorTypes.ts（camelCase 业务对象）。
 */
export const etfMonitorApi = {
  // 指数排行（按 index_code 聚合）
  getIndexRankings: (params: {
    tradeDate?: string | null
    sortBy?: EtfSortBy
    order?: 'desc' | 'asc'
    page?: number
    pageSize?: number
  }) =>
    apiClient.get<{ success: boolean; data: EtfIndexRankingsData }>(
      '/etf-monitor/index-rankings',
      {
        trade_date: params.tradeDate || undefined, // snake_case query 名
        sort_by: params.sortBy, // 值 camelCase（架构 §7.6 特例）
        order: params.order,
        page: params.page || 1,
        page_size: params.pageSize || 20,
      }
    ),

  // 指数明细（展开指数查看 ETF 明细）
  getIndexDetail: (params: {
    indexCode: string
    tradeDate?: string | null
  }) =>
    apiClient.get<{ success: boolean; data: EtfIndexDetailData }>(
      '/etf-monitor/index-detail',
      {
        index_code: params.indexCode,
        trade_date: params.tradeDate || undefined,
      }
    ),

  // 历史趋势
  getTrend: (params: {
    targetType: EtfTargetType
    targetCode: string
    metric: EtfTrendMetric
    days: EtfTrendDays
    endDate?: string | null
  }) =>
    apiClient.get<{ success: boolean; data: EtfTrendData }>('/etf-monitor/trend', {
      target_type: params.targetType,
      target_code: params.targetCode,
      metric: params.metric, // 值 camelCase（架构 §7.6 特例）
      days: params.days,
      end_date: params.endDate || undefined,
    }),

  // 最新交易日（日期选择器默认值 + 判断是否有任何数据）
  getLatestDate: () =>
    apiClient.get<{ success: boolean; data: EtfLatestDateData }>(
      '/etf-monitor/latest-date',
      {}
    ),
}

/**
 * 涨停专题（连板天梯）查询 API
 *
 * 对应后端 /api/v1/limit/*。query 参数 snake_case，响应字段 camelCase。
 */
export const limitApi = {
  // 单日连板天梯（板块统计 + 按连板数分层个股）
  getLadder: (params: { tradeDate?: string | null }) =>
    apiClient.get<{ success: boolean; data: LimitLadderData }>('/limit/ladder', {
      trade_date: params.tradeDate || undefined,
    }),

  // 多日连板统计表格
  getMultiDays: (params: { endDate?: string | null; days?: number }) =>
    apiClient.get<{ success: boolean; data: LimitMultiDaysData }>(
      '/limit/multi-days',
      {
        end_date: params.endDate || undefined,
        days: params.days || 5,
      }
    ),

  // 当日涨停个股平铺列表（分页）
  getList: (params: {
    tradeDate?: string | null
    limitType?: LimitType | null
    page?: number
    pageSize?: number
  }) =>
    apiClient.get<{ success: boolean; data: LimitListData }>('/limit/list', {
      trade_date: params.tradeDate || undefined,
      limit_type: params.limitType || undefined,
      page: params.page || 1,
      page_size: params.pageSize || 50,
    }),

  // 最新有数据交易日
  getLatestDate: () =>
    apiClient.get<{ success: boolean; data: LimitLatestDateData }>(
      '/limit/latest-date',
      {}
    ),
}

// ===================== 关键指数监控（15 期 plan-03 查询 API / plan-04 前端客户端）=====================
//
// apiClient.baseURL 已含 /api/v1（见上方 API_BASE_WITH_PREFIX），
// endpoint 不再带 /api/v1，避免双前缀（与 etfMonitorApi 一致）。
//
// 契约（plan-03 §3 / 架构 §7.2）：
// - query 参数 snake_case：ts_codes / start_date / end_date / ts_code /
//   index_code / top_n
// - 响应外层 { success, data }，data 内字段经后端 _dict_to_camel 转 camelCase
// - amount 后端已 ÷10000 转亿元输出（plan-03 Task 2），前端 helpers 不再除

/**
 * 关键指数监控查询 API（总览 / 走势 / 估值 / 权重 / 关注清单）。
 * 类型定义见 types/indexMonitorTypes.ts（camelCase 业务对象）。
 */
export const indexMonitorApi = {
  // 关注指数当日行情总览（AC-01）
  getOverview: () =>
    apiClient.get<{ success: boolean; data: IndexOverviewData }>(
      '/index-monitor/overview'
    ),

  // 多指数收盘价走势（最多 6 只，AC-02）
  getTrend: (tsCodes: string[], startDate?: string, endDate?: string) =>
    apiClient.get<{ success: boolean; data: IndexTrendData }>(
      '/index-monitor/trend',
      {
        ts_codes: tsCodes.join(','),
        start_date: startDate,
        end_date: endDate,
      }
    ),

  // 单指数估值序列 PE/PB/换手率（AC-03）
  getValuation: (tsCode: string, startDate?: string, endDate?: string) =>
    apiClient.get<{ success: boolean; data: IndexValuationData }>(
      '/index-monitor/valuation',
      {
        ts_code: tsCode,
        start_date: startDate,
        end_date: endDate,
      }
    ),

  // 成分股权重 + 集中度（AC-04）
  getWeights: (indexCode: string, topN: number = 20) =>
    apiClient.get<{ success: boolean; data: IndexWeightData }>(
      '/index-monitor/weights',
      {
        index_code: indexCode,
        top_n: topN,
      }
    ),

  // 关注清单查询（AC-07）
  getWatchlist: () =>
    apiClient.get<{ success: boolean; data: IndexWatchlistData }>(
      '/index-monitor/watchlist'
    ),

  // 关注清单全量更新（AC-07）
  updateWatchlist: (tsCodes: string[]) =>
    apiClient.put<{ success: boolean; data: IndexWatchlistUpdateData }>(
      '/index-monitor/watchlist',
      { ts_codes: tsCodes }
    ),
}
