/**
 * 基金反查页
 *
 * 路由：/dashboard/funds/reverse-lookup?symbol=600519&fund_type=股票型,混合型&fund_search=华夏
 * 按股票代码查询重仓基金列表，支持多维度联合筛选
 */
'use client'

import { useMemo, Suspense, useState, useCallback, useRef, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { DashboardLayout, DashboardHeader, ErrorState } from '@/components/dashboard'
import { Disclaimer } from '@/components/ui/Disclaimer'
import { useReverseLookup } from '@/hooks/useFunds'
import ReverseLookupTable from '@/components/funds/ReverseLookupTable'
import Pagination from '@/components/ui/Pagination'
import { FUND_TYPE_OPTIONS, MARKET_OPTIONS } from '@/components/funds/FundFilterPanel'
import { Checkbox } from '@/components/ui/Checkbox'
import SearchDropdownInput from '@/components/ui/SearchDropdownInput'
import { stocksApi } from '@/lib/api'
import { ArrowLeftIcon, SearchIcon, FilterIcon } from 'lucide-react'

const DEFAULT_PAGE_SIZE = 20

/**
 * 股票下拉搜索函数
 */
function useStockSearch() {
  return useCallback(async (keyword: string, page: number) => {
    const res = await stocksApi.searchStocks(keyword, { page, pageSize: 10 })
    const data = res.data as { data: { items: Array<{ symbol: string; name: string }>; total: number } }
    return {
      options: (data.data.items || []).map((s) => ({
        value: s.symbol,
        label: s.name,
      })),
      total: data.data.total || 0,
    }
  }, [])
}

function ReverseLookupContent() {
  const router = useRouter()
  const searchParams = useSearchParams()

  // 从 URL 解析初始状态
  const symbol = searchParams.get('symbol')?.trim() || ''
  // plan-03 / AC-05：from=fund-crowd 标识来自扎堆分析页下钻（前端路由层标识，非 API 参数）
  const fromFundCrowd = searchParams.get('from') === 'fund-crowd'
  const initialFundSearch = searchParams.get('fund_search') || ''
  const initialFundType = searchParams.get('fund_type')?.split(',').filter(Boolean) || []
  const initialMarket = searchParams.get('market')?.split(',').filter(Boolean) || []
  const initialPage = parseInt(searchParams.get('page') || '1', 10)

  const [page, setPage] = useState(initialPage)
  const [fundSearch, setFundSearch] = useState(initialFundSearch)
  const [fundType, setFundType] = useState<string[]>(initialFundType)
  const [market, setMarket] = useState<string[]>(initialMarket)

  // debounce fundSearch
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [debouncedFundSearch, setDebouncedFundSearch] = useState(initialFundSearch)

  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current)
    }
    debounceRef.current = setTimeout(() => {
      setDebouncedFundSearch(fundSearch)
      setPage(1)
    }, 300)
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current)
      }
    }
  }, [fundSearch])

  // URL 同步
  // plan-03 / AC-05：保留 from=fund-crowd 参数，避免筛选/翻页时 router.replace 丢失标识
  // （否则用户在 04 反查页切换股票/筛选后「返回扎堆分析」入口与差异提示会消失）
  const syncUrl = useCallback((newSymbol: string, newFundSearch: string, newFundType: string[], newMarket: string[], newPage: number) => {
    const params = new URLSearchParams()
    if (newSymbol) params.set('symbol', newSymbol)
    if (newFundSearch) params.set('fund_search', newFundSearch)
    if (newFundType.length > 0) params.set('fund_type', newFundType.join(','))
    if (newMarket.length > 0) params.set('market', newMarket.join(','))
    if (newPage > 1) params.set('page', String(newPage))
    if (fromFundCrowd) params.set('from', 'fund-crowd')
    const qs = params.toString()
    router.replace(`/dashboard/funds/reverse-lookup${qs ? `?${qs}` : ''}`, { scroll: false })
  }, [router, fromFundCrowd])

  // 构建 API 参数（全选 = 无筛选）
  const apiParams = useMemo(() => ({
    page,
    pageSize: DEFAULT_PAGE_SIZE,
    fundType: fundType.length > 0 && fundType.length < FUND_TYPE_OPTIONS.length ? fundType : undefined,
    market: market.length > 0 && market.length < MARKET_OPTIONS.length ? market : undefined,
    fundSearch: debouncedFundSearch || undefined,
  }), [page, fundType, market, debouncedFundSearch])

  const {
    items,
    total,
    totalPages,
    stockName,
    reportPeriod,
    isLoading,
    isError,
    mutate,
  } = useReverseLookup(symbol, apiParams)

  const handlePageChange = useCallback((newPage: number) => {
    setPage(newPage)
    syncUrl(symbol, fundSearch, fundType, market, newPage)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [symbol, fundSearch, fundType, market, syncUrl])

  // 股票搜索：选中后更新 URL
  const handleStockSelect = useCallback((option: { value: string; label: string }) => {
    setPage(1)
    setFundSearch('')
    setDebouncedFundSearch('')
    setFundType([])
    setMarket([])
    syncUrl(option.value, '', [], [], 1)
  }, [syncUrl])

  // 基金关键词搜索
  const handleFundSearchChange = useCallback((value: string) => {
    setFundSearch(value)
    syncUrl(symbol, value, fundType, market, 1)
  }, [symbol, fundType, market, syncUrl])

  // 基金类型切换
  const handleFundTypeToggle = useCallback((typeValue: string) => {
    setFundType(prev => {
      const next = prev.includes(typeValue)
        ? prev.filter(v => v !== typeValue)
        : [...prev, typeValue]
      setPage(1)
      syncUrl(symbol, fundSearch, next, market, 1)
      return next
    })
  }, [symbol, fundSearch, market, syncUrl])

  // 市场类型切换
  const handleMarketToggle = useCallback((marketValue: string) => {
    setMarket(prev => {
      const next = prev.includes(marketValue)
        ? prev.filter(v => v !== marketValue)
        : [...prev, marketValue]
      setPage(1)
      syncUrl(symbol, fundSearch, fundType, next, 1)
      return next
    })
  }, [symbol, fundSearch, fundType, syncUrl])

  const searchStocks = useStockSearch()

  // 构建标题
  const titleParts = useMemo(() => {
    if (!symbol) return null
    let title = ''
    if (stockName) {
      title = `${stockName}（${symbol}）`
    } else {
      title = symbol
    }
    title += ' 反查结果'
    if (reportPeriod) {
      title += `：最新报告期 ${reportPeriod} 持有该股的基金`
    }
    return { title, subtitle: total > 0 ? `共 ${total} 只基金重仓持有（占净值比 >= 1%）` : '' }
  }, [symbol, stockName, reportPeriod, total])

  // symbol 缺失
  if (!symbol) {
    return (
      <DashboardLayout>
        <DashboardHeader
          title="按股票反查基金"
          breadcrumbs={[
            { label: '仪表板', href: '/dashboard' },
            { label: '基金分析', href: '/dashboard/funds' },
            { label: '反查' },
          ]}
        />
        <div className="px-4 py-6 md:px-6 md:py-8">
          <div className="max-w-7xl mx-auto space-y-6">
            {/* plan-03 / AC-05：from=fund-crowd 时显示「返回扎堆分析」+ 差异提示，否则原「返回基金分析」 */}
            {fromFundCrowd ? (
              <button
                onClick={() => router.push('/dashboard/fund-crowd-analysis')}
                className="inline-flex items-center gap-1 text-sm text-primary hover:text-primary/80 transition-colors"
                data-testid="back-to-fund-crowd"
              >
                <ArrowLeftIcon className="w-4 h-4" />
                返回扎堆分析
              </button>
            ) : (
              <button
                onClick={() => router.push('/dashboard/funds')}
                className="inline-flex items-center gap-1 text-sm text-primary hover:text-primary/80 transition-colors"
              >
                <ArrowLeftIcon className="w-4 h-4" />
                返回基金分析
              </button>
            )}

            {/* 股票搜索框 */}
            <div className="max-w-md">
              <SearchDropdownInput
                placeholder="输入股票代码或名称搜索"
                icon={<SearchIcon className="w-4 h-4" />}
                onSearch={searchStocks}
                onSelect={handleStockSelect}
              />
            </div>

            <div className="bg-card rounded-xl border border-border shadow-sm p-12 text-center">
              <p className="text-lg font-medium text-foreground mb-2">请输入股票代码</p>
              <p className="text-sm text-muted-foreground">
                在上方搜索框输入股票代码或名称，查看重仓该股票的基金列表
              </p>
            </div>
          </div>
        </div>
      </DashboardLayout>
    )
  }

  // 错误态（如股票代码无效）
  if (isError && !isLoading) {
    return (
      <DashboardLayout>
        <DashboardHeader
          title="按股票反查基金"
          breadcrumbs={[
            { label: '仪表板', href: '/dashboard' },
            { label: '基金分析', href: '/dashboard/funds' },
            { label: '反查' },
          ]}
        />
        <div className="px-4 py-6 md:px-6 md:py-8">
          <div className="max-w-7xl mx-auto space-y-6">
            {/* plan-03 / AC-05：from=fund-crowd 时显示「返回扎堆分析」，否则原「返回基金分析」 */}
            {fromFundCrowd ? (
              <button
                onClick={() => router.push('/dashboard/fund-crowd-analysis')}
                className="inline-flex items-center gap-1 text-sm text-primary hover:text-primary/80 transition-colors"
                data-testid="back-to-fund-crowd"
              >
                <ArrowLeftIcon className="w-4 h-4" />
                返回扎堆分析
              </button>
            ) : (
              <button
                onClick={() => router.push('/dashboard/funds')}
                className="inline-flex items-center gap-1 text-sm text-primary hover:text-primary/80 transition-colors"
              >
                <ArrowLeftIcon className="w-4 h-4" />
                返回基金分析
              </button>
            )}
            <ErrorState
              title="股票代码无效"
              message="请检查股票代码是否正确后重试"
              onRetry={() => mutate()}
            />
          </div>
        </div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <DashboardHeader
        title={titleParts?.title || '按股票反查基金'}
        subtitle={titleParts?.subtitle}
        breadcrumbs={[
          { label: '仪表板', href: '/dashboard' },
          { label: '基金分析', href: '/dashboard/funds' },
          { label: '反查' },
        ]}
      />

      <div className="px-4 py-6 md:px-6 md:py-8">
        <div className="max-w-7xl mx-auto space-y-6">
          {/* 返回入口：plan-03 / AC-05 from=fund-crowd 时显示「返回扎堆分析」，否则原「返回基金分析」 */}
          {fromFundCrowd ? (
            <button
              onClick={() => router.push('/dashboard/fund-crowd-analysis')}
              className="inline-flex items-center gap-1 text-sm text-primary hover:text-primary/80 transition-colors"
              data-testid="back-to-fund-crowd"
            >
              <ArrowLeftIcon className="w-4 h-4" />
              返回扎堆分析
            </button>
          ) : (
            <button
              onClick={() => router.push('/dashboard/funds')}
              className="inline-flex items-center gap-1 text-sm text-primary hover:text-primary/80 transition-colors"
            >
              <ArrowLeftIcon className="w-4 h-4" />
              返回基金分析
            </button>
          )}

          {/* plan-03 / AC-05 双轨下钻口径差异提示：仅 from=fund-crowd 时渲染（ADR-4 + 架构 §7.6 + PRD §3.3） */}
          {fromFundCrowd && (
            <div
              className="bg-warning/10 border border-warning/30 rounded-lg p-3 text-sm text-warning"
              data-testid="fund-crowd-drilldown-hint"
              role="note"
            >
              扎堆统计计入全部重仓记录，本表按占净值比 ≥1% 展示，个别大基金的边界持仓可能未在下钻列表中显示。
            </div>
          )}

          {/* 搜索筛选区域 */}
          <div className="bg-card rounded-xl border border-border shadow-sm p-4 space-y-4">
            {/* 第一行：股票搜索 + 基金关键词搜索 */}
            <div className="flex flex-col sm:flex-row gap-3">
              {/* 股票搜索下拉框 */}
              <div className="flex-1 max-w-xs">
                <SearchDropdownInput
                  placeholder="切换股票"
                  icon={<SearchIcon className="w-4 h-4" />}
                  onSearch={searchStocks}
                  onSelect={handleStockSelect}
                />
              </div>

              {/* 基金代码/名称搜索 */}
              <div className="flex-1 relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <FilterIcon className="w-4 h-4 text-muted-foreground" />
                </div>
                <input
                  type="text"
                  placeholder="基金代码或名称"
                  value={fundSearch}
                  onChange={(e) => handleFundSearchChange(e.target.value)}
                  className="block w-full text-sm border rounded-lg transition-colors duration-200
                    focus:outline-none focus:ring-2 focus:ring-primary-light
                    border-border bg-card text-foreground placeholder-faint
                    focus:border-primary pl-10 pr-4 py-2.5"
                />
              </div>
            </div>

            {/* 第二行：市场 + 基金类型复选框 */}
            <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
              {/* 市场筛选 */}
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-muted-foreground whitespace-nowrap">市场</span>
                <div className="flex items-center gap-3">
                  {MARKET_OPTIONS.map((opt) => (
                    <Checkbox
                      key={opt.value}
                      label={opt.label}
                      checked={market.includes(opt.value)}
                      onCheckedChange={() => handleMarketToggle(opt.value)}
                    />
                  ))}
                </div>
              </div>

              {/* 分隔线 */}
              <div className="hidden sm:block w-px h-5 bg-border" />

              {/* 基金类型筛选 */}
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-muted-foreground whitespace-nowrap">类型</span>
                <div className="flex items-center gap-3">
                  {FUND_TYPE_OPTIONS.map((opt) => (
                    <Checkbox
                      key={opt.value}
                      label={opt.label}
                      checked={fundType.includes(opt.value)}
                      onCheckedChange={() => handleFundTypeToggle(opt.value)}
                    />
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* 反查结果 */}
          {!isLoading && items.length === 0 && !fundSearch && fundType.length === 0 && market.length === 0 ? (
            <div className="bg-card rounded-xl border border-border shadow-sm p-12 text-center">
              <SearchIcon className="w-12 h-12 mx-auto mb-3 text-faint" />
              <p className="text-lg font-medium text-foreground mb-2">
                最新一期暂无基金披露重仓持有该股票
              </p>
              <p className="text-sm text-muted-foreground">
                {`当前报告期无占净值比 >= 1% 的基金持仓记录`}
              </p>
            </div>
          ) : !isLoading && items.length === 0 ? (
            <div className="bg-card rounded-xl border border-border shadow-sm p-12 text-center">
              <SearchIcon className="w-12 h-12 mx-auto mb-3 text-faint" />
              <p className="text-lg font-medium text-foreground mb-2">无匹配结果</p>
              <p className="text-sm text-muted-foreground">
                当前筛选条件下没有匹配的基金，请调整筛选条件
              </p>
            </div>
          ) : (
            <>
              {/* 结果统计 */}
              {!isLoading && total > 0 && (
                <div className="text-sm text-muted-foreground">
                  共 <span className="font-semibold text-foreground">{total}</span> 只基金重仓持有（占净值比 &gt;= 1%）
                  {(fundSearch || fundType.length > 0 || market.length > 0) && (
                    <span className="ml-2">
                      （已筛选）
                    </span>
                  )}
                </div>
              )}

              {/* 反查表格 */}
              <ReverseLookupTable
                items={items}
                total={total}
                isLoading={isLoading}
                isError={isError && isLoading}
              />

              {/* 分页 */}
              {!isLoading && !isError && items.length > 0 && totalPages > 1 && (
                <Pagination
                  currentPage={page}
                  totalPages={totalPages}
                  total={total}
                  pageSize={DEFAULT_PAGE_SIZE}
                  onPageChange={handlePageChange}
                />
              )}
            </>
          )}

          {/* 免责声明 */}
          <Disclaimer showSeparator={true} />
        </div>
      </div>
    </DashboardLayout>
  )
}

export default function ReverseLookupPage() {
  return (
    <Suspense fallback={
      <DashboardLayout>
        <DashboardHeader title="按股票反查基金" breadcrumbs={[
          { label: '仪表板', href: '/dashboard' },
          { label: '基金分析', href: '/dashboard/funds' },
          { label: '反查' },
        ]} />
        <div className="px-4 py-6 md:px-6 md:py-8">
          <div className="max-w-7xl mx-auto space-y-6">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="h-10 bg-secondary/60 rounded animate-pulse" />
            ))}
          </div>
        </div>
      </DashboardLayout>
    }>
      <ReverseLookupContent />
    </Suspense>
  )
}
