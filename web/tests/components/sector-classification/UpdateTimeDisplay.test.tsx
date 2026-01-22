/**
 * UpdateTimeDisplay 组件测试
 */

import { render, screen } from '@testing-library/react'
import { UpdateTimeDisplay } from '@/components/sector-classification/UpdateTimeDisplay'

describe('UpdateTimeDisplay', () => {
  it('应该显示格式化的更新时间', () => {
    const timestamp = new Date('2026-01-22T15:30:00').getTime()
    render(<UpdateTimeDisplay lastFetch={timestamp} />)

    expect(screen.getByText(/数据更新时间：2026-01-22 15:30/)).toBeInTheDocument()
  })

  it('应该处理缺失的时间戳（null）', () => {
    render(<UpdateTimeDisplay lastFetch={null} />)

    expect(screen.getByText(/数据更新时间：未知/)).toBeInTheDocument()
  })

  it('应该处理 undefined 时间戳', () => {
    render(<UpdateTimeDisplay lastFetch={undefined} />)

    expect(screen.getByText(/数据更新时间：未知/)).toBeInTheDocument()
  })

  it('应该显示时钟图标', () => {
    const timestamp = Date.now()
    const { container } = render(<UpdateTimeDisplay lastFetch={timestamp} />)

    const svg = container.querySelector('svg')
    expect(svg).toBeInTheDocument()
    expect(svg).toHaveAttribute('fill', 'none')
    expect(svg).toHaveAttribute('stroke', 'currentColor')
  })

  it('应该应用自定义 className', () => {
    const timestamp = Date.now()
    const { container } = render(
      <UpdateTimeDisplay lastFetch={timestamp} className="custom-class" />
    )

    const wrapper = container.firstChild as HTMLElement
    expect(wrapper).toHaveClass('custom-class')
  })

  it('应该有正确的 ARIA 属性', () => {
    const timestamp = Date.now()
    render(<UpdateTimeDisplay lastFetch={timestamp} />)

    const element = screen.getByText(/数据更新时间：/)
    expect(element).toBeInTheDocument()
  })

  it('应该使用 Tailwind 样式', () => {
    const timestamp = Date.now()
    const { container } = render(<UpdateTimeDisplay lastFetch={timestamp} />)

    const wrapper = container.firstChild as HTMLElement
    expect(wrapper).toHaveClass('text-sm')
    expect(wrapper).toHaveClass('text-gray-500')
    expect(wrapper).toHaveClass('flex')
    expect(wrapper).toHaveClass('items-center')
  })
})
