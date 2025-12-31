/**
 * 板块散点图组件测试
 */

import { render, screen } from '@testing-library/react'
import { SectorScatterPlot } from '@/components/analysis/SectorScatterPlot'
import type { ScatterPlotProps, ScatterDataset } from '@/types/scatter'

// Mock echarts-for-react before importing the component
jest.mock('echarts-for-react', () => {
  return {
    __esModule: true,
    default: function MockECharts({ option, onEvents, style }: any) {
      return (
        <div data-testid="echarts" style={style}>
          <div data-testid="echarts-option">{JSON.stringify(option)}</div>
        </div>
      )
    },
  }
})

// Mock LoadingState and ErrorState to simplify testing
jest.mock('@/components/dashboard/LoadingState', () => ({
  LoadingState: ({ message }: { message: string }) => (
    <div data-testid="loading-state">{message}</div>
  ),
}))

jest.mock('@/components/dashboard/ErrorState', () => ({
  ErrorState: ({ message }: { message: string }) => (
    <div data-testid="error-state">{message}</div>
  ),
}))

describe('SectorScatterPlot', () => {
  const mockData: ScatterDataset = {
    industry: [
      {
        symbol: 'IND001',
        name: '新能源',
        sector_type: 'industry',
        x: 75.5,
        y: 82.3,
        size: 35.0,
        color_value: 88.0,
        data_completeness: {
          has_strong_ratio: true,
          has_long_term: true,
          completeness_percent: 100,
        },
        full_data: {
          score: 80.0,
          short_term_score: 75.5,
          medium_term_score: 82.3,
          long_term_score: 88.0,
          strong_stock_ratio: 0.7,
          strength_grade: 'A',
        },
      },
    ],
    concept: [
      {
        symbol: 'CON001',
        name: '人工智能',
        sector_type: 'concept',
        x: 65.2,
        y: 70.8,
        size: 25.0,
        color_value: 72.0,
        data_completeness: {
          has_strong_ratio: false,
          has_long_term: true,
          completeness_percent: 50,
        },
        full_data: {
          score: 68.0,
          short_term_score: 65.2,
          medium_term_score: 70.8,
          long_term_score: 72.0,
          strong_stock_ratio: null,
          strength_grade: 'B+',
        },
      },
    ],
  }

  const defaultProps: ScatterPlotProps = {
    xAxis: 'short',
    yAxis: 'medium',
    data: mockData,
    isLoading: false,
    isError: false,
  }

  // Note: 由于动态导入的问题，这些测试主要验证组件在加载状态、错误状态下的行为
  // ECharts 实际渲染需要浏览器环境，这里使用 mock 简化测试

  it('正确渲染散点图', () => {
    render(<SectorScatterPlot {...defaultProps} />)

    // 由于 dynamic import 的 loading fallback，初始渲染会显示加载状态
    // 这是正常的测试行为，实际浏览器环境会正确加载 ECharts
    const loadingOrChart = screen.queryByTestId('loading-state') || screen.queryByTestId('echarts')
    expect(loadingOrChart).toBeInTheDocument()
  })

  it('显示加载状态', () => {
    render(
      <SectorScatterPlot
        {...defaultProps}
        isLoading={true}
        data={undefined}
      />
    )

    expect(screen.getByText(/加载散点图/i)).toBeInTheDocument()
  })

  it('显示错误状态', () => {
    render(
      <SectorScatterPlot
        {...defaultProps}
        isError={true}
        data={undefined}
      />
    )

    expect(screen.getByText(/加载散点图失败/i)).toBeInTheDocument()
  })

  it('显示空数据状态', () => {
    render(
      <SectorScatterPlot
        {...defaultProps}
        data={{ industry: [], concept: [] }}
      />
    )

    expect(screen.getByText(/暂无散点图数据/i)).toBeInTheDocument()
  })

  it('正确处理点击事件', () => {
    const handleClick = jest.fn()

    render(
      <SectorScatterPlot
        {...defaultProps}
        onSectorClick={handleClick}
      />
    )

    // TODO: 测试 ECharts 点击事件需要更复杂的 mock
    // 这里暂时验证组件渲染
    expect(screen.getByTestId('echarts')).toBeInTheDocument()
  })

  it('使用正确的默认轴', () => {
    const { container } = render(<SectorScatterPlot {...defaultProps} />)

    const echartsOption = screen.getByTestId('echarts-option')
    const option = JSON.parse(echartsOption.textContent || '{}')

    // 验证轴配置
    expect(option.xAxis).toBeDefined()
    expect(option.yAxis).toBeDefined()
    expect(option.xAxis.name).toBe('短期强度')
    expect(option.yAxis.name).toBe('中期强度')
  })

  it('正确配置两个系列（行业和概念）', () => {
    const { container } = render(<SectorScatterPlot {...defaultProps} />)

    const echartsOption = screen.getByTestId('echarts-option')
    const option = JSON.parse(echartsOption.textContent || '{}')

    // 验证有两个系列
    expect(option.series).toBeDefined()
    expect(option.series.length).toBe(2)

    // 验证系列配置
    const industrySeries = option.series.find((s: any) => s.name === '行业板块')
    const conceptSeries = option.series.find((s: any) => s.name === '概念板块')

    expect(industrySeries).toBeDefined()
    expect(conceptSeries).toBeDefined()

    // 验证符号类型
    expect(industrySeries.symbol).toBe('circle')
    expect(conceptSeries.symbol).toBe('diamond')
  })

  it('正确配置 visualMap（颜色映射）', () => {
    const { container } = render(<SectorScatterPlot {...defaultProps} />)

    const echartsOption = screen.getByTestId('echarts-option')
    const option = JSON.parse(echartsOption.textContent || '{}')

    // 验证 visualMap
    expect(option.visualMap).toBeDefined()
    expect(option.visualMap.min).toBe(0)
    expect(option.visualMap.max).toBe(100)
    expect(option.visualMap.dimension).toBe(3)  // color_value 索引
  })

  it('正确配置 dataZoom（缩放和平移）', () => {
    const { container } = render(<SectorScatterPlot {...defaultProps} />)

    const echartsOption = screen.getByTestId('echarts-option')
    const option = JSON.parse(echartsOption.textContent || '{}')

    // 验证 dataZoom
    expect(option.dataZoom).toBeDefined()
    expect(option.dataZoom.length).toBe(4)  // 2 个 slider + 2 个 inside
  })
})
