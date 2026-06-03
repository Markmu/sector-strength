/**
 * 基金反查页
 *
 * 路由：/dashboard/funds/reverse-lookup?symbol=600519
 * 按股票代码查询重仓基金列表
 */
'use client'

import { useMemo, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { DashboardLayout, DashboardHeader, ErrorState } from '@/components/dashboard'
import { Disclaimer } from '@/components/ui/Disclaimer'
import { useReverseLookup } from '@/hooks/useFunds'
import ReverseLookupTable from '@/components/funds/ReverseLookupTable'
import Pagination from '@/components/funds/Pagination'
import { ArrowLeftIcon, SearchIcon } from 'lucide-react'
import { useState, useCallback } from 'react'

const DEFAULT_PAGE_SIZE = 20

function ReverseLookupContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const symbol = searchParams.get('symbol')?.trim() || ''

  const [page, setPage] = useState(1)

  const {
    items,
    total,
    totalPages,
    stockName,
    reportPeriod,
    isLoading,
    isError,
    mutate,
  } = useReverseLookup(symbol, { page, pageSize: DEFAULT_PAGE_SIZE })

  const handlePageChange = useCallback((newPage: number) => {
    setPage(newPage)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [])

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
            <button
              onClick={() => router.push('/dashboard/funds')}
              className="inline-flex items-center gap-1 text-sm text-primary hover:text-primary/80 transition-colors"
            >
              <ArrowLeftIcon className="w-4 h-4" />
              返回基金分析
            </button>
            <div className="bg-card rounded-xl border border-border shadow-sm p-12 text-center">
              <SearchIcon className="w-12 h-12 mx-auto mb-3 text-faint" />
              <p className="text-lg font-medium text-foreground mb-2">请输入股票代码</p>
              <p className="text-sm text-muted-foreground mb-6">
                请在基金分析页面输入股票代码进行反查
              </p>
              <button
                onClick={() => router.push('/dashboard/funds')}
                className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg border border-border bg-card hover:bg-secondary text-foreground transition-colors"
              >
                <ArrowLeftIcon className="w-4 h-4" />
                返回列表
              </button>
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
            <button
              onClick={() => router.push('/dashboard/funds')}
              className="inline-flex items-center gap-1 text-sm text-primary hover:text-primary/80 transition-colors"
            >
              <ArrowLeftIcon className="w-4 h-4" />
              返回基金分析
            </button>
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
          {/* 返回链接 */}
          <button
            onClick={() => router.push('/dashboard/funds')}
            className="inline-flex items-center gap-1 text-sm text-primary hover:text-primary/80 transition-colors"
          >
            <ArrowLeftIcon className="w-4 h-4" />
            返回基金分析
          </button>

          {/* 反查结果 */}
          {!isLoading && items.length === 0 ? (
            <div className="bg-card rounded-xl border border-border shadow-sm p-12 text-center">
              <SearchIcon className="w-12 h-12 mx-auto mb-3 text-faint" />
              <p className="text-lg font-medium text-foreground mb-2">
                最新一期暂无基金披露重仓持有该股票
              </p>
              <p className="text-sm text-muted-foreground">
                {`当前报告期无占净值比 >= 1% 的基金持仓记录`}
              </p>
            </div>
          ) : (
            <>
              {/* 结果统计 */}
              {!isLoading && total > 0 && (
                <div className="text-sm text-muted-foreground">
                  共 <span className="font-semibold text-foreground">{total}</span> 只基金重仓持有（占净值比 &gt;= 1%）
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
