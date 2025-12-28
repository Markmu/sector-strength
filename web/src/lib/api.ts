import { z } from 'zod'

// API 基础配置
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

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

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL
    this.defaultHeaders = {
      'Content-Type': 'application/json',
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
        if (value !== undefined && value !== null) {
          url.searchParams.append(key, String(value))
        }
      })
    }

    const config: RequestInit = {
      method,
      headers: {
        ...this.defaultHeaders,
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
        throw new Error(data.error?.message || `HTTP error! status: ${response.status}`)
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
export const stocksApi = {
  getStocks: (params?: { skip?: number; limit?: number }) =>
    apiClient.get<any[]>('/v1/stocks', params),
  getStock: (stockId: string) => apiClient.get<any>(`/v1/stocks/${stockId}`),
}

// 板块 API
export const sectorsApi = {
  getSectors: (params?: { skip?: number; limit?: number }) =>
    apiClient.get<any[]>('/v1/sectors', params),
  getSector: (sectorId: number) => apiClient.get<any>(`/v1/sectors/${sectorId}`),
  getSectorStocks: (sectorId: number, params?: { skip?: number; limit?: number }) =>
    apiClient.get<any[]>(`/v1/sectors/${sectorId}/stocks`, params),
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
    }>('/v1/sectors/search', { keyword, ...params }),
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
  }) => apiClient.get<any[]>('/v1/strength', params),
  getLatestStrength: (params?: { sector_id?: string; period?: string }) =>
    apiClient.get<any[]>('/v1/strength/latest', params),
}

// 用户资料 API
export const userApi = {
  // 获取用户资料
  getProfile: () => apiClient.get<any>('/v1/user/profile'),

  // 更新用户资料
  updateProfile: (data: {
    display_name?: string
    timezone?: string
    language?: string
  }) => apiClient.put<any>('/v1/user/profile', data),

  // 获取用户偏好设置
  getPreferences: () => apiClient.get<any>('/v1/user/preferences'),

  // 更新用户偏好设置
  updatePreferences: (data: {
    email_notifications?: boolean
    push_notifications?: boolean
    marketing_emails?: boolean
  }) => apiClient.put<any>('/v1/user/preferences', data),

  // 更改密码
  changePassword: (data: {
    current_password: string
    new_password: string
  }) => apiClient.post<any>('/v1/user/change-password', data),

  // 获取活跃会话
  getSessions: () => apiClient.get<any>('/v1/user/sessions'),

  // 终止特定会话
  terminateSession: (sessionId: string) =>
    apiClient.delete<any>(`/v1/user/sessions/${sessionId}`),

  // 终止所有其他会话
  terminateAllOtherSessions: () =>
    apiClient.delete<any>('/v1/user/sessions/all'),

  // 停用账户
  deactivateAccount: () => apiClient.post<any>('/v1/user/deactivate'),

  // 删除账户
  deleteAccount: () => apiClient.delete<any>('/v1/user/account'),
}

// 热力图 API
export const heatmapApi = {
  getHeatmap: (params?: { sector_type?: 'industry' | 'concept' }) =>
    apiClient.get<any>('/api/v1/heatmap', params),
}

// 管理员 API
// 创建专用的管理员 API 客户端，使用 JWT token 认证
class AdminApiClient extends ApiClient {
  constructor() {
    // 管理员 API 需要加上 /api 前缀
    super(`${API_BASE_URL}/api`)
  }

  private getAuthHeaders(): Record<string, string> {
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
        if (value !== undefined && value !== null) {
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
        ...authHeaders,  // 添加认证头
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
          // 可以在这里触发重新登录逻辑
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

  // DELETE 请求
  async delete<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'DELETE' })
  }
}

const adminApiClient = new AdminApiClient()

export const adminApi = {
  // 数据更新
  triggerUpdate: () => adminApiClient.post<{ success: boolean; message: string; task_id: string }>('/v1/admin/data/update'),
  getUpdateStatus: () => adminApiClient.get<any>('/v1/admin/data/update-status'),
  getUpdateHistory: (params?: { page?: number; page_size?: number }) =>
    adminApiClient.get<any>('/v1/admin/data/update-history', params),
  cancelUpdate: () => adminApiClient.post<any>('/v1/admin/data/update/cancel'),

  // 调度器管理
  getSchedulerStatus: () => adminApiClient.get<{ is_running: boolean; jobs: any }>('/v1/admin/data/scheduler/status'),
  startScheduler: () => adminApiClient.post<any>('/v1/admin/data/scheduler/start'),
  stopScheduler: () => adminApiClient.post<any>('/v1/admin/data/scheduler/stop'),
  triggerJob: (jobId: string) => adminApiClient.post<any>(`/v1/admin/data/scheduler/trigger/${jobId}`),

  // 数据质量
  checkDataQuality: () => adminApiClient.get<any>('/v1/admin/data/quality/check'),

  // 缓存管理
  getCacheStats: () => adminApiClient.get<any>('/v1/admin/data/cache/stats'),
  clearCache: (pattern?: string) => adminApiClient.post<any>('/v1/admin/data/cache/clear', undefined, { pattern }),

  // 系统健康
  getSystemHealth: () => adminApiClient.get<any>('/v1/admin/data/health'),
}

// 导出任务状态类型供组件使用
export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'

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
    adminApiClient.get<string[]>('/v1/admin/tasks/registered'),

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
    }>('/v1/admin/tasks', data),

  // 获取任务列表
  listTasks: (params?: {
    status?: string
    task_type?: string
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
        retryCount: number
        maxRetries: number
        createdAt: string
        startedAt?: string
        completedAt?: string
      }>
      total: number
      page: number
    }>('/v1/admin/tasks', params),

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
    }>(`/v1/admin/tasks/${taskId}`),

  // 取消任务
  cancelTask: (taskId: string) =>
    adminApiClient.post<{ taskId: string; cancelled: boolean }>(`/v1/admin/tasks/${taskId}/cancel`),

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
    }>(`/v1/admin/tasks/${taskId}/logs`, params),

  // 获取任务统计
  getTaskStats: () =>
    adminApiClient.get<{
      pending: number
      running: number
      completed: number
      failed: number
      cancelled: number
      total: number
    }>('/v1/admin/tasks/stats/summary'),
}
