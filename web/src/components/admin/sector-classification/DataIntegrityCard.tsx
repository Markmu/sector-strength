'use client'

import { Card, CardHeader, CardBody } from '@/components/ui/Card'
import { CheckCircle2, AlertTriangle, Database } from 'lucide-react'
import type { DataIntegrityCardProps } from './DataIntegrityCard.types'

/**
 * DataIntegrityCard - 数据完整性卡片
 *
 * @description
 * 显示板块分类数据的完整性状态：
 * - 数据覆盖率百分比
 * - 总板块数和有数据板块数
 * - 缺失数据的板块列表（如果有）
 *
 * @param dataIntegrity - 数据完整性信息
 * @param loading - 加载状态
 */
export function DataIntegrityCard({
  dataIntegrity,
  loading,
}: DataIntegrityCardProps) {
  if (loading || !dataIntegrity) {
    return null
  }

  const isComplete = dataIntegrity.missing_sectors.length === 0
  const completionRate =
    dataIntegrity.total_sectors > 0
      ? (dataIntegrity.sectors_with_data / dataIntegrity.total_sectors) * 100
      : 0

  return (
    <Card
      className={
        isComplete ? 'border-green-200 bg-green-50' : 'border-amber-200 bg-amber-50'
      }
    >
      <CardHeader>
        <div className="flex items-center gap-2">
          {isComplete ? (
            <CheckCircle2 className="w-5 h-5 text-green-600" />
          ) : (
            <AlertTriangle className="w-5 h-5 text-amber-600" />
          )}
          <h4 className="font-semibold text-[#1a1a2e]">数据完整性</h4>
        </div>
      </CardHeader>
      <CardBody>
        <div className="space-y-4">
          {/* 完整性概览 */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Database className="w-4 h-4 text-cyan-600" />
              <span className="text-sm text-[#6c757d]">数据覆盖率</span>
            </div>
            <span
              className={`text-lg font-bold ${
                isComplete ? 'text-green-600' : 'text-amber-600'
              }`}
            >
              {completionRate.toFixed(1)}%
            </span>
          </div>

          {/* 详细统计 */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-[#6c757d]">总板块数</p>
              <p className="text-2xl font-bold text-[#1a1a2e]">
                {dataIntegrity.total_sectors}
              </p>
            </div>
            <div>
              <p className="text-sm text-[#6c757d]">有数据板块</p>
              <p className="text-2xl font-bold text-cyan-600">
                {dataIntegrity.sectors_with_data}
              </p>
            </div>
          </div>

          {/* 缺失板块列表 */}
          {!isComplete && dataIntegrity.missing_sectors.length > 0 && (
            <div className="border-t border-amber-200 pt-4">
              <p className="text-sm font-semibold text-amber-900 mb-2">
                缺失数据的板块：
              </p>
              <ul className="text-sm text-amber-700 space-y-1">
                {dataIntegrity.missing_sectors.map((sector) => (
                  <li key={sector.sector_id}>{sector.sector_name}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </CardBody>
    </Card>
  )
}
