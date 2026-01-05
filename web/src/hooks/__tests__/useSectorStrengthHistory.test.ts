/**
 * useSectorStrengthHistory Hook 测试
 */

import { renderHook, waitFor } from '@testing-library/react'
import { useSectorStrengthHistory } from '../useSectorStrengthHistory'
import { sectorsApi } from '@/lib/api'

// Mock sectorsApi
jest.mock('@/lib/api', () => ({
  sectorsApi: {
    getSectorStrengthHistory: jest.fn(),
  },
}))

describe('useSectorStrengthHistory', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('应该成功获取板块强度历史数据', async () => {
    const mockData = {
      sector_id: '1',
      sector_name: '测试板块',
      data: [
        {
          date: '2024-12-01',
          score: 65.5,
          current_price: 1234.56,
        },
        {
          date: '2024-12-02',
          score: 67.2,
          current_price: 1240.0,
        },
      ],
    }

    ;(sectorsApi.getSectorStrengthHistory as jest.Mock).mockResolvedValue({
      data: mockData,
    })

    const { result } = renderHook(() =>
      useSectorStrengthHistory({
        sectorId: 1,
        timeRange: '2m',
      })
    )

    // 初始加载状态
    expect(result.current.isLoading).toBe(true)

    // 等待数据加载完成
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
      expect(result.current.data).toEqual(mockData)
      expect(result.current.isError).toBe(false)
    })

    // 验证 API 调用
    expect(sectorsApi.getSectorStrengthHistory).toHaveBeenCalledWith(1, {
      start_date: expect.any(String),
      end_date: expect.any(String),
    })
  })

  it('应该使用默认时间范围（2个月）', async () => {
    const mockData = {
      sector_id: '1',
      sector_name: '测试板块',
      data: [],
    }

    ;(sectorsApi.getSectorStrengthHistory as jest.Mock).mockResolvedValue({
      data: mockData,
    })

    renderHook(() =>
      useSectorStrengthHistory({
        sectorId: 1,
      })
    )

    await waitFor(() => {
      expect(sectorsApi.getSectorStrengthHistory).toHaveBeenCalled()
    })

    const callArgs = (sectorsApi.getSectorStrengthHistory as jest.Mock).mock.calls[0]
    expect(callArgs[0]).toBe(1)
    expect(callArgs[1]).toHaveProperty('start_date')
    expect(callArgs[1]).toHaveProperty('end_date')
  })

  it('应该处理 API 错误', async () => {
    const mockError = new Error('Network error')

    ;(sectorsApi.getSectorStrengthHistory as jest.Mock).mockRejectedValue(
      mockError
    )

    const { result } = renderHook(() =>
      useSectorStrengthHistory({
        sectorId: 1,
      })
    )

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
      expect(result.current.isError).toBe(true)
      expect(result.current.error).toBe(mockError)
    })
  })

  it('应该支持自定义时间范围', async () => {
    const mockData = {
      sector_id: '1',
      sector_name: '测试板块',
      data: [],
    }

    ;(sectorsApi.getSectorStrengthHistory as jest.Mock).mockResolvedValue({
      data: mockData,
    })

    renderHook(() =>
      useSectorStrengthHistory({
        sectorId: 1,
        timeRange: '1m',
      })
    )

    await waitFor(() => {
      expect(sectorsApi.getSectorStrengthHistory).toHaveBeenCalled()
    })
  })

  it('应该支持禁用自动查询', async () => {
    renderHook(() =>
      useSectorStrengthHistory({
        sectorId: 1,
        enabled: false,
      })
    )

    // 不应该调用 API
    expect(sectorsApi.getSectorStrengthHistory).not.toHaveBeenCalled()
  })

  it('应该支持 mutate 手动刷新', async () => {
    const mockData = {
      sector_id: '1',
      sector_name: '测试板块',
      data: [],
    }

    ;(sectorsApi.getSectorStrengthHistory as jest.Mock).mockResolvedValue({
      data: mockData,
    })

    const { result } = renderHook(() =>
      useSectorStrengthHistory({
        sectorId: 1,
      })
    )

    await waitFor(() => {
      expect(result.current.data).toEqual(mockData)
    })

    // 清除 mock 调用次数
    jest.clearAllMocks()

    // 手动刷新
    result.current.mutate()

    await waitFor(() => {
      expect(sectorsApi.getSectorStrengthHistory).toHaveBeenCalled()
    })
  })

  it('应该使用自定义日期参数', async () => {
    const mockData = {
      sector_id: '1',
      sector_name: '测试板块',
      data: [],
    }

    ;(sectorsApi.getSectorStrengthHistory as jest.Mock).mockResolvedValue({
      data: mockData,
    })

    const startDate = '2024-01-01'
    const endDate = '2024-12-31'

    renderHook(() =>
      useSectorStrengthHistory({
        sectorId: 1,
        startDate,
        endDate,
      })
    )

    await waitFor(() => {
      expect(sectorsApi.getSectorStrengthHistory).toHaveBeenCalledWith(1, {
        start_date: startDate,
        end_date: endDate,
      })
    })
  })
})
