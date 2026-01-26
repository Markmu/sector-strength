/**
 * Disclaimer 组件测试
 */

import { render, screen } from '@testing-library/react'
import { Disclaimer } from '@/components/ui/Disclaimer'

describe('Disclaimer', () => {
  it('应该显示完整的免责声明文本（包含缠论说明）', () => {
    render(<Disclaimer />)

    expect(screen.getByText(/数据仅供参考，不构成投资建议/)).toBeInTheDocument()
    expect(screen.getByText(/投资有风险，入市需谨慎/)).toBeInTheDocument()
    expect(screen.getByText(/板块强弱分类基于缠中说禅理论/)).toBeInTheDocument()
  })

  it('应该应用正确的样式类', () => {
    const { container } = render(<Disclaimer />)

    const text = screen.getByText(/数据仅供参考/)
    expect(text).toHaveClass('text-xs', 'text-gray-500')
  })

  it('应该显示自定义文本', () => {
    const customText = '自定义免责声明内容'
    render(<Disclaimer text={customText} />)

    expect(screen.getByText(customText)).toBeInTheDocument()
  })

  it('应该显示分隔线当 showSeparator 为 true', () => {
    const { container } = render(<Disclaimer showSeparator={true} />)

    const separator = container.querySelector('[role="separator"]')
    expect(separator).toBeInTheDocument()
    expect(separator).toHaveClass('border-t', 'border-gray-200')
  })

  it('应该不显示分隔线当 showSeparator 为 false', () => {
    const { container } = render(<Disclaimer showSeparator={false} />)

    const separator = container.querySelector('[role="separator"]')
    expect(separator).not.toBeInTheDocument()
  })

  it('应该有正确的可访问性属性', () => {
    render(<Disclaimer />)

    const footer = screen.getByRole('contentinfo')
    expect(footer).toBeInTheDocument()
    expect(footer).toHaveAttribute('aria-label', '免责声明')
  })

  it('文本颜色对比度应该符合可访问性标准', () => {
    const { container } = render(<Disclaimer />)

    const text = screen.getByText(/数据仅供参考/)
    expect(text).toHaveClass('text-gray-500')
    // text-gray-500 (rgb(107, 114, 128)) on white background has contrast ratio ~7:1 (AA compliant)
  })

  it('应该支持自定义类名', () => {
    const { container } = render(<Disclaimer className="custom-class" />)

    const footer = container.querySelector('footer')
    expect(footer).toHaveClass('custom-class')
  })

  it('应该包含免责声明前缀', () => {
    render(<Disclaimer />)

    const prefix = screen.getByText(/免责声明：/)
    expect(prefix).toBeInTheDocument()
    expect(prefix).toHaveClass('font-medium')
  })
})
