import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit'
import { stocksApi } from '@/lib/api'
import { Stock, StockFilter } from '@/types'

interface StocksState {
  stocks: Stock[]
  loading: boolean
  error: string | null
  filter: StockFilter
  selectedStock: Stock | null
  pagination: {
    page: number
    pageSize: number
    total: number
  }
}

const initialState: StocksState = {
  stocks: [],
  loading: false,
  error: null,
  filter: {
    sector: '',
    search: '',
    sortBy: 'change_rate',
    sortOrder: 'desc'
  },
  selectedStock: null,
  pagination: {
    page: 1,
    pageSize: 20,
    total: 0
  }
}

// 异步thunks
export const fetchStocks = createAsyncThunk(
  'stocks/fetchStocks',
  async (params?: { page?: number; pageSize?: number; filter?: StockFilter }) => {
    const { page, pageSize } = params || {}
    const skip = page && pageSize ? (page - 1) * pageSize : undefined
    const limit = pageSize
    const response = await stocksApi.getStocks({ skip, limit })
    return response
  }
)

export const fetchStockDetail = createAsyncThunk(
  'stocks/fetchStockDetail',
  async (code: string) => {
    const response = await stocksApi.getStock(code)
    return response
  }
)

const stocksSlice = createSlice({
  name: 'stocks',
  initialState,
  reducers: {
    setFilter: (state, action: PayloadAction<Partial<StockFilter>>) => {
      state.filter = { ...state.filter, ...action.payload }
    },
    clearFilter: (state) => {
      state.filter = {
        sector: '',
        search: '',
        sortBy: 'change_rate',
        sortOrder: 'desc'
      }
    },
    setSelectedStock: (state, action: PayloadAction<Stock | null>) => {
      state.selectedStock = action.payload
    },
    setPagination: (state, action: PayloadAction<Partial<StocksState['pagination']>>) => {
      state.pagination = { ...state.pagination, ...action.payload }
    },
    clearError: (state) => {
      state.error = null
    }
  },
  extraReducers: (builder) => {
    builder
      // fetchStocks
      .addCase(fetchStocks.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchStocks.fulfilled, (state, action) => {
        state.loading = false
        state.stocks = action.payload.data || []
        // Note: API response doesn't include total, keeping pagination as is
      })
      .addCase(fetchStocks.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message || '获取股票列表失败'
      })
      // fetchStockDetail
      .addCase(fetchStockDetail.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchStockDetail.fulfilled, (state, action) => {
        state.loading = false
        state.selectedStock = action.payload.data || null
      })
      .addCase(fetchStockDetail.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message || '获取股票详情失败'
      })
  }
})

export const { setFilter, clearFilter, setSelectedStock, setPagination, clearError } = stocksSlice.actions
export default stocksSlice.reducer