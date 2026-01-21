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
 * API 错误类型
 */
export interface ApiError {
  detail: string
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

    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }))
      throw new Error(error.detail || '获取分类数据失败')
    }

    return response.json()
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

    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }))
      throw new Error(error.detail || '获取板块分类失败')
    }

    return response.json()
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
        return {
          status: response.status,
          data: null,
          responseTime: endTime - startTime,
          error: data.detail || data.error?.message || `HTTP ${response.status}`,
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
        return {
          status: response.status,
          data: null,
          responseTime: endTime - startTime,
          error: data.detail || data.error?.message || `HTTP ${response.status}`,
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
