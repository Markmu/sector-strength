/**
 * 板块强弱分类表格组件
 *
 * 显示所有板块的分类结果，包括：
 * - 板块名称
 * - 分类级别（第 1 类 ~ 第 9 类）
 * - 状态（反弹/调整）
 * - 当前价格
 * - 涨跌幅（%）
 */

'use client'

import { useMemo } from 'react'
import { TrendingUp, TrendingDown } from 'lucide-react'
import Table, { type TableColumn } from '@/components/ui/table'
import type {
  SectorClassification,
  ClassificationState,
} from '@/types/sector-classification'
import {
  getLevelColor,
  getChangeColor,
  getStateColor,
} from '@/types/sector-classification'

export interface ClassificationTableProps {
  /** 分类数据列表 */
  data: SectorClassification[]
  /** 是否正在加载 */
  loading?: boolean
  /** 空数据提示文本 */
  emptyText?: string
  /** 行点击回调 */
  onRowClick?: (record: SectorClassification, index: number) => void
  /** 表格类名 */
  className?: string
}

/**
 * 分类表格组件
 *
 * @description
 * 按分类级别降序排列（第 9 类在前）
 * 使用颜色和图标直观展示板块强弱状态
 */
export function ClassificationTable({
  data,
  loading = false,
  emptyText = '暂无分类数据',
  onRowClick,
  className,
}: ClassificationTableProps) {
  // 按分类级别降序排列（第 9 类在前）
  const sortedData = useMemo(() => {
    return [...data].sort((a, b) => b.classification_level - a.classification_level)
  }, [data])

  // 渲染分类级别徽章
  const renderLevelBadge = (level: number) => {
    const colors = getLevelColor(level)
    return (
      <span
        className={`inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold border ${colors.bg} ${colors.text} ${colors.border}`}
      >
        第 {level} 类
      </span>
    )
  }

  // 渲染状态图标
  const renderStateIcon = (state: ClassificationState) => {
    const color = getStateColor(state)
    const isBounce = state === '反弹'

    return (
      <span className={`inline-flex items-center gap-1.5 ${color} font-medium`}>
        {isBounce ? (
          <TrendingUp className="w-4 h-4" aria-label="反弹" />
        ) : (
          <TrendingDown className="w-4 h-4" aria-label="调整" />
        )}
        {state}
      </span>
    )
  }

  // 渲染涨跌幅
  const renderChangePercent = (value: number) => {
    const color = getChangeColor(value)
    const sign = value > 0 ? '+' : ''

    return (
      <span className={`font-semibold tabular-nums ${color}`}>
        {sign}{value.toFixed(2)}%
      </span>
    )
  }

  // 表格列定义
  const columns: TableColumn<SectorClassification>[] = [
    {
      key: 'sector_name',
      title: '板块名称',
      align: 'left',
      render: (_, record) => (
        <span className="font-medium text-[#1a1a2e]">{record.sector_name}</span>
      ),
    },
    {
      key: 'classification_level',
      title: '分类级别',
      align: 'center',
      render: (_, record) => renderLevelBadge(record.classification_level),
    },
    {
      key: 'state',
      title: '状态',
      align: 'center',
      render: (_, record) => renderStateIcon(record.state),
    },
    {
      key: 'current_price',
      title: '当前价格',
      align: 'right',
      render: (_, record) => (
        <span className="tabular-nums text-[#1a1a2e]">
          {record.current_price.toFixed(2)}
        </span>
      ),
    },
    {
      key: 'change_percent',
      title: '涨跌幅',
      align: 'right',
      render: (_, record) => renderChangePercent(record.change_percent),
    },
  ]

  return (
    <Table
      columns={columns}
      data={sortedData}
      loading={loading}
      emptyText={emptyText}
      onRowClick={onRowClick}
      rowKey="id"
      striped
      bordered
      hoverable={!!onRowClick}
      className={className}
    />
  )
}

export default ClassificationTable
