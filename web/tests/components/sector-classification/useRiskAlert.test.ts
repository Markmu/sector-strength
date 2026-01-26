import { renderHook, act } from '@testing-library/react'
import { useRiskAlert } from '@/components/sector-classification/useRiskAlert'

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString()
    },
    clear: () => {
      store = {}
    },
  }
})()

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
})

describe('useRiskAlert', () => {
  beforeEach(() => {
    localStorage.clear()
    jest.clearAllMocks()
  })

  it('首次访问应该显示弹窗', () => {
    const { result } = renderHook(() => useRiskAlert())

    expect(result.current.open).toBe(true)
    expect(result.current.hasAcknowledged).toBe(false)
  })

  it('已确认后不应该显示弹窗', () => {
    // 设置已确认状态
    localStorage.setItem('riskAlertAcknowledged', 'true')

    const { result } = renderHook(() => useRiskAlert())

    expect(result.current.open).toBe(false)
    expect(result.current.hasAcknowledged).toBe(true)
  })

  it('确认后应该保存到 localStorage 并关闭弹窗', () => {
    const { result } = renderHook(() => useRiskAlert())

    expect(result.current.open).toBe(true)

    act(() => {
      result.current.handleConfirm()
    })

    expect(result.current.open).toBe(false)
    expect(result.current.hasAcknowledged).toBe(true)
    expect(localStorage.getItem('riskAlertAcknowledged')).toBe('true')
  })

  it('应该允许手动关闭弹窗', () => {
    const { result } = renderHook(() => useRiskAlert())

    act(() => {
      result.current.setOpen(false)
    })

    expect(result.current.open).toBe(false)
  })
})
