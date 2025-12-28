import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { SectorHeatmap } from '@/components/dashboard/SectorHeatmap'
import { heatmapApi } from '@/lib/api'
import type { HeatmapSector } from '@/types'

// Mock next/navigation
const mockPush = jest.fn()
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}))

// Mock echarts-for-react
jest.mock('echarts-for-react', () => {
  return function MockReactECharts({ option, onEvents }: any) {
    // 模拟点击事件
    React.useEffect(() => {
      if (onEvents?.click) {
        // 设置一个全局函数来模拟点击
        ;(window as any).simulateChartClick = (params: any) => {
          onEvents.click(params)
        }
      }
    }, [onEvents])

    return (
      <div data-testid="echarts-mock">
        <div data-testid="echarts-option">
          {JSON.stringify(option)}
        </div>
      </div>
    )
  }
})

const mockSectors: HeatmapSector[] = [
  { id: '1', name: '新能源', value: 85.5, color: '#22c55e' },
  { id: '2', name: '半导体', value: 72.3, color: '#4ade80' },
  { id: '3', name: '医药', value: 55.0, color: '#facc15' },
  { id: '4', name: '房地产', value: 25.0, color: '#fb923c' },
  { id: '5', name: '钢铁', value: 8.0, color: '#ef4444' },
]

const mockHeatmapResponse = {
  success: true,
  data: {
    sectors: mockSectors,
    timestamp: '2025-12-24T10:30:00Z',
  },
}

// Mock SWR
jest.mock('swr', () => ({
  __esModule: true,
  default: jest.fn(),
}))

import useSWR from 'swr'

describe('SectorHeatmap', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('渲染测试', () => {
    it('应该渲染热力图组件', async () => {
      // Mock SWR 返回数据
      ;(useSWR as jest.Mock).mockReturnValue({
        data: mockHeatmapResponse,
        error: undefined,
        isLoading: false,
        mutate: jest.fn(),
      })

      render(<SectorHeatmap />)

      await waitFor(() => {
        expect(screen.getByTestId('echarts-mock')).toBeInTheDocument()
      })
    })

    it('应该显示加载状态', () => {
      // Mock SWR 加载状态
      ;(useSWR as jest.Mock).mockReturnValue({
        data: undefined,
        error: undefined,
        isLoading: true,
        mutate: jest.fn(),
      })

      render(<SectorHeatmap />)

      expect(screen.getByText(/加载热力图/i)).toBeInTheDocument()
    })

    it('应该显示错误状态', async () => {
      // Mock SWR 错误状态
      ;(useSWR as jest.Mock).mockReturnValue({
        data: undefined,
        error: new Error('API Error'),
        isLoading: false,
        mutate: jest.fn(),
      })

      render(<SectorHeatmap />)

      await waitFor(() => {
        expect(screen.getByText(/加载热力图失败/i)).toBeInTheDocument()
      })
    })

    it('应该显示空数据状态', async () => {
      // Mock SWR 空数据状态
      ;(useSWR as jest.Mock).mockReturnValue({
        data: {
          success: true,
          data: { sectors: [], timestamp: '2025-12-24T10:30:00Z' },
        },
        error: undefined,
        isLoading: false,
        mutate: jest.fn(),
      })

      render(<SectorHeatmap />)

      await waitFor(() => {
        expect(screen.getByText(/暂无热力图数据/i)).toBeInTheDocument()
      })
    })
  })

  describe('数据转换测试', () => {
    it('应该正确转换热力图数据为 ECharts Treemap 格式', async () => {
      ;(useSWR as jest.Mock).mockReturnValue({
        data: mockHeatmapResponse,
        error: undefined,
        isLoading: false,
        mutate: jest.fn(),
      })

      render(<SectorHeatmap />)

      await waitFor(() => {
        const optionElement = screen.getByTestId('echarts-option')
        const option = JSON.parse(optionElement.textContent || '{}')

        expect(option.series).toBeDefined()
        expect(option.series[0].type).toBe('treemap')
        expect(option.series[0].data).toHaveLength(mockSectors.length)

        // 验证第一个区块的数据
        const firstBlock = option.series[0].data[0]
        expect(firstBlock.name).toBe('新能源')
        expect(firstBlock.value).toBe(85.5)
        expect(firstBlock.itemStyle.color).toBe('#22c55e')
      })
    })

    it('应该使用后端返回的颜色', async () => {
      ;(useSWR as jest.Mock).mockReturnValue({
        data: mockHeatmapResponse,
        error: undefined,
        isLoading: false,
        mutate: jest.fn(),
      })

      render(<SectorHeatmap />)

      await waitFor(() => {
        const optionElement = screen.getByTestId('echarts-option')
        const option = JSON.parse(optionElement.textContent || '{}')

        const data = option.series[0].data

        // 验证颜色映射
        expect(data[0].itemStyle.color).toBe('#22c55e') // 新能源 - 绿色
        expect(data[1].itemStyle.color).toBe('#4ade80') // 半导体 - 浅绿
        expect(data[2].itemStyle.color).toBe('#facc15') // 医药 - 黄色
        expect(data[3].itemStyle.color).toBe('#fb923c') // 房地产 - 橙色
        expect(data[4].itemStyle.color).toBe('#ef4444') // 钢铁 - 红色
      })
    })
  })

  describe('交互功能测试', () => {
    it('应该支持点击事件跳转到板块详情页', async () => {
      ;(useSWR as jest.Mock).mockReturnValue({
        data: mockHeatmapResponse,
        error: undefined,
        isLoading: false,
        mutate: jest.fn(),
      })

      render(<SectorHeatmap />)

      await waitFor(() => {
        expect(screen.getByTestId('echarts-mock')).toBeInTheDocument()
      })

      // 模拟点击新能源板块
      ;(window as any).simulateChartClick({ name: '新能源' })

      expect(mockPush).toHaveBeenCalledWith('/sector/1')
    })

    it('应该配置 tooltip 显示板块详情', async () => {
      ;(useSWR as jest.Mock).mockReturnValue({
        data: mockHeatmapResponse,
        error: undefined,
        isLoading: false,
        mutate: jest.fn(),
      })

      render(<SectorHeatmap />)

      await waitFor(() => {
        const optionElement = screen.getByTestId('echarts-option')
        const option = JSON.parse(optionElement.textContent || '{}')

        expect(option.tooltip).toBeDefined()
        expect(option.tooltip.trigger).toBe('item')
        // formatter 是函数，JSON.stringify 后变成 undefined
        // 我们通过检查其他属性来验证 tooltip 配置
        expect(option.tooltip.backgroundColor).toBe('rgba(0, 0, 0, 0.8)')
        expect(option.tooltip.borderColor).toBe('#333')
      })
    })
  })

  describe('样式和布局测试', () => {
    it('应该应用自定义 className', async () => {
      ;(useSWR as jest.Mock).mockReturnValue({
        data: mockHeatmapResponse,
        error: undefined,
        isLoading: false,
        mutate: jest.fn(),
      })

      const { container } = render(<SectorHeatmap className="custom-class" />)

      await waitFor(() => {
        expect(screen.getByTestId('echarts-mock')).toBeInTheDocument()
      })

      // 验证 className 被应用
      expect(container.querySelector('.custom-class')).toBeInTheDocument()
    })

    it('应该显示最后更新时间', async () => {
      ;(useSWR as jest.Mock).mockReturnValue({
        data: mockHeatmapResponse,
        error: undefined,
        isLoading: false,
        mutate: jest.fn(),
      })

      render(<SectorHeatmap />)

      await waitFor(() => {
        expect(screen.getByText(/最后更新/i)).toBeInTheDocument()
      })

      // 日期格式可能是 2025-12-24 或 2025/12/24
      expect(screen.getByText(/2025[-/]12[-/]24/)).toBeInTheDocument()
    })
  })

  describe('API 参数测试', () => {
    it('应该使用默认参数调用 API', async () => {
      ;(useSWR as jest.Mock).mockReturnValue({
        data: mockHeatmapResponse,
        error: undefined,
        isLoading: false,
        mutate: jest.fn(),
      })

      render(<SectorHeatmap />)

      await waitFor(() => {
        expect(screen.getByTestId('echarts-mock')).toBeInTheDocument()
      })

      // 验证 SWR 被调用
      expect(useSWR).toHaveBeenCalled()
    })

    it('应该使用 sectorType 参数调用 API', async () => {
      ;(useSWR as jest.Mock).mockReturnValue({
        data: mockHeatmapResponse,
        error: undefined,
        isLoading: false,
        mutate: jest.fn(),
      })

      render(<SectorHeatmap sectorType="industry" />)

      await waitFor(() => {
        expect(screen.getByTestId('echarts-mock')).toBeInTheDocument()
      })

      // 验证 SWR 被调用
      expect(useSWR).toHaveBeenCalled()
    })
  })

  describe('性能优化测试', () => {
    it('应该使用 React.memo 包裹组件', () => {
      // 验证组件有 displayName（来自 memo）
      expect(SectorHeatmap.displayName).toBe('SectorHeatmap')
    })

    it('应该在1秒内渲染100个板块 (AC7性能要求)', async () => {
      // 生成100个模拟板块数据
      const mock100Sectors: HeatmapSector[] = Array.from({ length: 100 }, (_, i) => ({
        id: `sector-${i}`,
        name: `板块${i}`,
        value: Math.random() * 100,
        color: '#22c55e',
      }))

      const mock100Response = {
        success: true,
        data: {
          sectors: mock100Sectors,
          timestamp: '2025-12-24T10:30:00Z',
        },
      }

      ;(useSWR as jest.Mock).mockReturnValue({
        data: mock100Response,
        error: undefined,
        isLoading: false,
        mutate: jest.fn(),
      })

      // 测量渲染时间
      const startTime = performance.now()
      render(<SectorHeatmap />)

      await waitFor(() => {
        expect(screen.getByTestId('echarts-mock')).toBeInTheDocument()
      })

      const endTime = performance.now()
      const renderTime = endTime - startTime

      // 验证渲染时间小于1秒（1000ms）
      expect(renderTime).toBeLessThan(1000)
      console.log(`100个板块渲染时间: ${renderTime.toFixed(2)}ms`)
    })
  })
})
