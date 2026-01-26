'use client'

import { Card, CardHeader, CardBody } from '@/components/ui/Card'
import {
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  TrendingUp,
} from 'lucide-react'
import type { DataFixStatusProps } from './DataFixStatus.types.ts'
import { DataFixStatus as FixStatus } from '@/types/data-fix'

/**
 * 数据修复状态显示组件
 *
 * @description
 * Story 4.5: Task 2
 * 显示数据修复的状态和结果
 *
 * @param status - 修复状态
 * @param result - 修复结果
 * @param error - 错误信息
 */
export function DataFixStatus({
  status,
  result,
  error,
}: DataFixStatusProps) {
  // 未开始状态不显示任何内容
  if (status === FixStatus.IDLE) {
    return null
  }

  return (
    <Card>
      <CardHeader>
        <h3 className="text-lg font-semibold text-[#1a1a2e]">
          修复状态
        </h3>
      </CardHeader>
      <CardBody>
        {/* 验证中 */}
        {status === FixStatus.VALIDATING && (
          <div className="flex items-center gap-3 text-cyan-600">
            <Loader2 className="w-5 h-5 animate-spin" />
            <span>验证中...</span>
          </div>
        )}

        {/* 修复中 */}
        {status === FixStatus.FIXING && (
          <div className="flex items-center gap-3 text-cyan-600">
            <Loader2 className="w-5 h-5 animate-spin" />
            <span>修复中，请稍候...</span>
          </div>
        )}

        {/* 成功 */}
        {status === FixStatus.SUCCESS && result && (
          <div className="space-y-4">
            <div className="flex items-center gap-3 text-green-600">
              <CheckCircle2 className="w-5 h-5" />
              <span className="font-semibold">修复完成！</span>
            </div>

            <div className="grid grid-cols-2 gap-4">
              {/* 成功修复 */}
              <div className="p-4 bg-green-50 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle2 className="w-4 h-4 text-green-600" />
                  <p className="text-sm text-[#6c757d]">成功修复</p>
                </div>
                <p className="text-2xl font-bold text-green-600">
                  {result.success_count}
                </p>
              </div>

              {/* 修复失败 */}
              {result.failed_count > 0 && (
                <div className="p-4 bg-red-50 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <XCircle className="w-4 h-4 text-red-600" />
                    <p className="text-sm text-[#6c757d]">修复失败</p>
                  </div>
                  <p className="text-2xl font-bold text-red-600">
                    {result.failed_count}
                  </p>
                </div>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4">
              {/* 修复耗时 */}
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <Clock className="w-4 h-4 text-cyan-600" />
                  <p className="text-sm text-[#6c757d]">修复耗时</p>
                </div>
                <p className="text-base font-semibold text-[#1a1a2e]">
                  {result.duration_seconds.toFixed(2)} 秒
                </p>
              </div>

              {/* 平均耗时 */}
              {result.success_count > 0 && (
                <div className="p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <TrendingUp className="w-4 h-4 text-cyan-600" />
                    <p className="text-sm text-[#6c757d]">平均耗时</p>
                  </div>
                  <p className="text-base font-semibold text-[#1a1a2e]">
                    {(result.duration_seconds / result.success_count).toFixed(2)} 秒/板块
                  </p>
                </div>
              )}
            </div>

            {/* 修复详情 */}
            {result.sectors.length > 0 && (
              <div className="border-t pt-4">
                <p className="text-sm font-semibold text-[#1a1a2e] mb-2">
                  修复详情
                </p>
                <div className="space-y-1 max-h-48 overflow-y-auto">
                  {result.sectors.map((sector) => (
                    <div
                      key={sector.sector_id}
                      className={`flex items-center justify-between text-sm p-2 rounded ${
                        sector.success
                          ? 'bg-green-50'
                          : 'bg-red-50'
                      }`}
                    >
                      <span className={sector.success ? 'text-green-900' : 'text-red-900'}>
                        {sector.sector_name}
                      </span>
                      {sector.success ? (
                        <CheckCircle2 className="w-4 h-4 text-green-600" />
                      ) : (
                        <span className="text-red-600">{sector.error || '失败'}</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* 失败 */}
        {status === FixStatus.ERROR && (
          <div className="space-y-4">
            <div className="flex items-center gap-3 text-red-600">
              <XCircle className="w-5 h-5" />
              <span className="font-semibold">修复失败</span>
            </div>
            {error && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-red-700">{error}</p>
              </div>
            )}
          </div>
        )}
      </CardBody>
    </Card>
  )
}
