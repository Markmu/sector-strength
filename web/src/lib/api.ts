import { z } from 'zod'
import { handleUnauthorizedRedirect } from './authRedirect'

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
  getSectorStocks: (sectorId: number, params?: { skip?: number; limit?: number }) =>
    apiClient.get<any[]>(`/sectors/${sectorId}/stocks`, params),
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
  getHeatmap: (params?: { sector_type?: string }) =>
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

  // 板块分类管理
  initSectorClassification: (params?: { start_date?: string; overwrite?: boolean }) =>
    adminApiClient.post<{task_id: string; message: string}>('/admin/sector-classification/initialize', params),
  updateSectorClassificationDaily: (params?: { target_date?: string; overwrite?: boolean }) =>
    adminApiClient.post<{task_id: string; message: string}>('/admin/sector-classification/update-daily', params),
  getSectorClassificationStatus: () =>
    adminApiClient.get<any>('/admin/sector-classification/status'),

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

  // 股东监控组管理（plan-03 / plan-01 后端契约）
  // 后端 ApiResponse 包 { success, data, message }，AdminApiClient.request 已提取 data 字段
  getShareholderGroups: () =>
    adminApiClient.get<Array<ShareholderGroupListItem>>('/admin/shareholder-groups'),
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
    INIT_SECTOR_CLASSIFICATIONS: 'init_sector_classifications',
    UPDATE_SECTOR_CLASSIFICATION_DAILY: 'update_sector_classification_daily',
    SYNC_FUND_BASIC: 'sync_fund_basic',
    SYNC_FUND_PORTFOLIO: 'sync_fund_portfolio',
    SYNC_TOP10_HOLDERS: 'sync_top10_holders',
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
    group_ids: string
    report_period: string
    industry?: string
    change_direction?: string
  }) => {
    const query = new URLSearchParams({
      group_ids: params.group_ids,
      report_period: params.report_period,
    })
    if (params.industry) query.append('industry', params.industry)
    if (params.change_direction)
      query.append('change_direction', params.change_direction)
    return apiClient.get<{
      success: boolean
      data: ShareholderSummaryResponse
    }>(`/shareholder-analysis/summary?${query}`)
  },
  getIndustryDistribution: (params: {
    group_ids: string
    report_period: string
    change_direction?: string
  }) => {
    const query = new URLSearchParams({
      group_ids: params.group_ids,
      report_period: params.report_period,
    })
    if (params.change_direction)
      query.append('change_direction', params.change_direction)
    return apiClient.get<{
      success: boolean
      data: ShareholderIndustryDistributionResponse
    }>(`/shareholder-analysis/industry-distribution?${query}`)
  },
  getHoldings: (params: {
    group_ids: string
    report_period: string
    industry?: string
    change_direction?: string
    page?: number
    pageSize?: number
  }) => {
    // query key 用 snake_case（后端 Query 参数约定，to_camel 不作用于 query）
    const query = new URLSearchParams({
      group_ids: params.group_ids,
      report_period: params.report_period,
      page: String(params.page || 1),
      page_size: String(params.pageSize || 20),
    })
    if (params.industry) query.append('industry', params.industry)
    if (params.change_direction)
      query.append('change_direction', params.change_direction)
    return apiClient.get<{
      success: boolean
      data: ShareholderHoldingsResponse
    }>(`/shareholder-analysis/holdings?${query}`)
  },
}
