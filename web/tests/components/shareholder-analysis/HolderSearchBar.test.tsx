/**
 * HolderSearchBar 组件测试
 *
 * 股东搜索栏（单股东持仓查询入口）：
 * - 渲染占位符 + 搜索图标
 * - value 受控：非空时显示「正在查看股东」chip + 清除按钮
 * - 输入关键词触发 searchHolders API（debounce 后）
 * - 选中下拉项触发 onHolderSelect（传完整 holderName）
 */
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import HolderSearchBar from '@/components/shareholder-analysis/HolderSearchBar'

// Mock API：只暴露 searchHolders（HolderSearchBar 唯一依赖）
jest.mock('@/lib/api', () => ({
  shareholderAnalysisApi: {
    searchHolders: jest.fn(),
  },
}))

const api = jest.requireMock('@/lib/api') as {
  shareholderAnalysisApi: { searchHolders: jest.Mock }
}

describe('HolderSearchBar', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('渲染', () => {
    it('渲染搜索框 + 占位符', () => {
      render(<HolderSearchBar value={null} onHolderSelect={jest.fn()} />)
      expect(
        screen.getByPlaceholderText('搜索股东名称，查看该股东持仓')
      ).toBeInTheDocument()
    })

    it('渲染搜索图标', () => {
      const { container } = render(
        <HolderSearchBar value={null} onHolderSelect={jest.fn()} />
      )
      expect(container.querySelector('svg')).toBeInTheDocument()
    })
  })

  describe('受控 value', () => {
    it('value 非空时显示「正在查看股东」chip + 股东名', () => {
      render(
        <HolderSearchBar
          value="中央汇金投资有限责任公司"
          onHolderSelect={jest.fn()}
        />
      )
      expect(screen.getByTestId('holder-filter-chip')).toBeInTheDocument()
      expect(
        screen.getByText('中央汇金投资有限责任公司')
      ).toBeInTheDocument()
    })

    it('value 为空时不显示 chip', () => {
      render(<HolderSearchBar value={null} onHolderSelect={jest.fn()} />)
      expect(
        screen.queryByTestId('holder-filter-chip')
      ).not.toBeInTheDocument()
    })

    it('点清除按钮调 onClear', async () => {
      const onClear = jest.fn()
      const user = userEvent.setup()
      render(
        <HolderSearchBar
          value="中央汇金投资有限责任公司"
          onHolderSelect={jest.fn()}
          onClear={onClear}
        />
      )
      await user.click(screen.getByLabelText('清除股东筛选'))
      expect(onClear).toHaveBeenCalledTimes(1)
    })
  })

  describe('搜索交互', () => {
    it('输入关键词触发 searchHolders（debounce 后传 keyword + page）', async () => {
      api.shareholderAnalysisApi.searchHolders.mockResolvedValue({
        data: {
          data: {
            holders: [{ holderName: '中央汇金投资有限责任公司' }],
            total: 1,
          },
        },
      })
      const user = userEvent.setup()
      render(<HolderSearchBar value={null} onHolderSelect={jest.fn()} />)

      await user.type(
        screen.getByPlaceholderText('搜索股东名称，查看该股东持仓'),
        '中央汇金'
      )

      // debounce 默认 300ms，真实 timer 下 waitFor 等待触发
      await waitFor(() => {
        expect(
          api.shareholderAnalysisApi.searchHolders
        ).toHaveBeenCalledWith(
          expect.objectContaining({ keyword: '中央汇金', page: 1 })
        )
      })
    })

    it('选中下拉项触发 onHolderSelect（传完整 holderName）', async () => {
      api.shareholderAnalysisApi.searchHolders.mockResolvedValue({
        data: {
          data: {
            holders: [{ holderName: '中央汇金投资有限责任公司' }],
            total: 1,
          },
        },
      })
      const onHolderSelect = jest.fn()
      const user = userEvent.setup()
      render(<HolderSearchBar value={null} onHolderSelect={onHolderSelect} />)

      await user.type(
        screen.getByPlaceholderText('搜索股东名称，查看该股东持仓'),
        '中央汇金'
      )

      // 等下拉项出现（formatOption 渲染为纯股东名）
      const option = await screen.findByText('中央汇金投资有限责任公司')
      await user.click(option)

      expect(onHolderSelect).toHaveBeenCalledWith('中央汇金投资有限责任公司')
    })
  })
})
