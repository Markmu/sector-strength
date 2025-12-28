/**
 * useMarketIndex Hook 测试
 */

import { renderHook, waitFor } from '@testing-library/react'
import { useMarketIndex } from '@/hooks/useMarketIndex'

// Mock SWR
jest.mock('swr', () => ({
  __esModule: true,
  default: jest.fn(),
}))

import useSWR from 'swr'

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
  })

  describe('基础功能测试', () => {
    it('应该返回初始加载状态', () => {
      ;(useSWR as jest.Mock).mockReturnValue({
        data: undefined,
        error: undefined,
        isLoading: true,
        mutate: jest.fn(),
      })

      const { result } = renderHook(() => useMarketIndex())

      expect(result.current.isLoading).toBe(true)
      expect(result.current.isError).toBeUndefined()
      expect(result.current.index).toBeUndefined()
      expect(result.current.stats).toBeUndefined()
      expect(result.current.trend).toEqual([])
    })

    it('应该返回市场指数数据', () => {
      ;(useSWR as jest.Mock).mockReturnValue({
        data: mockMarketIndexResponse,
        error: undefined,
        isLoading: false,
        mutate: jest.fn(),
      })

      const { result } = renderHook(() => useMarketIndex())

      expect(result.current.index).toEqual(mockMarketIndexResponse.data.index)
      expect(result.current.stats).toEqual(mockMarketIndexResponse.data.stats)
      expect(result.current.trend).toEqual(mockMarketIndexResponse.data.trend)
      expect(result.current.isLoading).toBe(false)
      expect(result.current.isError).toBeUndefined()
    })

    it('应该返回错误状态', () => {
      const mockError = new Error('API Error')

      ;(useSWR as jest.Mock).mockReturnValue({
        data: undefined,
        error: mockError,
        isLoading: false,
        mutate: jest.fn(),
      })

      const { result } = renderHook(() => useMarketIndex())

      expect(result.current.isError).toBe(mockError)
      expect(result.current.index).toBeUndefined()
      expect(result.current.stats).toBeUndefined()
    })

    it('应该处理空数据响应', () => {
      ;(useSWR as jest.Mock).mockReturnValue({
        data: { success: true, data: null },
        error: undefined,
        isLoading: false,
        mutate: jest.fn(),
      })

      const { result } = renderHook(() => useMarketIndex())

      expect(result.current.index).toBeUndefined()
      expect(result.current.stats).toBeUndefined()
    })

    it('应该处理 undefined data', () => {
      ;(useSWR as jest.Mock).mockReturnValue({
        data: undefined,
        error: undefined,
        isLoading: false,
        mutate: jest.fn(),
      })

      const { result } = renderHook(() => useMarketIndex())

      expect(result.current.index).toBeUndefined()
      expect(result.current.stats).toBeUndefined()
      expect(result.current.trend).toEqual([])
    })
  })

  describe('SWR 配置测试', () => {
    it('应该配置禁用自动轮询（用户要求手动刷新）', () => {
      renderHook(() => useMarketIndex())

      expect(useSWR).toHaveBeenCalled()

      const callArgs = (useSWR as jest.Mock).mock.calls[0]
      const config = callArgs[2]

      expect(config.refreshInterval).toBe(0)
    })

    it('应该禁用窗口聚焦刷新但启用网络重连刷新', () => {
      renderHook(() => useMarketIndex())

      const callArgs = (useSWR as jest.Mock).mock.calls[0]
      const config = callArgs[2]

      expect(config.revalidateOnFocus).toBe(false)
      expect(config.revalidateOnReconnect).toBe(true)
    })
  })

  describe('数据转换测试', () => {
    it('应该正确提取 index 数据', () => {
      ;(useSWR as jest.Mock).mockReturnValue({
        data: mockMarketIndexResponse,
        error: undefined,
        isLoading: false,
        mutate: jest.fn(),
      })

      const { result } = renderHook(() => useMarketIndex())

      expect(result.current.index?.value).toBe(68.5)
      expect(result.current.index?.change).toBe(2.3)
      expect(result.current.index?.color).toBe('#10B981')
    })

    it('应该正确提取 stats 数据', () => {
      ;(useSWR as jest.Mock).mockReturnValue({
        data: mockMarketIndexResponse,
        error: undefined,
        isLoading: false,
        mutate: jest.fn(),
      })

      const { result } = renderHook(() => useMarketIndex())

      expect(result.current.stats?.totalSectors).toBe(45)
      expect(result.current.stats?.upSectors).toBe(28)
      expect(result.current.stats?.downSectors).toBe(15)
      expect(result.current.stats?.neutralSectors).toBe(2)
    })

    it('应该正确提取 trend 数据', () => {
      ;(useSWR as jest.Mock).mockReturnValue({
        data: mockMarketIndexResponse,
        error: undefined,
        isLoading: false,
        mutate: jest.fn(),
      })

      const { result } = renderHook(() => useMarketIndex())

      expect(result.current.trend).toHaveLength(3)
      expect(result.current.trend[0].value).toBe(65.2)
    })

    it('应该处理空 trend 数组', () => {
      ;(useSWR as jest.Mock).mockReturnValue({
        data: {
          success: true,
          data: {
            ...mockMarketIndexResponse.data,
            trend: [],
          },
        },
        error: undefined,
        isLoading: false,
        mutate: jest.fn(),
      })

      const { result } = renderHook(() => useMarketIndex())

      expect(result.current.trend).toEqual([])
    })
  })

  describe('mutate 函数测试', () => {
    it('应该返回 mutate 函数', () => {
      const mockMutate = jest.fn()

      ;(useSWR as jest.Mock).mockReturnValue({
        data: mockMarketIndexResponse,
        error: undefined,
        isLoading: false,
        mutate: mockMutate,
      })

      const { result } = renderHook(() => useMarketIndex())

      expect(result.current.mutate).toBe(mockMutate)
    })

    it('应该可以手动触发重新验证', () => {
      const mockMutate = jest.fn()

      ;(useSWR as jest.Mock).mockReturnValue({
        data: mockMarketIndexResponse,
        error: undefined,
        isLoading: false,
        mutate: mockMutate,
      })

      const { result } = renderHook(() => useMarketIndex())

      result.current.mutate()

      expect(mockMutate).toHaveBeenCalled()
    })
  })
})
