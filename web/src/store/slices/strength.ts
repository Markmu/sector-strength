import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import { strengthApi } from '@/lib/api'
import { StrengthScore, StrengthFilter } from '@/types'

interface StrengthState {
  scores: StrengthScore[]
  loading: boolean
  error: string | null
  filter: StrengthFilter
  realTimeData: Record<string, StrengthScore>
}

const initialState: StrengthState = {
  scores: [],
  loading: false,
  error: null,
  filter: {
    period: '20d',
  },
  realTimeData: {}
}

// 异步thunks
export const fetchStrengthScores = createAsyncThunk(
  'strength/fetchStrengthScores',
  async (params?: { filter?: StrengthFilter }) => {
    const response = await strengthApi.getStrength(params?.filter)
    return response
  }
)

export const fetchRealtimeStrength = createAsyncThunk(
  'strength/fetchRealtimeStrength',
  async () => {
    const response = await strengthApi.getLatestStrength()
    return response
  }
)

const strengthSlice = createSlice({
  name: 'strength',
  initialState,
  reducers: {
    setFilter: (state, action) => {
      state.filter = { ...state.filter, ...action.payload }
    },
    updateRealtimeScore: (state, action) => {
      const { sector, score } = action.payload
      state.realTimeData[sector] = score
    },
    clearError: (state) => {
      state.error = null
    }
  },
  extraReducers: (builder) => {
    builder
      // fetchStrengthScores
      .addCase(fetchStrengthScores.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchStrengthScores.fulfilled, (state, action) => {
        state.loading = false
        state.scores = action.payload.data || []
      })
      .addCase(fetchStrengthScores.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message || '获取强度数据失败'
      })
      // fetchRealtimeStrength
      .addCase(fetchRealtimeStrength.pending, (state) => {
        state.error = null
      })
      .addCase(fetchRealtimeStrength.fulfilled, (state, action) => {
        state.realTimeData = (action.payload.data || []).reduce((acc, score) => {
          const key = score.sector_id || score.stock_id || 'unknown'
          acc[key] = score
          return acc
        }, {} as Record<string, StrengthScore>)
      })
      .addCase(fetchRealtimeStrength.rejected, (state, action) => {
        state.error = action.error.message || '获取实时强度失败'
      })
  }
})

export const { setFilter, updateRealtimeScore, clearError } = strengthSlice.actions
export default strengthSlice.reducer