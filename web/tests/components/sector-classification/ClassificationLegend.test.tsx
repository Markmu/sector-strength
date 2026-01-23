/**
 * ClassificationLegend 组件测试
 */

import { render, screen } from '@testing-library/react'
import { ClassificationLegend } from '@/components/sector-classification/ClassificationLegend'

describe('ClassificationLegend', () => {
  describe('渲染测试', () => {
    it('应该渲染所有9个分类级别', () => {
      render(<ClassificationLegend />)

      expect(screen.getByText('第 9 类')).toBeInTheDocument()
      expect(screen.getByText('第 8 类')).toBeInTheDocument()
      expect(screen.getByText('第 7 类')).toBeInTheDocument()
      expect(screen.getByText('第 6 类')).toBeInTheDocument()
      expect(screen.getByText('第 5 类')).toBeInTheDocument()
      expect(screen.getByText('第 4 类')).toBeInTheDocument()
      expect(screen.getByText('第 3 类')).toBeInTheDocument()
      expect(screen.getByText('第 2 类')).toBeInTheDocument()
      expect(screen.getByText('第 1 类')).toBeInTheDocument()
    })

    it('应该显示每个级别的描述', () => {
      render(<ClassificationLegend />)

      expect(screen.getByText('最强')).toBeInTheDocument()
      expect(screen.getByText('最弱')).toBeInTheDocument()
      expect(screen.getByText('攻克 240 日线')).toBeInTheDocument()
      expect(screen.getByText('攻克 10 日线')).toBeInTheDocument()
    })

    it('当 showTitle 为 true 时应该显示标题', () => {
      render(<ClassificationLegend showTitle={true} />)

      expect(screen.getByText('分类级别说明')).toBeInTheDocument()
    })

    it('当 showTitle 为 false 时不应该显示标题', () => {
      render(<ClassificationLegend showTitle={false} />)

      expect(screen.queryByText('分类级别说明')).not.toBeInTheDocument()
    })
  })

  describe('布局测试', () => {
    it('应该支持水平布局（默认）', () => {
      const { container } = render(<ClassificationLegend layout="horizontal" />)

      const badgesContainer = container.querySelector('.flex-wrap')
      expect(badgesContainer).toBeInTheDocument()
    })

    it('应该支持垂直布局', () => {
      const { container } = render(<ClassificationLegend layout="vertical" />)

      const badgesContainer = container.querySelector('.flex-col')
      expect(badgesContainer).toBeInTheDocument()
    })

    it('应该应用自定义 className', () => {
      const { container } = render(
        <ClassificationLegend className="custom-class" />
      )

      const legendContainer = container.firstChild
      expect(legendContainer).toHaveClass('custom-class')
    })
  })

  describe('样式和可访问性测试', () => {
    it('应该应用正确的颜色样式', () => {
      const { container } = render(<ClassificationLegend />)

      const badges = container.querySelectorAll('div[class*="bg-"]')
      expect(badges.length).toBeGreaterThan(0)

      // 检查第 9 类是祖母绿色（emerald）
      const level9Badge = screen.getByText('第 9 类').closest('div')
      expect(level9Badge).toHaveClass('bg-emerald-600')

      // 检查第 8 类是祖母绿色
      const level8Badge = screen.getByText('第 8 类').closest('div')
      expect(level8Badge).toHaveClass('bg-emerald-500')

      // 检查第 4 类是琥珀色
      const level4Badge = screen.getByText('第 4 类').closest('div')
      expect(level4Badge).toHaveClass('bg-amber-500')

      // 检查第 1 类是红色
      const level1Badge = screen.getByText('第 1 类').closest('div')
      expect(level1Badge).toHaveClass('bg-red-600')
    })

    it('颜色对比度应该符合可访问性要求', () => {
      render(<ClassificationLegend />)

      const level9Badge = screen.getByText('第 9 类').closest('div')
      expect(level9Badge).toHaveClass('text-white')  // 深绿背景用白色文字

      const level5Badge = screen.getByText('第 5 类').closest('div')
      expect(level5Badge).toHaveClass('text-black')  // 黄色背景用黑色文字
    })

    it('所有 badge 应该有 cursor-default 样式', () => {
      const { container } = render(<ClassificationLegend />)

      const badges = container.querySelectorAll('[class*="cursor-default"]')
      expect(badges.length).toBe(9)  // 9 个级别
    })
  })

  describe('内容测试', () => {
    it('应该显示完整的级别标签', () => {
      render(<ClassificationLegend />)

      // 验证所有级别的标签格式
      expect(screen.getByText('第 9 类: 最强')).toBeInTheDocument()
      expect(screen.getByText('第 8 类: 攻克 240 日线')).toBeInTheDocument()
      expect(screen.getByText('第 7 类: 攻克 120 日线')).toBeInTheDocument()
      expect(screen.getByText('第 6 类: 攻克 90 日线')).toBeInTheDocument()
      expect(screen.getByText('第 5 类: 攻克 60 日线')).toBeInTheDocument()
      expect(screen.getByText('第 4 类: 攻克 30 日线')).toBeInTheDocument()
      expect(screen.getByText('第 3 类: 攻克 20 日线')).toBeInTheDocument()
      expect(screen.getByText('第 2 类: 攻克 10 日线')).toBeInTheDocument()
      expect(screen.getByText('第 1 类: 最弱')).toBeInTheDocument()
    })

    it('所有 badge 应该有 whitespace-nowrap 类', () => {
      const { container } = render(<ClassificationLegend />)

      const badges = container.querySelectorAll('[class*="whitespace-nowrap"]')
      expect(badges.length).toBe(9)
    })
  })
})
