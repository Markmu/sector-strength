import useSWR from 'swr'
import { fetcher } from '@/lib/fetcher'

interface MissingRange {
  start: string
  end: string
}

interface ActiveTask {
  task_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  total: number
  error_message: string | null
}

export interface DataTypeStatus {
  type: 'history' | 'ma' | 'strength'
  label: string
  latest_date: string | null
  status: 'normal' | 'missing' | 'no_data'
  missing_range: MissingRange | null
  active_task: ActiveTask | null
}

/**
 * 检查是否有活跃任务（pending 或 running）
 *
 * fetcher 自动 unwrap { success, data: {...} } 后得到 { items: [...] }，
 * hasActiveTask 接收已提取的 items 数组。
 */
function hasActiveTask(data: DataTypeStatus[] | undefined): boolean {
  if (!data || !Array.isArray(data)) return false
  return data.some(
    (item) => item.active_task?.status === 'pending' || item.active_task?.status === 'running'
  )
}

/**
 * SWR hook：获取数据状态
 *
 * - 请求 GET /api/v1/admin/data/status
 * - 后端经 ApiResponse 包装返回 { success, data: { items: [...] } }
 * - fetcher 解包 result.data 得到 { items: [...] }
 * - 此处从 SWR data 中提取 items 字段，适配为 DataTypeStatus[] 数组
 * - 当存在活跃任务（pending/running）时，每 2 秒自动刷新（ADR-4）
 * - 返回 { data, isLoading, error, mutate }
 */
export function useDataStatus() {
  const { data, isLoading, error, mutate } = useSWR<{ items: DataTypeStatus[] }>(
    '/api/v1/admin/data/status',
    fetcher,
    {
      refreshInterval: (latestData) => (hasActiveTask(latestData?.items) ? 2000 : 0),
      revalidateOnFocus: true,
    }
  )

  const items = data?.items ?? []

  return {
    data: items,
    isLoading,
    error,
    mutate,
  }
}
