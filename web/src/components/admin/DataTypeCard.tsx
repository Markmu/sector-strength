'use client'

import { Loader2 } from 'lucide-react'
import type { DataTypeStatus } from '@/hooks/useDataStatus'

interface DataTypeCardProps {
  data: DataTypeStatus
  onBackfill: (type: 'history' | 'ma' | 'strength') => void
  backfilling: boolean
}

/**
 * 单类数据状态卡片组件
 *
 * 根据 data.status 渲染不同状态：
 * - no_data: 灰色"暂无数据"Badge，无补齐按钮
 * - normal: 绿色"正常"Badge，显示最新日期
 * - missing: 橙色"缺失"Badge，显示最新日期 + 缺失范围 + 补齐按钮
 *
 * active_task 渲染：
 * - pending/running: 进度条 + 百分比文字
 * - failed: 红色错误信息 + "重新补齐"按钮
 * - completed/null: 不显示任务信息
 */
export default function DataTypeCard({ data, onBackfill, backfilling }: DataTypeCardProps) {
  const { type, label, latest_date, status, missing_range, active_task } = data

  // 活跃任务（pending/running）时显示进度条
  const isActiveTask = active_task?.status === 'pending' || active_task?.status === 'running'
  // 失败任务
  const isFailedTask = active_task?.status === 'failed'

  // 计算进度百分比
  const progressPercent =
    isActiveTask && active_task!.total > 0
      ? Math.round((active_task!.progress / active_task!.total) * 100)
      : 0

  // 是否显示补齐按钮：缺失状态 且 没有活跃任务 且 没有失败任务
  const showBackfillButton = status === 'missing' && !isActiveTask

  return (
    <div
      data-testid={`data-type-card-${type}`}
      className="border rounded-lg p-4 space-y-3"
    >
      {/* 卡片标题行 */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-foreground">{label}</h3>
        {status === 'no_data' && (
          <span
            data-testid="status-badge"
            className="px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-500"
          >
            暂无数据
          </span>
        )}
        {status === 'normal' && (
          <span
            data-testid="status-badge"
            className="px-2 py-0.5 rounded-full text-xs font-medium bg-slate-700 text-white"
          >
            正常
          </span>
        )}
        {status === 'missing' && (
          <span
            data-testid="status-badge"
            className="px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700"
          >
            缺失
          </span>
        )}
      </div>

      {/* 最新日期 */}
      {latest_date && (
        <div className="text-sm text-muted-foreground">
          最新日期：{latest_date}
        </div>
      )}

      {/* 缺失范围 */}
      {status === 'missing' && missing_range && (
        <div data-testid="missing-range" className="text-sm text-amber-600">
          缺失范围：{missing_range.start} ~ {missing_range.end}
        </div>
      )}

      {/* 活跃任务进度条 */}
      {isActiveTask && (
        <div className="space-y-1">
          <div
            data-testid="progress-bar"
            className="w-full bg-blue-100 rounded-full h-2"
          >
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          <div className="text-xs text-muted-foreground text-right">
            {progressPercent}%
          </div>
        </div>
      )}

      {/* 失败任务错误信息 + 重新补齐按钮 */}
      {isFailedTask && (
        <div className="space-y-2">
          <div
            data-testid="task-error-message"
            className="text-sm text-red-600"
          >
            {active_task!.error_message || '补齐任务失败'}
          </div>
          <button
            data-testid="retry-backfill-button"
            onClick={() => onBackfill(type)}
            disabled={backfilling}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-blue-600 bg-blue-50 rounded-md hover:bg-blue-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {backfilling && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            重新补齐
          </button>
        </div>
      )}

      {/* 补齐按钮 */}
      {showBackfillButton && (
        <button
          data-testid="backfill-button"
          onClick={() => onBackfill(type)}
          disabled={backfilling}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {backfilling && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
          补齐缺失数据
        </button>
      )}
    </div>
  )
}
