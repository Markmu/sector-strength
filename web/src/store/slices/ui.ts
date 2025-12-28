import { createSlice, PayloadAction } from '@reduxjs/toolkit'

interface UIState {
  theme: 'light' | 'dark'
  sidebarCollapsed: boolean
  notifications: Notification[]
  modals: {
    stockDetail: {
      open: boolean
      stockCode?: string
    }
    sectorDetail: {
      open: boolean
      sectorCode?: string
    }
  }
  loading: {
    global: boolean
    [key: string]: boolean
  }
}

interface Notification {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message: string
  timestamp: number
  duration?: number
}

const initialState: UIState = {
  theme: 'light',
  sidebarCollapsed: false,
  notifications: [],
  modals: {
    stockDetail: {
      open: false
    },
    sectorDetail: {
      open: false
    }
  },
  loading: {
    global: false
  }
}

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    setTheme: (state, action: PayloadAction<'light' | 'dark'>) => {
      state.theme = action.payload
    },
    toggleSidebar: (state) => {
      state.sidebarCollapsed = !state.sidebarCollapsed
    },
    setSidebarCollapsed: (state, action: PayloadAction<boolean>) => {
      state.sidebarCollapsed = action.payload
    },
    addNotification: (state, action: PayloadAction<Omit<Notification, 'id' | 'timestamp'>>) => {
      const notification: Notification = {
        ...action.payload,
        id: Date.now().toString(),
        timestamp: Date.now()
      }
      state.notifications.push(notification)
    },
    removeNotification: (state, action: PayloadAction<string>) => {
      state.notifications = state.notifications.filter(n => n.id !== action.payload)
    },
    clearNotifications: (state) => {
      state.notifications = []
    },
    openStockDetailModal: (state, action: PayloadAction<string>) => {
      state.modals.stockDetail = {
        open: true,
        stockCode: action.payload
      }
    },
    closeStockDetailModal: (state) => {
      state.modals.stockDetail.open = false
      delete state.modals.stockDetail.stockCode
    },
    openSectorDetailModal: (state, action: PayloadAction<string>) => {
      state.modals.sectorDetail = {
        open: true,
        sectorCode: action.payload
      }
    },
    closeSectorDetailModal: (state) => {
      state.modals.sectorDetail.open = false
      delete state.modals.sectorDetail.sectorCode
    },
    setLoading: (state, action: PayloadAction<{ key: string; loading: boolean }>) => {
      state.loading[action.payload.key] = action.payload.loading
      if (action.payload.key === 'global') {
        state.loading.global = action.payload.loading
      }
    },
  }
})

export const {
  setTheme,
  toggleSidebar,
  setSidebarCollapsed,
  addNotification,
  removeNotification,
  clearNotifications,
  openStockDetailModal,
  closeStockDetailModal,
  openSectorDetailModal,
  closeSectorDetailModal,
  setLoading
} = uiSlice.actions

export default uiSlice.reducer