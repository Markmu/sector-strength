/**
 * 基金列表页内容组件
 *
 * 使用 useSearchParams 需要被 Suspense 包裹
 *
 * 两种模式：
 * - 基金列表模式（默认）：显示基金搜索、筛选、列表
 * - 股票反查模式：URL 带 symbol 参数时，显示反查筛选和结果
 */
'use client'

import { useState, useCallback, useMemo, useRef, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { DashboardLayout, DashboardHeader } from '@/components/dashboard'
import { Disclaimer } from '@/components/ui/Disclaimer'
import { useFundList, useReverseLookup } from '@/hooks/useFunds'
import FundSearchBar from '@/components/funds/FundSearchBar'
import FundFilterPanel, {
  type FundFilterValues,
  MARKET_OPTIONS,
  FUND_TYPE_OPTIONS,
} from '@/components/funds/FundFilterPanel'
import FundListTable from '@/components/funds/FundListTable'
import ReverseLookupTable from '@/components/funds/ReverseLookupTable'
import Pagination from '@/components/ui/Pagination'
import { Checkbox } from '@/components/ui/Checkbox'
import { ArrowLeftIcon } from 'lucide-react'

const DEFAULT_PAGE_SIZE = 20
const VALID_PAGE_SIZES = [10, 20, 50, 100]

export default function FundListPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()

  // 判断模式：URL 有 symbol 参数则进入反查模式
  const reverseLookupSymbol = searchParams.get('symbol')?.trim() || ''

  // 从 URL 恢复状态
  const initialSearch = searchParams.get('search') || ''
  const initialPage = parseInt(searchParams.get('page') || '1', 10)
  const initialPageSize = (() => {
    const ps = parseInt(searchParams.get('pageSize') || '', 10)
    return VALID_PAGE_SIZES.includes(ps) ? ps : DEFAULT_PAGE_SIZE
  })()
  const initialMarket = searchParams.get('market')?.split(',').filter(Boolean) || []
  const initialFundType =
    searchParams.get('fundType')?.split(',').filter(Boolean) || []

  // ===== 基金列表模式状态 =====
  const [search, setSearch] = useState(initialSearch)
  const [filters, setFilters] = useState<FundFilterValues>({
    market: initialMarket,
    fundType: initialFundType,
  })
  const [page, setPage] = useState(initialPage)
  const [pageSize, setPageSize] = useState(initialPageSize)

  // ===== 反查模式状态 =====
  const [rlPage, setRlPage] = useState(initialPage)
  const [rlFundSearch, setRlFundSearch] = useState(searchParams.get('fund_search') || '')
  const [rlFundType, setRlFundType] = useState<string[]>(
    searchParams.get('rl_fund_type')?.split(',').filter(Boolean) || []
  )
  const [rlMarket, setRlMarket] = useState<string[]>(
    searchParams.get('rl_market')?.split(',').filter(Boolean) || []
  )

  // 反查模式下的 fund_search debounce
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [rlDebouncedFundSearch, setRlDebouncedFundSearch] = useState(
    searchParams.get('fund_search') || ''
  )

  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current)
    }
    debounceRef.current = setTimeout(() => {
      setRlDebouncedFundSearch(rlFundSearch)
      setRlPage(1)
    }, 300)
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current)
      }
    }
  }, [rlFundSearch])

  // ===== URL 同步 =====
  const syncUrl = useCallback(
    (params: Record<string, string | undefined>) => {
      const urlParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value) urlParams.set(key, value)
      })
      const qs = urlParams.toString()
      router.replace(`/dashboard/funds${qs ? `?${qs}` : ''}`, { scroll: false })
    },
    [router]
  )

  // ===== 基金列表 API 参数 =====
  const apiParams = useMemo(
    () => ({
      search: search || undefined,
      market: filters.market.length > 0 && filters.market.length < MARKET_OPTIONS.length
        ? filters.market
        : undefined,
      fundType: filters.fundType.length > 0 && filters.fundType.length < FUND_TYPE_OPTIONS.length
        ? filters.fundType
        : undefined,
      page,
      pageSize,
    }),
    [search, filters, page, pageSize]
  )

  // ===== 反查 API 参数 =====
  const rlApiParams = useMemo(() => ({
    page: rlPage,
    pageSize: DEFAULT_PAGE_SIZE,
    fundType: rlFundType.length > 0 && rlFundType.length < FUND_TYPE_OPTIONS.length ? rlFundType : undefined,
    market: rlMarket.length > 0 && rlMarket.length < MARKET_OPTIONS.length ? rlMarket : undefined,
    fundSearch: rlDebouncedFundSearch || undefined,
  }), [rlPage, rlFundType, rlMarket, rlDebouncedFundSearch])

  // ===== 数据获取 =====
  const { funds, total, totalPages, isLoading, isError } = useFundList(
    !reverseLookupSymbol ? apiParams : { page: 1, pageSize: 1 }
  )

  const {
    items: rlItems,
    total: rlTotal,
    totalPages: rlTotalPages,
    stockName,
    reportPeriod,
    isLoading: rlIsLoading,
    isError: rlIsError,
    mutate: rlMutate,
  } = useReverseLookup(reverseLookupSymbol, reverseLookupSymbol ? rlApiParams : undefined)

  // ===== 基金列表模式回调 =====
  const handleSearch = useCallback(
    (value: string) => {
      setSearch(value)
      setPage(1)
      syncUrl({
        search: value || undefined,
        market: filters.market.length > 0 ? filters.market.join(',') : undefined,
        fundType: filters.fundType.length > 0 ? filters.fundType.join(',') : undefined,
        page: undefined,
        pageSize: pageSize !== DEFAULT_PAGE_SIZE ? String(pageSize) : undefined,
      })
    },
    [filters, pageSize, syncUrl]
  )

  const handleFilterChange = useCallback(
    (newFilters: FundFilterValues) => {
      setFilters(newFilters)
      setPage(1)
      syncUrl({
        search: search || undefined,
        market: newFilters.market.length > 0 ? newFilters.market.join(',') : undefined,
        fundType: newFilters.fundType.length > 0 ? newFilters.fundType.join(',') : undefined,
        page: undefined,
        pageSize: pageSize !== DEFAULT_PAGE_SIZE ? String(pageSize) : undefined,
      })
    },
    [search, pageSize, syncUrl]
  )

  const handlePageChange = useCallback(
    (newPage: number) => {
      setPage(newPage)
      syncUrl({
        search: search || undefined,
        market: filters.market.length > 0 ? filters.market.join(',') : undefined,
        fundType: filters.fundType.length > 0 ? filters.fundType.join(',') : undefined,
        page: newPage > 1 ? String(newPage) : undefined,
        pageSize: pageSize !== DEFAULT_PAGE_SIZE ? String(pageSize) : undefined,
      })
      window.scrollTo({ top: 0, behavior: 'smooth' })
    },
    [search, filters, pageSize, syncUrl]
  )

  const handlePageSizeChange = useCallback(
    (newSize: number) => {
      setPageSize(newSize)
      setPage(1)
      syncUrl({
        search: search || undefined,
        market: filters.market.length > 0 ? filters.market.join(',') : undefined,
        fundType: filters.fundType.length > 0 ? filters.fundType.join(',') : undefined,
        page: undefined,
        pageSize: newSize !== DEFAULT_PAGE_SIZE ? String(newSize) : undefined,
      })
      window.scrollTo({ top: 0, behavior: 'smooth' })
    },
    [search, filters, syncUrl]
  )

  // ===== 反查模式回调 =====
  const handleReverseLookup = useCallback(
    (symbol: string, _name: string) => {
      setRlPage(1)
      setRlFundSearch('')
      setRlDebouncedFundSearch('')
      setRlFundType([])
      setRlMarket([])
      syncUrl({ symbol })
    },
    [syncUrl]
  )

  const handleExitReverseLookup = useCallback(() => {
    syncUrl({
      search: search || undefined,
      market: filters.market.length > 0 ? filters.market.join(',') : undefined,
      fundType: filters.fundType.length > 0 ? filters.fundType.join(',') : undefined,
    })
  }, [search, filters, syncUrl])

  // 反查模式 URL 同步辅助
  const rlSyncUrl = useCallback((overrides: {
    fundSearch?: string
    fundType?: string[]
    market?: string[]
    rlPage?: number
  }) => {
    const ft = overrides.fundType ?? rlFundType
    const mk = overrides.market ?? rlMarket
    const fs = overrides.fundSearch ?? rlFundSearch
    const p = overrides.rlPage ?? rlPage
    syncUrl({
      symbol: reverseLookupSymbol,
      fund_search: fs || undefined,
      rl_fund_type: ft.length > 0 ? ft.join(',') : undefined,
      rl_market: mk.length > 0 ? mk.join(',') : undefined,
      page: p > 1 ? String(p) : undefined,
    })
  }, [reverseLookupSymbol, rlFundSearch, rlFundType, rlMarket, rlPage, syncUrl])

  const handleRlFundSearchChange = useCallback((value: string) => {
    setRlFundSearch(value)
    rlSyncUrl({ fundSearch: value, rlPage: 1 })
  }, [rlSyncUrl])

  const handleRlFundTypeToggle = useCallback((typeValue: string) => {
    setRlFundType(prev => {
      const next = prev.includes(typeValue) ? prev.filter(v => v !== typeValue) : [...prev, typeValue]
      setRlPage(1)
      rlSyncUrl({ fundType: next, rlPage: 1 })
      return next
    })
  }, [rlSyncUrl])

  const handleRlMarketToggle = useCallback((marketValue: string) => {
    setRlMarket(prev => {
      const next = prev.includes(marketValue) ? prev.filter(v => v !== marketValue) : [...prev, marketValue]
      setRlPage(1)
      rlSyncUrl({ market: next, rlPage: 1 })
      return next
    })
  }, [rlSyncUrl])

  const handleRlPageChange = useCallback((newPage: number) => {
    setRlPage(newPage)
    rlSyncUrl({ rlPage: newPage })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [rlSyncUrl])

  // ===== 计算 =====
  const hasSearch = !!(search || filters.market.length > 0 || filters.fundType.length > 0)

  // ===== 反查模式渲染 =====
  if (reverseLookupSymbol) {
    const rlTitle = stockName
      ? `${stockName}（${reverseLookupSymbol}）反查结果`
      : `${reverseLookupSymbol} 反查结果`

    return (
      <DashboardLayout>
        <DashboardHeader
          title="基金分析 · 按股票反查"
          subtitle={reportPeriod ? `最新报告期 ${reportPeriod} 持有该股的基金` : undefined}
          breadcrumbs={[
            { label: '仪表板', href: '/dashboard' },
            { label: '基金分析', href: '/dashboard/funds' },
            { label: '反查' },
          ]}
        />

        <div className="px-4 py-6 md:px-6 md:py-8">
          <div className="max-w-7xl mx-auto space-y-4">
            {/* 搜索栏（复用，支持切换股票或退回基金列表） */}
            <FundSearchBar onSearch={() => {}} onReverseLookup={handleReverseLookup} />

            {/* 退出反查 + 标题 */}
            <div className="flex items-center gap-3">
              <button
                onClick={handleExitReverseLookup}
                className="inline-flex items-center gap-1 text-sm text-primary hover:text-primary/80 transition-colors"
              >
                <ArrowLeftIcon className="w-4 h-4" />
                返回基金列表
              </button>
              <span className="text-sm text-muted-foreground">|</span>
              <span className="text-sm font-medium text-foreground">{rlTitle}</span>
            </div>

            {/* 反查筛选栏 */}
            <div className="bg-card rounded-xl border border-border shadow-sm px-4 py-3 space-y-3">
              {/* 基金关键词搜索 */}
              <div className="flex flex-col sm:flex-row sm:items-center gap-3">
                <input
                  type="text"
                  placeholder="基金代码或名称"
                  value={rlFundSearch}
                  onChange={(e) => handleRlFundSearchChange(e.target.value)}
                  className="block w-full sm:max-w-xs text-sm border rounded-lg transition-colors duration-200
                    focus:outline-none focus:ring-2 focus:ring-primary-light
                    border-border bg-card text-foreground placeholder-faint
                    focus:border-primary px-4 py-2"
                />
                {!rlIsLoading && (
                  <div className="text-sm text-muted-foreground whitespace-nowrap">
                    共 <span className="font-semibold text-foreground">{rlTotal}</span> 只基金重仓持有
                    {(rlFundSearch || rlFundType.length > 0 || rlMarket.length > 0) && '（已筛选）'}
                  </div>
                )}
              </div>

              {/* 市场 + 类型复选框 */}
              <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-muted-foreground whitespace-nowrap">市场</span>
                  <div className="flex items-center gap-3">
                    {MARKET_OPTIONS.map((opt) => (
                      <Checkbox
                        key={opt.value}
                        label={opt.label}
                        checked={rlMarket.includes(opt.value)}
                        onCheckedChange={() => handleRlMarketToggle(opt.value)}
                      />
                    ))}
                  </div>
                </div>
                <div className="hidden sm:block w-px h-5 bg-border" />
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-muted-foreground whitespace-nowrap">类型</span>
                  <div className="flex items-center gap-3">
                    {FUND_TYPE_OPTIONS.map((opt) => (
                      <Checkbox
                        key={opt.value}
                        label={opt.label}
                        checked={rlFundType.includes(opt.value)}
                        onCheckedChange={() => handleRlFundTypeToggle(opt.value)}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* 反查结果表格 */}
            {!rlIsLoading && rlItems.length === 0 && !rlFundSearch && rlFundType.length === 0 && rlMarket.length === 0 ? (
              <div className="bg-card rounded-xl border border-border shadow-sm p-12 text-center">
                <p className="text-lg font-medium text-foreground mb-2">
                  最新一期暂无基金披露重仓持有该股票
                </p>
                <p className="text-sm text-muted-foreground">
                  当前报告期无占净值比 &gt;= 1% 的基金持仓记录
                </p>
              </div>
            ) : !rlIsLoading && rlItems.length === 0 ? (
              <div className="bg-card rounded-xl border border-border shadow-sm p-12 text-center">
                <p className="text-lg font-medium text-foreground mb-2">无匹配结果</p>
                <p className="text-sm text-muted-foreground">
                  当前筛选条件下没有匹配的基金，请调整筛选条件
                </p>
              </div>
            ) : (
              <>
                <ReverseLookupTable
                  items={rlItems}
                  total={rlTotal}
                  isLoading={rlIsLoading}
                  isError={rlIsError && rlIsLoading}
                />

                {/* 分页 */}
                {!rlIsLoading && !rlIsError && rlItems.length > 0 && rlTotalPages > 1 && (
                  <Pagination
                    currentPage={rlPage}
                    totalPages={rlTotalPages}
                    total={rlTotal}
                    pageSize={DEFAULT_PAGE_SIZE}
                    onPageChange={handleRlPageChange}
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

  // ===== 基金列表模式渲染（默认） =====
  return (
    <DashboardLayout>
      <DashboardHeader
        title="基金分析"
        subtitle="搜索和筛选基金，查看持仓明细"
        breadcrumbs={[
          { label: '仪表板', href: '/dashboard' },
          { label: '基金分析' },
        ]}
      />

      <div className="px-4 py-6 md:px-6 md:py-8">
        <div className="max-w-7xl mx-auto space-y-4">
          {/* 搜索栏 */}
          <FundSearchBar searchValue={search} onSearch={handleSearch} onReverseLookup={handleReverseLookup} />

          {/* 筛选栏 + 结果统计 */}
          <div className="bg-card rounded-xl border border-border shadow-sm px-4 py-3">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <FundFilterPanel value={filters} onChange={handleFilterChange} />
              {!isLoading && (
                <div className="text-sm text-muted-foreground whitespace-nowrap">
                  {hasSearch ? (
                    <>
                      找到 <span className="font-semibold text-foreground">{total}</span> 只匹配基金
                    </>
                  ) : (
                    <>
                      共 <span className="font-semibold text-foreground">{total}</span> 只基金
                    </>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* 基金列表表格 */}
          <FundListTable
            funds={funds}
            isLoading={isLoading}
            isError={!!isError}
            hasSearch={hasSearch}
          />

          {/* 分页 */}
          {!isLoading && !isError && funds.length > 0 && (
            <Pagination
              currentPage={page}
              totalPages={totalPages}
              total={total}
              pageSize={pageSize}
              onPageChange={handlePageChange}
              onPageSizeChange={handlePageSizeChange}
              showPageSizeSelector={true}
              showJumpToPage={true}
            />
          )}

          {/* 免责声明 */}
          <Disclaimer showSeparator={true} />
        </div>
      </div>
    </DashboardLayout>
  )
}
