/**
 * 板块强弱分类表格组件测试
 */

import React from 'react'
import { render, screen } from '@testing-library/react'
import { ClassificationTable } from '@/components/sector-classification/ClassificationTable'
import type { SectorClassification } from '@/types/sector-classification'

// Mock Table component
jest.mock('@/components/ui/table', () => {
  return {
    __esModule: true,
    default: ({
      columns,
      data,
      loading,
      emptyText,
      onRowClick,
      rowKey = 'id',
    }: any) => (
      <div data-testid="mock-table">
        {loading && <div data-testid="table-loading">加载中...</div>}
        {!loading && data.length === 0 && <div data-testid="table-empty">{emptyText}</div>}
        {!loading && data.length > 0 && (
          <div data-testid="table-rows">
            {data.map((record: any, index: number) => (
              <div
                key={String(record[rowKey] ?? index)}
                data-testid={`table-row-${index}`}
                onClick={() => onRowClick?.(record, index)}
                style={{ cursor: onRowClick ? 'pointer' : 'default' }}
              >
                {columns.map((col: any) => (
                  <div key={String(col.key)} data-testid={`cell-${col.key}`}>
                    {col.render ? col.render(record[col.key], record, index) : String(record[col.key] ?? '-')}
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}
      </div>
    ),
  }
})

// 测试数据
const mockData: SectorClassification[] = [
  {
    id: '1',
    sector_id: 'sector-1',
    sector_name: '科技板块',
    classification_date: '2026-01-22',
    classification_level: 9,
    state: '反弹',
    current_price: 150.25,
    change_percent: 2.5,
    created_at: '2026-01-22T10:00:00Z',
  },
  {
    id: '2',
    sector_id: 'sector-2',
    sector_name: '金融板块',
    classification_date: '2026-01-22',
    classification_level: 1,
    state: '调整',
    current_price: 98.50,
    change_percent: -1.2,
    created_at: '2026-01-22T10:00:00Z',
  },
  {
    id: '3',
    sector_id: 'sector-3',
    sector_name: '医药板块',
    classification_date: '2026-01-22',
    classification_level: 5,
    state: '反弹',
    current_price: 75.30,
    change_percent: 0.0,
    created_at: '2026-01-22T10:00:00Z',
  },
]

describe('ClassificationTable', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('应该渲染表格头', () => {
    render(<ClassificationTable data={mockData} />)

    expect(screen.getByText('板块名称')).toBeInTheDocument()
    expect(screen.getByText('分类级别')).toBeInTheDocument()
    expect(screen.getByText('状态')).toBeInTheDocument()
    expect(screen.getByText('当前价格')).toBeInTheDocument()
    expect(screen.getByText('涨跌幅')).toBeInTheDocument()
  })

  it('应该渲染板块数据', () => {
    render(<ClassificationTable data={mockData} />)

    expect(screen.getByText('科技板块')).toBeInTheDocument()
    expect(screen.getByText('金融板块')).toBeInTheDocument()
    expect(screen.getByText('医药板块')).toBeInTheDocument()
  })

  it('应该按分类级别降序排列（第 9 类在前）', () => {
    render(<ClassificationTable data={mockData} />)

    const rows = screen.getAllByTestId(/table-row-\d/)
    expect(rows).toHaveLength(3)

    // 第一行应该是第 9 类（科技板块）
    expect(rows[0]).toHaveTextContent('科技板块')
    expect(rows[0]).toHaveTextContent('第 9 类')

    // 第二行应该是第 5 类（医药板块）
    expect(rows[1]).toHaveTextContent('医药板块')
    expect(rows[1]).toHaveTextContent('第 5 类')

    // 第三行应该是第 1 类（金融板块）
    expect(rows[2]).toHaveTextContent('金融板块')
    expect(rows[2]).toHaveTextContent('第 1 类')
  })

  it('应该正确渲染分类级别徽章', () => {
    render(<ClassificationTable data={mockData} />)

    // 第 9 类 - 深绿色
    const level9Badge = screen.getByText('第 9 类')
    expect(level9Badge).toBeInTheDocument()
    expect(level9Badge).toHaveClass('bg-emerald-600', 'text-white')

    // 第 5 类 - 黄色
    const level5Badge = screen.getByText('第 5 类')
    expect(level5Badge).toBeInTheDocument()
    expect(level5Badge).toHaveClass('bg-yellow-500', 'text-black')

    // 第 1 类 - 深红色
    const level1Badge = screen.getByText('第 1 类')
    expect(level1Badge).toBeInTheDocument()
    expect(level1Badge).toHaveClass('bg-red-600', 'text-white')
  })

  it('应该正确渲染状态图标', () => {
    render(<ClassificationTable data={mockData} />)

    // 反弹状态
    const bounceIcons = screen.getAllByLabelText('反弹')
    expect(bounceIcons.length).toBeGreaterThan(0)
    bounceIcons.forEach(icon => {
      expect(icon).toHaveClass('text-green-600')
    })

    // 调整状态
    const adjustIcon = screen.getByLabelText('调整')
    expect(adjustIcon).toBeInTheDocument()
    expect(adjustIcon).toHaveClass('text-red-600')
  })

  it('应该正确渲染涨跌幅颜色', () => {
    render(<ClassificationTable data={mockData} />)

    // 正数涨跌幅 - 红色（A股习惯）
    const positiveChange = screen.getByText('+2.50%')
    expect(positiveChange).toBeInTheDocument()
    expect(positiveChange).toHaveClass('text-red-600')

    // 负数涨跌幅 - 绿色（A股习惯）
    const negativeChange = screen.getByText('-1.20%')
    expect(negativeChange).toBeInTheDocument()
    expect(negativeChange).toHaveClass('text-green-600')

    // 零涨跌幅 - 灰色
    const zeroChange = screen.getByText('0.00%')
    expect(zeroChange).toBeInTheDocument()
    expect(zeroChange).toHaveClass('text-gray-500')
  })

  it('应该处理空数据', () => {
    render(<ClassificationTable data={[]} />)

    expect(screen.getByTestId('table-empty')).toBeInTheDocument()
    expect(screen.getByText('暂无分类数据')).toBeInTheDocument()
  })

  it('应该显示加载状态', () => {
    render(<ClassificationTable data={[]} loading={true} />)

    expect(screen.getByTestId('table-loading')).toBeInTheDocument()
    expect(screen.getByText('加载中...')).toBeInTheDocument()
  })

  it('应该支持行点击', () => {
    const handleRowClick = jest.fn()

    render(<ClassificationTable data={mockData} onRowClick={handleRowClick} />)

    const firstRow = screen.getByTestId('table-row-0')
    firstRow.click()

    // 排序后第一行是第 9 类（科技板块，原始索引 0）
    expect(handleRowClick).toHaveBeenCalledWith(mockData[0], 0)
  })

  it('应该正确格式化当前价格', () => {
    render(<ClassificationTable data={mockData} />)

    expect(screen.getByText('150.25')).toBeInTheDocument()
    expect(screen.getByText('98.50')).toBeInTheDocument()
    expect(screen.getByText('75.30')).toBeInTheDocument()
  })

  it('应该处理无效的分类级别', () => {
    const invalidData: SectorClassification[] = [
      {
        id: '1',
        sector_id: 'sector-1',
        sector_name: '测试板块',
        classification_date: '2026-01-22',
        classification_level: 0, // 无效级别
        state: '反弹',
        current_price: 100,
        change_percent: 0,
        created_at: '2026-01-22T10:00:00Z',
      },
    ]

    render(<ClassificationTable data={invalidData} />)

    // 应该使用默认的灰色样式
    const levelBadge = screen.getByText('第 0 类')
    expect(levelBadge).toBeInTheDocument()
    expect(levelBadge).toHaveClass('bg-gray-500', 'text-white')
  })

  it('应该支持自定义空数据文本', () => {
    render(<ClassificationTable data={[]} emptyText="没有数据" />)

    expect(screen.getByText('没有数据')).toBeInTheDocument()
  })

  it('应该支持自定义类名', () => {
    const { container } = render(
      <ClassificationTable data={mockData} className="custom-class" />
    )

    const table = container.querySelector('.custom-class')
    expect(table).toBeInTheDocument()
  })

  // Props 默认值测试
  it('应该使用默认的空数据文本', () => {
    render(<ClassificationTable data={[]} />)

    expect(screen.getByText('暂无分类数据')).toBeInTheDocument()
  })

  it('应该默认不显示加载状态', () => {
    const { container } = render(<ClassificationTable data={mockData} />)

    const loading = container.querySelector('[data-testid="table-loading"]')
    expect(loading).not.toBeInTheDocument()
  })

  it('应该默认不支持行点击', () => {
    const { container } = render(<ClassificationTable data={mockData} />)

    // 没有 onRowClick 时，行不应该有 pointer 样式
    const rows = container.querySelectorAll('[style*="cursor: default"]')
    expect(rows.length).toBeGreaterThan(0)
  })
})
