'use client'

/**
 * AuditLogsFilters 组件
 *
 * @description
 * 审计日志筛选组件，提供操作类型、操作人和日期范围筛选功能。
 *
 * Acceptance Criteria:
 * - 实现操作类型筛选（下拉选择）
 * - 实现操作人筛选（下拉选择）
 * - 实现日期范围筛选（开始日期 ~ 结束日期）
 * - 实现筛选条件清除按钮
 */

import { Card, CardHeader, CardBody } from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import { X } from 'lucide-react'
import type { AuditLogsFiltersProps } from './AuditLogsFilters.types'
import { ACTION_TYPE_NAMES } from '@/types/audit-logs'

/**
 * 审计日志筛选组件
 */
export function AuditLogsFilters({
  filters,
  onUpdateFilters,
  onClearFilters,
  actionTypes,
  users,
}: AuditLogsFiltersProps) {
  /**
   * 处理筛选条件变化
   *
   * @param key - 筛选条件键
   * @param value - 筛选条件值
   */
  const handleFilterChange = (key: string, value: string) => {
    onUpdateFilters({
      ...filters,
      [key]: value || undefined,
    })
  }

  // 检查是否有激活的筛选条件
  const hasActiveFilters = Object.values(filters).some((v) => v !== undefined)

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-[#1a1a2e]">筛选条件</h3>
          {hasActiveFilters && (
            <Button
              onClick={onClearFilters}
              variant="outline"
              size="sm"
              className="inline-flex items-center gap-2"
            >
              <X className="w-4 h-4" />
              清除筛选
            </Button>
          )}
        </div>
      </CardHeader>
      <CardBody>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* 操作类型筛选 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              操作类型
            </label>
            <select
              value={filters.action_type || ''}
              onChange={(e) => handleFilterChange('action_type', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
            >
              <option value="">全部</option>
              {actionTypes.map((type) => (
                <option key={type} value={type}>
                  {ACTION_TYPE_NAMES[type] || type}
                </option>
              ))}
            </select>
          </div>

          {/* 操作人筛选 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              操作人
            </label>
            <select
              value={filters.user_id || ''}
              onChange={(e) => handleFilterChange('user_id', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
            >
              <option value="">全部</option>
              {users.map((user) => (
                <option key={user.id} value={user.id}>
                  {user.username}
                </option>
              ))}
            </select>
          </div>

          {/* 开始日期筛选 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              开始日期
            </label>
            <input
              type="date"
              value={filters.start_date || ''}
              onChange={(e) => handleFilterChange('start_date', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
            />
          </div>

          {/* 结束日期筛选 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              结束日期
            </label>
            <input
              type="date"
              value={filters.end_date || ''}
              onChange={(e) => handleFilterChange('end_date', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
            />
          </div>
        </div>
      </CardBody>
    </Card>
  )
}
