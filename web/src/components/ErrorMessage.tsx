/**
 * 错误消息显示组件
 *
 * 用于显示友好的错误提示，支持重试功能
 */

'use client'

import React from 'react'

interface ErrorMessageProps {
  error: string
  code?: string
  onRetry?: () => void
  retryLabel?: string
}

export function ErrorMessage({
  error,
  code,
  onRetry,
  retryLabel = "重试"
}: ErrorMessageProps) {
  return (
    <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4 my-4">
      <div className="flex items-start">
        <div className="flex-shrink-0">
          <svg
            className="h-5 w-5 text-destructive"
            viewBox="0 0 20 20"
            fill="currentColor"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-9a1 1 0 11-2 0 1 1 0 012 0zm-1 4a1 1 0 102 0 1 1 0 00-2 0z"
              clipRule="evenodd"
            />
          </svg>
        </div>
        <div className="ml-3 flex-1">
          <h3 className="text-sm font-medium text-destructive">
            {code || "错误"}
          </h3>
          <div className="mt-2 text-sm text-destructive/80">
            <p>{error}</p>
          </div>
          {onRetry && (
            <div className="mt-4">
              <button
                onClick={onRetry}
                className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-destructive bg-destructive/10 hover:bg-destructive/20 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-destructive"
              >
                {retryLabel}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default ErrorMessage
