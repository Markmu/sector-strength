/**
 * MarketMetricsPanel 组件测试（第 16 期 plan-07 Task 6）
 *
 * 覆盖：加载 / 错误重试 / 空态（管理员链接 + 普通文案）/ 正常态卡片与双图表 /
 * 缺口提示 / 范围切换（aria-pressed）。FEAT-0003：指标切换按钮移除，
 * 图表区拆分为成交量/平均价双折线（testid chart-volume / chart-price）。
 *
 * Mock 策略（参照 tests/dashboard/MarketIndexDisplay.test.tsx 范式）：
 * - echarts-for-react → 返回 null（避免 Canvas）
 * - next/dynamic → 同步解析到上面的 mock
 * - swr → 控制 useSWR 返回值（data/isLoading/error/mutate）
 * - @/contexts/AuthContext → 控制 isAdmin
 */
import { render, screen, fireEvent } from '@testing-library/react'
import MarketMetricsPanel from '@/components/market-metrics/MarketMetricsPanel'

// Mock ECharts 组件（避免 Canvas 错误）
jest.mock('echarts-for-react', () => ({
  __esModule: true,
  default: () => null,
}))

jest.mock('next/dynamic', () => () => {
  const ECharts = require('echarts-for-react').default
  return ECharts
})

// Mock SWR：控制 useSWR 返回值
const mockMutate = jest.fn()
let mockSwrValue: any = { data: undefined, isLoading: true, error: undefined, mutate: mockMutate }
jest.mock('swr', () => ({
  __esModule: true,
  default: jest.fn(() => mockSwrValue),
}))

// Mock AuthContext：控制 isAdmin
let mockIsAdmin = false
jest.mock('@/contexts/AuthContext', () => ({
  __esModule: true,
  useAuth: () => ({ isAdmin: mockIsAdmin }),
}))

import type { MarketMetricsTrendData } from '@/types/marketMetricsTypes'

/** 满数据趋势 fixture（与 mock-market-metrics-api.ts 同口径） */
function buildTrend(opts?: { empty?: boolean; gaps?: boolean }): MarketMetricsTrendData {
  if (opts?.empty) {
    return { latest: null, points: [], range: 30, hasMissingDates: false }
  }
  const mk = (i: number, tradeDate: string, isNull: boolean) =>
    isNull
      ? {
          tradeDate,
          volumeShares: null,
          amountYuan: null,
          averagePrice: null,
          finalStockCount: null,
          suspendedStockCount: null,
        }
      : {
          tradeDate,
          volumeShares: 7.2e9 + i * 1e7,
          amountYuan: 8.2e11 + i * 2e9,
          averagePrice: 11.38 + i * 0.01,
          finalStockCount: 5200 + (i % 5),
          suspendedStockCount: 22 + (i % 7),
        }
  if (opts?.gaps) {
    const points = [mk(0, '2026-08-07', false), mk(1, '2026-08-08', false), mk(2, '2026-08-09', true), mk(3, '2026-08-10', false), mk(4, '2026-08-11', true), mk(5, '2026-08-12', false), mk(6, '2026-08-13', false)]
    return { latest: points[6] as any, points: points as any, range: 30, hasMissingDates: true }
  }
  const points = [
    mk(0, '2026-08-12', false),
    mk(1, '2026-08-13', false),
  ]
  return { latest: points[1] as any, points: points as any, range: 30, hasMissingDates: false }
}

function setSwr(value: Partial<typeof mockSwrValue>) {
  mockSwrValue = { ...mockSwrValue, ...value }
}

describe('MarketMetricsPanel', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    mockIsAdmin = false
    mockSwrValue = { data: undefined, isLoading: true, error: undefined, mutate: mockMutate }
  })

  describe('加载与错误态', () => {
    it('加载中显示加载态', () => {
      setSwr({ data: undefined, isLoading: true, error: undefined })
      render(<MarketMetricsPanel />)
      expect(screen.getByText(/加载市场量价数据中/i)).toBeInTheDocument()
    })

    it('请求失败显示错误框与重试按钮', () => {
      setSwr({
        data: undefined,
        isLoading: false,
        error: new Error('Internal Server Error'),
      })
      render(<MarketMetricsPanel />)
      expect(screen.getByTestId('market-metrics-error')).toBeInTheDocument()
      expect(screen.getByTestId('market-metrics-retry')).toBeInTheDocument()
    })

    it('点击重试仅调用 mutate（AC-12 局部刷新）', () => {
      setSwr({
        data: undefined,
        isLoading: false,
        error: new Error('boom'),
      })
      render(<MarketMetricsPanel />)
      fireEvent.click(screen.getByTestId('market-metrics-retry'))
      expect(mockMutate).toHaveBeenCalledTimes(1)
    })
  })

  describe('空态（latest === null）', () => {
    it('管理员：显示前往数据管理链接（href /dashboard/admin/data）', () => {
      mockIsAdmin = true
      setSwr({
        data: { success: true, data: buildTrend({ empty: true }) },
        isLoading: false,
        error: undefined,
      })
      render(<MarketMetricsPanel />)
      expect(screen.getByTestId('market-metrics-empty')).toBeInTheDocument()
      const link = screen.getByTestId('market-metrics-empty-admin-link')
      expect(link).toHaveAttribute('href', '/dashboard/admin/data')
    })

    it('普通用户：纯文案，不渲染管理员链接', () => {
      mockIsAdmin = false
      setSwr({
        data: { success: true, data: buildTrend({ empty: true }) },
        isLoading: false,
        error: undefined,
      })
      render(<MarketMetricsPanel />)
      expect(screen.getByTestId('market-metrics-empty')).toBeInTheDocument()
      expect(screen.queryByTestId('market-metrics-empty-admin-link')).toBeNull()
      expect(screen.getByText(/请联系管理员同步数据/i)).toBeInTheDocument()
    })
  })

  describe('正常态', () => {
    beforeEach(() => {
      setSwr({
        data: { success: true, data: buildTrend() },
        isLoading: false,
        error: undefined,
      })
    })

    it('渲染面板根、双图表容器（成交额/平均价）、最近结果日', () => {
      render(<MarketMetricsPanel />)
      expect(screen.getByTestId('market-metrics-panel')).toBeInTheDocument()
      expect(
        screen.getByTestId('market-metrics-chart-amount')
      ).toBeInTheDocument()
      expect(
        screen.getByTestId('market-metrics-chart-price')
      ).toBeInTheDocument()
      // 旧单图表容器与指标切换按钮已移除（FEAT-0003）
      expect(screen.queryByTestId('market-metrics-chart')).toBeNull()
      expect(
        screen.queryByTestId('market-metrics-metric-amountYuan')
      ).toBeNull()
      expect(
        screen.queryByTestId('market-metrics-metric-volumeShares')
      ).toBeNull()
      expect(
        screen.queryByTestId('market-metrics-metric-averagePrice')
      ).toBeNull()
      expect(screen.getByTestId('market-metrics-latest-date')).toHaveTextContent(
        '2026-08-13'
      )
    })

    it('双图标签可见：成交额趋势 / 平均价趋势', () => {
      render(<MarketMetricsPanel />)
      expect(screen.getByText('成交额趋势')).toBeInTheDocument()
      expect(screen.getByText('平均价趋势')).toBeInTheDocument()
    })

    it('单位换算：成交额/成交量 ÷1e8 转亿，平均价 2 位小数', () => {
      render(<MarketMetricsPanel />)
      // amountYuan = 8.2e11 + 2e9 = 822000000000 → /1e8 = 8220 亿元
      expect(screen.getByText(/成交额（亿元）/i).parentElement).toHaveTextContent(
        '8,220'
      )
      // volumeShares = 7.2e9 + 1e7 = 7210000000 → /1e8 = 72.1 亿股
      expect(screen.getByText(/成交量（亿股）/i).parentElement).toHaveTextContent(
        '72.1'
      )
      // averagePrice = 11.39 → 11.39
      expect(screen.getByText(/平均价（元）/i).parentElement).toHaveTextContent(
        '11.39'
      )
    })

    it('缺口 fixture：显示部分日期无数据提示', () => {
      setSwr({
        data: { success: true, data: buildTrend({ gaps: true }) },
        isLoading: false,
        error: undefined,
      })
      render(<MarketMetricsPanel />)
      expect(screen.getByTestId('market-metrics-missing-hint')).toHaveTextContent(
        /部分日期无数据/i
      )
    })

    it('默认范围 30 active，点击 90 切换', () => {
      render(<MarketMetricsPanel />)
      expect(screen.getByTestId('market-metrics-range-30')).toHaveAttribute(
        'aria-pressed',
        'true'
      )
      fireEvent.click(screen.getByTestId('market-metrics-range-90'))
      expect(screen.getByTestId('market-metrics-range-90')).toHaveAttribute(
        'aria-pressed',
        'true'
      )
      expect(screen.getByTestId('market-metrics-range-30')).toHaveAttribute(
        'aria-pressed',
        'false'
      )
    })
  })
})
