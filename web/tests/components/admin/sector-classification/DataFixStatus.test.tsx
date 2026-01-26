/**
 * DataFixStatus 组件测试
 *
 * Story 4.5: Task 7
 * 测试数据修复状态显示的功能
 */

import { render, screen } from '@testing-library/react'
import { DataFixStatus } from '@/components/admin/sector-classification/DataFixStatus'
import { DataFixStatus as FixStatus } from '@/types/data-fix'

describe('DataFixStatus', () => {
  describe('IDLE 状态测试', () => {
    it('IDLE 状态不应该渲染任何内容', () => {
      const { container } = render(
        <DataFixStatus
          status={FixStatus.IDLE}
          result={null}
          error={null}
        />
      )

      expect(container.firstChild).toBeNull()
    })
  })

  describe('验证和修复中状态测试', () => {
    it('VALIDATING 状态应该显示"验证中..."', () => {
      render(
        <DataFixStatus
          status={FixStatus.VALIDATING}
          result={null}
          error={null}
        />
      )

      expect(screen.getByText('验证中...')).toBeInTheDocument()
    })

    it('FIXING 状态应该显示"修复中..."', () => {
      render(
        <DataFixStatus
          status={FixStatus.FIXING}
          result={null}
          error={null}
        />
      )

      expect(screen.getByText('修复中，请稍候...')).toBeInTheDocument()
    })
  })

  describe('成功状态测试', () => {
    const mockResult = {
      success_count: 2,
      failed_count: 1,
      duration_seconds: 3.5,
      sectors: [
        {
          sector_id: '1',
          sector_name: '新能源',
          success: true,
        },
        {
          sector_id: '2',
          sector_name: '银行',
          success: true,
        },
        {
          sector_id: '3',
          sector_name: '医药',
          success: false,
          error: '数据获取失败',
        },
      ],
    }

    it('SUCCESS 状态应该显示"修复完成！"', () => {
      render(
        <DataFixStatus
          status={FixStatus.SUCCESS}
          result={mockResult}
          error={null}
        />
      )

      expect(screen.getByText('修复完成！')).toBeInTheDocument()
    })

    it('应该显示成功修复数量', () => {
      render(
        <DataFixStatus
          status={FixStatus.SUCCESS}
          result={mockResult}
          error={null}
        />
      )

      expect(screen.getByText('2')).toBeInTheDocument() // success_count
      expect(screen.getByText('成功修复')).toBeInTheDocument()
    })

    it('应该显示失败数量（如果有）', () => {
      render(
        <DataFixStatus
          status={FixStatus.SUCCESS}
          result={mockResult}
          error={null}
        />
      )

      expect(screen.getByText('1')).toBeInTheDocument() // failed_count
      expect(screen.getByText('修复失败')).toBeInTheDocument()
    })

    it('应该显示修复耗时', () => {
      render(
        <DataFixStatus
          status={FixStatus.SUCCESS}
          result={mockResult}
          error={null}
        />
      )

      expect(screen.getByText('3.50 秒')).toBeInTheDocument()
      expect(screen.getByText('修复耗时')).toBeInTheDocument()
    })

    it('应该显示平均耗时', () => {
      render(
        <DataFixStatus
          status={FixStatus.SUCCESS}
          result={mockResult}
          error={null}
        />
      )

      expect(screen.getByText('1.75 秒/板块')).toBeInTheDocument()
      expect(screen.getByText('平均耗时')).toBeInTheDocument()
    })

    it('应该显示修复详情', () => {
      render(
        <DataFixStatus
          status={FixStatus.SUCCESS}
          result={mockResult}
          error={null}
        />
      )

      expect(screen.getByText('修复详情')).toBeInTheDocument()
      expect(screen.getByText('新能源')).toBeInTheDocument()
      expect(screen.getByText('银行')).toBeInTheDocument()
      expect(screen.getByText('医药')).toBeInTheDocument()
    })

    it('成功的板块应该显示成功图标', () => {
      render(
        <DataFixStatus
          status={FixStatus.SUCCESS}
          result={mockResult}
          error={null}
        />
      )

      // 新能源和银行应该成功
      const新能源Items = screen.getAllByText('新能源')
      const successItem = 新能源Items.find(item => item.classList.contains('text-green-900'))
      expect(successItem).toBeInTheDocument()
    })

    it('失败的板块应该显示错误信息', () => {
      render(
        <DataFixStatus
          status={FixStatus.SUCCESS}
          result={mockResult}
          error={null}
        />
      )

      expect(screen.getByText('数据获取失败')).toBeInTheDocument()
    })

    it('没有失败时不应显示失败卡片', () => {
      const successOnlyResult = {
        success_count: 2,
        failed_count: 0,
        duration_seconds: 2.5,
        sectors: [
          {
            sector_id: '1',
            sector_name: '新能源',
            success: true,
          },
          {
            sector_id: '2',
            sector_name: '银行',
            success: true,
          },
        ],
      }

      render(
        <DataFixStatus
          status={FixStatus.SUCCESS}
          result={successOnlyResult}
          error={null}
        />
      )

      expect(screen.queryByText('修复失败')).not.toBeInTheDocument()
    })
  })

  describe('错误状态测试', () => {
    it('ERROR 状态应该显示"修复失败"', () => {
      render(
        <DataFixStatus
          status={FixStatus.ERROR}
          result={null}
          error="网络连接失败"
        />
      )

      expect(screen.getByText('修复失败')).toBeInTheDocument()
    })

    it('应该显示错误信息', () => {
      render(
        <DataFixStatus
          status={FixStatus.ERROR}
          result={null}
          error="网络连接失败"
        />
      )

      expect(screen.getByText('网络连接失败')).toBeInTheDocument()
    })

    it('错误信息为 null 时不应显示错误详情', () => {
      render(
        <DataFixStatus
          status={FixStatus.ERROR}
          result={null}
          error={null}
        />
      )

      expect(screen.getByText('修复失败')).toBeInTheDocument()
      // 不应该有额外的错误信息卡片
    })
  })
})
