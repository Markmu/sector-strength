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

export default function FundListPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()

  // 从 URL 恢复状态
  const initialSearch = searchParams.get('search') || ''
  const initialPage = parseInt(searchParams.get('page') || '1', 10)
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

  // 构建 API 参数
  const apiParams = useMemo(
    () => ({
      search: search || undefined,
      market: filters.market.join(',') || undefined,
      fundType: filters.fundType.join(',') || undefined,
      page,
      pageSize: DEFAULT_PAGE_SIZE,
    }),
    [search, filters, page]
  )

  // SWR 数据获取
  const { funds, total, totalPages, isLoading, isError } = useFundList(apiParams)

  // URL query 同步
  const syncUrl = useCallback(
    (newSearch: string, newFilters: FundFilterValues, newPage: number) => {
      const params = new URLSearchParams()
      if (newSearch) params.set('search', newSearch)
      if (newFilters.market.length > 0) params.set('market', newFilters.market.join(','))
      if (newFilters.fundType.length > 0) params.set('fundType', newFilters.fundType.join(','))
      if (newPage > 1) params.set('page', String(newPage))
      params.set('pageSize', String(DEFAULT_PAGE_SIZE))

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
      syncUrl(value, filters, 1)
    },
    [filters, syncUrl]
  )

  // 过滤变化处理
  const handleFilterChange = useCallback(
    (newFilters: FundFilterValues) => {
      setFilters(newFilters)
      setPage(1)
      syncUrl(search, newFilters, 1)
    },
    [search, syncUrl]
  )

  // 分页变化处理
  const handlePageChange = useCallback(
    (newPage: number) => {
      setPage(newPage)
      syncUrl(search, filters, newPage)
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
        <div className="max-w-7xl mx-auto space-y-6">
          {/* 搜索栏 */}
          <FundSearchBar searchValue={search} onSearch={handleSearch} />

          {/* 主内容区：左侧过滤 + 右侧列表 */}
          <div className="flex flex-col lg:flex-row gap-6">
            {/* 左侧过滤面板 */}
            <div className="w-full lg:w-56 flex-shrink-0">
              <FundFilterPanel value={filters} onChange={handleFilterChange} />
            </div>

            {/* 右侧列表和分页 */}
            <div className="flex-1 min-w-0 space-y-4">
              {/* 结果统计 */}
              {!isLoading && (
                <div className="text-sm text-muted-foreground">
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
                  pageSize={DEFAULT_PAGE_SIZE}
                  onPageChange={handlePageChange}
                />
              )}
            </div>
          </div>

          {/* 免责声明 */}
          <Disclaimer showSeparator={true} />
        </div>
      </div>
    </DashboardLayout>
  )
}
