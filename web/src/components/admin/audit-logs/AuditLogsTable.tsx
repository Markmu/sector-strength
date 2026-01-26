'use client'

/**
 * AuditLogsTable 组件
 *
 * @description
 * 审计日志表格组件，显示操作时间、操作人、操作类型、操作内容和 IP 地址。
 * 支持分页和展开长文本。
 *
 * Acceptance Criteria:
 * - 显示操作时间（中文本地化格式）
 * - 显示操作人用户名
 * - 显示操作类型（带颜色标签）
 * - 显示操作内容（可展开查看完整内容）
 * - 显示 IP 地址
 * - 支持分页（每页 20 条）
 */

import { useState } from 'react'
import { Card, CardHeader, CardBody } from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Eye,
  EyeOff,
} from 'lucide-react'
import type { AuditLogsTableProps } from './AuditLogsTable.types'
import { ACTION_TYPE_COLORS, ACTION_TYPE_NAMES } from '@/types/audit-logs'
import type { ActionType } from '@/types/audit-logs'

/**
 * 格式化时间为中文本地化格式
 *
 * @param isoString - ISO 8601 格式的时间字符串
 * @returns 格式化后的时间字符串
 */
function formatTime(isoString: string): string {
  return new Date(isoString).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

/**
 * 审计日志表格组件
 */
export function AuditLogsTable({
  logs,
  loading,
  currentPage,
  totalPages,
  total,
  onNextPage,
  onPrevPage,
  onGoToPage,
}: AuditLogsTableProps) {
  // 展开行的状态管理
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set())

  /**
   * 切换行的展开/收起状态
   */
  const toggleRow = (id: string) => {
    const newExpanded = new Set(expandedRows)
    if (newExpanded.has(id)) {
      newExpanded.delete(id)
    } else {
      newExpanded.add(id)
    }
    setExpandedRows(newExpanded)
  }

  // 加载中状态
  if (loading) {
    return (
      <Card>
        <CardBody>
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-600"></div>
          </div>
        </CardBody>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-[#1a1a2e]">审计日志列表</h3>
            <p className="text-sm text-[#6c757d]">
              共 {total} 条记录，当前第 {currentPage}/{totalPages} 页
            </p>
          </div>
        </div>
      </CardHeader>
      <CardBody>
        {logs.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-[#6c757d]">暂无审计日志</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead>
                <tr className="bg-gray-50">
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    操作时间
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    操作人
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    操作类型
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    操作内容
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    IP 地址
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    操作
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {logs.map((log) => {
                  const actionType = log.action_type as ActionType
                  const isLongText = log.action_details.length > 50
                  const isExpanded = expandedRows.has(log.id)

                  return (
                    <tr key={log.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatTime(log.created_at)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {log.username}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                            ACTION_TYPE_COLORS[actionType] ||
                            'bg-gray-100 text-gray-700'
                          }`}
                        >
                          {ACTION_TYPE_NAMES[actionType] || actionType}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-900">
                        <div className="max-w-xs">
                          {isLongText ? (
                            <>
                              {isExpanded ? (
                                <div>{log.action_details}</div>
                              ) : (
                                <div>{log.action_details.substring(0, 50)}...</div>
                              )}
                            </>
                          ) : (
                            <div>{log.action_details}</div>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {log.ip_address || '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {isLongText && (
                          <button
                            onClick={() => toggleRow(log.id)}
                            className="text-cyan-600 hover:text-cyan-900 inline-flex items-center gap-1"
                          >
                            {isExpanded ? (
                              <>
                                <EyeOff className="w-4 h-4" />
                                收起
                              </>
                            ) : (
                              <>
                                <Eye className="w-4 h-4" />
                                展开
                              </>
                            )}
                          </button>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* 分页控件 */}
        {totalPages > 1 && (
          <div className="mt-6 flex items-center justify-between">
            <div className="text-sm text-gray-700">
              当前第 <span className="font-semibold">{currentPage}</span> 页，
              共 <span className="font-semibold">{totalPages}</span> 页
            </div>
            <div className="flex items-center gap-2">
              <Button
                onClick={() => onGoToPage(1)}
                disabled={currentPage === 1}
                variant="outline"
                size="sm"
              >
                <ChevronsLeft className="w-4 h-4" />
              </Button>
              <Button
                onClick={onPrevPage}
                disabled={currentPage === 1}
                variant="outline"
                size="sm"
              >
                <ChevronLeft className="w-4 h-4" />
                上一页
              </Button>
              <Button
                onClick={onNextPage}
                disabled={currentPage === totalPages}
                variant="outline"
                size="sm"
              >
                下一页
                <ChevronRight className="w-4 h-4" />
              </Button>
              <Button
                onClick={() => onGoToPage(totalPages)}
                disabled={currentPage === totalPages}
                variant="outline"
                size="sm"
              >
                <ChevronsRight className="w-4 h-4" />
              </Button>
            </div>
          </div>
        )}
      </CardBody>
    </Card>
  )
}
