/**
 * AdminConfigDisplay 组件测试
 *
 * 测试配置展示组件的功能
 */

import { render, screen } from '@testing-library/react'
import { AdminConfigDisplay } from '@/components/admin/sector-classification/AdminConfigDisplay'
import { CLASSIFICATION_CONFIG } from '@/types/admin-config'

describe('AdminConfigDisplay', () => {
  it('应该显示所有配置参数', () => {
    render(<AdminConfigDisplay config={CLASSIFICATION_CONFIG} />)

    expect(screen.getByText('均线周期配置')).toBeInTheDocument()
    expect(screen.getByText('判断基准天数')).toBeInTheDocument()
    expect(screen.getByText('分类数量')).toBeInTheDocument()
    expect(screen.getByText('分类级别定义')).toBeInTheDocument()
  })

  it('应该显示所有均线周期', () => {
    render(<AdminConfigDisplay config={CLASSIFICATION_CONFIG} />)

    CLASSIFICATION_CONFIG.ma_periods.forEach((period) => {
      expect(screen.getByText(`${period} 日线`)).toBeInTheDocument()
    })
  })

  it('应该显示判断基准天数', () => {
    render(<AdminConfigDisplay config={CLASSIFICATION_CONFIG} />)

    expect(screen.getByText('5 天')).toBeInTheDocument()
  })

  it('应该显示分类数量', () => {
    render(<AdminConfigDisplay config={CLASSIFICATION_CONFIG} />)

    expect(screen.getByText('9 类')).toBeInTheDocument()
  })

  it('应该显示所有分类级别定义', () => {
    render(<AdminConfigDisplay config={CLASSIFICATION_CONFIG} />)

    CLASSIFICATION_CONFIG.level_definitions.forEach((def) => {
      expect(screen.getByText(def.name)).toBeInTheDocument()
      expect(screen.getByText(def.description)).toBeInTheDocument()
    })
  })
})
