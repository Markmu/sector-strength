/**
 * ClassificationLevelDefinition 组件测试
 *
 * 测试分类级别定义展示组件的功能
 */

import { render, screen } from '@testing-library/react'
import { ClassificationLevelDefinition } from '@/components/admin/sector-classification/ClassificationLevelDefinition'
import { CLASSIFICATION_CONFIG } from '@/types/admin-config'

describe('ClassificationLevelDefinition', () => {
  it('应该显示分类级别定义表格', () => {
    render(
      <ClassificationLevelDefinition definitions={CLASSIFICATION_CONFIG.level_definitions} />
    )

    expect(screen.getByText('分类级别定义')).toBeInTheDocument()
  })

  it('应该显示所有级别', () => {
    render(
      <ClassificationLevelDefinition definitions={CLASSIFICATION_CONFIG.level_definitions} />
    )

    for (let i = 1; i <= 9; i++) {
      expect(screen.getByText(`第 ${i} 类`)).toBeInTheDocument()
    }
  })

  it('应该显示所有级别说明', () => {
    render(
      <ClassificationLevelDefinition definitions={CLASSIFICATION_CONFIG.level_definitions} />
    )

    expect(screen.getByText('价格在所有均线上方（最强）')).toBeInTheDocument()
    expect(screen.getByText('攻克 240 日线')).toBeInTheDocument()
    expect(screen.getByText('攻克 120 日线')).toBeInTheDocument()
    expect(screen.getByText('攻克 90 日线')).toBeInTheDocument()
    expect(screen.getByText('攻克 60 日线')).toBeInTheDocument()
    expect(screen.getByText('攻克 30 日线')).toBeInTheDocument()
    expect(screen.getByText('攻克 20 日线')).toBeInTheDocument()
    expect(screen.getByText('攻克 10 日线')).toBeInTheDocument()
    expect(screen.getByText('价格在所有均线下方（最弱）')).toBeInTheDocument()
  })

  it('应该显示强度标签', () => {
    render(
      <ClassificationLevelDefinition definitions={CLASSIFICATION_CONFIG.level_definitions} />
    )

    expect(screen.getByText('最强')).toBeInTheDocument()
    expect(screen.getByText('最弱')).toBeInTheDocument()
    expect(screen.getByText('强势')).toBeInTheDocument()
    expect(screen.getByText('中等')).toBeInTheDocument()
    expect(screen.getByText('弱势')).toBeInTheDocument()
  })

  it('应该有正确的表头', () => {
    render(
      <ClassificationLevelDefinition definitions={CLASSIFICATION_CONFIG.level_definitions} />
    )

    expect(screen.getByText('级别')).toBeInTheDocument()
    expect(screen.getByText('强度')).toBeInTheDocument()
    expect(screen.getByText('说明')).toBeInTheDocument()
  })
})
