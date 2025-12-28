import { configureStore } from '@reduxjs/toolkit'
import stocksReducer from './slices/stocks'
import sectorsReducer from './slices/sectors'
import strengthReducer from './slices/strength'
import uiReducer from './slices/ui'

export const store = configureStore({
  reducer: {
    stocks: stocksReducer,
    sectors: sectorsReducer,
    strength: strengthReducer,
    ui: uiReducer,
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