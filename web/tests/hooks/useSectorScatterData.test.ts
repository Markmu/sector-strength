/**
 * useSectorScatterData Hook 测试
 */

import { renderHook } from '@testing-library/react'
import { useSectorScatterData } from '../useSectorScatterData'
import type { SectorScatterResponse } from '@/types/scatter'

// Mock fetch
global.fetch = jest.fn()

// Mock SWR
jest.mock('swr', () => ({
  __esModule: true,
  default: jest.fn(),
}))

const mockUseSWR = require('swr').default

describe('useSectorScatterData', () => {
  const mockData: SectorScatterResponse = {
    scatter_data: {
      industry: [
        {
          symbol: 'IND001',
          name: '新能源',
          sector_type: 'industry',
          x: 75.5,
          y: 82.3,
          size: 35.0,
          color_value: 88.0,
          data_completeness: {
            has_strong_ratio: true,
            has_long_term: true,
            completeness_percent: 100,
          },
          full_data: {
            score: 80.0,
            short_term_score: 75.5,
            medium_term_score: 82.3,
            long_term_score: 88.0,
            strong_stock_ratio: 0.7,
            strength_grade: 'A',
          },
        },
      ],
      concept: [],
    },
    total_count: 1,
    returned_count: 1,
    filters_applied: {
      sector_type: null,
      grade_range: null,
      axes: ['short', 'medium'],
      pagination: {
        offset: 0,
        limit: 200,
      },
    },
    cache_status: 'miss',
  }

  beforeEach(() => {
    jest.clearAllMocks()
    // 默认 mock SWR 返回数据
    mockUseSWR.mockReturnValue({
      data: mockData,
      error: null,
      isLoading: false,
      isValidating: false,
      mutate: jest.fn(),
    })
  })

  it('使用默认参数正确调用 SWR', () => {
    renderHook(() => useSectorScatterData())

    expect(mockUseSWR).toHaveBeenCalled()
    const callArgs = mockUseSWR.mock.calls[0]

    // 验证 URL 参数
    const url = callArgs[0]
    expect(url).toContain('x_axis=short')
    expect(url).toContain('y_axis=medium')
    expect(url).toContain('offset=0')
    expect(url).toContain('limit=200')
  })

  it('使用自定义参数正确调用 SWR', () => {
    renderHook(() => useSectorScatterData({
      xAxis: 'long',
      yAxis: 'composite',
      sectorType: 'industry',
      minGrade: 'A',
      maxGrade: 'S',
      offset: 10,
      limit: 100,
    }))

    expect(mockUseSWR).toHaveBeenCalled()
    const url = mockUseSWR.mock.calls[0][0]

    expect(url).toContain('x_axis=long')
    expect(url).toContain('y_axis=composite')
    expect(url).toContain('sector_type=industry')
    expect(url).toContain('min_grade=A')
    expect(url).toContain('max_grade=S')
    expect(url).toContain('offset=10')
    expect(url).toContain('limit=100')
  })

  it('正确返回数据', () => {
    const { result } = renderHook(() => useSectorScatterData())

    expect(result.current.data).toEqual(mockData)
    expect(result.current.isLoading).toBe(false)
    expect(result.current.isError).toBe(false)
  })

  it('正确处理加载状态', () => {
    mockUseSWR.mockReturnValue({
      data: null,
      error: null,
      isLoading: true,
      isValidating: false,
      mutate: jest.fn(),
    })

    const { result } = renderHook(() => useSectorScatterData())

    expect(result.current.isLoading).toBe(true)
    expect(result.current.data).toBeNull()
  })

  it('正确处理错误状态', () => {
    const mockError = new Error('API 请求失败')
    mockUseSWR.mockReturnValue({
      data: null,
      error: mockError,
      isLoading: false,
      isValidating: false,
      mutate: jest.fn(),
    })

    const { result } = renderHook(() => useSectorScatterData())

    expect(result.current.isError).toBe(true)
    expect(result.current.error).toEqual(mockError)
  })

  it('正确处理 validating 状态', () => {
    mockUseSWR.mockReturnValue({
      data: mockData,
      error: null,
      isLoading: false,
      isValidating: true,
      mutate: jest.fn(),
    })

    const { result } = renderHook(() => useSectorScatterData())

    expect(result.current.isValidating).toBe(true)
    expect(result.current.data).toEqual(mockData)
  })

  it('返回正确的 mutate 函数', () => {
    const mockMutate = jest.fn()
    mockUseSWR.mockReturnValue({
      data: mockData,
      error: null,
      isLoading: false,
      isValidating: false,
      mutate: mockMutate,
    })

    const { result } = renderHook(() => useSectorScatterData())

    expect(result.current.mutate).toEqual(mockMutate)
  })

  it('enabled=false 时不调用 SWR', () => {
    renderHook(() => useSectorScatterData({ enabled: false }))

    expect(mockUseSWR).toHaveBeenCalledWith(
      null,  // enabled=false 时传入 null
      expect.anything(),
      expect.anything()
    )
  })

  it('正确构建 calcDate 参数', () => {
    renderHook(() => useSectorScatterData({
      calcDate: '2024-01-15',
    }))

    const url = mockUseSWR.mock.calls[0][0]
    expect(url).toContain('calc_date=2024-01-15')
  })
})
