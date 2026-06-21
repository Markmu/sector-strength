/**
 * HoldingsDetail 组件测试 — holderName 维度切换
 *
 * 验证：
 * - 传 holderName 时，传给 SWR hook 的 params 含 holder_name、不含 group_ids
 * - 传 groupIds 时，params 含 group_ids、不含 holder_name
 * - holderName 模式下正常渲染汇总统计 + 子组件
 *
 * HoldingsDetail 的数据正确性由后端 pytest（57 个集成测试）覆盖；
 * 此处只验证前端「维度参数切换」接线 + 渲染不崩溃。
 */
import { render, screen } from '@testing-library/react'
import HoldingsDetail from '@/components/shareholder-analysis/HoldingsDetail'

// Mock 三个 SWR hooks（捕获传入的 params）
jest.mock('@/hooks/useShareholderAnalysis', () => ({
  useShareholderSummary: jest.fn(),
  useShareholderIndustryDistribution: jest.fn(),
  useShareholderHoldings: jest.fn(),
}))

// Mock 子组件（避免 echarts / 复杂交互），只验证接线
jest.mock('@/components/shareholder-analysis/IndustryDistribution', () => ({
  __esModule: true,
  default: () => <div data-testid="industry-dist" />,
}))
jest.mock('@/components/shareholder-analysis/HoldingsTable', () => ({
  __esModule: true,
  default: () => <div data-testid="holdings-table" />,
}))

const hooks = jest.requireMock('@/hooks/useShareholderAnalysis') as {
  useShareholderSummary: jest.Mock
  useShareholderIndustryDistribution: jest.Mock
  useShareholderHoldings: jest.Mock
}

describe('HoldingsDetail - 维度切换', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    hooks.useShareholderSummary.mockReturnValue({
      summary: {
        summary: {
          stockCount: 3,
          totalHoldAmount: 1000,
          avgHoldFloatRatio: 0.05,
        },
        trend: {
          increaseCount: 1,
          decreaseCount: 0,
          newCount: 2,
          exitCount: 1,
        },
        hasPrevPeriod: true,
      },
      isLoading: false,
      isError: false,
    })
    hooks.useShareholderIndustryDistribution.mockReturnValue({
      distribution: [
        { industry: '银行', stockCount: 1, percentage: 33.3 },
      ],
      isLoading: false,
      isError: false,
    })
    hooks.useShareholderHoldings.mockReturnValue({
      holdings: [
        {
          symbol: '600519',
          stockName: '贵州茅台',
          totalHoldAmount: 1000,
          totalHoldFloatRatio: 0.1,
          changeDirection: 'increase',
          industries: ['白酒'],
        },
      ],
      total: 3,
      isLoading: false,
      isError: false,
    })
  })

  it('传 holderName 时 hook 收到 holder_name 维度（不含 group_ids）', () => {
    render(
      <HoldingsDetail
        holderName="中央汇金投资有限责任公司"
        reportPeriod="2024-12-31"
        hasPrevPeriod
      />
    )
    const summaryParams = hooks.useShareholderSummary.mock.calls[0][0]
    expect(summaryParams.holder_name).toBe('中央汇金投资有限责任公司')
    expect(summaryParams.group_ids).toBeUndefined()
    expect(summaryParams.report_period).toBe('2024-12-31')

    const holdingsParams = hooks.useShareholderHoldings.mock.calls[0][0]
    expect(holdingsParams.holder_name).toBe('中央汇金投资有限责任公司')
    expect(holdingsParams.group_ids).toBeUndefined()
  })

  it('传 groupIds 时 hook 收到 group_ids 维度（不含 holder_name）', () => {
    render(
      <HoldingsDetail groupIds={[1, 2]} reportPeriod="2024-12-31" hasPrevPeriod />
    )
    const summaryParams = hooks.useShareholderSummary.mock.calls[0][0]
    expect(summaryParams.group_ids).toBe('1,2')
    expect(summaryParams.holder_name).toBeUndefined()
  })

  it('holderName 模式下渲染持仓汇总 + 子组件', () => {
    render(
      <HoldingsDetail
        holderName="中央汇金投资有限责任公司"
        reportPeriod="2024-12-31"
        hasPrevPeriod
      />
    )
    expect(screen.getByText('持仓汇总')).toBeInTheDocument()
    expect(screen.getByText('变动趋势')).toBeInTheDocument()
    // stockCount=3 渲染
    expect(screen.getByText('3')).toBeInTheDocument()
    // 子组件渲染（mock 后的 testid）
    expect(screen.getByTestId('industry-dist')).toBeInTheDocument()
    expect(screen.getByTestId('holdings-table')).toBeInTheDocument()
  })
})
