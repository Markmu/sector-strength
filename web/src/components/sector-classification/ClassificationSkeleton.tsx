/**
 * 板块分类表格骨架屏组件
 *
 * 在数据加载时显示，模拟表格结构
 */

'use client'

import { cn } from '@/lib/utils'

/**
 * 骨架屏单元格组件
 */
interface SkeletonCellProps {
  className?: string
}

function SkeletonCell({ className }: SkeletonCellProps) {
  return (
    <div
      className={cn(
        'h-4 bg-gray-200 rounded animate-pulse',
        className
      )}
      aria-hidden="true"
    />
  )
}

/**
 * 骨架屏行组件
 */
interface SkeletonRowProps {
  cells: string[] // 每个单元格的宽度类名
}

function SkeletonRow({ cells }: SkeletonRowProps) {
  return (
    <tr aria-hidden="true">
      {cells.map((width, index) => (
        <td key={index} className="px-4 py-3 border-b border-gray-100">
          <SkeletonCell className={width} />
        </td>
      ))}
    </tr>
  )
}

/**
 * 分类表格骨架屏组件
 *
 * @description
 * 模拟表格结构，包括表头和 5 行数据
 * 用于页面加载时提供视觉反馈
 */
export function ClassificationSkeleton() {
  // 定义表格单元格宽度（模拟真实内容）
  const headerWidths = ['w-24', 'w-16', 'w-12', 'w-16', 'w-16']
  const rowWidths = [
    ['w-28', 'w-14', 'w-10', 'w-16', 'w-14'],
    ['w-32', 'w-14', 'w-10', 'w-16', 'w-12'],
    ['w-24', 'w-14', 'w-10', 'w-16', 'w-14'],
    ['w-30', 'w-14', 'w-10', 'w-16', 'w-12'],
    ['w-26', 'w-14', 'w-10', 'w-16', 'w-14'],
  ]

  return (
    <div
      className="bg-white rounded-xl border border-[#e9ecef] shadow-sm overflow-hidden"
      role="status"
    >
      {/* 骨架屏表格 */}
      <div className="overflow-x-auto">
        <table className="w-full">
          {/* 表头 */}
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-4 py-3 text-left">
                <SkeletonCell className="w-20" />
              </th>
              <th className="px-4 py-3 text-center">
                <SkeletonCell className="w-16" />
              </th>
              <th className="px-4 py-3 text-center">
                <SkeletonCell className="w-12" />
              </th>
              <th className="px-4 py-3 text-right">
                <SkeletonCell className="w-16" />
              </th>
              <th className="px-4 py-3 text-right">
                <SkeletonCell className="w-16" />
              </th>
            </tr>
          </thead>

          {/* 表体 */}
          <tbody>
            {rowWidths.map((widths, index) => (
              <SkeletonRow key={index} cells={widths} />
            ))}
          </tbody>
        </table>
      </div>

      {/* 屏幕阅读器文本 */}
      <span className="sr-only">正在加载板块分类数据...</span>
    </div>
  )
}

export default ClassificationSkeleton
