'use client'

/**
 * 涨停专题同步面板（数据管理页「涨停专题」Tab）
 *
 * 范式对齐 16/17 期 MarketMetricsSyncPanel / MarginSyncPanel，按涨停专题契约裁剪：
 * - 两种触发模式（后端 POST /admin/init/limit 契约）：
 *   - 「同步最新交易日」：起止都留空，后端经 trade_cal 回退最新交易日（单日）；
 *   - 「按范围同步」：起止同时给出，逐交易日升序同步，单日失败不中断。
 * - 增量默认值：展示当前最新数据日期（GET /limit/latest-date = limit_list_d
 *   最大 trade_date），起止默认填充「最新数据日期+1 天 ~ 今天」；开始日期
 *   不强制，可往前选以重跑历史（同步按 trade_date 删旧插新、幂等），用户
 *   手动修改后不再自动预填。
 * - 前端校验：起止必须成对（镜像后端 400 拒绝）+ 倒置/未来/超 10 年。
 * - sync_limit_data handler 不持久化结构化 result（仅日志与 progress），
 *   故无 16/17 期的终态三类计数与 dateResults，终态简化为状态横幅
 *   （完成/失败原因/已取消），明细见同步记录表与任务日志。
 * - 进度口径随模式：范围任务 total=交易日数；单日任务 total=3（三表步骤）。
 * - 互斥：记录列表含 pending/running 同类任务 → 按钮禁用 + 提示；后端二次
 *   拒绝展示 message（前端禁用不承担一致性）。
 * - 记录区：SWR 拉 /api/v1/admin/tasks?task_types=sync_limit_data + 分页；
 *   范围列对无参数任务显示「最新交易日」。
 * - 取消：复用 useTaskStatus.cancel()。
 */
import React, { useState, useCallback, useMemo } from 'react'
import useSWR from 'swr'
import {
  Database,
  Loader2,
  AlertCircle,
  CheckCircle2,
  RefreshCw,
  Calendar,
  CalendarClock,
  Ban,
  Zap,
} from 'lucide-react'
import { adminApi, limitApi } from '@/lib/api'
import { useTaskStatus, type TaskData, type TaskStatus } from '@/hooks/useTaskStatus'
import { useAuth } from '@/contexts/AuthContext'
import { useRequireAdmin } from '@/hooks/useRequireAdmin'
import { fetcher } from '@/lib/fetcher'

/** 同步任务类型（后端 task_type） */
const TASK_TYPE = 'sync_limit_data'
/** 记录分页大小（与 IndexSyncPanel / MarginSyncPanel 一致） */
const PAGE_SIZE = 20
/** 轮询间隔（2s） */
const POLL_INTERVAL = 2000
/** 跨度上限（10 年，与后端 _MAX_BACKSPAN_DAYS 一致） */
const TEN_YEARS_MS = 10 * 365.25 * 24 * 3600 * 1000

/** sync_limit_data 无结构化 result（handler 仅日志），result 恒为 null/undefined */
type LimitTaskResult = Record<string, unknown> | null

/** 同步记录行（与后端 AsyncTask.to_dict camelCase 契约一致） */
interface SyncRecord {
  taskId: string
  taskType: string
  status: TaskStatus
  progress: number
  total: number
  createdAt: string
  errorMessage?: string | null
  params?: Record<string, unknown> | null
}

/** 按本地时区格式化日期，避免 toISOString() 在 UTC 转换后产生日期偏移。 */
function formatLocalDate(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

/** ISO 日期字符串加 N 天（按本地时区，返回 YYYY-MM-DD）。 */
function addDaysISO(iso: string, days: number): string {
  const d = new Date(`${iso}T00:00:00`)
  d.setDate(d.getDate() + days)
  return formatLocalDate(d)
}

/** 本地任务终态横幅信息（handler 无 result，仅状态与失败原因） */
interface TerminalInfo {
  status: TaskStatus
  errorMessage?: string
}

export default function LimitSyncPanel() {
  useRequireAdmin()
  const { isAdmin } = useAuth()

  const todayStr = useMemo(() => formatLocalDate(new Date()), [])
  // 用户手动改过任一日期后冻结为用户值，不再跟随默认预填
  const [overrideDates, setOverrideDates] = useState<{
    start: string
    end: string
  } | null>(null)

  // ---- 本地任务状态 ----
  const [taskId, setTaskId] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const [terminalInfo, setTerminalInfo] = useState<TerminalInfo | null>(null)
  // 创建/同步过程错误（前端校验失败或后端拒绝 message）
  const [syncError, setSyncError] = useState<string | null>(null)
  const [cancelRequested, setCancelRequested] = useState(false)

  // ---- 记录分页 ----
  const [recordsPage, setRecordsPage] = useState(1)

  // ---- 记录列表 SWR（fetcher 拼 NEXT_PUBLIC_API_URL 前缀，key 含 /api/v1 前缀） ----
  const recordsKey = `/api/v1/admin/tasks?task_types=${TASK_TYPE}&page=${recordsPage}&page_size=${PAGE_SIZE}`
  const {
    data: tasksData,
    isLoading: recordsLoading,
    mutate: refreshRecords,
  } = useSWR<{ tasks: SyncRecord[]; total: number; page: number }>(recordsKey, fetcher)

  const syncRecords = tasksData?.tasks ?? []
  const recordsTotal = tasksData?.total ?? 0

  // ---- 当前最新数据日期（GET /limit/latest-date，limit_list_d 最大 trade_date） ----
  const {
    data: latestData,
    isLoading: latestLoading,
    mutate: refreshLatest,
  } = useSWR<{ hasData: boolean; tradeDate: string | null }>(
    'limit-sync-latest-date',
    async () => {
      // apiClient.get 返回 ApiResponse<T> 双层信封，业务数据在 data.data
      const resp = await limitApi.getLatestDate()
      const d = resp.data?.data
      return { hasData: d?.hasData ?? false, tradeDate: d?.tradeDate ?? null }
    }
  )
  const latestDate = latestData?.hasData ? latestData.tradeDate ?? null : null
  /** 增量起点 = 最新数据日期的下一天（同步必须从此日开始） */
  const incrementStart = latestDate ? addDaysISO(latestDate, 1) : null

  // ---- 起止日期展示值：默认派生「最新+1 天 ~ 今天」，手动修改后取用户冻结值 ----
  const startDate = overrideDates?.start ?? incrementStart ?? ''
  const endDate = overrideDates?.end ?? (incrementStart ? todayStr : '')

  // ---- useTaskStatus 回调（终态后同时刷新记录与最新数据日期） ----
  const handleComplete = useCallback(
    (task: TaskData<LimitTaskResult>) => {
      setTerminalInfo({ status: task.status })
      setSyncError(null)
      setTaskId(null)
      setCreating(false)
      setCancelRequested(false)
      refreshRecords()
      refreshLatest()
    },
    [refreshRecords, refreshLatest]
  )

  const handleFailed = useCallback(
    (task: TaskData<LimitTaskResult>) => {
      setTerminalInfo({ status: task.status, errorMessage: task.errorMessage })
      setSyncError(task.errorMessage || '同步失败')
      setTaskId(null)
      setCreating(false)
      setCancelRequested(false)
      refreshRecords()
      refreshLatest()
    },
    [refreshRecords, refreshLatest]
  )

  const handleCancelled = useCallback(() => {
    setTerminalInfo({ status: 'cancelled' })
    setTaskId(null)
    setCreating(false)
    setCancelRequested(false)
    refreshRecords()
    refreshLatest()
  }, [refreshRecords, refreshLatest])

  const { task, cancel } = useTaskStatus<LimitTaskResult>(taskId, {
    enabled: !!taskId,
    pollInterval: POLL_INTERVAL,
    onComplete: handleComplete,
    onFailed: handleFailed,
    onCancelled: handleCancelled,
  })

  // ---- 前端校验（与后端 init_limit 校验同口径，前端拦截不承担一致性） ----
  // 开始日期不强制从最新数据下一天起：默认预填为增量起点，但允许往前选重跑历史。
  const validationMsg = useMemo(() => {
    const hasStart = !!startDate
    const hasEnd = !!endDate
    if (hasStart !== hasEnd) return '请同时选择起止日期，或都留空使用「同步最新交易日」'
    if (!hasStart) return null
    if (startDate > endDate) {
      // 默认预填即此态：最新数据已到今天，下一天尚未到来
      if (incrementStart && incrementStart > todayStr && startDate >= incrementStart) {
        return `数据已同步至 ${latestDate}，今日无增量范围（${incrementStart} 尚未到来）；如需重跑历史请把开始日期往前选`
      }
      return '开始日期不能晚于结束日期'
    }
    if (endDate > todayStr) return '结束日期不能晚于今天'
    const spanMs = new Date(endDate).getTime() - new Date(startDate).getTime()
    if (spanMs > TEN_YEARS_MS) return '日期范围不能超过 10 年'
    return null
  }, [startDate, endDate, todayStr, latestDate, incrementStart])

  // ---- 互斥与禁用判定 ----
  const recordsHaveRunning = syncRecords.some(
    (r) => r.status === 'pending' || r.status === 'running'
  )
  const localRunning = !!task && (task.status === 'pending' || task.status === 'running')
  const localBusy = creating || localRunning
  const isRunning = recordsHaveRunning || localBusy
  const rangeValid = !!startDate && !!endDate && !validationMsg
  const latestDisabled = isRunning
  const rangeDisabled = isRunning || !rangeValid

  // 校验/错误统一展示（前端校验优先，否则后端错误）
  const showError = validationMsg ?? syncError

  // ---- 创建同步（latest = 留空参数；range = 起止成对） ----
  const startSync = async (mode: 'latest' | 'range') => {
    if (mode === 'range' && !rangeValid) return
    if (mode === 'latest' && latestDisabled) return
    setCreating(true)
    setTerminalInfo(null)
    setSyncError(null)
    setCancelRequested(false)
    try {
      const response =
        mode === 'latest'
          ? await adminApi.initLimit()
          : await adminApi.initLimit(startDate, endDate)
      const newTaskId = response.data?.task_id
      if (!newTaskId) {
        throw new Error('未返回任务 ID')
      }
      setTaskId(newTaskId)
      refreshRecords()
    } catch (error) {
      const msg = (error as Error).message
      setSyncError(msg)
      setCreating(false)
    }
  }

  // ---- 取消 ----
  const handleCancel = async () => {
    if (!taskId) return
    setCancelRequested(true)
    try {
      await cancel()
    } catch {
      // useTaskStatus 内部已设 isError；保持取消中过渡直至终态
    }
  }

  // ---- 进度口径：范围任务=交易日，单日任务=三表步骤 ----
  const isRangeTask = !!(task?.params?.start_date)
  const progressUnit = isRangeTask ? '交易日' : '步（三表）'
  const progressPercent =
    task && task.total > 0 ? Math.round((task.progress / task.total) * 100) : 0

  // ---- 终态展示：优先本地终态回调记录，其次当前轮询任务（终态但未被清理）----
  const terminalFromTask: TerminalInfo | null =
    task && !localRunning ? { status: task.status, errorMessage: task.errorMessage } : null
  const displayTerminal = terminalInfo ?? terminalFromTask

  // ---- 渲染 ----
  if (!isAdmin) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-destructive mx-auto mb-4" />
          <p className="text-muted-foreground">您没有权限访问此页面</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6" data-testid="limit-sync-panel">
      {/* 创建区 */}
      <div className="bg-card rounded-lg shadow-sm border border-border p-6">
        <div className="flex items-center gap-2 mb-4">
          <Database className="w-5 h-5 text-primary" />
          <h3 className="text-lg font-semibold text-foreground">涨停专题同步</h3>
        </div>
        <p className="text-sm text-muted-foreground mb-2">
          同步涨停专题三表（涨跌停明细 / 连板天梯 / 涨停最强板块），按 trade_date
          删旧插新、幂等可重跑。可一键同步最新交易日，或按日期范围逐交易日回补。
        </p>

        {/* 当前最新数据日期与增量口径 */}
        <div
          data-testid="limit-sync-latest-date"
          className="flex items-center gap-2 text-sm mb-4"
        >
          <CalendarClock className="w-4 h-4 text-muted-foreground" />
          {latestLoading ? (
            <span className="text-muted-foreground">最新数据日期加载中…</span>
          ) : latestDate ? (
            <span className="text-muted-foreground">
              当前最新数据日期：
              <span className="font-mono font-semibold text-foreground">{latestDate}</span>
              <span className="ml-2 text-xs">
                （增量从 {incrementStart} 起，结束日期默认今天）
              </span>
            </span>
          ) : (
            <span className="text-muted-foreground">
              暂无历史数据：请手动选择起止范围，或使用「同步最新交易日」
            </span>
          )}
        </div>

        <div className="flex items-center gap-4 flex-wrap">
          {/* 一键同步最新交易日（起止留空） */}
          <button
            data-testid="limit-sync-latest-button"
            onClick={() => startSync('latest')}
            disabled={latestDisabled}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {localBusy ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>同步…（{task?.progress ?? 0} / {task?.total ?? 0}）</span>
              </>
            ) : (
              <>
                <Zap className="w-4 h-4" />
                <span>同步最新交易日</span>
              </>
            )}
          </button>

          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-muted-foreground" />
            <input
              type="date"
              value={startDate}
              onChange={(e) =>
                setOverrideDates({ start: e.target.value, end: endDate })
              }
              disabled={localBusy}
              aria-label="开始日期"
              className="px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-primary focus:border-primary disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <span className="text-sm text-muted-foreground">至</span>
            <input
              type="date"
              value={endDate}
              onChange={(e) =>
                setOverrideDates({ start: startDate, end: e.target.value })
              }
              disabled={localBusy}
              aria-label="结束日期"
              className="px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-primary focus:border-primary disabled:opacity-50 disabled:cursor-not-allowed"
            />
          </div>

          <button
            data-testid="limit-sync-start-button"
            onClick={() => startSync('range')}
            disabled={rangeDisabled}
            className="flex items-center gap-2 px-4 py-2 border border-primary text-primary rounded-lg hover:bg-primary/5 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <RefreshCw className="w-4 h-4" />
            <span>按范围同步</span>
          </button>

          {/* 取消（running 时可见） */}
          {localRunning && (
            <button
              onClick={handleCancel}
              disabled={cancelRequested}
              className="flex items-center gap-2 px-3 py-2 border border-border rounded-lg text-sm text-foreground hover:bg-secondary transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {cancelRequested ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  取消中…
                </>
              ) : (
                <>
                  <Ban className="w-4 h-4" />
                  取消同步
                </>
              )}
            </button>
          )}
        </div>

        {/* 行内错误提示：前端校验失败或后端拒绝 message */}
        {showError && (
          <div
            data-testid="limit-sync-validation-error"
            className="mt-3 flex items-center gap-2 text-sm text-destructive"
          >
            <AlertCircle className="w-4 h-4" />
            <span>{showError}</span>
          </div>
        )}

        {/* 互斥提示：记录列表含运行中同类任务 */}
        {recordsHaveRunning && (
          <div
            data-testid="limit-sync-mutex-hint"
            className="mt-3 flex items-center gap-2 text-sm text-amber-600 dark:text-amber-400"
          >
            <AlertCircle className="w-4 h-4" />
            <span>已有涨停专题任务在运行，请等待当前任务完成后再发起新同步</span>
          </div>
        )}

        {/* 进度区（running） */}
        {localRunning && task && task.total > 0 && (
          <div data-testid="limit-sync-progress" className="mt-4">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm text-muted-foreground">
                同步中…（{task.progress} / {task.total} {progressUnit}）
              </span>
              <span className="text-sm text-muted-foreground">{progressPercent}%</span>
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

      {/* 终态横幅（handler 无结构化 result，仅状态与失败原因，明细见记录与日志） */}
      {displayTerminal && !localRunning && (
        <div
          data-testid={`limit-sync-terminal-${displayTerminal.status}`}
          className={`rounded-lg shadow-sm border p-6 ${
            displayTerminal.status === 'completed'
              ? 'bg-card border-fall/30'
              : displayTerminal.status === 'failed'
                ? 'bg-card border-destructive/30'
                : 'bg-card border-border'
          }`}
        >
          <div className="flex items-start gap-3">
            {displayTerminal.status === 'completed' ? (
              <CheckCircle2 className="w-5 h-5 text-fall mt-0.5" />
            ) : (
              <AlertCircle
                className={`w-5 h-5 mt-0.5 ${displayTerminal.status === 'failed' ? 'text-destructive' : 'text-muted-foreground'}`}
              />
            )}
            <div className="text-sm">
              <div className="font-medium text-foreground">
                {displayTerminal.status === 'completed'
                  ? '同步完成'
                  : displayTerminal.status === 'failed'
                    ? '同步失败'
                    : '已取消'}
              </div>
              {displayTerminal.status === 'failed' && displayTerminal.errorMessage && (
                <p
                  className="mt-1 text-destructive break-all"
                  data-testid="limit-sync-terminal-error"
                >
                  {displayTerminal.errorMessage}
                </p>
              )}
              <p className="mt-1 text-muted-foreground">
                逐日明细见下方同步记录与任务日志（按 trade_date 删旧插新，可直接重跑）。
              </p>
            </div>
          </div>
        </div>
      )}

      {/* 同步记录表格（分页） */}
      <div className="bg-card rounded-lg shadow-sm border border-border">
        <div className="px-6 py-4 border-b border-border flex items-center justify-between">
          <h3 className="text-lg font-semibold text-foreground">同步记录</h3>
          <button
            onClick={() => refreshRecords()}
            className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
            title="刷新"
          >
            <RefreshCw className="w-4 h-4" />
            <span>刷新</span>
          </button>
        </div>
        <div data-testid="limit-sync-records">
          {recordsLoading && syncRecords.length === 0 ? (
            <div className="px-6 py-8 flex items-center justify-center text-muted-foreground">
              <Loader2 className="w-4 h-4 animate-spin mr-2" />
              加载中...
            </div>
          ) : syncRecords.length === 0 ? (
            <div className="px-6 py-8 text-center text-muted-foreground">暂无同步记录</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="px-6 py-3 text-left font-medium text-muted-foreground">时间</th>
                    <th className="px-6 py-3 text-left font-medium text-muted-foreground">任务</th>
                    <th className="px-6 py-3 text-left font-medium text-muted-foreground">范围</th>
                    <th className="px-6 py-3 text-left font-medium text-muted-foreground">状态</th>
                    <th className="px-6 py-3 text-left font-medium text-muted-foreground">进度</th>
                    <th className="px-6 py-3 text-left font-medium text-muted-foreground">详情</th>
                  </tr>
                </thead>
                <tbody>
                  {syncRecords.map((record) => {
                    const params = (record.params || {}) as {
                      start_date?: string
                      end_date?: string
                    }
                    const rangeText =
                      params.start_date && params.end_date
                        ? `${params.start_date} ~ ${params.end_date}`
                        : '最新交易日'
                    return (
                      <tr key={record.taskId} className="border-b border-border last:border-0">
                        <td className="px-6 py-3 text-muted-foreground whitespace-nowrap">
                          {record.createdAt
                            ? new Date(record.createdAt).toLocaleString('zh-CN')
                            : '-'}
                        </td>
                        <td className="px-6 py-3 font-mono text-xs text-muted-foreground">
                          {record.taskId.slice(0, 8)}
                        </td>
                        <td className="px-6 py-3 text-muted-foreground whitespace-nowrap">
                          {rangeText}
                        </td>
                        <td className="px-6 py-3">
                          <StatusBadge status={record.status} />
                        </td>
                        <td className="px-6 py-3 text-muted-foreground tabular-nums whitespace-nowrap">
                          {record.progress} / {record.total}
                        </td>
                        <td className="px-6 py-3 text-muted-foreground max-w-xs truncate">
                          {record.status === 'failed' && record.errorMessage
                            ? record.errorMessage
                            : '-'}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
        {/* 分页 */}
        {(recordsPage > 1 || recordsTotal > recordsPage * PAGE_SIZE) && (
          <div className="px-6 py-3 border-t border-border flex items-center justify-between">
            <span className="text-xs text-muted-foreground">
              共 {recordsTotal} 条，第 {recordsPage} 页
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setRecordsPage((p) => Math.max(1, p - 1))}
                disabled={recordsPage <= 1}
                className="rounded border border-border px-3 py-1 text-sm text-foreground transition-colors hover:bg-secondary disabled:opacity-40 disabled:cursor-not-allowed"
              >
                上一页
              </button>
              {recordsTotal > recordsPage * PAGE_SIZE && (
                <button
                  type="button"
                  data-testid="limit-sync-records-next-page"
                  onClick={() => setRecordsPage((p) => p + 1)}
                  className="rounded border border-border px-3 py-1 text-sm text-foreground transition-colors hover:bg-secondary"
                >
                  下一页
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

/** 状态徽章（五态，与 IndexSyncPanel / MarginSyncPanel 一致） */
function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { color: string; label: string }> = {
    pending: { color: 'bg-secondary text-foreground', label: '等待中' },
    running: { color: 'bg-primary-light text-primary', label: '运行中' },
    completed: { color: 'bg-fall/10 text-fall', label: '已完成' },
    failed: { color: 'bg-destructive/10 text-destructive', label: '失败' },
    cancelled: { color: 'bg-secondary text-muted-foreground', label: '已取消' },
  }

  const { color, label } = config[status] || {
    color: 'bg-secondary text-muted-foreground',
    label: status,
  }

  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${color}`}>
      {label}
    </span>
  )
}
