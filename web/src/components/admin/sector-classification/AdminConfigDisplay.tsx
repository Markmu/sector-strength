'use client'

import { Card, CardHeader, CardBody } from '@/components/ui/Card'
import { TestAlgorithmButton } from './TestAlgorithmButton'
import { TestResultDisplay } from './TestResultDisplay'
import { useClassificationTest } from './useClassificationTest'
import type { AdminConfigDisplayProps } from './AdminConfigDisplay.types'
import { ClassificationLevelDefinition } from './ClassificationLevelDefinition'

/**
 * AdminConfigDisplay - 管理员配置展示组件
 *
 * @description
 * 显示板块强弱分类的系统参数配置：
 * - 算法测试按钮和结果展示（Story 4.2 新增）
 * - 均线周期配置
 * - 判断基准天数
 * - 分类数量
 * - 分类级别定义
 *
 * 这些参数是只读的，用于管理员确认系统配置
 */
export function AdminConfigDisplay({ config }: AdminConfigDisplayProps) {
  const { testing, testResult, error, runTest, reset } = useClassificationTest()

  const handleTest = () => {
    reset() // 清除之前的测试结果
    runTest()
  }

  return (
    <div className="space-y-6">
      {/* 算法测试区域（Story 4.2 新增） */}
      <Card>
        <CardHeader>
          <h3 className="text-lg font-semibold text-[#1a1a2e]">算法测试</h3>
          <p className="text-sm text-[#6c757d]">测试分类算法是否正常工作</p>
        </CardHeader>
        <CardBody>
          <TestAlgorithmButton testing={testing} onTest={handleTest} />
        </CardBody>
      </Card>

      {/* 测试结果展示（Story 4.2 新增） */}
      {(testing || testResult || error) && (
        <TestResultDisplay
          testing={testing}
          result={testResult}
          error={error}
          onRetry={handleTest}
        />
      )}

      {/* 均线周期卡片 */}
      <Card>
        <CardHeader>
          <h3 className="text-lg font-semibold text-[#1a1a2e]">均线周期配置</h3>
          <p className="text-sm text-[#6c757d]">用于板块分类计算的均线周期（天）</p>
        </CardHeader>
        <CardBody>
          <div className="flex flex-wrap gap-2">
            {config.ma_periods.map((period) => (
              <span
                key={period}
                className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-cyan-100 text-cyan-800 border border-cyan-200"
              >
                {period} 日线
              </span>
            ))}
          </div>
        </CardBody>
      </Card>

      {/* 判断基准天数卡片 */}
      <Card>
        <CardHeader>
          <h3 className="text-lg font-semibold text-[#1a1a2e]">判断基准天数</h3>
          <p className="text-sm text-[#6c757d]">用于判断反弹/调整状态的天数基准</p>
        </CardHeader>
        <CardBody>
          <p className="text-3xl font-bold text-cyan-600">{config.benchmark_days} 天</p>
        </CardBody>
      </Card>

      {/* 分类数量卡片 */}
      <Card>
        <CardHeader>
          <h3 className="text-lg font-semibold text-[#1a1a2e]">分类数量</h3>
          <p className="text-sm text-[#6c757d]">板块强弱分类的总类别数</p>
        </CardHeader>
        <CardBody>
          <p className="text-3xl font-bold text-cyan-600">{config.classification_count} 类</p>
        </CardBody>
      </Card>

      {/* 分类级别定义 */}
      <ClassificationLevelDefinition definitions={config.level_definitions} />
    </div>
  )
}
