/**
 * useClassificationTest Hook 测试
 *
 * 测试分类测试状态管理 hook
 */

import { renderHook, act, waitFor } from '@testing-library/react'
import { useClassificationTest } from '@/components/admin/sector-classification/useClassificationTest'
import type { ClassificationTestResult, TestApiResponse } from '@/types/admin-test'

// Mock apiClient
const mockPost = jest.fn()
jest.mock('@/lib/apiClient', () => ({
  apiClient: {
    post: jest.fn(() => mockPost()),
  },
}))

describe('useClassificationTest', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('初始状态', () => {
    it('应该返回正确的初始状态', () => {
      const { result } = renderHook(() => useClassificationTest())

      expect(result.current.testing).toBe(false)
      expect(result.current.testResult).toBeNull()
      expect(result.current.error).toBeNull()
      expect(typeof result.current.runTest).toBe('function')
      expect(typeof result.current.reset).toBe('function')
    })
  })

  describe('runTest 成功场景', () => {
    const successResponse: TestApiResponse = {
      success: true,
      data: {
        total_count: 50,
        success_count: 50,
        failure_count: 0,
        duration_ms: 1234,
        timestamp: '2026-01-26T10:00:00Z',
      },
    }

    it('成功调用时应该设置测试状态', async () => {
      mockPost.mockResolvedValue(successResponse)

      const { result } = renderHook(() => useClassificationTest())

      await act(async () => {
        await result.current.runTest()
      })

      expect(result.current.testing).toBe(false)
      expect(result.current.testResult).toEqual(successResponse.data)
      expect(result.current.error).toBeNull()
    })

    it('测试中应该设置 testing 为 true', async () => {
      mockPost.mockImplementation(
        () =>
          new Promise((resolve) => {
            setTimeout(() => resolve(successResponse), 100)
          })
      )

      const { result } = renderHook(() => useClassificationTest())

      act(() => {
        result.current.runTest()
      })

      expect(result.current.testing).toBe(true)

      await waitFor(() => {
        expect(result.current.testing).toBe(false)
      })
    })

    it('应该包含部分失败的结果', async () => {
      const partialFailureResponse: TestApiResponse = {
        success: true,
        data: {
          total_count: 50,
          success_count: 45,
          failure_count: 5,
          duration_ms: 2345,
          timestamp: '2026-01-26T11:00:00Z',
          failures: [
            { sector_id: '1', sector_name: '测试板块A', error: '数据不足' },
          ],
        },
      }

      mockPost.mockResolvedValue(partialFailureResponse)

      const { result } = renderHook(() => useClassificationTest())

      await act(async () => {
        await result.current.runTest()
      })

      expect(result.current.testResult?.failure_count).toBe(5)
      expect(result.current.testResult?.failures).toHaveLength(1)
    })
  })

  describe('runTest 错误场景', () => {
    it('网络错误应该设置错误状态', async () => {
      const networkError = new Error('网络连接失败')
      mockPost.mockRejectedValue(networkError)

      const { result } = renderHook(() => useClassificationTest())

      await act(async () => {
        await result.current.runTest()
      })

      expect(result.current.testing).toBe(false)
      expect(result.current.testResult).toBeNull()
      expect(result.current.error).toBe('网络连接失败')
    })

    it('字符串错误应该直接设置', async () => {
      mockPost.mockRejectedValue('请求超时')

      const { result } = renderHook(() => useClassificationTest())

      await act(async () => {
        await result.current.runTest()
      })

      expect(result.current.error).toBe('请求超时')
    })

    it('API 返回 success=false 应该显示错误', async () => {
      const errorResponse: TestApiResponse = {
        success: false,
        error: {
          code: 'INTERNAL_ERROR',
          message: '服务器内部错误',
        },
      }

      mockPost.mockResolvedValue(errorResponse)

      const { result } = renderHook(() => useClassificationTest())

      await act(async () => {
        await result.current.runTest()
      })

      expect(result.current.error).toBe('服务器内部错误')
      expect(result.current.testResult).toBeNull()
    })

    it('API 返回 success=false 且无错误信息应该显示默认消息', async () => {
      const errorResponse: TestApiResponse = {
        success: false,
      }

      mockPost.mockResolvedValue(errorResponse)

      const { result } = renderHook(() => useClassificationTest())

      await act(async () => {
        await result.current.runTest()
      })

      expect(result.current.error).toBe('测试失败')
    })
  })

  describe('reset 功能', () => {
    it('reset 应该清除所有状态', async () => {
      mockPost.mockResolvedValue({
        success: true,
        data: {
          total_count: 50,
          success_count: 50,
          failure_count: 0,
          duration_ms: 1234,
          timestamp: '2026-01-26T10:00:00Z',
        },
      })

      const { result } = renderHook(() => useClassificationTest())

      // 先执行一次成功的测试
      await act(async () => {
        await result.current.runTest()
      })

      expect(result.current.testResult).not.toBeNull()

      // 重置
      act(() => {
        result.current.reset()
      })

      expect(result.current.testing).toBe(false)
      expect(result.current.testResult).toBeNull()
      expect(result.current.error).toBeNull()
    })

    it('reset 后可以重新执行测试', async () => {
      mockPost.mockResolvedValue({
        success: true,
        data: {
          total_count: 30,
          success_count: 30,
          failure_count: 0,
          duration_ms: 500,
          timestamp: '2026-01-26T12:00:00Z',
        },
      })

      const { result } = renderHook(() => useClassificationTest())

      // 第一次测试
      await act(async () => {
        await result.current.runTest()
      })

      const firstResult = result.current.testResult

      // 重置
      act(() => {
        result.current.reset()
      })

      // 第二次测试
      await act(async () => {
        await result.current.runTest()
      })

      expect(result.current.testResult).not.toBeNull()
      expect(mockPost).toHaveBeenCalledTimes(2)
    })
  })

  describe('API 调用验证', () => {
    it('应该调用正确的 API 端点', async () => {
      mockPost.mockResolvedValue({
        success: true,
        data: {
          total_count: 0,
          success_count: 0,
          failure_count: 0,
          duration_ms: 0,
          timestamp: '2026-01-26T10:00:00Z',
        },
      })

      const { apiClient } = require('@/lib/apiClient')

      const { result } = renderHook(() => useClassificationTest())

      await act(async () => {
        await result.current.runTest()
      })

      expect(apiClient.post).toHaveBeenCalledWith(
        '/api/v1/admin/sector-classification/test'
      )
    })
  })

  describe('状态转换测试', () => {
    it('错误后重置再测试应该成功', async () => {
      mockPost
        .mockRejectedValueOnce(new Error('第一次失败'))
        .mockResolvedValueOnce({
          success: true,
          data: {
            total_count: 20,
            success_count: 20,
            failure_count: 0,
            duration_ms: 800,
            timestamp: '2026-01-26T10:00:00Z',
          },
        })

      const { result } = renderHook(() => useClassificationTest())

      // 第一次测试失败
      await act(async () => {
        await result.current.runTest()
      })

      expect(result.current.error).toBe('第一次失败')

      // 重置
      act(() => {
        result.current.reset()
      })

      // 第二次测试成功
      await act(async () => {
        await result.current.runTest()
      })

      expect(result.current.error).toBeNull()
      expect(result.current.testResult?.success_count).toBe(20)
    })
  })
})
