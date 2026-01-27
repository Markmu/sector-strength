import { configureStore } from '@reduxjs/toolkit'
import { useDispatch, useSelector } from 'react-redux'
import stocksReducer from './slices/stocks'
import sectorsReducer from './slices/sectors'
import strengthReducer from './slices/strength'
import uiReducer from './slices/ui'
import sectorClassificationReducer from './slices/sectorClassificationSlice'

export const store = configureStore({
  reducer: {
    stocks: stocksReducer,
    sectors: sectorsReducer,
    strength: strengthReducer,
    ui: uiReducer,
    sectorClassification: sectorClassificationReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['persist/PERSIST'],
      },
    }),
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch

// 导出类型化的 hooks
export const useAppDispatch = () => useDispatch<AppDispatch>()
export const useAppSelector: <T>(selector: (state: RootState) => T) => T = useSelector

// 重新导出 sectorClassification slice 的内容
export {
  fetchClassifications,
  clearError,
  reset,
  selectClassifications,
  selectLoading,
  selectError,
  selectLastFetch,
  selectShouldRefresh,
} from './slices/sectorClassificationSlice'