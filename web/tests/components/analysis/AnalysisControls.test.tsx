/**
 * 分析控制面板组件测试
 */

import { render, screen, fireEvent } from '@testing-library/react'
import { AnalysisControls } from '@/components/analysis/AnalysisControls'
import type { SectorType, AxisType } from '@/types/scatter'

describe('AnalysisControls', () => {
  const defaultProps = {
    xAxis: 'short' as AxisType,
    yAxis: 'medium' as AxisType,
    sectorType: 'industry' as SectorType,
    minGrade: null as string | null,
    maxGrade: null as string | null,
    onXAxisChange: jest.fn(),
    onYAxisChange: jest.fn(),
    onSectorTypeChange: jest.fn(),
    onGradeRangeChange: jest.fn(),
  }

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('正确渲染所有控件', () => {
    render(<AnalysisControls {...defaultProps} />)

    // 验证板块类型按钮（不再有"全部"选项）
    expect(screen.getAllByText(/行业板块/i)).toHaveLength(2) // 按钮 + 状态显示
    expect(screen.getAllByText(/概念板块/i)).toHaveLength(1) // 只有按钮

    // 验证轴选择器
    expect(screen.getByLabelText(/X轴维度/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Y轴维度/i)).toBeInTheDocument()

    // 验证等级筛选（使用 getAllByRole 检查有 4 个 select：X轴、Y轴、最低等级、最高等级）
    expect(screen.getAllByRole('combobox')).toHaveLength(4)
  })

  it('正确切换板块类型', () => {
    const handleChange = jest.fn()
    render(
      <AnalysisControls
        {...defaultProps}
        onSectorTypeChange={handleChange}
      />
    )

    // 点击行业板块按钮（使用 closest 确保获取按钮元素）
    const buttons = screen.getAllByText(/行业板块/i)
    const industryButton = buttons.find(el => el.closest('button'))?.closest('button')
    fireEvent.click(industryButton!)

    expect(handleChange).toHaveBeenCalledWith('industry')

    // 点击概念板块按钮
    const conceptButton = screen.getByText(/概念板块/i).closest('button')
    fireEvent.click(conceptButton!)

    expect(handleChange).toHaveBeenCalledWith('concept')
  })

  it('正确切换 X 轴维度', () => {
    const handleChange = jest.fn()
    render(
      <AnalysisControls
        {...defaultProps}
        onXAxisChange={handleChange}
      />
    )

    const select = screen.getByLabelText(/X轴维度/i)

    // 切换到长期强度
    fireEvent.change(select, { target: { value: 'long' } })
    expect(handleChange).toHaveBeenCalledWith('long')
  })

  it('正确切换 Y 轴维度', () => {
    const handleChange = jest.fn()
    render(
      <AnalysisControls
        {...defaultProps}
        onYAxisChange={handleChange}
      />
    )

    const select = screen.getByLabelText(/Y轴维度/i)

    // 切换到综合强度
    fireEvent.change(select, { target: { value: 'composite' } })
    expect(handleChange).toHaveBeenCalledWith('composite')
  })

  it('正确设置等级范围', () => {
    const handleChange = jest.fn()
    render(
      <AnalysisControls
        {...defaultProps}
        onGradeRangeChange={handleChange}
      />
    )

    // 使用 getAllByRole 获取所有 select 元素
    // 索引: 0=X轴, 1=Y轴, 2=最低等级, 3=最高等级
    const selects = screen.getAllByRole('combobox')

    // 设置最低等级为 A（索引 2）
    fireEvent.change(selects[2], { target: { value: 'A' } })
    expect(handleChange).toHaveBeenCalledWith('A', null)

    // 设置最高等级为 S（索引 3）
    fireEvent.change(selects[3], { target: { value: 'S' } })
    expect(handleChange).toHaveBeenLastCalledWith(null, 'S')

    // 验证总共调用了 2 次
    expect(handleChange).toHaveBeenCalledTimes(2)
  })

  it('正确显示当前筛选状态', () => {
    render(
      <AnalysisControls
        {...defaultProps}
        xAxis="short"
        yAxis="medium"
        sectorType="industry"
        minGrade="A"
        maxGrade="S"
      />
    )

    // 验证筛选状态显示
    expect(screen.getByText(/当前筛选/i)).toBeInTheDocument()
    expect(screen.getAllByText(/行业板块/i)).toHaveLength(2) // 按钮和状态显示
    expect(screen.getByText(/X: 短期强度/i)).toBeInTheDocument()
    expect(screen.getByText(/Y: 中期强度/i)).toBeInTheDocument()
    expect(screen.getByText(/等级: A - S/i)).toBeInTheDocument()
  })

  it('显示正确的激活状态', () => {
    render(
      <AnalysisControls
        {...defaultProps}
        sectorType="industry"
      />
    )

    // 行业板块按钮应该是激活状态（找到按钮元素）
    const buttons = screen.getAllByText(/行业板块/i)
    const industryButton = buttons.find(el => el.closest('button'))?.closest('button')
    expect(industryButton).toHaveClass('bg-cyan-500')

    // 概念板块按钮不应该激活
    const conceptButton = screen.getByText(/概念板块/i).closest('button')
    expect(conceptButton).not.toHaveClass('bg-cyan-500')
  })
})
