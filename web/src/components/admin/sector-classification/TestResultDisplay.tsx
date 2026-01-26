'use client'

import { Card, CardHeader, CardBody } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { CheckCircle2, XCircle, AlertCircle, RotateCcw } from 'lucide-react'
import type { TestResultDisplayProps } from './TestResultDisplay.types'

/**
 * TestResultDisplay - 测试结果展示组件
 *
 * @description
 * 显示分类算法测试的结果：
 * - 加载中状态（testing = true）
 * - 成功结果（包含总数、成功数、失败数、耗时）
 * - 失败错误信息（带重试按钮）
 * - 部分失败（显示失败板块列表）
 *
 * @param result - 测试结果
 * @param error - 错误信息
 * @param onRetry - 重试回调
 * @param testing - 是否正在测试
 */
export function TestResultDisplay({
  result,
  error,
  onRetry,
  testing,
}: TestResultDisplayProps) {
  // 加载中状态
  if (testing) {
    return (
      <Card>
        <CardBody>
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-500"></div>
            <span className="ml-3 text-[#6c757d]">正在测试分类算法...</span>
          </div>
        </CardBody>
      </Card>
    )
  }

  // 错误状态
  if (error) {
    return (
      <Card className="border-red-200 bg-red-50">
        <CardBody>
          <div className="flex items-start gap-3">
            <XCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h4 className="font-semibold text-red-900 mb-1">测试失败</h4>
              <p className="text-sm text-red-700 mb-4">{error}</p>
              <Button onClick={onRetry} variant="outline" size="sm">
                <RotateCcw className="w-4 h-4 mr-1" />
                重试
              </Button>
            </div>
          </div>
        </CardBody>
      </Card>
    )
  }

  // 成功状态
  if (result) {
    const hasFailures = result.failure_count > 0

    return (
      <Card className={hasFailures ? 'border-amber-200 bg-amber-50' : 'border-green-200 bg-green-50'}>
        <CardHeader>
          <div className="flex items-center gap-2">
            {hasFailures ? (
              <AlertCircle className="w-5 h-5 text-amber-600" />
            ) : (
              <CheckCircle2 className="w-5 h-5 text-green-600" />
            )}
            <h4 className="font-semibold text-[#1a1a2e]">
              {hasFailures ? '测试完成（部分失败）' : '测试完成'}
            </h4>
          </div>
        </CardHeader>
        <CardBody>
          <p className="text-lg mb-4">
            测试完成！共计算 <span className="font-bold">{result.total_count}</span> 个板块分类。
          </p>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div>
              <p className="text-sm text-[#6c757d]">成功数量</p>
              <p className="text-2xl font-bold text-green-600">{result.success_count}</p>
            </div>
            <div>
              <p className="text-sm text-[#6c757d]">失败数量</p>
              <p className={`text-2xl font-bold ${hasFailures ? 'text-red-600' : 'text-green-600'}`}>
                {result.failure_count}
              </p>
            </div>
            <div>
              <p className="text-sm text-[#6c757d]">计算耗时</p>
              <p className="text-2xl font-bold text-cyan-600">{result.duration_ms} ms</p>
            </div>
            <div>
              <p className="text-sm text-[#6c757d]">测试时间</p>
              <p className="text-sm font-semibold text-[#1a1a2e]">
                {new Date(result.timestamp).toLocaleString('zh-CN')}
              </p>
            </div>
          </div>

          {hasFailures && result.failures && result.failures.length > 0 && (
            <div className="border-t border-amber-200 pt-4">
              <p className="text-sm font-semibold text-red-900 mb-2">失败的板块：</p>
              <ul className="text-sm text-red-700 space-y-1">
                {result.failures.map((failure, index) => (
                  <li key={index}>
                    {failure.sector_name} - {failure.error}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </CardBody>
      </Card>
    )
  }

  // 初始状态（无结果）
  return null
}
