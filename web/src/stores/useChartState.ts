import { create } from 'zustand'
import type { TimeRangeOption, MAPeriod } from '@/types'

interface ChartState {
  // 时间范围
  timeRange: TimeRangeOption

  // 自定义日期范围 (当 timeRange 为 'custom' 时使用)
  customStartDate: string | null
  customEndDate: string | null

  // 均线显示状态
  visibleMAs: Record<MAPeriod, boolean>

  // 操作方法
  setTimeRange: (timeRange: TimeRangeOption) => void
  setCustomDateRange: (startDate: string | null, endDate: string | null) => void
  toggleMA: (maPeriod: MAPeriod) => void
  setMAVisibility: (maPeriod: MAPeriod, visible: boolean) => void
  resetMAs: () => void
}

// 默认均线显示状态
const DEFAULT_MA_VISIBILITY: Record<MAPeriod, boolean> = {
  ma5: true,
  ma10: true,
  ma20: true,
  ma30: true,
  ma60: true,
  ma90: false,
  ma120: false,
  ma240: false,
}

export const useChartState = create<ChartState>((set) => ({
  // 初始状态
  timeRange: '2m', // 默认显示2个月
  customStartDate: null,
  customEndDate: null,
  visibleMAs: DEFAULT_MA_VISIBILITY,

  // 设置时间范围
  setTimeRange: (timeRange) => set({ timeRange }),

  // 设置自定义日期范围
  setCustomDateRange: (startDate, endDate) => set({
    customStartDate: startDate,
    customEndDate: endDate,
  }),

  // 切换均线显示状态
  toggleMA: (maPeriod) =>
    set((state) => ({
      visibleMAs: {
        ...state.visibleMAs,
        [maPeriod]: !state.visibleMAs[maPeriod],
      },
    })),

  // 设置均线显示状态
  setMAVisibility: (maPeriod, visible) =>
    set((state) => ({
      visibleMAs: {
        ...state.visibleMAs,
        [maPeriod]: visible,
      },
    })),

  // 重置均线显示状态
  resetMAs: () => set({ visibleMAs: DEFAULT_MA_VISIBILITY }),
}))
