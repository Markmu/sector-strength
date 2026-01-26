/**
 * DataIntegrityCard 组件测试
 */

import { render, screen } from '@testing-library/react'
import { DataIntegrityCard } from '@/components/admin/sector-classification/DataIntegrityCard'
import type { DataIntegrity } from '@/types/admin-monitoring'

// Mock Card 组件
jest.mock('@/components/ui/Card', () => {
  return {
    __esModule: true,
    Card: ({ children, className }: any) => <div className={className} data-testid="card">{children}</div>,
    CardHeader: ({ children }: any) => <div data-testid="card-header">{children}</div>,
    CardBody: ({ children }: any) => <div data-testid="card-body">{children}</div>,
  }
})

describe('DataIntegrityCard', () => {
  const mockDataIntegrity: DataIntegrity = {
    total_sectors: 15,
    sectors_with_data: 15,
    missing_sectors: []
  }

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('应该显示完整数据状态', () => {
    render(
      <DataIntegrityCard
        dataIntegrity={mockDataIntegrity}
        loading={false}
      />
    )

    expect(screen.getByText('数据完整性')).toBeInTheDocument()
    expect(screen.getByText('100.0%')).toBeInTheDocument()
    expect(screen.getByText('15')).toBeInTheDocument() // 总板块数
  })

  it('应该显示部分缺失状态', () => {
    const partialDataIntegrity: DataIntegrity = {
      total_sectors: 15,
      sectors_with_data: 13,
      missing_sectors: [
        { sector_id: '1', sector_name: '银行' },
        { sector_id: '2', sector_name: '保险' }
      ]
    }

    render(
      <DataIntegrityCard
        dataIntegrity={partialDataIntegrity}
        loading={false}
      />
    )

    expect(screen.getByText('86.7%')).toBeInTheDocument()
    expect(screen.getByText('银行')).toBeInTheDocument()
    expect(screen.getByText('保险')).toBeInTheDocument()
  })

  it('加载中时不显示内容', () => {
    const { container } = render(
      <DataIntegrityCard
        dataIntegrity={null}
        loading={true}
      />
    )

    // Card 不应该渲染
    expect(container.querySelector('[data-testid="card"]')).not.toBeInTheDocument()
  })

  it('没有数据时不显示内容', () => {
    const { container } = render(
      <DataIntegrityCard
        dataIntegrity={null}
        loading={false}
      />
    )

    expect(container.querySelector('[data-testid="card"]')).not.toBeInTheDocument()
  })

  it('应该正确计算数据覆盖率', () => {
    const testCases = [
      { total: 10, with_data: 10, expected: '100.0%' },
      { total: 10, with_data: 5, expected: '50.0%' },
      { total: 15, with_data: 13, expected: '86.7%' },
    ]

    testCases.forEach(({ total, with_data, expected }) => {
      const dataIntegrity: DataIntegrity = {
        total_sectors: total,
        sectors_with_data: with_data,
        missing_sectors: []
      }

      const { rerender } = render(
        <DataIntegrityCard
          dataIntegrity={dataIntegrity}
          loading={false}
        />
      )

      expect(screen.getByText(expected)).toBeInTheDocument()

      rerender(<div />)
    })
  })

  it('应该显示缺失板块列表', () => {
    const dataIntegrity: DataIntegrity = {
      total_sectors: 5,
      sectors_with_data: 2,
      missing_sectors: [
        { sector_id: '1', sector_name: '科技' },
        { sector_id: '2', sector_name: '金融' },
        { sector_id: '3', sector_name: '医药' }
      ]
    }

    render(
      <DataIntegrityCard
        dataIntegrity={dataIntegrity}
        loading={false}
      />
    )

    expect(screen.getByText('缺失数据的板块：')).toBeInTheDocument()
    expect(screen.getByText('科技')).toBeInTheDocument()
    expect(screen.getByText('金融')).toBeInTheDocument()
    expect(screen.getByText('医药')).toBeInTheDocument()
  })
})
