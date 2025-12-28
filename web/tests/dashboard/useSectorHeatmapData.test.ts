import { renderHook, waitFor } from '@testing-library/react'
import { useSectorHeatmapData } from '@/hooks/useSectorHeatmapData'
import { heatmapApi } from '@/lib/api'
import type { HeatmapSector } from '@/types'

// Mock heatmap API
jest.mock('@/lib/api', () => ({
  heatmapApi: {
    getHeatmap: jest.fn(),
  },
}))

// Mock SWR
jest.mock('swr', () => ({
  __esModule: true,
  default: jest.fn(),
}))

import useSWR from 'swr'

const mockSectors: HeatmapSector[] = [
  { id: '1', name: '新能源', value: 85.5, color: '#22c55e' },
  { id: '2', name: '半导体', value: 72.3, color: '#4ade80' },
  { id: '3', name: '医药', value: 55.0, color: '#facc15' },
]

const mockHeatmapResponse = {
  success: true,
  data: {
    sectors: mockSectors,
    timestamp: '2025-12-24T10:30:00Z',
  },
}

describe('useSectorHeatmapData', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    jest.useFakeTimers()
  })

  afterEach(() => {
    jest.runOnlyPendingTimers()
    jest.useRealTimers()
  })

  describe('基础功能测试', () => {
    it('应该返回初始加载状态', () => {
      // Mock SWR 返回初始状态
      ;(useSWR as jest.Mock).mockReturnValue({
        data: undefined,
        error: undefined,
        isLoading: true,
        mutate: jest.fn(),
      })

      const { result } = renderHook(() => useSectorHeatmapData())

      expect(result.current.isLoading).toBe(true)
      expect(result.current.isError).toBe(false)
      expect(result.current.sectors).toEqual([])
    })

    it('应该返回热力图数据', async () => {
      // Mock SWR 返回数据
      ;(useSWR as jest.Mock).mockReturnValue({
        data: mockHeatmapResponse,
        error: undefined,
        isLoading: false,
        mutate: jest.fn(),
      })

      const { result } = renderHook(() => useSectorHeatmapData())

      expect(result.current.sectors).toEqual(mockSectors)
      expect(result.current.timestamp).toBe('2025-12-24T10:30:00Z')
      expect(result.current.isLoading).toBe(false)
      expect(result.current.isError).toBe(false)
    })

    it('应该返回错误状态', () => {
      const mockError = new Error('API Error')

      ;(useSWR as jest.Mock).mockReturnValue({
        data: undefined,
        error: mockError,
        isLoading: false,
        mutate: jest.fn(),
      })

      const { result } = renderHook(() => useSectorHeatmapData())

      expect(result.current.isError).toBe(true)
      expect(result.current.error).toBe(mockError)
      expect(result.current.sectors).toEqual([])
    })
  })

  describe('SWR 配置测试', () => {
    it('应该配置禁用自动轮询（用户要求手动刷新）', () => {
      const { result } = renderHook(() => useSectorHeatmapData())

      // 验证 SWR 被调用
      expect(useSWR).toHaveBeenCalled()

      const callArgs = (useSWR as jest.Mock).mock.calls[0]
      const config = callArgs[2]

      expect(config.refreshInterval).toBe(0)
    })

    it('应该配置禁用窗口聚焦刷新但启用网络重连刷新', () => {
      renderHook(() => useSectorHeatmapData())

      const callArgs = (useSWR as jest.Mock).mock.calls[0]
      const config = callArgs[2]

      expect(config.revalidateOnFocus).toBe(false)
      expect(config.revalidateOnReconnect).toBe(true)
    })

    it('应该配置去重间隔', () => {
      renderHook(() => useSectorHeatmapData())

      const callArgs = (useSWR as jest.Mock).mock.calls[0]
      const config = callArgs[2]

      expect(config.dedupingInterval).toBe(1000)
    })
  })

  describe('参数测试', () => {
    it('应该使用默认查询键', () => {
      renderHook(() => useSectorHeatmapData())

      const callArgs = (useSWR as jest.Mock).mock.calls[0]
      const queryKey = callArgs[0]

      expect(queryKey).toBe('/api/v1/heatmap')
    })

    it('应该使用带 sectorType 的查询键', () => {
      renderHook(() => useSectorHeatmapData({ sectorType: 'industry' }))

      const callArgs = (useSWR as jest.Mock).mock.calls[0]
      const queryKey = callArgs[0]

      expect(queryKey).toBe('/api/v1/heatmap?sector_type=industry')
    })

    it('应该支持 concept 类型', () => {
      renderHook(() => useSectorHeatmapData({ sectorType: 'concept' }))

      const callArgs = (useSWR as jest.Mock).mock.calls[0]
      const queryKey = callArgs[0]

      expect(queryKey).toBe('/api/v1/heatmap?sector_type=concept')
    })
  })

  describe('启用/禁用测试', () => {
    it('enabled=false 时应该禁用请求', () => {
      renderHook(() => useSectorHeatmapData({ enabled: false }))

      const callArgs = (useSWR as jest.Mock).mock.calls[0]

      // SWR 传入 null 作为 key 时禁用请求
      expect(callArgs[0]).toBeNull()
    })

    it('enabled=true 时应该启用请求', () => {
      renderHook(() => useSectorHeatmapData({ enabled: true }))

      const callArgs = (useSWR as jest.Mock).mock.calls[0]

      expect(callArgs[0]).toBeTruthy()
    })
  })

  describe('数据转换测试', () => {
    it('应该正确提取 sectors 数组', () => {
      ;(useSWR as jest.Mock).mockReturnValue({
        data: mockHeatmapResponse,
        error: undefined,
        isLoading: false,
        mutate: jest.fn(),
      })

      const { result } = renderHook(() => useSectorHeatmapData())

      expect(result.current.sectors).toEqual(mockSectors)
      expect(result.current.sectors).toHaveLength(3)
    })

    it('应该处理空数据响应', () => {
      ;(useSWR as jest.Mock).mockReturnValue({
        data: { success: true, data: { sectors: [], timestamp: '2025-12-24T10:30:00Z' } },
        error: undefined,
        isLoading: false,
        mutate: jest.fn(),
      })

      const { result } = renderHook(() => useSectorHeatmapData())

      expect(result.current.sectors).toEqual([])
    })

    it('应该处理 undefined data', () => {
      ;(useSWR as jest.Mock).mockReturnValue({
        data: undefined,
        error: undefined,
        isLoading: false,
        mutate: jest.fn(),
      })

      const { result } = renderHook(() => useSectorHeatmapData())

      expect(result.current.sectors).toEqual([])
      expect(result.current.timestamp).toBeUndefined()
    })
  })

  describe('mutate 函数测试', () => {
    it('应该返回 mutate 函数', () => {
      const mockMutate = jest.fn()

      ;(useSWR as jest.Mock).mockReturnValue({
        data: mockHeatmapResponse,
        error: undefined,
        isLoading: false,
        mutate: mockMutate,
      })

      const { result } = renderHook(() => useSectorHeatmapData())

      expect(result.current.mutate).toBe(mockMutate)
    })

    it('应该可以手动触发重新验证', () => {
      const mockMutate = jest.fn()

      ;(useSWR as jest.Mock).mockReturnValue({
        data: mockHeatmapResponse,
        error: undefined,
        isLoading: false,
        mutate: mockMutate,
      })

      const { result } = renderHook(() => useSectorHeatmapData())

      result.current.mutate()

      expect(mockMutate).toHaveBeenCalled()
    })
  })
})
