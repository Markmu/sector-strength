/**
 * SWR Fetcher 工具函数
 *
 * 提供统一的 API 请求 fetcher，自动携带认证令牌
 */
import { handleUnauthorizedRedirect } from './authRedirect'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * 获取认证头
 */
export function getAuthHeaders(): Record<string, string> {
  if (typeof window === 'undefined') return {}

  const accessToken = localStorage.getItem('accessToken')
  const tokenType = localStorage.getItem('tokenType') || 'Bearer'

  if (!accessToken) return {}

  return {
    'Authorization': `${tokenType} ${accessToken}`,
  }
}

/**
 * 标准 fetcher - 携带认证令牌
 */
export async function fetcher<T>(url: string): Promise<T> {
  const fullUrl = url.startsWith('http') ? url : `${API_BASE}${url}`

  const response = await fetch(fullUrl, {
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
  })

  if (!response.ok) {
    if (response.status === 401) {
      handleUnauthorizedRedirect()
    }
    const error = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }))
    throw new Error(error.detail || error.error?.message || `API 请求失败: ${response.status}`)
  }

  const result = await response.json()
  return result.data || result
}

/**
 * 带 POST 方法的 fetcher
 */
export async function postFetcher<T>(url: string, data?: any): Promise<T> {
  const fullUrl = url.startsWith('http') ? url : `${API_BASE}${url}`

  const response = await fetch(fullUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify(data),
  })

  if (!response.ok) {
    if (response.status === 401) {
      handleUnauthorizedRedirect()
    }
    const error = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }))
    throw new Error(error.detail || error.error?.message || `API 请求失败: ${response.status}`)
  }

  const result = await response.json()
  return result.data || result
}
