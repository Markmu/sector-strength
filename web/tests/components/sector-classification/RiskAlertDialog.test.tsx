import { render, screen, fireEvent } from '@testing-library/react'
import { RiskAlertDialog } from '@/components/sector-classification/RiskAlertDialog'

describe('RiskAlertDialog', () => {
  it('当 open 为 true 时应该显示弹窗', () => {
    const handleClose = jest.fn()
    const handleConfirm = jest.fn()

    render(
      <RiskAlertDialog
        open={true}
        onOpenChange={handleClose}
        onConfirm={handleConfirm}
      />
    )

    expect(screen.getByText('重要提示')).toBeInTheDocument()
    expect(screen.getByText(/板块分类数据仅供参考/)).toBeInTheDocument()
  })

  it('当 open 为 false 时不应该显示弹窗', () => {
    const handleClose = jest.fn()
    const handleConfirm = jest.fn()

    render(
      <RiskAlertDialog
        open={false}
        onOpenChange={handleClose}
        onConfirm={handleConfirm}
      />
    )

    expect(screen.queryByText('重要提示')).not.toBeInTheDocument()
  })

  it('应该显示所有风险提示内容', () => {
    const handleClose = jest.fn()
    const handleConfirm = jest.fn()

    render(
      <RiskAlertDialog
        open={true}
        onOpenChange={handleClose}
        onConfirm={handleConfirm}
      />
    )

    expect(screen.getByText(/板块分类数据仅供参考/)).toBeInTheDocument()
    expect(screen.getByText(/股票市场有风险/)).toBeInTheDocument()
    expect(screen.getByText(/过往表现不代表未来收益/)).toBeInTheDocument()
    expect(screen.getByText(/根据自己的风险承受能力/)).toBeInTheDocument()
  })

  it('应该调用 onConfirm 当点击确认按钮', () => {
    const handleClose = jest.fn()
    const handleConfirm = jest.fn()

    render(
      <RiskAlertDialog
        open={true}
        onOpenChange={handleClose}
        onConfirm={handleConfirm}
      />
    )

    const confirmButton = screen.getByRole('button', { name: '我已知晓并理解' })
    fireEvent.click(confirmButton)

    expect(handleConfirm).toHaveBeenCalledTimes(1)
  })

  it('应该有警告图标', () => {
    const handleClose = jest.fn()
    const handleConfirm = jest.fn()

    render(
      <RiskAlertDialog
        open={true}
        onOpenChange={handleClose}
        onConfirm={handleConfirm}
      />
    )

    // 检查 AlertTriangle 图标（通过 SVG 元素）
    const icon = document.querySelector('svg')
    expect(icon).toBeInTheDocument()
  })

  it('应该有正确的可访问性属性', () => {
    const handleClose = jest.fn()
    const handleConfirm = jest.fn()

    render(
      <RiskAlertDialog
        open={true}
        onOpenChange={handleClose}
        onConfirm={handleConfirm}
      />
    )

    const dialog = screen.getByRole('alertdialog')
    expect(dialog).toBeInTheDocument()
    expect(dialog).toHaveAttribute('aria-modal', 'true')
  })
})
