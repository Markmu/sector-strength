/**
 * 板块分类 API 客户端
 *
 * 提供板块分类 API 的调用方法，自动处理认证和错误
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const API_BASE_WITH_PREFIX = `${API_BASE}/api/v1`

/**
 * 板块分类数据类型
 */
export interface SectorClassification {
  id: number
  sector_id: number
  symbol: string
  classification_date: string
  classification_level: number
  state: '反弹' | '调整'
  current_price: number | null
  change_percent: number | null
  price_5_days_ago: number | null
  ma_5: number | null
  ma_10: number | null
  ma_20: number | null
  ma_30: number | null
  ma_60: number | null
  ma_90: number | null
  ma_120: number | null
  ma_240: number | null
  created_at: string
}

/**
 * API 响应类型
 */
export interface ApiResponse<T> {
  data: T
  total?: number
}

/**
 * 标准错误响应类型
 */
export interface StandardApiError {
  error: {
    code: string
    message: string
    timestamp: string
  }
}

/**
 * 旧版 API 错误类型（兼容）
 */
export interface ApiError {
  detail: string
}

/**
 * API 客户端错误类
 */
export class ApiClientError extends Error {
  code: string
  timestamp: string

  constructor(message: string, code: string, timestamp: string) {
    super(message)
    this.name = 'ApiClientError'
    this.code = code
    this.timestamp = timestamp
  }
}

/**
 * 测试结果类型
 */
export interface TestResult {
  status: number
  data: unknown
  responseTime: number
  error?: string
}

/**
 * 获取认证头
 */
function getAuthHeaders(): Record<string, string> {
  if (typeof window === 'undefined') return {}

  const accessToken = localStorage.getItem('accessToken')
  const tokenType = localStorage.getItem('tokenType') || 'Bearer'

  if (!accessToken) return {}

  return {
    'Authorization': `${tokenType} ${accessToken}`,
  }
}

/**
 * 板块分类 API 客户端类
 */
class SectorClassificationAPI {
  private baseURL: string

  constructor() {
    this.baseURL = API_BASE_WITH_PREFIX
  }

  /**
   * 处理 API 响应，解析标准错误格式
   */
  private async handleResponse(response: Response): Promise<any> {
    if (!response.ok) {
      // 尝试解析标准错误响应格式
      const contentType = response.headers.get('content-type')
      if (contentType?.includes('application/json')) {
        const data: StandardApiError | ApiError = await response.json()

        // 检查是否是标准错误格式
        if ('error' in data && 'code' in data.error && 'message' in data.error) {
          throw new ApiClientError(
            data.error.message,
            data.error.code,
            data.error.timestamp
          )
        }

        // 兼容旧版错误格式
        if ('detail' in data) {
          throw new Error(data.detail)
        }
      }

      // 如果无法解析错误，使用默认错误消息
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    return response.json()
  }

  /**
   * 获取所有板块分类
   */
  async getAllClassifications(params?: { skip?: number; limit?: number }): Promise<ApiResponse<SectorClassification[]>> {
    const url = new URL(`${this.baseURL}/sector-classifications`)
    if (params?.skip !== undefined) url.searchParams.append('skip', params.skip.toString())
    if (params?.limit !== undefined) url.searchParams.append('limit', params.limit.toString())

    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
    })

    return this.handleResponse(response)
  }

  /**
   * 获取单个板块分类
   */
  async getClassificationById(sectorId: number): Promise<ApiResponse<SectorClassification>> {
    const response = await fetch(`${this.baseURL}/sector-classifications/${sectorId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
    })

    return this.handleResponse(response)
  }

  /**
   * 带响应时间测量的获取所有分类
   */
  async getAllClassificationsWithTiming(params?: { skip?: number; limit?: number }): Promise<TestResult> {
    const startTime = performance.now()

    try {
      const response = await fetch(`${this.baseURL}/sector-classifications${this.buildQueryString(params)}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders(),
        },
      })

      const endTime = performance.now()
      const data = await response.json()

      if (!response.ok) {
        // 尝试解析错误格式
        let errorMessage = `HTTP ${response.status}`
        if (typeof data === 'object' && data !== null) {
          if ('error' in data && typeof data.error === 'object') {
            const errorData = data.error as { code?: string; message?: string; timestamp?: string }
            errorMessage = errorData.message || errorMessage
          } else if ('detail' in data && typeof data.detail === 'string') {
            errorMessage = data.detail
          }
        }

        return {
          status: response.status,
          data: null,
          responseTime: endTime - startTime,
          error: errorMessage,
        }
      }

      return {
        status: response.status,
        data,
        responseTime: endTime - startTime,
      }
    } catch (error) {
      const endTime = performance.now()
      return {
        status: 0,
        data: null,
        responseTime: endTime - startTime,
        error: error instanceof Error ? error.message : '未知错误',
      }
    }
  }

  /**
   * 带响应时间测量的获取单个分类
   */
  async getClassificationByIdWithTiming(sectorId: number): Promise<TestResult> {
    const startTime = performance.now()

    try {
      const response = await fetch(`${this.baseURL}/sector-classifications/${sectorId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders(),
        },
      })

      const endTime = performance.now()
      const data = await response.json()

      if (!response.ok) {
        // 尝试解析错误格式
        let errorMessage = `HTTP ${response.status}`
        if (typeof data === 'object' && data !== null) {
          if ('error' in data && typeof data.error === 'object') {
            const errorData = data.error as { code?: string; message?: string; timestamp?: string }
            errorMessage = errorData.message || errorMessage
          } else if ('detail' in data && typeof data.detail === 'string') {
            errorMessage = data.detail
          }
        }

        return {
          status: response.status,
          data: null,
          responseTime: endTime - startTime,
          error: errorMessage,
        }
      }

      return {
        status: response.status,
        data,
        responseTime: endTime - startTime,
      }
    } catch (error) {
      const endTime = performance.now()
      return {
        status: 0,
        data: null,
        responseTime: endTime - startTime,
        error: error instanceof Error ? error.message : '未知错误',
      }
    }
  }

  /**
   * 构建查询字符串
   */
  private buildQueryString(params?: { skip?: number; limit?: number }): string {
    if (!params) return ''

    const searchParams = new URLSearchParams()
    if (params.skip !== undefined) searchParams.append('skip', params.skip.toString())
    if (params.limit !== undefined) searchParams.append('limit', params.limit.toString())

    const queryString = searchParams.toString()
    return queryString ? `?${queryString}` : ''
  }
}

/**
 * 导出单例实例
 */
export const sectorClassificationApi = new SectorClassificationAPI()
