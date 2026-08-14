/**
 * MarginPanel 组件测试（第 17 期 plan-07 Task 5）
 *
 * 覆盖：加载 / 错误重试 / 空态（管理员链接 + 普通文案）/ 正常态卡片与图表 /
 * 缺口提示 / 范围切换（aria-pressed）。
 *
 * legend 4 项 / 双 Y 轴 yAxisIndex / 缺口 null 非 0 等 ECharts option 级断言
 * 由 E2E 经 __echartsInst__ 钩子读 getOption() 覆盖（用例文档约定，
 * jest 与 E2E 同源互补）。
 *
 * Mock 策略（照抄 tests/market-metrics/MarketMetricsPanel.test.tsx 范式）：
 * - echarts-for-react → 返回 null（避免 Canvas）
 * - next/dynamic → 同步解析到上面的 mock
 * - swr → 控制 useSWR 返回值（data/isLoading/error/mutate）
 * - @/contexts/AuthContext → 控制 isAdmin
 */
import { render, screen, fireEvent } from '@testing-library/react'
import MarginPanel from '@/components/market-margin/MarginPanel'

// Mock ECharts 组件（避免 Canvas 错误）
jest.mock('echarts-for-react', () => ({
  __esModule: true,
  default: () => null,
}))

// Mock next/dynamic：返回渲染 null 的同步组件（loader 不执行，绕开 ssr:false 动态链）
jest.mock('next/dynamic', () => ({
  __esModule: true,
  default: () => () => null,
}))

// Mock SWR：控制 useSWR 返回值
const mockMutate = jest.fn()
interface SwrValue {
  data?: { success: boolean; data: MarginTrendData } | undefined
  isLoading: boolean
  error?: unknown
  mutate: typeof mockMutate
}
let mockSwrValue: SwrValue = {
  data: undefined,
  isLoading: true,
  error: undefined,
  mutate: mockMutate,
}
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

import type { MarginTrendData, MarginPoint } from '@/types/marginTypes'

/** 满数据趋势 fixture（与 tests/e2e/helpers/mock-margin-api.ts 同口径：元原始值） */
function buildTrend(opts?: { empty?: boolean; gaps?: boolean }): MarginTrendData {
  if (opts?.empty) {
    return { latest: null, points: [], range: 30, hasMissingDates: false }
  }
  const mk = (i: number, tradeDate: string, isNull: boolean): MarginPoint =>
    isNull
      ? {
          tradeDate,
          rzye: null,
          rqye: null,
          rzmre: null,
          rzche: null,
          rqmcl: null,
          rzrqye: null,
        }
      : {
          tradeDate,
          rzye: 2.1e12 + i * 1e10,
          rqye: 7.5e11 + i * 5e9,
          rzmre: 2.2e11 + i * 1e9,
          rzche: 2.1e11 + i * 1e9,
          rqmcl: 3.2e9 + i * 1e7,
          rzrqye: 2.1e12 + i * 1e10 + 7.5e11 + i * 5e9,
        }
  if (opts?.gaps) {
    // 7 日轴，索引 2、4 为缺口日（六指标 null，非 0）
    const points = [
      mk(0, '2026-08-07', false),
      mk(1, '2026-08-08', false),
      mk(2, '2026-08-09', true),
      mk(3, '2026-08-10', false),
      mk(4, '2026-08-11', true),
      mk(5, '2026-08-12', false),
      mk(6, '2026-08-13', false),
    ]
    return { latest: points[6], points, range: 30, hasMissingDates: true }
  }
  const points = [
    mk(0, '2026-08-12', false),
    mk(1, '2026-08-13', false),
  ]
  return { latest: points[1], points, range: 30, hasMissingDates: false }
}

function setSwr(value: Partial<typeof mockSwrValue>) {
  mockSwrValue = { ...mockSwrValue, ...value }
}

describe('MarginPanel', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    mockIsAdmin = false
    mockSwrValue = { data: undefined, isLoading: true, error: undefined, mutate: mockMutate }
  })

  describe('加载与错误态', () => {
    it('加载中显示加载态', () => {
      setSwr({ data: undefined, isLoading: true, error: undefined })
      render(<MarginPanel />)
      expect(screen.getByText(/加载融资融券数据中/i)).toBeInTheDocument()
    })

    it('请求失败显示错误框与重试按钮', () => {
      setSwr({
        data: undefined,
        isLoading: false,
        error: new Error('Internal Server Error'),
      })
      render(<MarginPanel />)
      expect(screen.getByTestId('margin-error')).toBeInTheDocument()
      expect(screen.getByTestId('margin-retry')).toBeInTheDocument()
    })

    it('点击重试仅调用 mutate（局部刷新）', () => {
      setSwr({
        data: undefined,
        isLoading: false,
        error: new Error('boom'),
      })
      render(<MarginPanel />)
      fireEvent.click(screen.getByTestId('margin-retry'))
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
      render(<MarginPanel />)
      expect(screen.getByTestId('margin-empty')).toBeInTheDocument()
      const link = screen.getByTestId('margin-empty-admin-link')
      expect(link).toHaveAttribute('href', '/dashboard/admin/data')
    })

    it('普通用户：纯文案，不渲染管理员链接', () => {
      mockIsAdmin = false
      setSwr({
        data: { success: true, data: buildTrend({ empty: true }) },
        isLoading: false,
        error: undefined,
      })
      render(<MarginPanel />)
      expect(screen.getByTestId('margin-empty')).toBeInTheDocument()
      expect(screen.queryByTestId('margin-empty-admin-link')).toBeNull()
      expect(screen.getByText(/尚未同步|暂无/i)).toBeInTheDocument()
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

    it('渲染面板根、图表容器、最近结果日', () => {
      render(<MarginPanel />)
      expect(screen.getByTestId('margin-panel')).toBeInTheDocument()
      expect(screen.getByTestId('margin-chart')).toBeInTheDocument()
      expect(screen.getByTestId('margin-latest-date')).toHaveTextContent('2026-08-13')
    })

    it('4 张最新值卡片：÷1e8 转亿（zh-CN 2 位小数）+ 亿元标签', () => {
      render(<MarginPanel />)
      // rzye = 2.1e12 + 1e10 = 2.11e12 → /1e8 = 21100 亿元
      expect(screen.getByTestId('margin-card-rzye')).toHaveTextContent('21,100')
      // rqye = 7.5e11 + 5e9 = 7.55e11 → 7550 亿元
      expect(screen.getByTestId('margin-card-rqye')).toHaveTextContent('7,550')
      // rzrqye = 2.11e12 + 7.55e11 = 2.865e12 → 28650 亿元
      expect(screen.getByTestId('margin-card-rzrqye')).toHaveTextContent('28,650')
      // rzmre = 2.2e11 + 1e9 = 2.21e11 → 2210 亿元
      expect(screen.getByTestId('margin-card-rzmre')).toHaveTextContent('2,210')
      // 每张卡片带亿元标签与指标名
      for (const label of ['融资余额', '融券余额', '两融合计余额', '融资买入额']) {
        expect(screen.getByText(new RegExp(`${label}（亿元）`))).toBeInTheDocument()
      }
    })

    it('无缺口时不显示缺口提示', () => {
      render(<MarginPanel />)
      expect(screen.queryByTestId('margin-missing-hint')).toBeNull()
    })

    it('缺口 fixture：显示部分日期无数据提示', () => {
      setSwr({
        data: { success: true, data: buildTrend({ gaps: true }) },
        isLoading: false,
        error: undefined,
      })
      render(<MarginPanel />)
      expect(screen.getByTestId('margin-missing-hint')).toHaveTextContent(
        /部分日期无数据/i
      )
    })

    it('默认范围 30 active，点击 90 切换', () => {
      render(<MarginPanel />)
      expect(screen.getByTestId('margin-range-30')).toHaveAttribute('aria-pressed', 'true')
      expect(screen.getByTestId('margin-range-90')).toHaveAttribute('aria-pressed', 'false')
      fireEvent.click(screen.getByTestId('margin-range-90'))
      expect(screen.getByTestId('margin-range-90')).toHaveAttribute('aria-pressed', 'true')
      expect(screen.getByTestId('margin-range-30')).toHaveAttribute('aria-pressed', 'false')
    })
  })
})
