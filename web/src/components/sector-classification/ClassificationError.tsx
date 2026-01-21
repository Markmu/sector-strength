/**
 * 板块分类错误状态组件
 *
 * 在数据获取失败时显示错误信息和重试按钮
 */

'use client'

import { RefreshCw } from 'lucide-react'
import Button from '@/components/ui/Button'

/**
 * 错误消息映射
 * 将错误类型映射为用户友好的中文消息
 */
const ERROR_MESSAGES: Record<string, string> = {
  'NETWORK_ERROR': '网络连接失败，请检查网络设置',
  'TIMEOUT': '请求超时，请稍后重试',
  'UNAUTHORIZED': '未授权，请重新登录',
  'FORBIDDEN': '无权限访问',
  'NOT_FOUND': '未找到分类数据',
  'SERVER_ERROR': '服务器错误，请稍后重试',
}

/**
 * 获取用户友好的错误消息
 *
 * @description
 * 使用精确匹配（而非 includes）来避免误匹配
 * 优先匹配完整错误码，否则返回原始错误消息
 */
function getErrorMessage(error: string): string {
  // 尝试精确匹配已知错误类型
  if (ERROR_MESSAGES[error]) {
    return ERROR_MESSAGES[error]
  }

  // 如果包含错误码，尝试提取并匹配
  for (const [key, message] of Object.entries(ERROR_MESSAGES)) {
    // 使用正则表达式精确匹配错误码边界
    const regex = new RegExp(`\\b${key}\\b`)
    if (regex.test(error)) {
      return message
    }
  }

  // 返回原始错误或默认消息
  return error || '获取数据失败，请重试'
}

export interface ClassificationErrorProps {
  /** 错误信息 */
  error: string | null
  /** 重试回调 */
  onRetry: () => void
  /** 是否正在重试 */
  isRetrying?: boolean
  /** 自定义类名 */
  className?: string
}

/**
 * 分类错误状态组件
 *
 * @description
 * 显示友好的错误提示和重试按钮
 * 支持可访问性标准（WCAG AA）
 */
export function ClassificationError({
  error,
  onRetry,
  isRetrying = false,
  className,
}: ClassificationErrorProps) {
  const errorMessage = getErrorMessage(error || '')

  return (
    <div
      className={className}
      role="alert"
      aria-live="assertive"
      aria-atomic="true"
    >
      {/* 错误提示卡片 */}
      <div className="bg-white rounded-xl border border-red-200 shadow-sm p-8">
        {/* 错误图标和标题 */}
        <div className="flex items-start gap-4">
          {/* 错误图标 */}
          <div className="flex-shrink-0 w-12 h-12 rounded-full bg-red-50 flex items-center justify-center">
            <svg
              className="w-6 h-6 text-red-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
          </div>

          {/* 错误内容 */}
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              获取分类数据失败
            </h3>
            <p className="text-sm text-gray-600 mb-4">
              {errorMessage}
            </p>

            {/* 重试按钮 */}
            <Button
              variant="primary"
              size="md"
              icon={<RefreshCw className="w-4 h-4" />}
              loading={isRetrying}
              onClick={onRetry}
              aria-label="重新获取分类数据"
            >
              重新加载
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ClassificationError
