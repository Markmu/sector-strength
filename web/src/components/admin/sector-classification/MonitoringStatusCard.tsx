'use client'

import { Card, CardHeader, CardBody } from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  RefreshCw,
  Clock,
  Activity,
  TrendingUp,
} from 'lucide-react'
import type { MonitoringStatusCardProps } from './MonitoringStatusCard.types'
import type { CalculationStatusType } from '@/types/admin-monitoring'

/**
 * MonitoringStatusCard - 运行状态监控卡片
 *
 * @description
 * 显示板块分类计算的实时运行状态：
 * - 最后计算时间
 * - 计算状态（正常/异常/失败）
 * - 计算耗时
 * - 今日计算次数
 * - 提供手动刷新按钮
 *
 * @param status - 监控状态数据
 * @param loading - 加载状态
 * @param error - 错误信息
 * @param onRefresh - 刷新回调
 */
export function MonitoringStatusCard({
  status,
  loading,
  error,
  onRefresh,
}: MonitoringStatusCardProps) {
  // 获取状态图标和颜色
  const getStatusDisplay = (): {
    icon: React.ReactNode
    text: string
    color: string
    bgColor: string
  } => {
    if (loading) {
      return {
        icon: <RefreshCw className="w-5 h-5 animate-spin text-cyan-600" />,
        text: '加载中...',
        color: 'text-cyan-600',
        bgColor: 'bg-cyan-50',
      }
    }

    if (error || !status) {
      return {
        icon: <XCircle className="w-5 h-5 text-red-600" />,
        text: '获取状态失败',
        color: 'text-red-600',
        bgColor: 'bg-red-50',
      }
    }

    switch (status.calculation_status) {
      case 'normal':
        return {
          icon: <CheckCircle2 className="w-5 h-5 text-green-600" />,
          text: '正常',
          color: 'text-green-600',
          bgColor: 'bg-green-50',
        }
      case 'abnormal':
        return {
          icon: <AlertTriangle className="w-5 h-5 text-amber-600" />,
          text: '异常',
          color: 'text-amber-600',
          bgColor: 'bg-amber-50',
        }
      case 'failed':
        return {
          icon: <XCircle className="w-5 h-5 text-red-600" />,
          text: '失败',
          color: 'text-red-600',
          bgColor: 'bg-red-50',
        }
      default:
        return {
          icon: <Clock className="w-5 h-5 text-gray-600" />,
          text: '未知',
          color: 'text-gray-600',
          bgColor: 'bg-gray-50',
        }
    }
  }

  const statusDisplay = getStatusDisplay()

  // 格式化时间
  const formatTime = (isoString: string): string => {
    return new Date(isoString).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-[#1a1a2e]">运行状态监控</h3>
            <p className="text-sm text-[#6c757d]">板块分类计算的实时运行状态</p>
          </div>
          <Button
            onClick={onRefresh}
            disabled={loading}
            variant="outline"
            size="sm"
            className="inline-flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span>刷新</span>
          </Button>
        </div>
      </CardHeader>
      <CardBody>
        {error && !status && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-700">{error}</p>
          </div>
        )}

        {status && (
          <div className="space-y-6">
            {/* 计算状态 */}
            <div
              className={`p-4 rounded-lg border ${statusDisplay.bgColor} border-${statusDisplay.color.split('-')[1]}-200`}
            >
              <div className="flex items-center gap-3">
                {statusDisplay.icon}
                <div>
                  <p className="text-sm text-[#6c757d]">计算状态</p>
                  <p
                    className={`text-lg font-semibold ${statusDisplay.color}`}
                  >
                    {statusDisplay.text}
                  </p>
                </div>
              </div>
            </div>

            {/* 状态指标 */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* 最后计算时间 */}
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <Clock className="w-4 h-4 text-cyan-600" />
                  <p className="text-sm text-[#6c757d]">最后计算时间</p>
                </div>
                <p className="text-base font-semibold text-[#1a1a2e]">
                  {formatTime(status.last_calculation_time)}
                </p>
              </div>

              {/* 计算耗时 */}
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <Activity className="w-4 h-4 text-cyan-600" />
                  <p className="text-sm text-[#6c757d]">计算耗时</p>
                </div>
                <p className="text-base font-semibold text-[#1a1a2e]">
                  {status.last_calculation_duration_ms} ms
                </p>
              </div>

              {/* 今日计算次数 */}
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <TrendingUp className="w-4 h-4 text-cyan-600" />
                  <p className="text-sm text-[#6c757d]">今日计算次数</p>
                </div>
                <p className="text-base font-semibold text-[#1a1a2e]">
                  {status.today_calculation_count} 次
                </p>
              </div>
            </div>
          </div>
        )}
      </CardBody>
    </Card>
  )
}
