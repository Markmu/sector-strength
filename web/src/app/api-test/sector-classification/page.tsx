'use client'

import { useState } from 'react'
import { sectorClassificationApi, TestResult } from '@/lib/sectorClassificationApi'
import { ErrorMessage } from '@/components/ErrorMessage'

/**
 * API 测试页面
 *
 * 用于测试板块分类 API 端点的功能
 */
export default function SectorClassificationAPITestPage() {
  const [allResult, setAllResult] = useState<TestResult | null>(null)
  const [singleResult, setSingleResult] = useState<TestResult | null>(null)
  const [sectorId, setSectorId] = useState<string>('1')
  const [loading, setLoading] = useState(false)

  /**
   * 测试获取所有分类
   */
  const handleTestGetAll = async () => {
    setLoading(true)
    try {
      const result = await sectorClassificationApi.getAllClassificationsWithTiming()
      setAllResult(result)
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '未知错误'
      setAllResult({
        status: 500,
        data: null,
        responseTime: 0,
        error: errorMessage
      })
    } finally {
      setLoading(false)
    }
  }

  /**
   * 测试获取单个分类
   */
  const handleTestGetSingle = async () => {
    // 输入验证
    const sectorIdNum = parseInt(sectorId, 10)
    if (!sectorId || isNaN(sectorIdNum) || sectorIdNum <= 0) {
      setSingleResult({
        status: 400,
        data: null,
        responseTime: 0,
        error: '请输入有效的板块 ID（正整数）'
      })
      return
    }

    setLoading(true)
    try {
      const result = await sectorClassificationApi.getClassificationByIdWithTiming(sectorIdNum)
      setSingleResult(result)
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '未知错误'
      setSingleResult({
        status: 500,
        data: null,
        responseTime: 0,
        error: errorMessage
      })
    } finally {
      setLoading(false)
    }
  }

  /**
   * 根据状态码和错误消息获取中文描述
   */
  const getErrorMessage = (status: number, error?: string): string => {
    if (status === 401) {
      return '未认证：请先登录'
    }
    if (status === 404) {
      return '板块不存在'
    }
    if (status >= 500) {
      return '服务器错误，请稍后重试'
    }
    if (status === 0) {
      return '网络错误：无法连接到服务器'
    }
    return error || '未知错误'
  }

  /**
   * 渲染测试结果
   */
  const renderTestResult = (result: TestResult, onRetry?: () => void) => (
    <div className="mt-4">
      <div className="flex items-center gap-4 mb-2">
        <span className={`font-semibold ${result.error ? 'text-red-500' : 'text-green-500'}`}>
          状态码: {result.status}
        </span>
        <span className="text-gray-600">
          响应时间: {result.responseTime.toFixed(2)}ms
        </span>
      </div>

      {result.error && (
        <ErrorMessage
          error={getErrorMessage(result.status, result.error)}
          code={`HTTP ${result.status}`}
          onRetry={onRetry}
          retryLabel="重试"
        />
      )}

      {result.data && (
        <pre className="bg-gray-900 text-green-400 p-4 rounded overflow-x-auto text-sm">
          {JSON.stringify(result.data, null, 2)}
        </pre>
      )}
    </div>
  )

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl md:text-3xl font-bold mb-2">API 测试页面</h1>
        <p className="text-gray-600 mb-8">板块强弱分类 API 端点验证工具</p>

        {/* 测试获取所有分类 */}
        <section className="bg-white rounded-lg shadow p-4 md:p-6 mb-6">
          <h2 className="text-lg md:text-xl font-semibold mb-4">测试获取所有分类</h2>
          <button
            onClick={handleTestGetAll}
            disabled={loading}
            className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? '测试中...' : '测试获取所有分类'}
          </button>

          {allResult && renderTestResult(allResult, handleTestGetAll)}
        </section>

        {/* 测试获取单个分类 */}
        <section className="bg-white rounded-lg shadow p-4 md:p-6">
          <h2 className="text-lg md:text-xl font-semibold mb-4">测试获取单个分类</h2>
          <div className="flex flex-col md:flex-row items-start md:items-center gap-4 mb-4">
            <input
              type="number"
              value={sectorId}
              onChange={(e) => setSectorId(e.target.value)}
              placeholder="输入板块 ID"
              className="border border-gray-300 rounded px-3 py-2 w-full md:w-40"
            />
            <button
              onClick={handleTestGetSingle}
              disabled={loading || !sectorId}
              className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? '测试中...' : '测试获取单个分类'}
            </button>
          </div>

          {singleResult && renderTestResult(singleResult, handleTestGetSingle)}
        </section>

        {/* 说明 */}
        <div className="mt-8 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <h3 className="font-semibold text-blue-900 mb-2">使用说明</h3>
          <ul className="text-sm text-blue-800 space-y-1">
            <li>• 此页面用于验证板块分类 API 端点的可用性</li>
            <li>• 点击按钮测试对应的 API 接口</li>
            <li>• 响应结果包含状态码、响应时间和 JSON 数据</li>
            <li>• 如果出现 401 错误，请先登录获取认证令牌</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
