'use client'

/**
 * 融资融券同步面板（第 17 期 plan-08 Task 3/4/5）
 *
 * 数据管理页「融资融券」Tab 内容，范式严格对齐 16 期 MarketMetricsSyncPanel.tsx，
 * 按两融契约裁剪（无 expected/daily/suspended/final 四类计数）：
 * - 创建区：起止日期输入（默认最近 1 年：end=今天、start=今天−364 自然日，spec 边界
 *   "历史范围=近1年"；16 期默认 30 自然日，此处不同）+ 前端校验（倒置/未来/超 10 年）
 * - 点击 → adminApi.initMargin（POST /admin/init/margin，body snake_case）→ taskId
 *   → useTaskStatus 2s 轮询
 * - 进度区：running 显示 progress/total（交易日口径）+ 百分比
 * - 终态区：success/skipped/failed 三类计数（成功/跳过非交易日/失败）
 * - 日期结果区：dateResults 列表点击展开状态 + 失败原因（截断 100 字符、title 保留
 *   全文）；unprocessedDates 非空时独立提示块（取消/超时/重启恢复遗留）
 * - 互斥：记录列表含 pending/running 同类任务 → 按钮禁用 + 提示；后端二次拒绝展示
 *   message（前端禁用不承担一致性）
 * - 记录区：SWR 拉 /api/v1/admin/tasks?task_types=sync_market_margin + 分页
 * - 取消：复用 useTaskStatus.cancel()；失败重试：终态 failed 后创建区释放（同参数预填）
 *
 * result 键全 camelCase（plan-04 handler 构造即 camelCase，to_dict() 原样透传），
 * 前端直消费、无键转换。
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
  ChevronDown,
  ChevronRight,
  Ban,
} from 'lucide-react'
import { adminApi } from '@/lib/api'
import { useTaskStatus, type TaskData } from '@/hooks/useTaskStatus'
import { useAuth } from '@/contexts/AuthContext'
import { useRequireAdmin } from '@/hooks/useRequireAdmin'
import { fetcher } from '@/lib/fetcher'
import type { MarginTaskResult, MarginDateResult } from '@/types/marginTypes'

/** 同步任务类型（后端 task_type） */
const TASK_TYPE = 'sync_market_margin'
/** 记录分页大小（与 IndexSyncPanel / MarketMetricsSyncPanel 一致） */
const PAGE_SIZE = 20
/** 轮询间隔（2s） */
const POLL_INTERVAL = 2000
/** 失败原因截断长度（字符，title 保留全文） */
const REASON_TRUNCATE = 100
/** dateResults 默认渲染条数（近 1 年 ≈ 240+ 交易日，避免一次性 DOM 爆炸） */
const MAX_VISIBLE_DATE_RESULTS = 50
/** 跨度上限（10 年） */
const TEN_YEARS_MS = 10 * 365.25 * 24 * 3600 * 1000
/** 默认回看自然日（近 1 年：今天 − 364 天） */
const DEFAULT_LOOKBACK_DAYS = 364

/** 同步记录行（与后端 AsyncTask.to_dict camelCase 契约一致，携带 result） */
interface SyncRecord {
  taskId: string
  taskType: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress: number
  total: number
  createdAt: string
  errorMessage?: string | null
  params?: Record<string, unknown> | null
  result?: MarginTaskResult | null
}

/** 按本地时区格式化日期，避免 toISOString() 在 UTC 转换后产生日期偏移。 */
function formatLocalDate(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

/** 回退 N 个自然日，返回新 Date。 */
function subtractDays(date: Date, days: number): Date {
  const result = new Date(date)
  result.setDate(result.getDate() - days)
  return result
}

/** 截断文本并追加省略号（仅展示层，title 保留全文）。 */
function truncateReason(text: string | undefined, max: number): string {
  if (!text) return ''
  return text.length > max ? `${text.slice(0, max)}…` : text
}

export default function MarginSyncPanel() {
  useRequireAdmin()
  const { isAdmin } = useAuth()

  // ---- 创建区：起止日期（默认近 1 年，end=今天、start=今天−364） ----
  const [startDate, setStartDate] = useState<string>(() =>
    formatLocalDate(subtractDays(new Date(), DEFAULT_LOOKBACK_DAYS))
  )
  const [endDate, setEndDate] = useState<string>(() => formatLocalDate(new Date()))

  // ---- 本地任务状态 ----
  const [taskId, setTaskId] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  // 终态聚合结果（来自本地任务 result）
  const [terminalResult, setTerminalResult] = useState<MarginTaskResult | null>(null)
  // 创建/同步过程错误（前端校验失败或后端拒绝 message）
  const [syncError, setSyncError] = useState<string | null>(null)
  const [cancelRequested, setCancelRequested] = useState(false)

  // ---- 记录分页 ----
  const [recordsPage, setRecordsPage] = useState(1)

  // ---- dateResults 展开（按 tradeDate）+ 懒加载条数 ----
  const [expandedDates, setExpandedDates] = useState<Set<string>>(new Set())
  const [visibleDateResults, setVisibleDateResults] = useState(MAX_VISIBLE_DATE_RESULTS)

  // ---- 记录列表 SWR（fetcher 拼 NEXT_PUBLIC_API_URL 前缀，key 含 /api/v1 前缀） ----
  const recordsKey = `/api/v1/admin/tasks?task_types=${TASK_TYPE}&page=${recordsPage}&page_size=${PAGE_SIZE}`
  const {
    data: tasksData,
    isLoading: recordsLoading,
    mutate: refreshRecords,
  } = useSWR<{ tasks: SyncRecord[]; total: number; page: number }>(recordsKey, fetcher)

  const syncRecords = tasksData?.tasks ?? []
  const recordsTotal = tasksData?.total ?? 0

  // ---- useTaskStatus 回调 ----
  const handleComplete = useCallback(
    (task: TaskData<MarginTaskResult>) => {
      setTerminalResult(task.result ?? null)
      setSyncError(null)
      setTaskId(null)
      setCreating(false)
      setCancelRequested(false)
      refreshRecords()
    },
    [refreshRecords]
  )

  const handleFailed = useCallback(
    (task: TaskData<MarginTaskResult>) => {
      setTerminalResult(task.result ?? null)
      setSyncError(task.errorMessage || '同步失败')
      setTaskId(null)
      setCreating(false)
      setCancelRequested(false)
      refreshRecords()
    },
    [refreshRecords]
  )

  const handleCancelled = useCallback(
    (task: TaskData<MarginTaskResult>) => {
      setTerminalResult(task.result ?? null)
      setTaskId(null)
      setCreating(false)
      setCancelRequested(false)
      refreshRecords()
    },
    [refreshRecords]
  )

  // onProgress 不需要额外 state：task 对象由 useTaskStatus 内部维护并触发重渲染
  const { task, cancel } = useTaskStatus<MarginTaskResult>(taskId, {
    enabled: !!taskId,
    pollInterval: POLL_INTERVAL,
    onComplete: handleComplete,
    onFailed: handleFailed,
    onCancelled: handleCancelled,
  })

  // ---- 前端校验（与后端 plan-05 五项校验中的前三项同口径，前端拦截不承担一致性） ----
  const todayStr = useMemo(() => formatLocalDate(new Date()), [])
  const validationMsg = useMemo(() => {
    if (!startDate || !endDate) return null
    if (startDate > endDate) return '开始日期不能晚于结束日期'
    if (endDate > todayStr) return '结束日期不能晚于今天'
    const spanMs = new Date(endDate).getTime() - new Date(startDate).getTime()
    if (spanMs > TEN_YEARS_MS) return '日期范围不能超过 10 年'
    return null
  }, [startDate, endDate, todayStr])

  // ---- 互斥与禁用判定 ----
  const recordsHaveRunning = syncRecords.some(
    (r) => r.status === 'pending' || r.status === 'running'
  )
  const localRunning = !!task && (task.status === 'pending' || task.status === 'running')
  const localBusy = creating || localRunning
  const isRunning = recordsHaveRunning || localBusy
  const datesValid = !!startDate && !!endDate && !validationMsg
  const startDisabled = isRunning || !datesValid

  // ---- 展示结果：优先本地终态回调，其次当前轮询 task.result，最后最近一条带 result 的记录 ----
  // 本地任务 running（pending/running）时禁止回退到历史记录，避免"正在跑却显示旧结果"
  // 的视觉歧义（16 期 review S-1 同款裁定）。此时结果区不渲染，改由下方占位块提示。
  const recordResult = syncRecords.find((r) => r.result)?.result ?? null
  const displayResult: MarginTaskResult | null = localRunning
    ? terminalResult ?? task?.result ?? null
    : terminalResult ?? task?.result ?? recordResult

  // 校验/错误统一展示（前端校验优先，否则后端错误）
  const showError = validationMsg ?? syncError

  // ---- 创建同步 ----
  const startSync = async () => {
    if (!datesValid) return
    setCreating(true)
    setTerminalResult(null)
    setSyncError(null)
    setCancelRequested(false)
    setVisibleDateResults(MAX_VISIBLE_DATE_RESULTS)
    try {
      const response = await adminApi.initMargin(startDate, endDate)
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

  // ---- dateResults 展开/收起 ----
  const toggleDateExpand = (tradeDate: string) => {
    setExpandedDates((prev) => {
      const next = new Set(prev)
      if (next.has(tradeDate)) {
        next.delete(tradeDate)
      } else {
        next.add(tradeDate)
      }
      return next
    })
  }

  // dateResults 按交易日倒序（最近在前）
  const sortedDateResults: MarginDateResult[] = useMemo(() => {
    if (!displayResult?.dateResults) return []
    return [...displayResult.dateResults].sort((a, b) =>
      b.tradeDate.localeCompare(a.tradeDate)
    )
  }, [displayResult])
  const visibleDateResultList = sortedDateResults.slice(0, visibleDateResults)

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

  const progressPercent =
    task && task.total > 0 ? Math.round((task.progress / task.total) * 100) : 0

  return (
    <div className="space-y-6" data-testid="margin-sync-panel">
      {/* 创建区 */}
      <div className="bg-card rounded-lg shadow-sm border border-border p-6">
        <div className="flex items-center gap-2 mb-4">
          <Database className="w-5 h-5 text-primary" />
          <h3 className="text-lg font-semibold text-foreground">融资融券同步</h3>
        </div>
        <p className="text-sm text-muted-foreground mb-4">
          按日期范围逐交易日同步沪深北全市场融资融券指标（融资余额/融券余额/买卖额等）。
          交易日口径推进，非交易日自动跳过，结束后显示成功/跳过/失败三类计数，可展开失败日期查看原因。
        </p>

        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-muted-foreground" />
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              disabled={localBusy}
              aria-label="开始日期"
              className="px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-primary focus:border-primary disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <span className="text-sm text-muted-foreground">至</span>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              disabled={localBusy}
              aria-label="结束日期"
              className="px-3 py-2 border border-border rounded-lg bg-background text-foreground focus:ring-2 focus:ring-primary focus:border-primary disabled:opacity-50 disabled:cursor-not-allowed"
            />
          </div>

          <button
            data-testid="margin-sync-start-button"
            onClick={startSync}
            disabled={startDisabled}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {localBusy ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>同步…（{task?.progress ?? 0} / {task?.total ?? 0}）</span>
              </>
            ) : (
              <>
                <RefreshCw className="w-4 h-4" />
                <span>开始同步</span>
              </>
            )}
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
            data-testid="margin-sync-validation-error"
            className="mt-3 flex items-center gap-2 text-sm text-destructive"
          >
            <AlertCircle className="w-4 h-4" />
            <span>{showError}</span>
          </div>
        )}

        {/* 互斥提示：记录列表含运行中同类任务 */}
        {recordsHaveRunning && (
          <div
            data-testid="margin-sync-mutex-hint"
            className="mt-3 flex items-center gap-2 text-sm text-amber-600 dark:text-amber-400"
          >
            <AlertCircle className="w-4 h-4" />
            <span>已有融资融券任务在运行，请等待当前任务完成后再发起新同步</span>
          </div>
        )}

        {/* 进度区（running） */}
        {localRunning && task && task.total > 0 && (
          <div className="mt-4" data-testid="margin-sync-progress">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm text-muted-foreground">
                同步中…（{task.progress} / {task.total} 交易日）
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

      {/* 同步进行中占位（本地任务 running）：隐藏历史结果回退，结果待任务完成 */}
      {localRunning && (
        <div
          data-testid="margin-sync-result-pending"
          className="bg-card rounded-lg shadow-sm border border-border p-6"
        >
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="w-4 h-4 animate-spin text-primary" />
            <span>同步进行中，结果待任务完成后展示</span>
          </div>
        </div>
      )}

      {/* 终态结果区：三类计数 */}
      {displayResult && (
        <div className="bg-card rounded-lg shadow-sm border border-border p-6">
          <div className="flex items-center gap-2 mb-4">
            <CheckCircle2 className="w-5 h-5 text-primary" />
            <h3 className="text-lg font-semibold text-foreground">同步结果</h3>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div className="rounded-lg border border-fall/30 bg-fall/5 p-4">
              <div className="text-xs text-muted-foreground mb-1">成功</div>
              <div
                className="text-2xl font-semibold text-fall tabular-nums"
                data-testid="margin-sync-success-count"
              >
                {displayResult.successCount}
              </div>
              <div className="text-xs text-muted-foreground">交易日</div>
            </div>
            <div className="rounded-lg border border-border bg-secondary/30 p-4">
              <div className="text-xs text-muted-foreground mb-1">跳过</div>
              <div
                className="text-2xl font-semibold text-foreground tabular-nums"
                data-testid="margin-sync-skipped-count"
              >
                {displayResult.skippedCount}
              </div>
              <div className="text-xs text-muted-foreground">非交易日</div>
            </div>
            <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4">
              <div className="text-xs text-muted-foreground mb-1">失败</div>
              <div
                className="text-2xl font-semibold text-destructive tabular-nums"
                data-testid="margin-sync-failed-count"
              >
                {displayResult.failedCount}
              </div>
              <div className="text-xs text-muted-foreground">交易日</div>
            </div>
          </div>

          {/* 未处理日期提示（取消/超时/重启恢复遗留） */}
          {displayResult.unprocessedDates && displayResult.unprocessedDates.length > 0 && (
            <div
              data-testid="margin-sync-unprocessed-dates"
              className="mt-4 rounded-lg border border-amber-500/30 bg-amber-500/5 p-4"
            >
              <div className="flex items-center gap-2 mb-1 text-sm font-medium text-amber-600 dark:text-amber-400">
                <AlertCircle className="w-4 h-4" />
                未处理日期（取消/超时/重启恢复遗留）
              </div>
              <p className="text-sm text-muted-foreground">
                {displayResult.unprocessedDates.join('、')}
              </p>
            </div>
          )}

          {/* 日期结果列表（点击展开状态 + 截断 reason，两融无四类计数） */}
          {sortedDateResults.length > 0 && (
            <div className="mt-6">
              <h4 className="text-sm font-semibold text-foreground mb-3">逐日同步结果</h4>
              <ul
                data-testid="margin-sync-date-result-list"
                className="divide-y divide-border rounded-lg border border-border bg-background/50"
              >
                {visibleDateResultList.map((dr) => {
                  const expanded = expandedDates.has(dr.tradeDate)
                  return (
                    <li
                      key={dr.tradeDate}
                      data-testid={`margin-sync-date-result-${dr.tradeDate}`}
                      onClick={() => toggleDateExpand(dr.tradeDate)}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault()
                          toggleDateExpand(dr.tradeDate)
                        }
                      }}
                      className="cursor-pointer px-4 py-3 transition-colors hover:bg-secondary/40"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="flex items-center gap-2">
                          {expanded ? (
                            <ChevronDown className="w-4 h-4 text-muted-foreground" />
                          ) : (
                            <ChevronRight className="w-4 h-4 text-muted-foreground" />
                          )}
                          <span className="font-mono tabular-nums text-foreground">
                            {dr.tradeDate}
                          </span>
                        </div>
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                            dr.status === 'success'
                              ? 'bg-fall/10 text-fall'
                              : 'bg-destructive/10 text-destructive'
                          }`}
                        >
                          {dr.status === 'success' ? '成功' : '失败'}
                        </span>
                      </div>
                      {expanded && (
                        <div className="mt-3 text-sm">
                          <div className="text-muted-foreground">
                            状态{' '}
                            <span
                              className={`font-semibold ${
                                dr.status === 'success' ? 'text-fall' : 'text-destructive'
                              }`}
                            >
                              {dr.status === 'success' ? '成功' : '失败'}
                            </span>
                          </div>
                          {dr.reason && (
                            <div className="mt-1 text-destructive" title={dr.reason}>
                              原因：{truncateReason(dr.reason, REASON_TRUNCATE)}
                            </div>
                          )}
                        </div>
                      )}
                    </li>
                  )
                })}
              </ul>
              {sortedDateResults.length > visibleDateResults && (
                <button
                  type="button"
                  onClick={() =>
                    setVisibleDateResults((c) => c + MAX_VISIBLE_DATE_RESULTS)
                  }
                  className="mt-3 inline-flex items-center gap-1 text-sm text-primary hover:underline"
                >
                  <ChevronDown className="w-4 h-4" />
                  加载更多（剩余 {sortedDateResults.length - visibleDateResults} 日）
                </button>
              )}
            </div>
          )}
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
        <div data-testid="margin-sync-records">
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
                    const params = record.params || {}
                    const sd = params.start_date
                    const ed = params.end_date
                    const rangeText =
                      sd && ed ? `${sd} ~ ${ed}` : sd ? `${sd} ~ ` : '-'
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
                  data-testid="margin-sync-records-next-page"
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

/** 状态徽章（五态，与 IndexSyncPanel / MarketMetricsSyncPanel 一致） */
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
