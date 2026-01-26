/**
 * useDataFix Hook 测试
 *
 * Story 4.5: Task 7.3
 * 测试数据修复 Hook 的功能
 */

import { renderHook, act, waitFor } from '@testing-library/react'
import { useDataFix } from '@/components/admin/sector-classification/useDataFix'
import { adminApiClient } from '@/lib/api'
import type { DataFixRequest } from '@/types/data-fix'
import { DataFixStatus as FixStatus } from '@/types/data-fix'

// Mock adminApiClient
jest.mock('@/lib/api', () => ({
  adminApiClient: {
    post: jest.fn(),
  },
}))

describe('useDataFix', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('初始状态测试', () => {
    it('应该返回初始状态', () => {
      const { result } = renderHook(() => useDataFix())

      expect(result.current.status).toBe(FixStatus.IDLE)
      expect(result.current.result).toBeNull()
      expect(result.current.error).toBeNull()
      expect(result.current.isFixing).toBe(false)
    })

    it('应该提供 fix 和 reset 函数', () => {
      const { result } = renderHook(() => useDataFix())

      expect(typeof result.current.fix).toBe('function')
      expect(typeof result.current.reset).toBe('function')
    })
  })

  describe('修复功能测试', () => {
    it('应该成功修复数据', async () => {
      const mockResponse = {
        data: {
          success_count: 1,
          failed_count: 0,
          duration_seconds: 1.5,
          sectors: [
            {
              sector_id: '1',
              sector_name: '新能源',
              success: true,
            }
          ]
        }
      }

      ;(adminApiClient.post as jest.Mock).mockResolvedValue(mockResponse)

      const { result } = renderHook(() => useDataFix())

      const request: DataFixRequest = {
        sector_id: '1',
        days: 30,
        overwrite: false,
      }

      await act(async () => {
        await result.current.fix(request)
      })

      await waitFor(() => {
        expect(result.current.status).toBe(FixStatus.SUCCESS)
        expect(result.current.result).toEqual(mockResponse.data)
        expect(result.current.error).toBeNull()
      })
    })

    it('修复过程中 isFixing 应该为 true', async () => {
      let resolvePromise: any
      ;(adminApiClient.post as jest.Mock).mockImplementation(
        () =>
          new Promise((resolve) => {
            resolvePromise = resolve
          })
      )

      const { result } = renderHook(() => useDataFix())

      const request: DataFixRequest = {
        sector_id: '1',
        days: 30,
        overwrite: false,
      }

      act(() => {
        result.current.fix(request)
      })

      // 立即检查 - 应该在修复中
      expect(result.current.isFixing).toBe(true)

      // 完成请求
      await act(async () => {
        resolvePromise({ data: { success_count: 1, failed_count: 0, duration_seconds: 1, sectors: [] } })
      })
    })

    it('应该处理 API 错误', async () => {
      const mockError = new Error('网络错误')
      ;(adminApiClient.post as jest.Mock).mockRejectedValue(mockError)

      const { result } = renderHook(() => useDataFix())

      const request: DataFixRequest = {
        sector_id: '1',
        days: 30,
        overwrite: false,
      }

      await act(async () => {
        await result.current.fix(request)
      })

      await waitFor(() => {
        expect(result.current.status).toBe(FixStatus.ERROR)
        expect(result.current.error).toBe('网络错误')
        expect(result.current.result).toBeNull()
      })
    })
  })

  describe('参数验证测试', () => {
    it('不提供板块 ID 或名称应该失败', async () => {
      const { result } = renderHook(() => useDataFix())

      const request: DataFixRequest = {
        days: 30,
        overwrite: false,
      }

      await act(async () => {
        await result.current.fix(request)
      })

      await waitFor(() => {
        expect(result.current.status).toBe(FixStatus.ERROR)
        expect(result.current.error).toBe('请提供板块 ID 或板块名称')
      })
    })

    it('同时提供板块 ID 和名称应该失败', async () => {
      const { result } = renderHook(() => useDataFix())

      const request: DataFixRequest = {
        sector_id: '1',
        sector_name: '新能源',
        days: 30,
        overwrite: false,
      }

      await act(async () => {
        await result.current.fix(request)
      })

      await waitFor(() => {
        expect(result.current.status).toBe(FixStatus.ERROR)
        expect(result.current.error).toBe('只能提供板块 ID 或板块名称其中之一')
      })
    })

    it('时间范围小于等于 0 应该失败', async () => {
      const { result } = renderHook(() => useDataFix())

      const request: DataFixRequest = {
        sector_id: '1',
        days: 0,
        overwrite: false,
      }

      await act(async () => {
        await result.current.fix(request)
      })

      await waitFor(() => {
        expect(result.current.status).toBe(FixStatus.ERROR)
        expect(result.current.error).toBe('时间范围必须大于 0')
      })
    })
  })

  describe('重置功能测试', () => {
    it('reset 应该重置所有状态', async () => {
      const mockError = new Error('测试错误')
      ;(adminApiClient.post as jest.Mock).mockRejectedValue(mockError)

      const { result } = renderHook(() => useDataFix())

      const request: DataFixRequest = {
        sector_id: '1',
        days: 30,
        overwrite: false,
      }

      // 执行修复并产生错误
      await act(async () => {
        await result.current.fix(request)
      })

      await waitFor(() => {
        expect(result.current.status).toBe(FixStatus.ERROR)
      })

      // 重置状态
      act(() => {
        result.current.reset()
      })

      expect(result.current.status).toBe(FixStatus.IDLE)
      expect(result.current.result).toBeNull()
      expect(result.current.error).toBeNull()
      expect(result.current.isFixing).toBe(false)
    })
  })

  describe('状态转换测试', () => {
    it('应该从 IDLE 转换到 VALIDATING 再到 FIXING', async () => {
      let resolvePromise: any
      ;(adminApiClient.post as jest.Mock).mockImplementation(
        () =>
          new Promise((resolve) => {
            resolvePromise = resolve
          })
      )

      const { result } = renderHook(() => useDataFix())

      const request: DataFixRequest = {
        sector_id: '1',
        days: 30,
        overwrite: false,
      }

      // 开始修复
      act(() => {
        result.current.fix(request)
      })

      // 应该先进入验证状态
      expect(result.current.status).toBe(FixStatus.VALIDATING)

      // 然后进入修复状态
      await waitFor(() => {
        expect(result.current.status).toBe(FixStatus.FIXING)
      })

      // 完成请求
      await act(async () => {
        resolvePromise({ data: { success_count: 1, failed_count: 0, duration_seconds: 1, sectors: [] } })
      })
    })
  })
})
