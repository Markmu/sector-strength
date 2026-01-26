'use client'

import { Card, CardHeader, CardBody } from '@/components/ui/Card'
import Table from '@/components/ui/Table'
import type { ClassificationLevelDefinition as ClassificationLevelDefinitionType } from '@/types/admin-config'
import { getLevelStrengthLabel, getLevelBadgeColor } from '@/types/admin-config'
import type { ClassificationLevelDefinitionProps } from './ClassificationLevelDefinition.types'

/**
 * ClassificationLevelDefinition - 分类级别定义组件
 *
 * @description
 * 使用表格展示缠论板块强弱分类的 9 个级别定义
 * 从第 9 类（最强）到第 1 类（最弱）
 * 使用颜色标识表示强度梯度（绿色→红色）
 */
export function ClassificationLevelDefinition({ definitions }: ClassificationLevelDefinitionProps) {
  const columns = [
    {
      key: 'level',
      title: '级别',
      width: '100px',
      align: 'left' as const,
      render: (_: any, record: ClassificationLevelDefinitionType) => (
        <span className={`font-semibold ${record.color}`}>
          {record.name}
        </span>
      ),
    },
    {
      key: 'strength',
      title: '强度',
      width: '100px',
      align: 'center' as const,
      render: (_: any, record: ClassificationLevelDefinitionType) => (
        <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${getLevelBadgeColor(record.level)}`}>
          {getLevelStrengthLabel(record.level)}
        </span>
      ),
    },
    {
      key: 'description',
      title: '说明',
      align: 'left' as const,
    },
  ]

  return (
    <Card>
      <CardHeader>
        <h3 className="text-lg font-semibold text-[#1a1a2e]">分类级别定义</h3>
        <p className="text-sm text-[#6c757d]">缠论板块强弱分类的完整级别说明（第 9 类 → 第 1 类）</p>
      </CardHeader>
      <CardBody>
        <Table
          columns={columns}
          data={definitions}
          bordered
          compact
        />
      </CardBody>
    </Card>
  )
}
