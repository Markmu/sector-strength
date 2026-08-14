/**
 * MarketMetricsSyncPanel 组件测试（第 16 期 plan-08 Task 7）
 *
 * 覆盖：默认渲染（合法默认日期→按钮可用）/ 前端校验三类拦截（倒置/未来/超 10 年，AC-10）/
 * 互斥禁用（记录含运行中任务，AC-11）/ 创建调用 snake_case body / 后端拒绝展示 message /
 * 终态三类计数（AC-02）/ dateResults 四类计数展开（AC-07）/ unprocessedDates 提示 /
 * 记录表格状态徽章 + 分页。
 *
 * Mock 策略（参照 MarketMetricsPanel.test.tsx 范式）：
 * - swr → 控制 useSWR 返回值（records）
 * - @/hooks/useTaskStatus → 控制 task/cancel
 * - @/lib/api → 控制 adminApi.initMarketMetrics
 * - @/contexts/AuthContext → 控制 isAdmin
 * - @/hooks/useRequireAdmin → no-op（避免 router）
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import MarketMetricsSyncPanel from '@/components/market-metrics/MarketMetricsSyncPanel'

// ---- Mock adminApi（initMarketMetrics 可按用例覆写返回） ----
const mockInitMarketMetrics = jest.fn()
jest.mock('@/lib/api', () => ({
  __esModule: true,
  adminApi: { initMarketMetrics: (...args: unknown[]) => mockInitMarketMetrics(...args) },
}))

// ---- Mock useTaskStatus：返回受控 task / cancel ----
const mockCancel = jest.fn()
let mockTaskStatusValue: any = { task: null, cancel: mockCancel }
jest.mock('@/hooks/useTaskStatus', () => ({
  __esModule: true,
  useTaskStatus: jest.fn(() => mockTaskStatusValue),
}))

// ---- Mock useSWR：控制记录列表 ----
const mockRefreshRecords = jest.fn()
let mockSwrValue: any = {
  data: undefined,
  isLoading: false,
  mutate: mockRefreshRecords,
}
jest.mock('swr', () => ({
  __esModule: true,
  default: jest.fn(() => mockSwrValue),
}))

// ---- Mock 权限 ----
let mockIsAdmin = true
jest.mock('@/contexts/AuthContext', () => ({
  __esModule: true,
  useAuth: () => ({ isAdmin: mockIsAdmin }),
}))
jest.mock('@/hooks/useRequireAdmin', () => ({
  __esModule: true,
  useRequireAdmin: jest.fn(),
}))

import type {
  MarketMetricsTaskResult,
  MarketMetricsDateResult,
} from '@/types/marketMetricsTypes'
import type { TaskData } from '@/hooks/useTaskStatus'

/** 构造 MarketMetricsTaskResult fixture（与 mock-market-metrics-sync-api 同口径） */
function buildResult(opts?: {
  successDays?: number
  failedDays?: number
  skippedCount?: number
  unprocessedDates?: string[]
}): MarketMetricsTaskResult {
  const successDays = opts?.successDays ?? 2
  const failedDays = opts?.failedDays ?? 1
  const dateResults: MarketMetricsDateResult[] = []
  const base = new Date('2026-08-13T00:00:00Z')
  let offset = 0
  const iso = (d: Date) => d.toISOString().slice(0, 10)
  const stepBack = () => {
    const d = new Date(base)
    d.setUTCDate(d.getUTCDate() - offset)
    offset += 1
    return iso(d)
  }
  for (let i = 0; i < successDays; i++) {
    const daily = 5180 + i
    const suspended = 24 + (i % 5)
    dateResults.push({
      tradeDate: stepBack(),
      status: 'success',
      expected: daily + suspended,
      daily,
      suspended,
      final: daily,
    })
  }
  for (let i = 0; i < failedDays; i++) {
    const daily = 4100 + i
    const suspended = 18 + (i % 4)
    dateResults.push({
      tradeDate: stepBack(),
      status: 'failed',
      expected: daily + suspended + 120,
      daily,
      suspended,
      final: 0,
      reason: '完整性校验失败：daily_count + suspended_count 与 expected 不一致，缺失 120 只',
    })
  }
  return {
    successCount: successDays,
    skippedCount: opts?.skippedCount ?? 8,
    failedCount: failedDays,
    dateResults,
    unprocessedDates: opts?.unprocessedDates ?? [],
  }
}

/** 构造 completed TaskData（携带 result） */
function buildCompletedTask(result: MarketMetricsTaskResult | null): TaskData {
  return {
    taskId: 'task-mm-sync-001',
    taskType: 'sync_market_metrics',
    status: 'completed',
    progress: 10,
    total: 10,
    percent: 100,
    params: { start_date: '2026-07-15', end_date: '2026-08-13' },
    errorMessage: undefined,
    retryCount: 0,
    maxRetries: 0,
    createdAt: '2026-08-13T10:00:00.000Z',
    startedAt: '2026-08-13T10:00:00.000Z',
    completedAt: '2026-08-13T10:05:00.000Z',
    result,
  }
}

/** 构造 running TaskData（无 result，本地任务未终态） */
function buildRunningTask(): TaskData {
  return {
    taskId: 'task-mm-sync-001',
    taskType: 'sync_market_metrics',
    status: 'running',
    progress: 3,
    total: 10,
    percent: 30,
    params: { start_date: '2026-07-15', end_date: '2026-08-13' },
    errorMessage: undefined,
    retryCount: 0,
    maxRetries: 0,
    createdAt: '2026-08-13T10:00:00.000Z',
    startedAt: '2026-08-13T10:00:00.000Z',
    completedAt: undefined,
    result: undefined,
  }
}

function setSwr(value: Partial<typeof mockSwrValue>) {
  mockSwrValue = { ...mockSwrValue, ...value }
}

function setTaskStatus(value: Partial<typeof mockTaskStatusValue>) {
  mockTaskStatusValue = { ...mockTaskStatusValue, ...value }
}

describe('MarketMetricsSyncPanel', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    mockIsAdmin = true
    mockInitMarketMetrics.mockReset()
    mockSwrValue = { data: undefined, isLoading: false, mutate: mockRefreshRecords }
    mockTaskStatusValue = { task: null, cancel: mockCancel }
  })

  describe('默认渲染与前端校验（AC-10）', () => {
    it('渲染面板根、两个日期输入、开始同步按钮；默认合法日期→按钮可用', () => {
      render(<MarketMetricsSyncPanel />)
      expect(screen.getByTestId('market-metrics-sync-panel')).toBeInTheDocument()
      expect(screen.getByLabelText('开始日期')).toBeInTheDocument()
      expect(screen.getByLabelText('结束日期')).toBeInTheDocument()
      const btn = screen.getByTestId('market-metrics-sync-start-button')
      expect(btn).toBeInTheDocument()
      // 默认最近 30 自然日（合法）→ 按钮可用
      expect(btn).not.toBeDisabled()
      // 无校验错误、无互斥提示
      expect(screen.queryByTestId('market-metrics-sync-validation-error')).toBeNull()
      expect(screen.queryByTestId('market-metrics-sync-mutex-hint')).toBeNull()
    })

    it('起止倒置：按钮禁用 + 行内错误提示', () => {
      render(<MarketMetricsSyncPanel />)
      fireEvent.change(screen.getByLabelText('开始日期'), { target: { value: '2026-08-10' } })
      fireEvent.change(screen.getByLabelText('结束日期'), { target: { value: '2026-08-01' } })
      expect(screen.getByTestId('market-metrics-sync-start-button')).toBeDisabled()
      expect(screen.getByTestId('market-metrics-sync-validation-error')).toHaveTextContent(
        /不能晚于/
      )
    })

    it('未来结束日：按钮禁用 + 行内错误提示', () => {
      render(<MarketMetricsSyncPanel />)
      fireEvent.change(screen.getByLabelText('开始日期'), { target: { value: '2026-08-01' } })
      fireEvent.change(screen.getByLabelText('结束日期'), { target: { value: '2099-12-31' } })
      expect(screen.getByTestId('market-metrics-sync-start-button')).toBeDisabled()
      expect(screen.getByTestId('market-metrics-sync-validation-error')).toHaveTextContent(
        /不能晚于今天/
      )
    })

    it('跨度超 10 年：按钮禁用 + 行内错误提示', () => {
      render(<MarketMetricsSyncPanel />)
      fireEvent.change(screen.getByLabelText('开始日期'), { target: { value: '2000-01-01' } })
      fireEvent.change(screen.getByLabelText('结束日期'), { target: { value: '2026-08-13' } })
      expect(screen.getByTestId('market-metrics-sync-start-button')).toBeDisabled()
      expect(screen.getByTestId('market-metrics-sync-validation-error')).toHaveTextContent(
        /10 年/
      )
    })
  })

  describe('创建调用与互斥（AC-11）', () => {
    it('点击开始同步：以 snake_case body 调用 initMarketMetrics', async () => {
      mockInitMarketMetrics.mockResolvedValue({ data: { task_id: 'task-new' } })
      render(<MarketMetricsSyncPanel />)
      fireEvent.change(screen.getByLabelText('开始日期'), { target: { value: '2026-07-15' } })
      fireEvent.change(screen.getByLabelText('结束日期'), { target: { value: '2026-08-13' } })
      fireEvent.click(screen.getByTestId('market-metrics-sync-start-button'))
      await waitFor(() => {
        expect(mockInitMarketMetrics).toHaveBeenCalledWith('2026-07-15', '2026-08-13')
      })
    })

    it('后端互斥拒绝（success=false 抛错）：展示返回 message', async () => {
      const mutexMsg = '已有市场量价同步任务正在运行，请等待当前任务完成'
      mockInitMarketMetrics.mockRejectedValue(new Error(mutexMsg))
      render(<MarketMetricsSyncPanel />)
      fireEvent.change(screen.getByLabelText('开始日期'), { target: { value: '2026-07-15' } })
      fireEvent.change(screen.getByLabelText('结束日期'), { target: { value: '2026-08-13' } })
      fireEvent.click(screen.getByTestId('market-metrics-sync-start-button'))
      await waitFor(() => {
        expect(screen.getByTestId('market-metrics-sync-validation-error')).toHaveTextContent(
          mutexMsg
        )
      })
    })

    it('记录列表含运行中任务：按钮禁用 + 互斥提示（AC-11）', () => {
      setSwr({
        data: {
          tasks: [
            {
              taskId: 'task-running',
              taskType: 'sync_market_metrics',
              status: 'running',
              progress: 3,
              total: 10,
              createdAt: '2026-08-13T10:00:00.000Z',
              result: null,
              params: { start_date: '2026-07-15', end_date: '2026-08-13' },
            },
          ],
          total: 1,
          page: 1,
        },
      })
      render(<MarketMetricsSyncPanel />)
      expect(screen.getByTestId('market-metrics-sync-start-button')).toBeDisabled()
      expect(screen.getByTestId('market-metrics-sync-mutex-hint')).toBeInTheDocument()
    })
  })

  describe('终态结果与日期展开（AC-02 / AC-07）', () => {
    it('本地任务终态：显示 success/skipped/failed 三类计数', () => {
      const result = buildResult({ successDays: 2, failedDays: 1 })
      setTaskStatus({ task: buildCompletedTask(result) })
      render(<MarketMetricsSyncPanel />)
      expect(screen.getByTestId('market-metrics-sync-success-count')).toHaveTextContent('2')
      expect(screen.getByTestId('market-metrics-sync-skipped-count')).toHaveTextContent('8')
      expect(screen.getByTestId('market-metrics-sync-failed-count')).toHaveTextContent('1')
    })

    it('点击失败日期行展开四类计数与原因（AC-07）', () => {
      const result = buildResult({ successDays: 1, failedDays: 1 })
      setTaskStatus({ task: buildCompletedTask(result) })
      render(<MarketMetricsSyncPanel />)
      const failedDate = result.dateResults.find((d) => d.status === 'failed')!.tradeDate
      const row = screen.getByTestId(`market-metrics-sync-date-result-${failedDate}`)
      // 列表可见
      expect(screen.getByTestId('market-metrics-sync-date-result-list')).toBeInTheDocument()
      // 点击展开
      fireEvent.click(row)
      expect(row).toHaveTextContent(String(result.dateResults[1].expected))
      expect(row).toHaveTextContent(String(result.dateResults[1].daily))
      expect(row).toHaveTextContent(String(result.dateResults[1].suspended))
      expect(row).toHaveTextContent(String(result.dateResults[1].final))
      expect(row).toHaveTextContent(/完整性校验失败/)
    })

    it('unprocessedDates 非空：独立提示块可见且含日期', () => {
      const result = buildResult({ successDays: 1, failedDays: 0, unprocessedDates: ['2026-08-10'] })
      setTaskStatus({ task: buildCompletedTask(result) })
      render(<MarketMetricsSyncPanel />)
      const hint = screen.getByTestId('market-metrics-sync-unprocessed-dates')
      expect(hint).toBeInTheDocument()
      expect(hint).toHaveTextContent('2026-08-10')
    })
  })

  describe('本地任务 running 时隐藏历史结果区（S-1）', () => {
    it('本地任务 running：不显示历史三类计数与 dateResults，改为进行中占位', () => {
      const historyResult = buildResult({ successDays: 1, failedDays: 1 })
      // 历史记录含一条 completed result（若无 S-1 修复会被回退显示）
      setSwr({
        data: {
          tasks: [
            {
              taskId: 'task-mm-history',
              taskType: 'sync_market_metrics',
              status: 'completed',
              progress: 10,
              total: 10,
              createdAt: '2026-08-12T10:00:00.000Z',
              result: historyResult,
              params: { start_date: '2026-07-15', end_date: '2026-08-13' },
            },
          ],
          total: 1,
          page: 1,
        },
      })
      // 本地任务 running（未终态，无 result）
      setTaskStatus({ task: buildRunningTask() })
      render(<MarketMetricsSyncPanel />)

      // 终态三类计数不渲染
      expect(screen.queryByTestId('market-metrics-sync-success-count')).toBeNull()
      expect(screen.queryByTestId('market-metrics-sync-skipped-count')).toBeNull()
      expect(screen.queryByTestId('market-metrics-sync-failed-count')).toBeNull()
      // 历史日期结果列表不渲染
      expect(screen.queryByTestId('market-metrics-sync-date-result-list')).toBeNull()
      // 进行中占位可见
      const pending = screen.getByTestId('market-metrics-result-pending')
      expect(pending).toBeInTheDocument()
      expect(pending).toHaveTextContent(/同步进行中/)
      // 历史记录列表区照常显示
      expect(screen.getByTestId('market-metrics-sync-records')).toBeInTheDocument()
    })

    it('本地任务转入终态后恢复显示结果区，占位消失', () => {
      const result = buildResult({ successDays: 2, failedDays: 1 })
      // 无历史记录，仅本地任务终态 result
      setTaskStatus({ task: buildCompletedTask(result) })
      render(<MarketMetricsSyncPanel />)

      // 结果区恢复显示
      expect(screen.getByTestId('market-metrics-sync-success-count')).toHaveTextContent('2')
      expect(screen.getByTestId('market-metrics-sync-skipped-count')).toHaveTextContent('8')
      expect(screen.getByTestId('market-metrics-sync-failed-count')).toHaveTextContent('1')
      // 占位消失
      expect(screen.queryByTestId('market-metrics-result-pending')).toBeNull()
    })
  })

  describe('记录表格与分页', () => {
    it('记录列表渲染状态徽章 + 分页下一页（total > page_size）', () => {
      const result = buildResult()
      setSwr({
        data: {
          tasks: [
            {
              taskId: 'task-mm-003',
              taskType: 'sync_market_metrics',
              status: 'completed',
              progress: 10,
              total: 10,
              createdAt: '2026-08-13T10:00:00.000Z',
              result,
              params: { start_date: '2026-07-15', end_date: '2026-08-13' },
            },
            {
              taskId: 'task-mm-002',
              taskType: 'sync_market_metrics',
              status: 'failed',
              progress: 7,
              total: 10,
              createdAt: '2026-08-12T10:00:00.000Z',
              errorMessage: 'Tushare 限流',
              result: null,
              params: { start_date: '2026-07-15', end_date: '2026-08-13' },
            },
            {
              taskId: 'task-mm-001',
              taskType: 'sync_market_metrics',
              status: 'cancelled',
              progress: 3,
              total: 10,
              createdAt: '2026-08-11T10:00:00.000Z',
              result: null,
              params: { start_date: '2026-07-15', end_date: '2026-08-13' },
            },
          ],
          total: 25,
          page: 1,
        },
      })
      render(<MarketMetricsSyncPanel />)
      const records = screen.getByTestId('market-metrics-sync-records')
      expect(records).toBeInTheDocument()
      // 五态中三态可见
      expect(records).toHaveTextContent('已完成')
      expect(records).toHaveTextContent('失败')
      expect(records).toHaveTextContent('已取消')
      // 分页下一页可见（total=25 > 20）
      expect(screen.getByTestId('market-metrics-sync-records-next-page')).toBeInTheDocument()
    })

    it('空记录列表：显示空态文案', () => {
      setSwr({ data: { tasks: [], total: 0, page: 1 } })
      render(<MarketMetricsSyncPanel />)
      expect(screen.getByText(/暂无同步记录/)).toBeInTheDocument()
    })
  })
})
