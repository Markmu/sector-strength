/**
 * useSectorMAHistory Hook 测试
 */

import { renderHook, waitFor } from '@testing-library/react'
import { useSectorMAHistory } from '../useSectorMAHistory'
import { sectorsApi } from '@/lib/api'

// Mock sectorsApi
jest.mock('@/lib/api', () => ({
  sectorsApi: {
    getSectorMAHistory: jest.fn(),
  },
}))

describe('useSectorMAHistory', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('应该成功获取板块均线历史数据', async () => {
    const mockData = {
      sector_id: '1',
      sector_name: '测试板块',
      data: [
        {
          date: '2024-12-01',
          current_price: 1234.56,
          ma5: 1220.0,
          ma10: 1215.0,
          ma20: 1210.0,
          ma30: 1205.0,
          ma60: 1200.0,
          ma90: null,
          ma120: null,
          ma240: null,
        },
        {
          date: '2024-12-02',
          current_price: 1240.0,
          ma5: 1225.0,
          ma10: 1218.0,
          ma20: 1212.0,
          ma30: 1208.0,
          ma60: 1202.0,
          ma90: null,
          ma120: null,
          ma240: null,
        },
      ],
    }

    ;(sectorsApi.getSectorMAHistory as jest.Mock).mockResolvedValue({
      data: mockData,
    })

    const { result } = renderHook(() =>
      useSectorMAHistory({
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
    expect(sectorsApi.getSectorMAHistory).toHaveBeenCalledWith(1, {
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

    ;(sectorsApi.getSectorMAHistory as jest.Mock).mockResolvedValue({
      data: mockData,
    })

    renderHook(() =>
      useSectorMAHistory({
        sectorId: 1,
      })
    )

    await waitFor(() => {
      expect(sectorsApi.getSectorMAHistory).toHaveBeenCalled()
    })

    const callArgs = (sectorsApi.getSectorMAHistory as jest.Mock).mock.calls[0]
    expect(callArgs[0]).toBe(1)
    expect(callArgs[1]).toHaveProperty('start_date')
    expect(callArgs[1]).toHaveProperty('end_date')
  })

  it('应该处理 API 错误', async () => {
    const mockError = new Error('Network error')

    ;(sectorsApi.getSectorMAHistory as jest.Mock).mockRejectedValue(mockError)

    const { result } = renderHook(() =>
      useSectorMAHistory({
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

    ;(sectorsApi.getSectorMAHistory as jest.Mock).mockResolvedValue({
      data: mockData,
    })

    renderHook(() =>
      useSectorMAHistory({
        sectorId: 1,
        timeRange: '6m',
      })
    )

    await waitFor(() => {
      expect(sectorsApi.getSectorMAHistory).toHaveBeenCalled()
    })
  })

  it('应该支持禁用自动查询', async () => {
    renderHook(() =>
      useSectorMAHistory({
        sectorId: 1,
        enabled: false,
      })
    )

    // 不应该调用 API
    expect(sectorsApi.getSectorMAHistory).not.toHaveBeenCalled()
  })

  it('应该支持 mutate 手动刷新', async () => {
    const mockData = {
      sector_id: '1',
      sector_name: '测试板块',
      data: [],
    }

    ;(sectorsApi.getSectorMAHistory as jest.Mock).mockResolvedValue({
      data: mockData,
    })

    const { result } = renderHook(() =>
      useSectorMAHistory({
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
      expect(sectorsApi.getSectorMAHistory).toHaveBeenCalled()
    })
  })

  it('应该使用自定义日期参数', async () => {
    const mockData = {
      sector_id: '1',
      sector_name: '测试板块',
      data: [],
    }

    ;(sectorsApi.getSectorMAHistory as jest.Mock).mockResolvedValue({
      data: mockData,
    })

    const startDate = '2024-01-01'
    const endDate = '2024-12-31'

    renderHook(() =>
      useSectorMAHistory({
        sectorId: 1,
        startDate,
        endDate,
      })
    )

    await waitFor(() => {
      expect(sectorsApi.getSectorMAHistory).toHaveBeenCalledWith(1, {
        start_date: startDate,
        end_date: endDate,
      })
    })
  })

  it('应该正确处理长期均线的 null 值', async () => {
    const mockData = {
      sector_id: '1',
      sector_name: '测试板块',
      data: [
        {
          date: '2024-12-01',
          current_price: 1234.56,
          ma5: 1220.0,
          ma10: 1215.0,
          ma20: 1210.0,
          ma30: 1205.0,
          ma60: 1200.0,
          ma90: null,
          ma120: null,
          ma240: null,
        },
      ],
    }

    ;(sectorsApi.getSectorMAHistory as jest.Mock).mockResolvedValue({
      data: mockData,
    })

    const { result } = renderHook(() =>
      useSectorMAHistory({
        sectorId: 1,
      })
    )

    await waitFor(() => {
      expect(result.current.data).toBeDefined()
    })

    expect(result.current.data?.data[0].ma90).toBeNull()
    expect(result.current.data?.data[0].ma120).toBeNull()
    expect(result.current.data?.data[0].ma240).toBeNull()
  })
})
