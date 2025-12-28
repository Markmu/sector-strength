/**
 * useTaskStatus Hook
 *
 * 用于轮询和跟踪异步任务状态的Hook。
 */

import { useEffect, useState, useCallback, useRef } from 'react'
import { tasksApi } from '@/lib/api'

// 任务状态类型
export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'

// 任务数据类型
export interface TaskData {
  taskId: string
  taskType: string
  status: TaskStatus
  progress: number
  total: number
  percent: number
  params?: Record<string, any>
  errorMessage?: string
  retryCount: number
  maxRetries: number
  createdAt: string
  startedAt?: string
  completedAt?: string
}

// Hook 选项
interface UseTaskStatusOptions {
  // 是否启用轮询
  enabled?: boolean
  // 轮询间隔（毫秒）
  pollInterval?: number
  // 任务完成后的回调
  onComplete?: (task: TaskData) => void
  // 任务失败后的回调
  onFailed?: (task: TaskData) => void
  // 任务取消后的回调
  onCancelled?: (task: TaskData) => void
  // 进度更新回调
  onProgress?: (task: TaskData) => void
}

// Hook 返回值
interface UseTaskStatusResult {
  task: TaskData | null
  isLoading: boolean
  isError: boolean
  error: unknown
  isPolling: boolean
  refetch: () => Promise<void>
  cancel: () => Promise<void>
}

const DEFAULT_POLL_INTERVAL = 2000 // 2秒

/**
 * 轮询任务状态的Hook
 *
 * @param taskId - 任务ID，如果为null则不进行轮询
 * @param options - Hook选项
 */
export function useTaskStatus(
  taskId: string | null,
  options: UseTaskStatusOptions = {}
): UseTaskStatusResult {
  const {
    enabled = true,
    pollInterval = DEFAULT_POLL_INTERVAL,
    onComplete,
    onFailed,
    onCancelled,
    onProgress,
  } = options

  const [task, setTask] = useState<TaskData | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isError, setIsError] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const [isPolling, setIsPolling] = useState(false)

  // 使用ref来存储回调，避免在依赖变化时重新设置定时器
  const onCompleteRef = useRef(onComplete)
  const onFailedRef = useRef(onFailed)
  const onCancelledRef = useRef(onCancelled)
  const onProgressRef = useRef(onProgress)

  // 更新回调ref
  useEffect(() => {
    onCompleteRef.current = onComplete
    onFailedRef.current = onFailed
    onCancelledRef.current = onCancelled
    onProgressRef.current = onProgress
  }, [onComplete, onFailed, onCancelled, onProgress])

  // 获取任务状态
  const fetchTaskStatus = useCallback(async () => {
    if (!taskId || !enabled) {
      return
    }

    setIsLoading(true)
    setIsError(false)
    setError(null)

    try {
      const response = await tasksApi.getTask(taskId)
      const taskData = response.data as TaskData

      setTask(taskData)

      // 根据状态触发回调
      if (taskData.status === 'completed') {
        setIsPolling(false)
        if (onCompleteRef.current) {
          onCompleteRef.current(taskData)
        }
      } else if (taskData.status === 'failed') {
        setIsPolling(false)
        if (onFailedRef.current) {
          onFailedRef.current(taskData)
        }
      } else if (taskData.status === 'cancelled') {
        setIsPolling(false)
        if (onCancelledRef.current) {
          onCancelledRef.current(taskData)
        }
      } else if (taskData.status === 'running') {
        // 任务运行中，触发进度回调
        if (onProgressRef.current) {
          onProgressRef.current(taskData)
        }
      }

      setIsLoading(false)
    } catch (err) {
      setIsError(true)
      setError(err)
      setIsLoading(false)
      setIsPolling(false)
    }
  }, [taskId, enabled])

  // 取消任务
  const cancelTask = useCallback(async () => {
    if (!taskId) {
      return
    }

    try {
      await tasksApi.cancelTask(taskId)
      setIsPolling(false)
      // 重新获取状态以更新UI
      await fetchTaskStatus()
    } catch (err) {
      setIsError(true)
      setError(err)
    }
  }, [taskId, fetchTaskStatus])

  // 设置轮询
  useEffect(() => {
    if (!taskId || !enabled) {
      setIsPolling(false)
      return
    }

    // 立即获取一次状态
    const fetchImmediately = async () => {
      if (!taskId || !enabled) return
      setIsLoading(true)
      setIsError(false)
      setError(null)

      try {
        const response = await tasksApi.getTask(taskId)
        const taskData = response.data as TaskData

        setTask(taskData)

        // 根据状态触发回调
        if (taskData.status === 'completed') {
          setIsPolling(false)
          if (onCompleteRef.current) {
            onCompleteRef.current(taskData)
          }
        } else if (taskData.status === 'failed') {
          setIsPolling(false)
          if (onFailedRef.current) {
            onFailedRef.current(taskData)
          }
        } else if (taskData.status === 'cancelled') {
          setIsPolling(false)
          if (onCancelledRef.current) {
            onCancelledRef.current(taskData)
          }
        } else if (taskData.status === 'running') {
          // 任务运行中，触发进度回调
          if (onProgressRef.current) {
            onProgressRef.current(taskData)
          }
        }

        setIsLoading(false)
      } catch (err) {
        setIsError(true)
        setError(err)
        setIsLoading(false)
        setIsPolling(false)
      }
    }

    fetchImmediately()

    // 设置定时轮询
    const intervalId = setInterval(async () => {
      if (!taskId || !enabled) return

      try {
        const response = await tasksApi.getTask(taskId)
        const taskData = response.data as TaskData

        setTask(taskData)

        // 根据状态触发回调
        if (taskData.status === 'completed') {
          setIsPolling(false)
          clearInterval(intervalId)
          if (onCompleteRef.current) {
            onCompleteRef.current(taskData)
          }
        } else if (taskData.status === 'failed') {
          setIsPolling(false)
          clearInterval(intervalId)
          if (onFailedRef.current) {
            onFailedRef.current(taskData)
          }
        } else if (taskData.status === 'cancelled') {
          setIsPolling(false)
          clearInterval(intervalId)
          if (onCancelledRef.current) {
            onCancelledRef.current(taskData)
          }
        } else if (taskData.status === 'running') {
          if (onProgressRef.current) {
            onProgressRef.current(taskData)
          }
        }
      } catch (err) {
        setIsError(true)
        setError(err)
        setIsPolling(false)
        clearInterval(intervalId)
      }
    }, pollInterval)

    setIsPolling(true)

    // 清理函数
    return () => {
      clearInterval(intervalId)
      setIsPolling(false)
    }
  }, [taskId, enabled, pollInterval])

  return {
    task,
    isLoading,
    isError,
    error,
    isPolling,
    refetch: fetchTaskStatus,
    cancel: cancelTask,
  }
}

/**
 * 批量跟踪多个任务状态的Hook
 *
 * @param taskIds - 任务ID数组
 * @param options - Hook选项
 */
export function useMultipleTaskStatus(
  taskIds: string[],
  options: UseTaskStatusOptions = {}
) {
  const [tasks, setTasks] = useState<Record<string, TaskData>>({})
  const [isLoading, setIsLoading] = useState(false)
  const [isError, setIsError] = useState(false)

  const fetchAllTasks = useCallback(async () => {
    if (taskIds.length === 0) {
      return
    }

    setIsLoading(true)
    setIsError(false)

    try {
      const response = await tasksApi.listTasks()
      const allTasks = response.data?.tasks || []

      // 筛选出我们关心的任务
      const filteredTasks = allTasks.filter((t) =>
        taskIds.includes(t.taskId)
      )

      const tasksMap: Record<string, TaskData> = {}
      filteredTasks.forEach((t) => {
        tasksMap[t.taskId] = t as TaskData
      })

      setTasks(tasksMap)
      setIsLoading(false)
    } catch (err) {
      setIsError(true)
      setIsLoading(false)
    }
  }, [taskIds])

  useEffect(() => {
    fetchAllTasks()
  }, [fetchAllTasks])

  return {
    tasks,
    isLoading,
    isError,
    refetch: fetchAllTasks,
  }
}

export default useTaskStatus
