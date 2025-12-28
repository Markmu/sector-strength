/**
 * useMarketIndex Hook 测试
 */

import { renderHook, waitFor } from '@testing-library/react'
import { useMarketIndex } from '@/hooks/useMarketIndex'
import { SWRConfig } from 'swr'

// Mock fetch
global.fetch = jest.fn()

const mockMarketIndexResponse = {
  success: true,
  data: {
    index: {
      value: 68.5,
      change: 2.3,
      timestamp: '2025-12-28T10:30:00Z',
      color: '#10B981',
    },
    stats: {
      totalSectors: 45,
      upSectors: 28,
      downSectors: 15,
      neutralSectors: 2,
    },
    trend: [
      { timestamp: '2025-12-27T10:00:00Z', value: 65.2 },
      { timestamp: '2025-12-27T11:00:00Z', value: 66.8 },
      { timestamp: '2025-12-27T12:00:00Z', value: 68.5 },
    ],
  },
}

describe('useMarketIndex', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    ;(global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockMarketIndexResponse,
    })
  })

  describe('基础功能测试', () => {
    it('应该返回初始加载状态', () => {
      const { result } = renderHook(() => useMarketIndex())

      expect(result.current.isLoading).toBe(true)
      expect(result.current.index).toBeUndefined()
      expect(result.current.stats).toBeUndefined()
      expect(result.current.trend).toEqual([])
    })

    it('应该返回市场指数数据', async () => {
      const { result } = renderHook(() => useMarketIndex())

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.index).toEqual(mockMarketIndexResponse.data.index)
      expect(result.current.stats).toEqual(mockMarketIndexResponse.data.stats)
      expect(result.current.trend).toEqual(mockMarketIndexResponse.data.trend)
    })

    it('应该返回错误状态', async () => {
      ;(global.fetch as jest.Mock).mockResolvedValue({
        ok: false,
        status: 500,
      })

      const { result } = renderHook(() => useMarketIndex())

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.isError).toBe(true)
    })

    it('应该处理空数据响应', async () => {
      ;(global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => ({ success: true, data: null }),
      })

      const { result } = renderHook(() => useMarketIndex())

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.index).toBeUndefined()
      expect(result.current.stats).toBeUndefined()
    })

    it('应该处理 undefined data', async () => {
      ;(global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => ({ success: false }),
      })

      const { result } = renderHook(() => useMarketIndex())

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.index).toBeUndefined()
      expect(result.current.stats).toBeUndefined()
    })
  })

  describe('SWR 配置测试', () => {
    it('应该配置禁用自动轮询', async () => {
      let capturedConfig: any = null

      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <SWRConfig value={{ provider: () => ({ config: (c: any) => { capturedConfig = c } }) }}>
          {children}
        </SWRConfig>
      )

      renderHook(() => useMarketIndex(), { wrapper })

      await waitFor(() => {
        expect(capturedConfig.refreshInterval).toBe(0)
      })
    })

    it('应该禁用窗口聚焦刷新', async () => {
      let capturedConfig: any = null

      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <SWRConfig value={{ provider: () => ({ config: (c: any) => { capturedConfig = c } }) }}>
          {children}
        </SWRConfig>
      )

      renderHook(() => useMarketIndex(), { wrapper })

      await waitFor(() => {
        expect(capturedConfig.revalidateOnFocus).toBe(false)
      })
    })

    it('应该启用网络重连刷新', async () => {
      let capturedConfig: any = null

      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <SWRConfig value={{ provider: () => ({ config: (c: any) => { capturedConfig = c } }) }}>
          {children}
        </SWRConfig>
      )

      renderHook(() => useMarketIndex(), { wrapper })

      await waitFor(() => {
        expect(capturedConfig.revalidateOnReconnect).toBe(true)
      })
    })
  })

  describe('mutate 函数测试', () => {
    it('应该返回 mutate 函数', () => {
      const { result } = renderHook(() => useMarketIndex())

      expect(result.current.mutate).toBeDefined()
      expect(typeof result.current.mutate).toBe('function')
    })

    it('应该可以手动触发重新验证', async () => {
      const { result } = renderHook(() => useMarketIndex())

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      // 调用 mutate 重新验证
      result.current.mutate()

      expect(global.fetch).toHaveBeenCalledTimes(2) // 初始加载 + mutate
    })
  })

  describe('数据转换测试', () => {
    it('应该正确提取 index 数据', async () => {
      const { result } = renderHook(() => useMarketIndex())

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.index?.value).toBe(68.5)
      expect(result.current.index?.change).toBe(2.3)
      expect(result.current.index?.color).toBe('#10B981')
    })

    it('应该正确提取 stats 数据', async () => {
      const { result } = renderHook(() => useMarketIndex())

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.stats?.totalSectors).toBe(45)
      expect(result.current.stats?.upSectors).toBe(28)
      expect(result.current.stats?.downSectors).toBe(15)
      expect(result.current.stats?.neutralSectors).toBe(2)
    })

    it('应该正确提取 trend 数据', async () => {
      const { result } = renderHook(() => useMarketIndex())

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.trend).toHaveLength(3)
      expect(result.current.trend[0].value).toBe(65.2)
    })

    it('应该处理空 trend 数组', async () => {
      ;(global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => ({
          success: true,
          data: {
            ...mockMarketIndexResponse.data,
            trend: [],
          },
        }),
      })

      const { result } = renderHook(() => useMarketIndex())

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.trend).toEqual([])
    })
  })
})
