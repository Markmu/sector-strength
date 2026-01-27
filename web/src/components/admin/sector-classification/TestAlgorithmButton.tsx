'use client'

import Button from '@/components/ui/Button'
import { Play, Loader2 } from 'lucide-react'
import type { TestAlgorithmButtonProps } from './TestAlgorithmButton.types'

/**
 * TestAlgorithmButton - 测试分类算法按钮组件
 *
 * @description
 * 管理员点击此按钮执行分类算法测试：
 * - 显示"测试分类算法"按钮
 * - 测试中显示"测试中..."加载状态
 * - 使用项目 Button 组件和 lucide-react 图标
 *
 * @param testing - 是否正在测试
 * @param onTest - 测试按钮点击回调
 * @param disabled - 是否禁用（可选）
 */
export function TestAlgorithmButton({
  testing,
  onTest,
  disabled = false,
}: TestAlgorithmButtonProps) {
  return (
    <Button
      onClick={onTest}
      disabled={disabled || testing}
      variant="primary"
      className="inline-flex items-center gap-2"
    >
      {testing ? (
        <>
          <Loader2 className="w-4 h-4 animate-spin" />
          <span>测试中...</span>
        </>
      ) : (
        <>
          <Play className="w-4 h-4" />
          <span>测试分类算法</span>
        </>
      )}
    </Button>
  )
}
