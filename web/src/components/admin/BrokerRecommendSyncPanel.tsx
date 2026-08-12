'use client'

/**
 * 券商月度金股同步面板（09 期 plan-03，AC-08-ui-1~5）
 *
 * 样式完全对齐 StockTop10SyncPanel：
 * - Toast（fixed top-4 right-4，带图标）
 * - 同步卡片（bg-card rounded-lg shadow-sm border，图标+标题+表单组+按钮+进度条）
 * - 同步记录表（卡片，表头 px-6 py-3，状态徽章）
 */
import React, { useMemo, useState } from 'react'
import useSWR from 'swr'
import {
  Star,
  RefreshCw,
  Loader2,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Calendar,
} from 'lucide-react'
import { adminApi } from '@/lib/api'
import { useTaskStatus } from '@/hooks/useTaskStatus'
import { fetcher } from '@/lib/fetcher'

const RECORDS_SWR_KEY =
  '/api/v1/admin/tasks?task_types=sync_broker_recommend&page=1&page_size=20'

/** 生成最近 12 个月的 YYYYMM 列表（含当月，降序） */
function getRecentMonths(count = 12): string[] {
  const months: string[] = []
  const now = new Date()
  for (let i = 0; i < count; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    months.push(`${y}${m}`)
  }
  return months
}

/** YYYYMM → "YYYY-MM" 显示 */
function formatMonth(yyyymm: string): string {
  if (!yyyymm || yyyymm.length !== 6) return yyyymm
  return `${yyyymm.slice(0, 4)}-${yyyymm.slice(4, 6)}`
}

function formatDateTime(iso?: string): string {
  if (!iso) return '-'
  try {
    return new Date(iso).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

interface TaskRecord {
  taskId: string
  taskType: string
  status: string
  percent: number
  progress: number
  total: number
  params?: { month?: string } | Record<string, unknown> | null
  errorMessage?: string
  createdAt: string
}

/**
 * fetcher 已自动解包 {success, data} 外层（fetcher.ts:48 `result.data || result`），
 * 后端 tasks 列表接口的 data 字段为 {tasks, total, page}（tasks.py:63），
 * 故 SWR 数据类型直接用 {tasks, total, page}，不再含 success/data 外层。
 */
interface TasksListData {
  tasks: TaskRecord[]
  total: number
  page: number
}

const STATUS_STYLES: Record<string, string> = {
  completed: 'bg-fall/10 text-fall',
  failed: 'bg-rise/10 text-rise',
  running: 'bg-primary-light text-primary',
  pending: 'bg-warning/10 text-warning',
  cancelled: 'bg-secondary text-foreground',
}
const STATUS_LABELS: Record<string, string> = {
  completed: '成功',
  failed: '失败',
  running: '运行中',
  pending: '等待中',
  cancelled: '已取消',
}

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-block px-2 py-0.5 text-xs rounded ${
        STATUS_STYLES[status] ?? 'bg-secondary text-foreground'
      }`}
    >
      {STATUS_LABELS[status] ?? status}
    </span>
  )
}

export default function BrokerRecommendSyncPanel() {
  const months = useMemo(() => getRecentMonths(12), [])
  const [selectedMonth, setSelectedMonth] = useState(months[0])
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null)
  const [toast, setToast] = useState<
    { type: 'success' | 'error'; message: string } | null
  >(null)

  const { data: recordsData, mutate: refreshRecords, isValidating } = useSWR<
    TasksListData
  >(RECORDS_SWR_KEY, fetcher, {
    revalidateOnFocus: false,
    refreshInterval: 5000,
  })
  const records = recordsData?.tasks ?? []

  const { task, cancel } = useTaskStatus(currentTaskId, {
    enabled: !!currentTaskId,
    pollInterval: 2000,
    onComplete: () => {
      setToast({ type: 'success', message: '券商金股同步完成' })
      setCurrentTaskId(null)
      refreshRecords()
    },
    onFailed: (t) => {
      setToast({
        type: 'error',
        message: `同步失败${t?.errorMessage ? '：' + t.errorMessage : ''}`,
      })
      setCurrentTaskId(null)
      refreshRecords()
    },
  })

  const isSyncing = !!currentTaskId
  const progressPercent = task?.percent ?? 0

  const handleSync = async () => {
    setToast(null)
    try {
      const response = await adminApi.initBrokerRecommend(selectedMonth)
      const taskId = (response as { data?: { task_id?: string } }).data?.task_id
      if (!taskId) {
        setToast({ type: 'error', message: '创建同步任务失败：未返回任务ID' })
        return
      }
      setCurrentTaskId(taskId)
      refreshRecords()
    } catch (e) {
      const msg =
        (e as { response?: { data?: { message?: string; detail?: string } } })
          ?.response?.data?.message ||
        (e as { response?: { data?: { message?: string; detail?: string } } })
          ?.response?.data?.detail ||
        '创建同步任务失败'
      setToast({ type: 'error', message: msg })
    }
  }

  const handleCancel = async () => {
    try {
      await cancel()
      setToast({ type: 'success', message: '已取消同步任务' })
      setCurrentTaskId(null)
      refreshRecords()
    } catch {
      setToast({ type: 'error', message: '取消任务失败' })
    }
  }

  return (
    <div className="space-y-6">
      {/* Toast */}
      {toast && (
        <div
          className={`fixed top-4 right-4 z-50 max-w-md px-4 py-3 rounded-lg shadow-lg border ${
            toast.type === 'success'
              ? 'bg-fall/10 border-fall/30 text-fall'
              : 'bg-rise/10 border-rise/30 text-rise'
          }`}
        >
          <div className="flex items-center gap-2">
            {toast.type === 'success' ? (
              <CheckCircle2 className="w-5 h-5 text-fall" />
            ) : (
              <XCircle className="w-5 h-5 text-rise" />
            )}
            <span className="text-sm font-medium">{toast.message}</span>
            <button
              type="button"
              onClick={() => setToast(null)}
              className="ml-2 text-current opacity-50 hover:opacity-100"
              aria-label="关闭"
            >
              ×
            </button>
          </div>
        </div>
      )}

      {/* 同步卡片 */}
      <div className="bg-card rounded-lg shadow-sm border border-border p-6">
        <div className="flex items-center gap-2 mb-4">
          <Star className="w-5 h-5 text-primary" />
          <h3 className="text-lg font-semibold text-foreground">券商金股同步</h3>
        </div>
        <p className="text-sm text-muted-foreground mb-4">
          从 Tushare 按月拉取券商金股推荐数据（券商每月荐股接口，月末快照）。
        </p>

        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-muted-foreground" />
            <select
              value={selectedMonth}
              onChange={(e) => setSelectedMonth(e.target.value)}
              disabled={isSyncing}
              className="px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-primary focus:border-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {months.map((m) => (
                <option key={m} value={m}>
                  {formatMonth(m)}
                </option>
              ))}
            </select>
          </div>

          {!isSyncing ? (
            <button
              type="button"
              onClick={handleSync}
              className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <RefreshCw className="w-4 h-4" />
              同步
            </button>
          ) : (
            <button
              type="button"
              onClick={handleCancel}
              className="flex items-center gap-2 px-4 py-2 border border-destructive text-destructive rounded-lg hover:bg-destructive/10 transition-colors"
            >
              取消同步
            </button>
          )}
        </div>

        {/* 进度条 */}
        {isSyncing && (
          <div className="mt-4">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm text-muted-foreground">
                同步中{task?.progress != null && task?.total != null
                  ? ` ${task.progress}/${task.total}`
                  : '…'}
              </span>
              <span className="text-sm text-muted-foreground">
                {progressPercent}%
              </span>
            </div>
            <div className="w-full bg-secondary rounded-full h-2">
              <div
                className="bg-primary rounded-full h-2 transition-all duration-300"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* 同步记录 */}
      <div className="bg-card rounded-lg shadow-sm border border-border">
        <div className="px-6 py-4 border-b border-border flex items-center justify-between">
          <h3 className="text-lg font-semibold text-foreground">同步记录</h3>
          <button
            type="button"
            onClick={() => refreshRecords()}
            className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            {isValidating ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4" />
            )}
            刷新
          </button>
        </div>

        {records.length === 0 ? (
          <div className="px-6 py-8 text-center text-muted-foreground">
            暂无同步记录
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="px-6 py-3 text-left font-medium text-muted-foreground">
                    时间
                  </th>
                  <th className="px-6 py-3 text-left font-medium text-muted-foreground">
                    月份
                  </th>
                  <th className="px-6 py-3 text-left font-medium text-muted-foreground">
                    状态
                  </th>
                  <th className="px-6 py-3 text-left font-medium text-muted-foreground">
                    详情
                  </th>
                </tr>
              </thead>
              <tbody>
                {records.map((r) => (
                  <tr key={r.taskId} className="border-b border-border last:border-0">
                    <td className="px-6 py-3 text-muted-foreground">
                      {formatDateTime(r.createdAt)}
                    </td>
                    <td className="px-6 py-3 text-foreground">
                      {r.params?.month
                        ? formatMonth(String(r.params.month))
                        : '-'}
                    </td>
                    <td className="px-6 py-3">
                      <StatusBadge status={r.status} />
                    </td>
                    <td className="px-6 py-3 text-muted-foreground text-xs">
                      {r.errorMessage || `${r.percent ?? 0}%`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
