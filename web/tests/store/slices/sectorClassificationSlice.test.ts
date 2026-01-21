/**
 * 板块分类 Slice 测试
 *
 * 测试 Redux reducer 和 asyncThunk 行为
 */

import reducer, {
  fetchClassifications,
  clearError,
  reset,
  initialState,
  selectClassifications,
  selectLoading,
  selectError,
  selectLastFetch,
  selectShouldRefresh,
  type SectorClassificationState,
} from '@/store/slices/sectorClassificationSlice'
import type { SectorClassification } from '@/types/sector-classification'

// Mock 数据
const mockClassifications: SectorClassification[] = [
  {
    id: '1',
    sector_id: 'sector-1',
    sector_name: '新能源',
    classification_date: '2026-01-22',
    classification_level: 9,
    state: '反弹',
    current_price: 1234.56,
    change_percent: 2.5,
    created_at: '2026-01-22T10:00:00Z',
  },
  {
    id: '2',
    sector_id: 'sector-2',
    sector_name: '半导体',
    classification_date: '2026-01-22',
    classification_level: 5,
    state: '调整',
    current_price: 987.65,
    change_percent: -1.2,
    created_at: '2026-01-22T10:00:00Z',
  },
]

describe('sectorClassificationSlice', () => {
  describe('初始状态', () => {
    it('应返回正确的初始状态', () => {
      expect(reducer(undefined, { type: 'unknown' })).toEqual(initialState)
    })

    it('初始状态应为空数组、未加载、无错误', () => {
      const state = reducer(undefined, { type: 'unknown' })
      expect(state.classifications).toEqual([])
      expect(state.loading).toBe(false)
      expect(state.error).toBe(null)
      expect(state.lastFetch).toBe(null)
    })
  })

  describe('Actions', () => {
    it('clearError 应清除错误信息', () => {
      const errorState: SectorClassificationState = {
        ...initialState,
        error: '网络错误',
      }
      const newState = reducer(errorState, clearError())
      expect(newState.error).toBe(null)
    })

    it('reset 应重置为初始状态', () => {
      const populatedState: SectorClassificationState = {
        classifications: mockClassifications,
        loading: false,
        error: null,
        lastFetch: Date.now(),
      }
      const newState = reducer(populatedState, reset())
      expect(newState).toEqual(initialState)
    })
  })

  describe('fetchClassifications asyncThunk', () => {
    it('pending 应设置 loading 为 true 并清除错误', () => {
      const action = { type: fetchClassifications.pending.type }
      const state = reducer(initialState, action)

      expect(state.loading).toBe(true)
      expect(state.error).toBe(null)
      expect(state.classifications).toEqual([])
    })

    it('fulfilled 应存储数据并设置 loading 为 false', () => {
      const action = {
        type: fetchClassifications.fulfilled.type,
        payload: mockClassifications,
      }
      const state = reducer(initialState, action)

      expect(state.loading).toBe(false)
      expect(state.classifications).toEqual(mockClassifications)
      expect(state.error).toBe(null)
      expect(state.lastFetch).toBeDefined()
      expect(state.lastFetch).toBeGreaterThan(0)
    })

    it('rejected 应存储错误并设置 loading 为 false', () => {
      const errorMessage = '网络连接失败'
      const action = {
        type: fetchClassifications.rejected.type,
        payload: errorMessage,
      }
      const state = reducer(initialState, action)

      expect(state.loading).toBe(false)
      expect(state.error).toBe(errorMessage)
      expect(state.classifications).toEqual([])
      expect(state.lastFetch).toBe(null)
    })

    it('rejected 无 payload 时应使用默认错误消息', () => {
      const action = {
        type: fetchClassifications.rejected.type,
      }
      const state = reducer(initialState, action)

      expect(state.loading).toBe(false)
      expect(state.error).toBe('获取分类数据失败，请重试')
    })
  })

  describe('Selectors', () => {
    const mockState: SectorClassificationState = {
      classifications: mockClassifications,
      loading: false,
      error: '测试错误',
      lastFetch: 1705900800000, // 2024-01-22 00:00:00 UTC
    }

    it('selectClassifications 应返回分类数据', () => {
      const result = selectClassifications({
        sectorClassification: mockState,
      } as any)
      expect(result).toEqual(mockClassifications)
    })

    it('selectLoading 应返回加载状态', () => {
      const result = selectLoading({
        sectorClassification: mockState,
      } as any)
      expect(result).toBe(false)
    })

    it('selectError 应返回错误信息', () => {
      const result = selectError({
        sectorClassification: mockState,
      } as any)
      expect(result).toBe('测试错误')
    })

    it('selectLastFetch 应返回最后获取时间', () => {
      const result = selectLastFetch({
        sectorClassification: mockState,
      } as any)
      expect(result).toBe(1705900800000)
    })

    it('selectShouldRefresh 无 lastFetch 时应返回 true', () => {
      const result = selectShouldRefresh({
        sectorClassification: {
          ...initialState,
          lastFetch: null,
        },
      } as any)
      expect(result).toBe(true)
    })

    it('selectShouldRefresh 超过 5 分钟时应返回 true', () => {
      const oldTime = Date.now() - 6 * 60 * 1000 // 6 分钟前
      const result = selectShouldRefresh({
        sectorClassification: {
          ...initialState,
          lastFetch: oldTime,
        },
      } as any)
      expect(result).toBe(true)
    })

    it('selectShouldRefresh 未超过 5 分钟时应返回 false', () => {
      const recentTime = Date.now() - 2 * 60 * 1000 // 2 分钟前
      const result = selectShouldRefresh({
        sectorClassification: {
          ...initialState,
          lastFetch: recentTime,
        },
      } as any)
      expect(result).toBe(false)
    })
  })
})
