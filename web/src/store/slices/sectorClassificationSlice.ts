/**
 * 板块强弱分类 Redux Slice
 *
 * 使用 Redux Toolkit 管理分类数据状态
 * 包含异步数据获取和错误处理
 */

import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit'
import type { SectorClassification } from '@/types/sector-classification'
import type { RootState } from '@/store/index'
import { sectorClassificationApi } from '@/lib/sectorClassificationApi'

/**
 * 板块分类状态接口
 */
export interface SectorClassificationState {
  /** 分类数据列表 */
  classifications: SectorClassification[]
  /** 加载状态 */
  loading: boolean
  /** 错误信息 */
  error: string | null
  /** 最后获取时间戳 */
  lastFetch: number | null
}

/**
 * 初始状态
 */
const initialState: SectorClassificationState = {
  classifications: [],
  loading: false,
  error: null,
  lastFetch: null,
}

/**
 * 异步 Thunk: 获取分类数据
 *
 * @description
 * 调用 API 获取最新的板块分类数据
 * - pending: 设置 loading = true
 * - fulfilled: 存储数据，设置 loading = false
 * - rejected: 存储错误，设置 loading = false
 */
export const fetchClassifications = createAsyncThunk(
  'sectorClassification/fetchAll',
  async (_, { rejectWithValue }) => {
    try {
      const response = await sectorClassificationApi.getAllClassifications()
      return response.data
    } catch (error: any) {
      // 提取错误消息
      const errorMessage = error?.message || '获取分类数据失败，请重试'
      return rejectWithValue(errorMessage)
    }
  }
)

/**
 * 板块分类 Slice
 */
const sectorClassificationSlice = createSlice({
  name: 'sectorClassification',
  initialState,
  reducers: {
    /**
     * 清除错误信息
     */
    clearError: (state) => {
      state.error = null
    },
    /**
     * 重置状态
     */
    reset: () => initialState,
  },
  extraReducers: (builder) => {
    builder
      // 获取分类数据 - 进行中
      .addCase(fetchClassifications.pending, (state) => {
        state.loading = true
        state.error = null
      })
      // 获取分类数据 - 成功
      .addCase(fetchClassifications.fulfilled, (state, action: PayloadAction<SectorClassification[]>) => {
        state.loading = false
        state.classifications = action.payload
        state.lastFetch = Date.now()
        state.error = null
      })
      // 获取分类数据 - 失败
      .addCase(fetchClassifications.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload as string || '获取分类数据失败，请重试'
      })
  },
})

// 导出 actions
export const { clearError, reset } = sectorClassificationSlice.actions

// 导出 selectors
/**
 * 选择分类数据
 */
export const selectClassifications = (state: RootState) =>
  state.sectorClassification.classifications

/**
 * 选择加载状态
 */
export const selectLoading = (state: RootState) =>
  state.sectorClassification.loading

/**
 * 选择错误信息
 */
export const selectError = (state: RootState) =>
  state.sectorClassification.error

/**
 * 选择最后获取时间
 */
export const selectLastFetch = (state: RootState) =>
  state.sectorClassification.lastFetch

/**
 * 选择是否需要刷新（距离上次获取超过 5 分钟）
 */
export const selectShouldRefresh = (state: RootState) => {
  if (!state.sectorClassification.lastFetch) return true
  const fiveMinutes = 5 * 60 * 1000
  return Date.now() - state.sectorClassification.lastFetch > fiveMinutes
}

// 导出 reducer
export default sectorClassificationSlice.reducer
