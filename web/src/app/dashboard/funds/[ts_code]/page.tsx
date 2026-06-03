/**
 * 基金详情页
 *
 * 动态路由：/dashboard/funds/[ts_code]
 * 并行获取基本信息与持仓数据。
 */
'use client'

import { useState, useMemo, useCallback } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { DashboardLayout, DashboardHeader, ErrorState } from '@/components/dashboard'
import { Disclaimer } from '@/components/ui/Disclaimer'
import { useFundDetail, useFundPortfolio } from '@/hooks/useFunds'
import FundInfoCard from '@/components/funds/FundInfoCard'
import FundPortfolioTable from '@/components/funds/FundPortfolioTable'
import EmptyPortfolioState from '@/components/funds/EmptyPortfolioState'
import { ArrowLeftIcon } from 'lucide-react'

const DEFAULT_PAGE_SIZE = 20

export default function FundDetailPage() {
  const router = useRouter()
  const params = useParams()
  const tsCode = decodeURIComponent(params.ts_code as string)

  const [showAll, setShowAll] = useState(false)

  // 并行获取基本信息与持仓
  const { fund, isLoading: isFundLoading, isError: isFundError, mutate: mutateFund } = useFundDetail(tsCode)
  const {
    portfolio,
    total,
    isPortfolioEmpty,
    hasPortfolio,
    latestReportPeriod,
    latestAnnDate,
    isLoading: isPortfolioLoading,
    isError: isPortfolioError,
    mutate: mutatePortfolio,
  } = useFundPortfolio(tsCode, {
    page: 1,
    pageSize: showAll ? 9999 : DEFAULT_PAGE_SIZE,
  })

  // 构建持仓标题
  const portfolioTitle = useMemo(() => {
    if (!latestReportPeriod) return null
    let title = `最新报告期 ${latestReportPeriod}`
    if (latestAnnDate) {
      title += `（公告日 ${latestAnnDate}）`
    }
    title += `，持仓明细（共 ${total} 条）`
    return title
  }, [latestReportPeriod, latestAnnDate, total])

  // "全部持仓"展开
  const handleShowAll = useCallback(() => {
    setShowAll(true)
  }, [])

  // 重试
  const handleRetry = useCallback(() => {
    mutateFund()
    mutatePortfolio()
  }, [mutateFund, mutatePortfolio])

  // 基本信息加载失败 → 整页错误态
  if (isFundError && !fund) {
    return (
      <DashboardLayout>
        <DashboardHeader
          title="基金详情"
          breadcrumbs={[
            { label: '仪表板', href: '/dashboard' },
            { label: '基金分析', href: '/dashboard/funds' },
            { label: '基金详情' },
          ]}
        />
        <div className="px-4 py-6 md:px-6 md:py-8">
          <div className="max-w-7xl mx-auto">
            <ErrorState
              title="基金不存在"
              message="未找到该基金信息，请检查代码是否正确"
              onRetry={handleRetry}
            />
            <div className="mt-4 text-center">
              <button
                onClick={() => router.push('/dashboard/funds')}
                className="inline-flex items-center gap-1 text-sm text-primary hover:text-primary/80 transition-colors"
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

  return (
    <DashboardLayout>
      <DashboardHeader
        title={fund?.name || '基金详情'}
        subtitle={fund?.tsCode}
        breadcrumbs={[
          { label: '仪表板', href: '/dashboard' },
          { label: '基金分析', href: '/dashboard/funds' },
          { label: fund?.name || '详情' },
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
            返回列表
          </button>

          {/* 基本信息卡片 */}
          {isFundLoading && !fund ? (
            <div className="bg-card rounded-xl border border-border shadow-sm p-6 animate-pulse">
              <div className="h-6 bg-secondary/60 rounded w-1/3 mb-4" />
              <div className="h-4 bg-secondary/60 rounded w-1/4 mb-6" />
              <div className="grid grid-cols-3 gap-4">
                {Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="space-y-2">
                    <div className="h-3 bg-secondary/60 rounded w-1/2" />
                    <div className="h-4 bg-secondary/60 rounded w-3/4" />
                  </div>
                ))}
              </div>
            </div>
          ) : fund ? (
            <FundInfoCard fund={fund} />
          ) : null}

          {/* 持仓区域 */}
          {isPortfolioEmpty ? (
            <EmptyPortfolioState
              isPortfolioEmpty={isPortfolioEmpty}
              hasPortfolio={hasPortfolio}
            />
          ) : (
            <>
              {/* 持仓标题 */}
              {portfolioTitle && (
                <div className="text-sm text-muted-foreground">
                  {portfolioTitle}
                </div>
              )}

              {/* 持仓表格 */}
              <FundPortfolioTable
                items={portfolio}
                total={total}
                isLoading={isPortfolioLoading}
                isError={isPortfolioError}
                onShowAll={showAll ? undefined : handleShowAll}
              />
            </>
          )}

          {/* 免责声明 */}
          <Disclaimer showSeparator={true} />
        </div>
      </div>
    </DashboardLayout>
  )
}
