/**
 * HelpButton 组件测试
 */

import { render, screen, fireEvent } from '@testing-library/react'
import { HelpButton } from '@/components/sector-classification/HelpButton'

describe('HelpButton', () => {
  it('应该渲染帮助图标按钮', () => {
    const handleClick = jest.fn()
    render(<HelpButton onClick={handleClick} />)

    const button = screen.getByRole('button', { name: '查看帮助' })
    expect(button).toBeInTheDocument()
    expect(button).toHaveAttribute('title', '查看板块强弱分类说明')
  })

  it('应该调用 onClick 回调', () => {
    const handleClick = jest.fn()
    render(<HelpButton onClick={handleClick} />)

    const button = screen.getByRole('button', { name: '查看帮助' })
    fireEvent.click(button)

    expect(handleClick).toHaveBeenCalledTimes(1)
  })

  it('应该应用自定义 className', () => {
    const handleClick = jest.fn()
    const { container } = render(
      <HelpButton onClick={handleClick} className="custom-class" />
    )

    const button = screen.getByRole('button')
    expect(button).toHaveClass('custom-class')
  })

  it('应该有正确的可访问性属性', () => {
    const handleClick = jest.fn()
    render(<HelpButton onClick={handleClick} />)

    const button = screen.getByRole('button', { name: '查看帮助' })
    expect(button).toHaveAttribute('aria-label', '查看帮助')
    expect(button).toHaveAttribute('type', 'button')
  })
})
