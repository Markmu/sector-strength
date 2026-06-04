/**
 * 基金列表页内容组件
 *
 * 使用 useSearchParams 需要被 Suspense 包裹
 */
'use client'

import { useState, useCallback, useMemo } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { DashboardLayout, DashboardHeader } from '@/components/dashboard'
import { Disclaimer } from '@/components/ui/Disclaimer'
import { useFundList } from '@/hooks/useFunds'
import FundSearchBar from '@/components/funds/FundSearchBar'
import FundFilterPanel, {
  type FundFilterValues,
} from '@/components/funds/FundFilterPanel'
import FundListTable from '@/components/funds/FundListTable'
import Pagination from '@/components/funds/Pagination'

const DEFAULT_PAGE_SIZE = 20
const VALID_PAGE_SIZES = [10, 20, 50, 100]

export default function FundListPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()

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

  // 搜索状态
  const [search, setSearch] = useState(initialSearch)

  // 过滤状态
  const [filters, setFilters] = useState<FundFilterValues>({
    market: initialMarket,
    fundType: initialFundType,
  })

  // 分页状态
  const [page, setPage] = useState(initialPage)
  const [pageSize, setPageSize] = useState(initialPageSize)

  // 构建 API 参数（全选等同于不筛选，不传参数）
  const apiParams = useMemo(
    () => ({
      search: search || undefined,
      market: filters.market.length > 0 && filters.market.length < 2
        ? filters.market.join(',')
        : undefined,
      fundType: filters.fundType.length > 0 && filters.fundType.length < 4
        ? filters.fundType.join(',')
        : undefined,
      page,
      pageSize,
    }),
    [search, filters, page, pageSize]
  )

  // SWR 数据获取
  const { funds, total, totalPages, isLoading, isError } = useFundList(apiParams)

  // URL query 同步
  const syncUrl = useCallback(
    (newSearch: string, newFilters: FundFilterValues, newPage: number, newPageSize: number) => {
      const params = new URLSearchParams()
      if (newSearch) params.set('search', newSearch)
      if (newFilters.market.length > 0) params.set('market', newFilters.market.join(','))
      if (newFilters.fundType.length > 0) params.set('fundType', newFilters.fundType.join(','))
      if (newPage > 1) params.set('page', String(newPage))
      if (newPageSize !== DEFAULT_PAGE_SIZE) params.set('pageSize', String(newPageSize))

      const qs = params.toString()
      router.replace(`/dashboard/funds${qs ? `?${qs}` : ''}`, { scroll: false })
    },
    [router]
  )

  // 搜索变化处理
  const handleSearch = useCallback(
    (value: string) => {
      setSearch(value)
      setPage(1)
      syncUrl(value, filters, 1, pageSize)
    },
    [filters, pageSize, syncUrl]
  )

  // 过滤变化处理
  const handleFilterChange = useCallback(
    (newFilters: FundFilterValues) => {
      setFilters(newFilters)
      setPage(1)
      syncUrl(search, newFilters, 1, pageSize)
    },
    [search, pageSize, syncUrl]
  )

  // 分页变化处理
  const handlePageChange = useCallback(
    (newPage: number) => {
      setPage(newPage)
      syncUrl(search, filters, newPage, pageSize)
      window.scrollTo({ top: 0, behavior: 'smooth' })
    },
    [search, filters, pageSize, syncUrl]
  )

  // 每页条数变化处理
  const handlePageSizeChange = useCallback(
    (newSize: number) => {
      setPageSize(newSize)
      setPage(1)
      syncUrl(search, filters, 1, newSize)
      window.scrollTo({ top: 0, behavior: 'smooth' })
    },
    [search, filters, syncUrl]
  )

  // 是否有搜索或过滤条件
  const hasSearch = !!(search || filters.market.length > 0 || filters.fundType.length > 0)

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
          <FundSearchBar searchValue={search} onSearch={handleSearch} />

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
