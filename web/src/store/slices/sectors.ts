import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit'
import { sectorsApi } from '@/lib/api'
import { Sector } from '@/types'

interface SectorsState {
  sectors: Sector[]
  loading: boolean
  error: string | null
  selectedSector: Sector | null
}

const initialState: SectorsState = {
  sectors: [],
  loading: false,
  error: null,
  selectedSector: null
}

// 异步thunks
export const fetchSectors = createAsyncThunk(
  'sectors/fetchSectors',
  async () => {
    const response = await sectorsApi.getSectors()
    return response
  }
)

export const fetchSectorDetail = createAsyncThunk(
  'sectors/fetchSectorDetail',
  async (code: string) => {
    const response = await sectorsApi.getSector(parseInt(code))
    return response
  }
)

export const fetchSectorStocks = createAsyncThunk(
  'sectors/fetchSectorStocks',
  async (code: string) => {
    const response = await sectorsApi.getSectorStocks(parseInt(code))
    return response
  }
)

const sectorsSlice = createSlice({
  name: 'sectors',
  initialState,
  reducers: {
    setSelectedSector: (state, action: PayloadAction<Sector | null>) => {
      state.selectedSector = action.payload
    },
    clearError: (state) => {
      state.error = null
    }
  },
  extraReducers: (builder) => {
    builder
      // fetchSectors
      .addCase(fetchSectors.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchSectors.fulfilled, (state, action) => {
        state.loading = false
        // 后端返回分页数据: { success: true, data: { items: [...], total, page, page_size } }
        const data = action.payload.data as any
        state.sectors = data?.items || []
      })
      .addCase(fetchSectors.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message || '获取板块列表失败'
      })
      // fetchSectorDetail
      .addCase(fetchSectorDetail.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchSectorDetail.fulfilled, (state, action) => {
        state.loading = false
        state.selectedSector = action.payload.data || null
      })
      .addCase(fetchSectorDetail.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message || '获取板块详情失败'
      })
  }
})

export const { setSelectedSector, clearError } = sectorsSlice.actions
export default sectorsSlice.reducer