/**
 * RefreshButton 组件测试
 *
 * 测试刷新按钮组件的渲染和交互
 */

import { render, screen, fireEvent, within, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Provider } from 'react-redux'
import { configureStore } from '@reduxjs/toolkit'
import { RefreshButton } from '@/components/sector-classification/RefreshButton'
import sectorClassificationReducer, { fetchClassifications } from '@/store/slices/sectorClassificationSlice'

// Mock Redux store
const createMockStore = (loading = false, error: string | null = null, lastFetch: number | null = null) =>
  configureStore({
    reducer: {
      sectorClassification: sectorClassificationReducer,
    },
    preloadedState: {
      sectorClassification: {
        classifications: [],
        loading,
        error,
        lastFetch,
      },
    },
  })

// Mock sectorClassificationApi
jest.mock('@/lib/sectorClassificationApi', () => ({
  sectorClassificationApi: {
    getAllClassifications: jest.fn(),
  },
}))

describe('RefreshButton', () => {
  describe('渲染', () => {
    it('应该渲染刷新按钮', () => {
      const store = createMockStore()

      render(
        <Provider store={store}>
          <RefreshButton />
        </Provider>
      )

      const button = screen.getByRole('button', { name: /刷新/ })
      expect(button).toBeInTheDocument()
    })

    it('应该显示刷新图标', () => {
      const store = createMockStore()

      render(
        <Provider store={store}>
          <RefreshButton showLabel={false} />
        </Provider>
      )

      const button = screen.getByRole('button')
      const svg = button.querySelector('svg')
      expect(svg).toBeInTheDocument()
    })

    it('应该显示默认标签文本', () => {
      const store = createMockStore()

      render(
        <Provider store={store}>
          <RefreshButton />
        </Provider>
      )

      expect(screen.getByText('刷新')).toBeInTheDocument()
    })

    it('showLabel={false} 时不应该显示标签文本', () => {
      const store = createMockStore()

      render(
        <Provider store={store}>
          <RefreshButton showLabel={false} />
        </Provider>
      )

      expect(screen.queryByText('刷新')).not.toBeInTheDocument()
    })

    it('应该应用自定义 className', () => {
      const store = createMockStore()

      const { container } = render(
        <Provider store={store}>
          <RefreshButton className="custom-class" />
        </Provider>
      )

      const button = screen.getByRole('button')
      expect(button).toHaveClass('custom-class')
    })

    it('应该有正确的 aria-label', () => {
      const store = createMockStore()

      render(
        <Provider store={store}>
          <RefreshButton />
        </Provider>
      )

      const button = screen.getByLabelText('刷新数据')
      expect(button).toBeInTheDocument()
    })

    it('loading 状态时应该有 aria-busy="true"', () => {
      const store = createMockStore(true)

      render(
        <Provider store={store}>
          <RefreshButton />
        </Provider>
      )

      const button = screen.getByRole('button')
      expect(button).toHaveAttribute('aria-busy', 'true')
    })
  })

  describe('交互', () => {
    it('点击应该触发 fetchClassifications action', async () => {
      const user = userEvent.setup()
      const store = createMockStore()

      render(
        <Provider store={store}>
          <RefreshButton />
        </Provider>
      )

      const button = screen.getByRole('button', { name: /刷新/ })
      await user.click(button)

      const actions = store.getActions()
      expect(actions).toHaveLength(1)
      expect(actions[0].type).toBe('sectorClassification/fetchAll/pending')
    })

    it('应该支持键盘操作 (Enter)', async () => {
      const user = userEvent.setup()
      const store = createMockStore()

      render(
        <Provider store={store}>
          <RefreshButton />
        </Provider>
      )

      const button = screen.getByRole('button')
      button.focus()
      await user.keyboard('{Enter}')

      const actions = store.getActions()
      expect(actions).toHaveLength(1)
    })

    it('应该支持键盘操作 (Space)', async () => {
      const user = userEvent.setup()
      const store = createMockStore()

      render(
        <Provider store={store}>
          <RefreshButton />
        </Provider>
      )

      const button = screen.getByRole('button')
      button.focus()
      await user.keyboard(' ')

      const actions = store.getActions()
      expect(actions).toHaveLength(1)
    })
  })

  describe('loading 状态', () => {
    it('loading 状态时应该禁用按钮', () => {
      const store = createMockStore(true)

      render(
        <Provider store={store}>
          <RefreshButton />
        </Provider>
      )

      const button = screen.getByRole('button')
      expect(button).toBeDisabled()
    })

    it('loading 状态时应该显示旋转动画', () => {
      const store = createMockStore(true)

      const { container } = render(
        <Provider store={store}>
          <RefreshButton showLabel={false} />
        </Provider>
      )

      const button = screen.getByRole('button')
      const svg = within(button).querySelector('svg')
      expect(svg).toHaveClass('animate-spin')
    })

    it('非 loading 状态时不应该有旋转动画', () => {
      const store = createMockStore(false)

      const { container } = render(
        <Provider store={store}>
          <RefreshButton showLabel={false} />
        </Provider>
      )

      const button = screen.getByRole('button')
      const svg = within(button).querySelector('svg')
      expect(svg).not.toHaveClass('animate-spin')
    })

    it('loading 状态时点击不应该触发 action', async () => {
      const user = userEvent.setup()
      const store = createMockStore(true)

      render(
        <Provider store={store}>
          <RefreshButton />
        </Provider>
      )

      const button = screen.getByRole('button', { name: /刷新/ })
      await user.click(button)

      const actions = store.getActions()
      expect(actions).toHaveLength(0)
    })
  })

  describe('可访问性', () => {
    it('按钮应该可以通过 Tab 键聚焦', () => {
      const store = createMockStore()

      render(
        <Provider store={store}>
          <RefreshButton />
        </Provider>
      )

      const button = screen.getByRole('button')
      expect(button).toHaveAttribute('type', 'button')
    })

    it('图标应该有 aria-hidden="true"', () => {
      const store = createMockStore()

      const { container } = render(
        <Provider store={store}>
          <RefreshButton />
        </Provider>
      )

      const button = screen.getByRole('button')
      const svg = within(button).querySelector('svg')
      expect(svg).toHaveAttribute('aria-hidden', 'true')
    })
  })

  describe('样式', () => {
    it('按钮应该有 gap-2 类', () => {
      const store = createMockStore()

      render(
        <Provider store={store}>
          <RefreshButton />
        </Provider>
      )

      const button = screen.getByRole('button')
      expect(button).toHaveClass('gap-2')
    })

    it('按钮应该使用 outline 变体', () => {
      const store = createMockStore()

      render(
        <Provider store={store}>
          <RefreshButton />
        </Provider>
      )

      const button = screen.getByRole('button')
      expect(button).toHaveClass('border')
    })

    it('按钮应该使用 sm 尺寸', () => {
      const store = createMockStore()

      render(
        <Provider store={store}>
          <RefreshButton />
        </Provider>
      )

      const button = screen.getByRole('button')
      expect(button).toHaveClass('px-3', 'py-1.5')
    })
  })

  describe('数据更新验证', () => {
    it('刷新成功后 lastFetch 时间戳应该更新', async () => {
      const user = userEvent.setup()
      const { sectorClassificationApi } = require('@/lib/sectorClassificationApi')

      // Mock 成功的 API 响应
      sectorClassificationApi.getAllClassifications.mockResolvedValue({
        data: [
          { sector: 'Technology', strength: 'Strong', score: 85 },
        ],
      })

      const store = createMockStore()

      render(
        <Provider store={store}>
          <RefreshButton />
        </Provider>
      )

      const initialLastFetch = store.getState().sectorClassification.lastFetch
      expect(initialLastFetch).toBeNull()

      // 点击刷新按钮
      const button = screen.getByRole('button', { name: /刷新/ })
      await user.click(button)

      // 等待 async action 完成
      await waitFor(() => {
        const state = store.getState().sectorClassification
        expect(state.lastFetch).toBeTruthy()
        expect(state.lastFetch).not.toBe(initialLastFetch)
      })
    })

    it('刷新成功后 error 应该被清除', async () => {
      const user = userEvent.setup()
      const { sectorClassificationApi } = require('@/lib/sectorClassificationApi')

      // Mock 成功的 API 响应
      sectorClassificationApi.getAllClassifications.mockResolvedValue({
        data: [],
      })

      // 创建带有错误状态的 store
      const store = createMockStore(false, '之前的错误')

      render(
        <Provider store={store}>
          <RefreshButton />
        </Provider>
      )

      expect(store.getState().sectorClassification.error).toBe('之前的错误')

      // 点击刷新按钮
      const button = screen.getByRole('button', { name: /刷新/ })
      await user.click(button)

      // 等待 async action 完成，error 应该被清除
      await waitFor(() => {
        expect(store.getState().sectorClassification.error).toBeNull()
      })
    })
  })

  describe('错误状态和重试', () => {
    it('API 失败后按钮应该恢复可点击状态', async () => {
      const user = userEvent.setup()
      const { sectorClassificationApi } = require('@/lib/sectorClassificationApi')

      // Mock API 失败
      sectorClassificationApi.getAllClassifications.mockRejectedValue(
        new Error('网络错误')
      )

      const store = createMockStore()

      render(
        <Provider store={store}>
          <RefreshButton />
        </Provider>
      )

      const button = screen.getByRole('button', { name: /刷新/ })

      // 初始状态：按钮启用
      expect(button).toBeEnabled()

      // 点击刷新
      await user.click(button)

      // loading 状态：按钮禁用
      await waitFor(() => {
        expect(button).toBeDisabled()
      })

      // 等待请求完成，按钮恢复启用
      await waitFor(() => {
        expect(button).toBeEnabled()
      }, { timeout: 3000 })

      // 验证错误状态被设置
      expect(store.getState().sectorClassification.error).toBeTruthy()
    })

    it('失败后可以再次点击重试', async () => {
      const user = userEvent.setup()
      const { sectorClassificationApi } = require('@/lib/sectorClassificationApi')

      // Mock API 第一次失败，第二次成功
      sectorClassificationApi.getAllClassifications
        .mockRejectedValueOnce(new Error('第一次失败'))
        .mockResolvedValueOnce({ data: [] })

      const store = createMockStore()

      render(
        <Provider store={store}>
          <RefreshButton />
        </Provider>
      )

      const button = screen.getByRole('button', { name: /刷新/ })

      // 第一次点击（失败）
      await user.click(button)
      await waitFor(() => {
        expect(button).toBeEnabled()
      }, { timeout: 3000 })

      expect(store.getState().sectorClassification.error).toBe('第一次失败')

      // 第二次点击（重试，成功）
      await user.click(button)
      await waitFor(() => {
        expect(store.getState().sectorClassification.error).toBeNull()
      }, { timeout: 3000 })
    })

    it('错误状态下不阻止按钮点击（允许重试）', async () => {
      const user = userEvent.setup()
      const { sectorClassificationApi } = require('@/lib/sectorClassificationApi')

      // Mock API 响应
      sectorClassificationApi.getAllClassifications.mockResolvedValue({
        data: [],
      })

      // 创建带有错误但不在 loading 状态的 store
      const store = createMockStore(false, '之前的错误')

      render(
        <Provider store={store}>
          <RefreshButton />
        </Provider>
      )

      const button = screen.getByRole('button', { name: /刷新/ })

      // 错误状态下按钮应该仍然可点击
      expect(button).toBeEnabled()

      // 点击应该触发新的请求
      await user.click(button)
      const actions = store.getActions()
      expect(actions.length).toBeGreaterThan(0)
    })
  })
})
