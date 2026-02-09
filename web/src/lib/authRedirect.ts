const AUTH_KEYS = ['accessToken', 'refreshToken', 'tokenType', 'expiresIn', 'user'] as const

export const AUTH_EXPIRED_EVENT = 'auth:expired'

function clearStoredAuth() {
  if (typeof window === 'undefined') return

  for (const key of AUTH_KEYS) {
    localStorage.removeItem(key)
  }
}

export function handleUnauthorizedRedirect() {
  if (typeof window === 'undefined') return

  clearStoredAuth()
  window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT))

  const currentPath = `${window.location.pathname}${window.location.search}`

  // 登录页本身不重复跳转，避免无意义循环
  if (window.location.pathname.startsWith('/login')) {
    return
  }

  const loginUrl = `/login?redirect=${encodeURIComponent(currentPath)}`
  window.location.replace(loginUrl)
}
