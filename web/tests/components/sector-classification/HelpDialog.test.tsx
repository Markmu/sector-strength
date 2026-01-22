/**
 * HelpDialog 组件测试
 */

import { render, screen, fireEvent } from '@testing-library/react'
import { HelpDialog } from '@/components/sector-classification/HelpDialog'

describe('HelpDialog', () => {
  it('当 open 为 false 时不应该显示弹窗', () => {
    render(<HelpDialog open={false} onOpenChange={jest.fn()} />)

    expect(screen.queryByText('板块强弱分类说明')).not.toBeInTheDocument()
  })

  it('当 open 为 true 时应该显示弹窗', () => {
    render(<HelpDialog open={true} onOpenChange={jest.fn()} />)

    expect(screen.getByText('板块强弱分类说明')).toBeInTheDocument()
  })

  it('应该显示所有分类级别说明', () => {
    render(<HelpDialog open={true} onOpenChange={jest.fn()} />)

    expect(screen.getByText('第 9 类')).toBeInTheDocument()
    expect(screen.getByText('最强，价格在所有均线上方')).toBeInTheDocument()
    expect(screen.getByText('第 1 类')).toBeInTheDocument()
    expect(screen.getByText('最弱，价格在所有均线下方')).toBeInTheDocument()
  })

  it('应该显示反弹/调整状态说明', () => {
    render(<HelpDialog open={true} onOpenChange={jest.fn()} />)

    expect(screen.getByText('反弹')).toBeInTheDocument()
    expect(screen.getByText('当前价格高于 5 天前价格')).toBeInTheDocument()
    expect(screen.getByText('调整')).toBeInTheDocument()
    expect(screen.getByText('当前价格低于 5 天前价格')).toBeInTheDocument()
  })

  it('应该调用 onOpenChange 当点击关闭按钮', () => {
    const handleClose = jest.fn()
    render(<HelpDialog open={true} onOpenChange={handleClose} />)

    const closeButton = screen.getByRole('button', { name: /close/i })
    fireEvent.click(closeButton)

    expect(handleClose).toHaveBeenCalledWith(false)
  })

  it('应该调用 onOpenChange 当按 ESC 键', () => {
    const handleClose = jest.fn()
    render(<HelpDialog open={true} onOpenChange={handleClose} />)

    fireEvent.keyDown(document, { key: 'Escape', code: 'Escape' })

    expect(handleClose).toHaveBeenCalledWith(false)
  })

  it('应该显示理论依据说明', () => {
    render(<HelpDialog open={true} onOpenChange={jest.fn()} />)

    expect(screen.getByText('理论依据：')).toBeInTheDocument()
    expect(screen.getByText(/板块强弱分类基于缠中说禅理论/)).toBeInTheDocument()
  })

  it('应该有正确的可访问性属性', () => {
    render(<HelpDialog open={true} onOpenChange={jest.fn()} />)

    const dialog = screen.getByRole('dialog')
    expect(dialog).toBeInTheDocument()
    expect(dialog).toHaveAttribute('aria-modal', 'true')
  })
})
