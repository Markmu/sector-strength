import { useState, useEffect, useCallback, useRef } from 'react'
import { apiClient, ApiResponse } from '@/lib/api'

// 导出任务状态Hook
export { useTaskStatus, useMultipleTaskStatus } from './useTaskStatus'

// 导出板块相关 Hooks
export { useSectorHeatmapData } from './useSectorHeatmapData'
export { useSectorRanking } from './useSectorRanking'
export { useSectorDistribution } from './useSectorDistribution'
export { useSectorGradeTable } from './useSectorGradeTable'
export { useSectorScatterData } from './useSectorScatterData'
export { useSectorStrengthHistory } from './useSectorStrengthHistory'
export { useSectorMAHistory } from './useSectorMAHistory'

// 导出其他业务 Hooks
export { useMarketIndex } from './useMarketIndex'
export { useStockRanking } from './useStockRanking'
export { useRequireAdmin } from './useRequireAdmin'

// API 请求 Hook
export function useApi<T = any>(
  url: string | null,
  params?: Record<string, any>,
  immediate = true
) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const execute = useCallback(async () => {
    if (!url) return

    setLoading(true)
    setError(null)

    try {
      const response = await apiClient.get<T>(url, params)
      setData(response.data || null)
    } catch (err) {
      setError(err instanceof Error ? err.message : '请求失败')
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [url, params])

  useEffect(() => {
    if (immediate && url) {
      execute()
    }
  }, [execute, immediate, url])

  return { data, loading, error, execute }
}

// 防抖 Hook
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value)

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)

    return () => {
      clearTimeout(handler)
    }
  }, [value, delay])

  return debouncedValue
}

// 本地存储 Hook
export function useLocalStorage<T>(
  key: string,
  initialValue: T
): [T, (value: T | ((val: T) => T)) => void] {
  const [storedValue, setStoredValue] = useState<T>(() => {
    if (typeof window === 'undefined') return initialValue
    try {
      const item = window.localStorage.getItem(key)
      return item ? JSON.parse(item) : initialValue
    } catch (error) {
      console.error(`Error reading localStorage key "${key}":`, error)
      return initialValue
    }
  })

  const setValue = useCallback(
    (value: T | ((val: T) => T)) => {
      try {
        const valueToStore = value instanceof Function ? value(storedValue) : value
        setStoredValue(valueToStore)
        if (typeof window !== 'undefined') {
          window.localStorage.setItem(key, JSON.stringify(valueToStore))
        }
      } catch (error) {
        console.error(`Error setting localStorage key "${key}":`, error)
      }
    },
    [key, storedValue]
  )

  return [storedValue, setValue]
}

// 媒体查询 Hook
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false)

  useEffect(() => {
    if (typeof window === 'undefined') return

    const media = window.matchMedia(query)
    setMatches(media.matches)

    const listener = (event: MediaQueryListEvent) => {
      setMatches(event.matches)
    }

    media.addEventListener('change', listener)
    return () => media.removeEventListener('change', listener)
  }, [query])

  return matches
}

// 窗口大小 Hook
export function useWindowSize() {
  const [windowSize, setWindowSize] = useState({
    width: 0,
    height: 0,
  })

  useEffect(() => {
    if (typeof window === 'undefined') return

    function handleResize() {
      setWindowSize({
        width: window.innerWidth,
        height: window.innerHeight,
      })
    }

    window.addEventListener('resize', handleResize)
    handleResize()

    return () => window.removeEventListener('resize', handleResize)
  }, [])

  return windowSize
}

// 在线状态 Hook
export function useOnlineStatus() {
  const [isOnline, setIsOnline] = useState(
    typeof navigator !== 'undefined' ? navigator.onLine : true
  )

  useEffect(() => {
    if (typeof window === 'undefined') return

    function handleOnline() {
      setIsOnline(true)
    }

    function handleOffline() {
      setIsOnline(false)
    }

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  return isOnline
}

// 定时器 Hook
export function useInterval(callback: () => void, delay: number | null) {
  const savedCallback = useRef(callback)

  useEffect(() => {
    savedCallback.current = callback
  }, [callback])

  useEffect(() => {
    if (delay === null) return

    const id = setInterval(() => {
      savedCallback.current()
    }, delay)

    return () => clearInterval(id)
  }, [delay])
}

// 上一次值的 Hook
export function usePrevious<T>(value: T): T | undefined {
  const ref = useRef<T | undefined>(undefined)
  useEffect(() => {
    ref.current = value
  })
  return ref.current
}

// 是否首次渲染 Hook
export function useIsFirstRender(): boolean {
  const ref = useRef(true)
  useEffect(() => {
    ref.current = false
  }, [])
  return ref.current
}

// 异步状态 Hook
export function useAsync<T>(
  asyncFunction: () => Promise<T>,
  dependencies: React.DependencyList = []
) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    let isCancelled = false

    setLoading(true)
    setError(null)

    asyncFunction()
      .then((result) => {
        if (!isCancelled) {
          setData(result)
        }
      })
      .catch((err) => {
        if (!isCancelled) {
          setError(err instanceof Error ? err : new Error('Unknown error'))
        }
      })
      .finally(() => {
        if (!isCancelled) {
          setLoading(false)
        }
      })

    return () => {
      isCancelled = true
    }
  }, dependencies)

  return { data, loading, error }
}

// 复制到剪贴板 Hook
export function useCopyToClipboard() {
  const [isCopied, setIsCopied] = useState(false)

  const copyToClipboard = useCallback(async (text: string) => {
    if (typeof window === 'undefined') return

    try {
      await navigator.clipboard.writeText(text)
      setIsCopied(true)
      setTimeout(() => setIsCopied(false), 2000)
    } catch (error) {
      console.error('Failed to copy text: ', error)
      setIsCopied(false)
    }
  }, [])

  return { isCopied, copyToClipboard }
}

// 页面可见性 Hook
export function usePageVisibility() {
  const [isVisible, setIsVisible] = useState(
    typeof document !== 'undefined' ? !document.hidden : true
  )

  useEffect(() => {
    if (typeof document === 'undefined') return

    const handleVisibilityChange = () => {
      setIsVisible(!document.hidden)
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [])

  return isVisible
}