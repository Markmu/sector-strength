/**
 * LimitSyncPanel 组件测试（数据管理「涨停专题」Tab）
 *
 * 覆盖：默认渲染 / 前端校验（不成对 / 倒置 / 未来 / 超 10 年）/
 * 最新数据日期展示与默认预填（最新+1 天 ~ 今天，手动修改不被覆盖，无数据不预填）/
 * 开始日期允许往前选重跑历史 / 数据已到今天（增量范围为空）提示 / 创建调用（latest 无参 / range 成对位置参数）/
 * 后端拒绝展示 message / 互斥禁用 / running 进度口径（范围=交易日，单日=步）/
 * 终态横幅（完成 / 失败原因） / 记录表格（徽章 + 范围文案 + 分页 + 空态）。
 *
 * Mock 策略（参照 MarginSyncPanel.test.tsx 范式）：
 * - swr → 按 key 分发：/api/v1/admin/tasks=记录列表，limit-sync-latest-date=最新日期
 * - @/hooks/useTaskStatus → 控制 task/cancel
 * - @/lib/api → 控制 adminApi.initLimit / limitApi.getLatestDate
 * - @/contexts/AuthContext → 控制 isAdmin
 * - @/hooks/useRequireAdmin → no-op（避免 router）
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import LimitSyncPanel from '@/components/limit/LimitSyncPanel'

// ---- Mock adminApi / limitApi（可按用例覆写返回） ----
const mockInitLimit = jest.fn()
const mockGetLatestDate = jest.fn()
jest.mock('@/lib/api', () => ({
  __esModule: true,
  adminApi: { initLimit: (...args: unknown[]) => mockInitLimit(...args) },
  limitApi: { getLatestDate: (...args: unknown[]) => mockGetLatestDate(...args) },
}))

// ---- Mock useTaskStatus：返回受控 task / cancel ----
const mockCancel = jest.fn()
let mockTaskStatusValue: {
  task: TaskData<LimitTaskResult> | null
  cancel: jest.Mock
} = { task: null, cancel: mockCancel }
jest.mock('@/hooks/useTaskStatus', () => ({
  __esModule: true,
  useTaskStatus: jest.fn(() => mockTaskStatusValue),
}))

// ---- Mock useSWR：按 key 分发记录列表与最新数据日期 ----
const mockRefreshRecords = jest.fn()
const mockRefreshLatest = jest.fn()
let mockRecordsSwr: {
  data?: { tasks: unknown[]; total: number; page: number }
  isLoading: boolean
  mutate: jest.Mock
}
let mockLatestSwr: {
  data?: { hasData: boolean; tradeDate: string | null }
  isLoading: boolean
  mutate: jest.Mock
}
jest.mock('swr', () => ({
  __esModule: true,
  default: jest.fn((key: unknown) =>
    String(key).startsWith('/api/v1/admin/tasks') ? mockRecordsSwr : mockLatestSwr
  ),
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

import type { TaskData, TaskStatus } from '@/hooks/useTaskStatus'

/** sync_limit_data 无结构化 result（handler 仅日志） */
type LimitTaskResult = Record<string, unknown> | null

/** 与组件 formatLocalDate 同口径（本地时区 YYYY-MM-DD） */
function toLocalISODate(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

/** ISO 日期加 N 天（与组件 addDaysISO 同口径） */
function addDaysISO(iso: string, days: number): string {
  const d = new Date(`${iso}T00:00:00`)
  d.setDate(d.getDate() + days)
  return toLocalISODate(d)
}

/** 构造 TaskData（status/params/errorMessage 可覆写） */
function buildTask(
  status: TaskStatus,
  overrides?: Partial<TaskData<LimitTaskResult>>
): TaskData<LimitTaskResult> {
  return {
    taskId: 'task-limit-sync-001',
    taskType: 'sync_limit_data',
    status,
    progress: 1,
    total: 3,
    percent: 33,
    params: {},
    errorMessage: undefined,
    retryCount: 0,
    maxRetries: 3,
    createdAt: '2026-08-15T10:00:00.000Z',
    startedAt: '2026-08-15T10:00:00.000Z',
    completedAt: undefined,
    result: null,
    ...overrides,
  }
}

function setRecordsSwr(value: Partial<typeof mockRecordsSwr>) {
  mockRecordsSwr = { ...mockRecordsSwr, ...value }
}

/** 设置最新数据日期（null = 暂无数据） */
function setLatestDate(tradeDate: string | null) {
  mockLatestSwr = {
    ...mockLatestSwr,
    data: { hasData: tradeDate !== null, tradeDate },
  }
}

function setTaskStatus(value: Partial<typeof mockTaskStatusValue>) {
  mockTaskStatusValue = { ...mockTaskStatusValue, ...value }
}

function fillRange(start: string, end: string) {
  fireEvent.change(screen.getByLabelText('开始日期'), { target: { value: start } })
  fireEvent.change(screen.getByLabelText('结束日期'), { target: { value: end } })
}

describe('LimitSyncPanel', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    mockIsAdmin = true
    mockInitLimit.mockReset()
    mockGetLatestDate.mockReset()
    mockRecordsSwr = { data: undefined, isLoading: false, mutate: mockRefreshRecords }
    // 默认「暂无数据」：既有用例手动填日期，不触发预填与增量起点约束
    mockLatestSwr = {
      data: { hasData: false, tradeDate: null },
      isLoading: false,
      mutate: mockRefreshLatest,
    }
    mockTaskStatusValue = { task: null, cancel: mockCancel }
  })

  describe('默认渲染与前端校验', () => {
    it('渲染面板根；无历史数据时日期留空、「按范围同步」禁用', () => {
      render(<LimitSyncPanel />)
      expect(screen.getByTestId('limit-sync-panel')).toBeInTheDocument()
      expect(screen.getByLabelText('开始日期')).toHaveValue('')
      expect(screen.getByLabelText('结束日期')).toHaveValue('')
      expect(screen.getByTestId('limit-sync-latest-date')).toHaveTextContent('暂无历史数据')
      expect(screen.getByTestId('limit-sync-latest-button')).not.toBeDisabled()
      expect(screen.getByTestId('limit-sync-start-button')).toBeDisabled()
      expect(screen.queryByTestId('limit-sync-validation-error')).toBeNull()
      expect(screen.queryByTestId('limit-sync-mutex-hint')).toBeNull()
    })

    it('起止不成对：「按范围同步」禁用 + 提示（镜像后端 400 拒绝口径）', () => {
      render(<LimitSyncPanel />)
      fireEvent.change(screen.getByLabelText('开始日期'), { target: { value: '2026-08-01' } })
      expect(screen.getByTestId('limit-sync-start-button')).toBeDisabled()
      expect(screen.getByTestId('limit-sync-validation-error')).toHaveTextContent(
        /同时选择起止日期/
      )
      // 范围校验不影响「同步最新交易日」
      expect(screen.getByTestId('limit-sync-latest-button')).not.toBeDisabled()
    })

    it('起止倒置 / 未来 / 超 10 年：「按范围同步」禁用 + 各自错误提示', () => {
      render(<LimitSyncPanel />)
      fillRange('2026-08-10', '2026-08-01')
      expect(screen.getByTestId('limit-sync-start-button')).toBeDisabled()
      expect(screen.getByTestId('limit-sync-validation-error')).toHaveTextContent(/不能晚于/)

      fillRange('2026-08-01', '2099-12-31')
      expect(screen.getByTestId('limit-sync-start-button')).toBeDisabled()
      expect(screen.getByTestId('limit-sync-validation-error')).toHaveTextContent(/不能晚于今天/)

      fillRange('2000-01-01', '2026-08-13')
      expect(screen.getByTestId('limit-sync-start-button')).toBeDisabled()
      expect(screen.getByTestId('limit-sync-validation-error')).toHaveTextContent(/10 年/)
    })
  })

  describe('最新数据日期展示与默认预填', () => {
    it('展示最新数据日期；起止默认预填「最新+1 天 ~ 今天」，范围按钮可用', async () => {
      setLatestDate('2026-08-13')
      render(<LimitSyncPanel />)

      const latestRow = screen.getByTestId('limit-sync-latest-date')
      expect(latestRow).toHaveTextContent('当前最新数据日期')
      expect(latestRow).toHaveTextContent('2026-08-13')

      // 预填经 useEffect 应用，waitFor 至生效
      await waitFor(() => {
        expect(screen.getByLabelText('开始日期')).toHaveValue('2026-08-14')
      })
      expect(screen.getByLabelText('结束日期')).toHaveValue(toLocalISODate(new Date()))
      expect(screen.getByTestId('limit-sync-start-button')).not.toBeDisabled()
      expect(screen.queryByTestId('limit-sync-validation-error')).toBeNull()
    })

    it('开始日期允许往前选（重跑历史）：不受最新数据下一天限制', async () => {
      setLatestDate('2026-08-13')
      render(<LimitSyncPanel />)
      await waitFor(() => {
        expect(screen.getByLabelText('开始日期')).toHaveValue('2026-08-14')
      })

      // 往前选到早于最新数据日期：合法范围即可用，无增量起点报错
      fireEvent.change(screen.getByLabelText('开始日期'), { target: { value: '2026-08-01' } })
      expect(screen.queryByTestId('limit-sync-validation-error')).toBeNull()
      expect(screen.getByTestId('limit-sync-start-button')).not.toBeDisabled()
    })

    it('最新数据已到今天：提示今日无增量范围，往前选开始日期后恢复可用', async () => {
      const today = toLocalISODate(new Date())
      setLatestDate(today)
      render(<LimitSyncPanel />)

      await waitFor(() => {
        expect(screen.getByLabelText('开始日期')).toHaveValue(addDaysISO(today, 1))
      })
      expect(screen.getByLabelText('结束日期')).toHaveValue(today)
      expect(screen.getByTestId('limit-sync-start-button')).toBeDisabled()
      expect(screen.getByTestId('limit-sync-validation-error')).toHaveTextContent(
        /数据已同步至/
      )
      // 一键同步最新交易日不受影响
      expect(screen.getByTestId('limit-sync-latest-button')).not.toBeDisabled()

      // 开始日期往前选到今天：范围合法，按钮恢复可用（重跑历史）
      fireEvent.change(screen.getByLabelText('开始日期'), { target: { value: today } })
      expect(screen.queryByTestId('limit-sync-validation-error')).toBeNull()
      expect(screen.getByTestId('limit-sync-start-button')).not.toBeDisabled()
    })

    it('用户手动修改日期后，预填不再覆盖手动选择', async () => {
      setLatestDate('2026-08-13')
      render(<LimitSyncPanel />)
      await waitFor(() => {
        expect(screen.getByLabelText('开始日期')).toHaveValue('2026-08-14')
      })

      // 手动清空开始日期 → 出现不成对提示（而非被重新预填）
      fireEvent.change(screen.getByLabelText('开始日期'), { target: { value: '' } })
      expect(screen.getByLabelText('开始日期')).toHaveValue('')
      expect(screen.getByTestId('limit-sync-validation-error')).toHaveTextContent(
        /同时选择起止日期/
      )
    })
  })

  describe('创建调用与互斥', () => {
    it('点击「同步最新交易日」：initLimit 无参调用（后端回退最新交易日）', async () => {
      mockInitLimit.mockResolvedValue({ data: { task_id: 'task-latest' } })
      render(<LimitSyncPanel />)
      fireEvent.click(screen.getByTestId('limit-sync-latest-button'))
      await waitFor(() => {
        expect(mockInitLimit).toHaveBeenCalledWith()
      })
    })

    it('点击「按范围同步」：initLimit 成对位置参数（body snake_case 由 api.ts 保证）', async () => {
      mockInitLimit.mockResolvedValue({ data: { task_id: 'task-range' } })
      render(<LimitSyncPanel />)
      fillRange('2026-07-15', '2026-08-13')
      expect(screen.getByTestId('limit-sync-start-button')).not.toBeDisabled()
      fireEvent.click(screen.getByTestId('limit-sync-start-button'))
      await waitFor(() => {
        expect(mockInitLimit).toHaveBeenCalledWith('2026-07-15', '2026-08-13')
      })
    })

    it('预填后直接点击「按范围同步」：以预填的增量范围调用', async () => {
      mockInitLimit.mockResolvedValue({ data: { task_id: 'task-range' } })
      setLatestDate('2026-08-13')
      render(<LimitSyncPanel />)
      await waitFor(() => {
        expect(screen.getByTestId('limit-sync-start-button')).not.toBeDisabled()
      })
      fireEvent.click(screen.getByTestId('limit-sync-start-button'))
      await waitFor(() => {
        expect(mockInitLimit).toHaveBeenCalledWith('2026-08-14', toLocalISODate(new Date()))
      })
    })

    it('后端互斥拒绝（success=false 抛错）：展示返回 message', async () => {
      const mutexMsg = '已有涨停专题同步任务正在运行，请等待当前任务完成'
      mockInitLimit.mockRejectedValue(new Error(mutexMsg))
      render(<LimitSyncPanel />)
      fireEvent.click(screen.getByTestId('limit-sync-latest-button'))
      await waitFor(() => {
        expect(screen.getByTestId('limit-sync-validation-error')).toHaveTextContent(mutexMsg)
      })
    })

    it('记录列表含运行中任务：两按钮均禁用 + 互斥提示', () => {
      setRecordsSwr({
        data: {
          tasks: [
            {
              taskId: 'task-running',
              taskType: 'sync_limit_data',
              status: 'running',
              progress: 1,
              total: 3,
              createdAt: '2026-08-15T10:00:00.000Z',
              result: null,
              params: {},
            },
          ],
          total: 1,
          page: 1,
        },
      })
      render(<LimitSyncPanel />)
      expect(screen.getByTestId('limit-sync-latest-button')).toBeDisabled()
      expect(screen.getByTestId('limit-sync-start-button')).toBeDisabled()
      expect(screen.getByTestId('limit-sync-mutex-hint')).toBeInTheDocument()
    })
  })

  describe('running 进度与终态横幅', () => {
    it('范围任务 running：进度按交易日口径展示', () => {
      setTaskStatus({
        task: buildTask('running', {
          progress: 3,
          total: 10,
          percent: 30,
          params: { start_date: '2026-07-15', end_date: '2026-08-13' },
        }),
      })
      render(<LimitSyncPanel />)
      const progress = screen.getByTestId('limit-sync-progress')
      expect(progress).toHaveTextContent('3 / 10 交易日')
      expect(progress).toHaveTextContent('30%')
      // 无结构化 result：终态横幅不渲染
      expect(screen.queryByTestId('limit-sync-terminal-completed')).toBeNull()
    })

    it('单日任务 running：进度按三表步骤口径展示', () => {
      setTaskStatus({ task: buildTask('running', { progress: 2, total: 3, percent: 67 }) })
      render(<LimitSyncPanel />)
      expect(screen.getByTestId('limit-sync-progress')).toHaveTextContent('2 / 3 步')
    })

    it('本地任务失败终态：横幅展示失败原因', () => {
      setTaskStatus({
        task: buildTask('failed', {
          errorMessage: 'Limit data sync failed: Tushare 限流',
        }),
      })
      render(<LimitSyncPanel />)
      expect(screen.getByTestId('limit-sync-terminal-failed')).toBeInTheDocument()
      expect(screen.getByTestId('limit-sync-terminal-failed')).toHaveTextContent('同步失败')
      expect(screen.getByTestId('limit-sync-terminal-error')).toHaveTextContent(
        'Limit data sync failed: Tushare 限流'
      )
    })

    it('本地任务完成终态：横幅展示同步完成', () => {
      setTaskStatus({ task: buildTask('completed', { progress: 3, total: 3, percent: 100 }) })
      render(<LimitSyncPanel />)
      expect(screen.getByTestId('limit-sync-terminal-completed')).toBeInTheDocument()
      expect(screen.getByTestId('limit-sync-terminal-completed')).toHaveTextContent('同步完成')
      expect(screen.queryByTestId('limit-sync-terminal-error')).toBeNull()
    })
  })

  describe('记录表格与分页', () => {
    it('记录列表渲染状态徽章 + 最新交易日范围文案 + 分页', () => {
      setRecordsSwr({
        data: {
          tasks: [
            {
              taskId: 'task-limit-003',
              taskType: 'sync_limit_data',
              status: 'completed',
              progress: 3,
              total: 3,
              createdAt: '2026-08-15T10:00:00.000Z',
              result: null,
              params: {},
            },
            {
              taskId: 'task-limit-002',
              taskType: 'sync_limit_data',
              status: 'failed',
              progress: 1,
              total: 3,
              createdAt: '2026-08-14T10:00:00.000Z',
              errorMessage: 'Tushare 限流',
              result: null,
              params: {},
            },
            {
              taskId: 'task-limit-001',
              taskType: 'sync_limit_data',
              status: 'completed',
              progress: 20,
              total: 20,
              createdAt: '2026-08-13T10:00:00.000Z',
              result: null,
              params: { start_date: '2026-07-15', end_date: '2026-08-13' },
            },
          ],
          total: 25,
          page: 1,
        },
      })
      render(<LimitSyncPanel />)
      const records = screen.getByTestId('limit-sync-records')
      expect(records).toBeInTheDocument()
      expect(records).toHaveTextContent('已完成')
      expect(records).toHaveTextContent('失败')
      // 无参数任务范围列显示「最新交易日」，范围任务显示起止
      expect(records).toHaveTextContent('最新交易日')
      expect(records).toHaveTextContent('2026-07-15 ~ 2026-08-13')
      // 分页下一页可见（total=25 > 20）
      expect(screen.getByTestId('limit-sync-records-next-page')).toBeInTheDocument()
    })

    it('空记录列表：显示空态文案', () => {
      setRecordsSwr({ data: { tasks: [], total: 0, page: 1 } })
      render(<LimitSyncPanel />)
      expect(screen.getByText(/暂无同步记录/)).toBeInTheDocument()
    })
  })

  describe('非管理员', () => {
    it('无权限：渲染权限提示，不渲染面板主体', () => {
      mockIsAdmin = false
      render(<LimitSyncPanel />)
      expect(screen.getByText(/没有权限/)).toBeInTheDocument()
      expect(screen.queryByTestId('limit-sync-panel')).toBeNull()
    })
  })
})
