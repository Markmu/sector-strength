/**
 * 个股分析页（最小落地页，AC-07）。
 *
 * 动态路由：/dashboard/stock-analysis/[id]
 * 作为板块成分股点击下钻的目标页，展示该股基础信息（代码/名称/强度分/趋势/最新价/市值）。
 * 个股深度功能（趋势图/均线/K线）不在本期范围，后续需求扩展。
 *
 * 数据来自既有 stocksApi.getStock（GET /stocks/{stock_id}，按 id 查询，isdigit 校验）。
 * 跳转参数用成分股项的 id（数据库主键），不用 symbol。
 */
'use client'

import { useMemo } from 'react'
import { useRouter, useParams } from 'next/navigation'
import useSWR from 'swr'
import { DashboardLayout, DashboardHeader } from '@/components/dashboard'
import { Disclaimer } from '@/components/ui/Disclaimer'
import StockInfoCard, {
  type StockDetailItem,
} from '@/components/stock-analysis/StockInfoCard'
import { stocksApi } from '@/lib/api'
import { ArrowLeftIcon } from 'lucide-react'

export default function StockAnalysisPage() {
  const router = useRouter()
  const params = useParams()
  const id = decodeURIComponent((params?.id as string) ?? '')

  // SWR fetcher：调 stocksApi.getStock，解包 .data.data 得 StockDetailItem
  const fetcher = async (): Promise<StockDetailItem> => {
    const response = await stocksApi.getStock(id)
    const outer = response.data
    if (!outer || !(outer as { data?: unknown }).data) {
      throw new Error('Failed to fetch stock detail')
    }
    // 后端返回 { success, data: StockDetail }；StockDetail 字段含 id/symbol/name/...
    return (outer as { data: StockDetailItem }).data
  }

  const queryKey = useMemo(() => (id ? `/stocks/${id}` : null), [id])

  const { data, error, isLoading, mutate } = useSWR<StockDetailItem>(
    queryKey,
    fetcher,
    {
      revalidateOnFocus: false,
      revalidateOnReconnect: true,
      dedupingInterval: 10000,
    }
  )

  const isError = !!error
  const title = data?.name ? `${data.name} - 个股分析` : '个股分析'

  return (
    <DashboardLayout>
      <DashboardHeader
        title={title}
        subtitle="个股基础信息（深度分析后续迭代）"
        breadcrumbs={[
          { label: '板块分析' },
          { label: '成分股' },
          { label: data?.name ?? '个股' },
        ]}
        actions={
          <button
            type="button"
            onClick={() => router.back()}
            data-testid="stock-back-btn"
            className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-lg border border-border text-foreground hover:bg-secondary"
          >
            <ArrowLeftIcon className="w-4 h-4" />
            返回
          </button>
        }
      />

      <div className="space-y-6">
        {/* 加载失败时提供重试 */}
        {isError && (
          <div className="bg-card rounded-xl border border-border shadow-sm p-6 text-center">
            <p className="text-sm text-muted-foreground mb-3">个股信息加载失败</p>
            <button
              type="button"
              onClick={() => mutate()}
              className="px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90"
            >
              重试
            </button>
          </div>
        )}

        {/* 基础信息卡（含三态分发） */}
        {!isError && (
          <StockInfoCard stock={data} isLoading={isLoading} isError={isError} />
        )}

        <Disclaimer showSeparator={true} />
      </div>
    </DashboardLayout>
  )
}
