/**
 * DataFixDialog 组件测试
 *
 * Story 4.5: Task 7.1, 7.2
 * 测试数据修复弹窗的功能
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DataFixDialog } from '@/components/admin/sector-classification/DataFixDialog'
import type { SectorOption } from '@/components/admin/sector-classification/DataFixDialog.types'

const mockSectors: SectorOption[] = [
  { id: '1', name: '新能源' },
  { id: '2', name: '银行' },
]

describe('DataFixDialog', () => {
  const mockOnClose = jest.fn()
  const mockOnComplete = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
  })

  const defaultProps = {
    open: true,
    onClose: mockOnClose,
    onComplete: mockOnComplete,
    sectors: mockSectors,
  }

  describe('渲染测试', () => {
    it('应该渲染弹窗', () => {
      render(<DataFixDialog {...defaultProps} />)

      expect(screen.getByText('数据修复')).toBeInTheDocument()
      expect(screen.getByText('修复异常的分类数据')).toBeInTheDocument()
    })

    it('应该显示板块选择方式', () => {
      render(<DataFixDialog {...defaultProps} />)

      expect(screen.getByText('板块选择方式')).toBeInTheDocument()
      expect(screen.getByText('按 ID')).toBeInTheDocument()
      expect(screen.getByText('按名称')).toBeInTheDocument()
    })

    it('应该显示时间范围选项', () => {
      render(<DataFixDialog {...defaultProps} />)

      expect(screen.getByText('时间范围')).toBeInTheDocument()
      expect(screen.getByText('最近 7 天')).toBeInTheDocument()
      expect(screen.getByText('最近 30 天')).toBeInTheDocument()
      expect(screen.getByText('最近 90 天')).toBeInTheDocument()
      expect(screen.getByText('最近 180 天')).toBeInTheDocument()
    })

    it('应该显示覆盖选项', () => {
      render(<DataFixDialog {...defaultProps} />)

      expect(screen.getByText('覆盖已有数据')).toBeInTheDocument()
    })

    it('应该显示警告提示', () => {
      render(<DataFixDialog {...defaultProps} />)

      expect(screen.getByText('注意')).toBeInTheDocument()
      expect(screen.getByText(/修复操作会重新计算分类数据/)).toBeInTheDocument()
    })

    it('应该显示取消和开始修复按钮', () => {
      render(<DataFixDialog {...defaultProps} />)

      expect(screen.getByText('取消')).toBeInTheDocument()
      expect(screen.getByText('开始修复')).toBeInTheDocument()
    })
  })

  describe('板块选择测试', () => {
    it('默认显示板块 ID 输入框', () => {
      render(<DataFixDialog {...defaultProps} />)

      expect(screen.getByPlaceholderText('输入板块 ID')).toBeInTheDocument()
    })

    it('点击"按名称"应该显示下拉选择', async () => {
      const user = userEvent.setup()
      render(<DataFixDialog {...defaultProps} />)

      const nameRadio = screen.getByLabelText('按名称')
      await user.click(nameRadio)

      expect(screen.getByText('选择板块')).toBeInTheDocument()
      expect(screen.getByText('新能源')).toBeInTheDocument()
      expect(screen.getByText('银行')).toBeInTheDocument()
    })

    it('选择板块后应该更新选中值', async () => {
      const user = userEvent.setup()
      render(<DataFixDialog {...defaultProps} />)

      const nameRadio = screen.getByLabelText('按名称')
      await user.click(nameRadio)

      const select = screen.getByText('选择板块').closest('select')
      if (select) {
        await user.selectOptions(select, '新能源')
        expect(select).toHaveValue('新能源')
      }
    })
  })

  describe('时间范围选择测试', () => {
    it('默认选中 30 天', () => {
      render(<DataFixDialog {...defaultProps} />)

      const thirtyDaysButton = screen.getByText('最近 30 天')
      expect(thirtyDaysButton).toHaveClass('bg-cyan-500')
    })

    it('点击其他时间范围应该更新选中状态', async () => {
      const user = userEvent.setup()
      render(<DataFixDialog {...defaultProps} />)

      const sevenDaysButton = screen.getByText('最近 7 天')
      await user.click(sevenDaysButton)

      expect(sevenDaysButton).toHaveClass('bg-cyan-500')
    })
  })

  describe('表单验证测试', () => {
    it('不输入板块 ID 点击提交应该显示错误', async () => {
      const user = userEvent.setup()
      render(<DataFixDialog {...defaultProps} />)

      const submitButton = screen.getByText('开始修复')
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText('请输入板块 ID')).toBeInTheDocument()
      })
    })

    it('选择板块名称但不选择具体板块应该显示错误', async () => {
      const user = userEvent.setup()
      render(<DataFixDialog {...defaultProps} />)

      // 切换到按名称选择
      const nameRadio = screen.getByLabelText('按名称')
      await user.click(nameRadio)

      // 点击提交
      const submitButton = screen.getByText('开始修复')
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText('请选择板块')).toBeInTheDocument()
      })
    })
  })

  describe('交互测试', () => {
    it('点击取消按钮应该调用 onClose', async () => {
      const user = userEvent.setup()
      render(<DataFixDialog {...defaultProps} />)

      const cancelButton = screen.getByText('取消')
      await user.click(cancelButton)

      expect(mockOnClose).toHaveBeenCalledTimes(1)
    })

    it('输入有效信息后点击提交应该调用 onComplete', async () => {
      const user = userEvent.setup()
      render(<DataFixDialog {...defaultProps} />)

      // 输入板块 ID
      const sectorIdInput = screen.getByPlaceholderText('输入板块 ID')
      await user.type(sectorIdInput, '123')

      // 点击提交
      const submitButton = screen.getByText('开始修复')
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockOnComplete).toHaveBeenCalledTimes(1)
      })
    })

    it('打开弹窗时应该重置表单', async () => {
      const user = userEvent.setup()
      const { rerender } = render(<DataFixDialog {...defaultProps} />)

      // 输入一些数据
      const sectorIdInput = screen.getByPlaceholderText('输入板块 ID')
      await user.type(sectorIdInput, '123')

      // 关闭再打开弹窗
      rerender(<DataFixDialog {...defaultProps} open={false} />)
      rerender(<DataFixDialog {...defaultProps} open={true} />)

      // 表单应该被重置
      expect(screen.getByPlaceholderText('输入板块 ID')).toHaveValue('')
    })
  })
})
