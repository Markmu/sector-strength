'use client'

import { Badge } from '@/components/ui/badge'

export interface ClassificationLegendProps {
  /**
   * 自定义类名（可选）
   */
  className?: string
  /**
   * 是否显示标题（默认 false）
   */
  showTitle?: boolean
  /**
   * 布局方向（默认 horizontal）
   */
  layout?: 'horizontal' | 'vertical'
}

/**
 * 图例项数据结构
 */
interface LegendItem {
  level: number
  label: string
  colorClass: string
  description: string
}

/**
 * 分类级别图例数据
 *
 * 颜色模式：与 LEVEL_COLOR_MAP 保持一致（使用 emerald 色系）
 * - 第 9 类：深祖母绿色（最强）
 * - 第 8 类：祖母绿色系
 * - 第 7 类：绿色
 * - 第 6 类：青绿色
 * - 第 5 类：黄色
 * - 第 4 类：琥珀色
 * - 第 3 类：橙色
 * - 第 2 类：红色系
 * - 第 1 类：深红色（最弱）
 */
/**
 * 分类级别图例数据
 *
 * 颜色模式：与 LEVEL_COLOR_MAP 保持一致（使用 emerald 色系）
 * - 第 9 类：深祖母绿色（最强）
 * - 第 8 类：祖母绿色系
 * - 第 7 类：绿色
 * - 第 6 类：青绿色
 * - 第 5 类：黄色
 * - 第 4 类：琥珀色
 * - 第 3 类：橙色
 * - 第 2 类：红色系
 * - 第 1 类：深红色（最弱）
 */
const LEGEND_ITEMS: LegendItem[] = [
  { level: 9, label: '第 9 类', colorClass: 'bg-emerald-600 text-white hover:bg-emerald-700', description: '最强' },
  { level: 8, label: '第 8 类', colorClass: 'bg-emerald-500 text-white hover:bg-emerald-600', description: '攻克 240 日线' },
  { level: 7, label: '第 7 类', colorClass: 'bg-green-500 text-white hover:bg-green-600', description: '攻克 120 日线' },
  { level: 6, label: '第 6 类', colorClass: 'bg-lime-500 text-white hover:bg-lime-600', description: '攻克 90 日线' },
  { level: 5, label: '第 5 类', colorClass: 'bg-yellow-500 text-black hover:bg-yellow-600', description: '攻克 60 日线' },
  { level: 4, label: '第 4 类', colorClass: 'bg-amber-500 text-white hover:bg-amber-600', description: '攻克 30 日线' },
  { level: 3, label: '第 3 类', colorClass: 'bg-orange-500 text-white hover:bg-orange-600', description: '攻克 20 日线' },
  { level: 2, label: '第 2 类', colorClass: 'bg-red-400 text-white hover:bg-red-500', description: '攻克 10 日线' },
  { level: 1, label: '第 1 类', colorClass: 'bg-red-600 text-white hover:bg-red-700', description: '最弱' },
] as const

/**
 * 分类级别图例组件
 *
 * 显示所有 9 个分类级别的颜色图例，帮助用户理解颜色编码的含义。
 *
 * @description
 * - 使用 shadcn/ui Badge 组件显示每个级别
 * - 支持水平或垂直布局
 * - 可选标题显示
 * - 颜色对比度符合可访问性要求（WCAG AA）
 * - 响应式设计（移动端自动换行）
 *
 * @example
 * ```tsx
 * // 水平布局（默认）
 * <ClassificationLegend />
 *
 * // 垂直布局
 * <ClassificationLegend layout="vertical" />
 *
 * // 显示标题
 * <ClassificationLegend showTitle={true} />
 * ```
 */
export function ClassificationLegend({
  className = '',
  showTitle = false,
  layout = 'horizontal'
}: ClassificationLegendProps) {
  const isHorizontal = layout === 'horizontal'

  return (
    <div className={`space-y-2 ${className}`}>
      {showTitle && (
        <h3 className="text-sm font-semibold text-gray-700">分类级别说明</h3>
      )}

      <div className={`flex ${isHorizontal ? 'flex-wrap gap-2' : 'flex-col gap-2'}`}>
        {LEGEND_ITEMS.map((item) => (
          <Badge
            key={item.level}
            className={`${item.colorClass} text-xs font-medium whitespace-nowrap cursor-default transition-colors`}
          >
            {item.label}: {item.description}
          </Badge>
        ))}
      </div>
    </div>
  )
}

export default ClassificationLegend
