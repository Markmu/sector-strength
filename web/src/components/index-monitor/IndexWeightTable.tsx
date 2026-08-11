'use client'

/**
 * 成分权重表（第 15 期 plan-04 Task 10）
 *
 * AC-04：单选指数 + top_n 选择器（10/20/30），展示前 N 成分股权重 + 集中度（top5/top10）
 * AC-06：点击成分股跳转个股分析页 /dashboard/stock-analysis/[conCode]
 *
 * 实现：
 * - 单选指数（从 watchlist，默认选第一只）
 * - top_n 选择器（10/20/30）
 * - SWR 调 indexMonitorApi.getWeights(indexCode, topN)
 * - 表格：排名 / 成分股名称（无名称显示 con_code）/ 权重% / 个股分析跳转
 * - 集中度展示：前5合计 / 前10合计
 */
import React, { useMemo, useState, useEffect } from 'react'
import useSWR from 'swr'
import Link from 'next/link'
import { Loader2, AlertCircle, ArrowRight } from 'lucide-react'
import { indexMonitorApi } from '@/lib/api'
import type {
  IndexWatchlistItem,
  IndexWeightData,
} from '@/types/indexMonitorTypes'
import SimpleSelect from '@/components/ui/SimpleSelect'
import { formatWeight } from './helpers'

const SWR_OPTIONS = { revalidateOnFocus: false, dedupingInterval: 30000 } as const

const TOP_N_OPTIONS = [10, 20, 30]

interface Props {
  watchlist: IndexWatchlistItem[]
}

export default function IndexWeightTable({ watchlist }: Props) {
  const [tsCode, setTsCode] = useState<string>(() => watchlist[0]?.tsCode ?? '')
  const [topN, setTopN] = useState<number>(20)

  // watchlist 变化时若 tsCode 失效则重置
  useEffect(() => {
    if (watchlist.length > 0 && !watchlist.some((w) => w.tsCode === tsCode)) {
      setTsCode(watchlist[0].tsCode)
    } else if (watchlist.length > 0 && !tsCode) {
      setTsCode(watchlist[0].tsCode)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [watchlist.length])

  const selectOptions = useMemo(
    () => watchlist.map((w) => ({ value: w.tsCode, label: w.name })),
    [watchlist]
  )
  const topNOptions = useMemo(
    () => TOP_N_OPTIONS.map((n) => ({ value: String(n), label: `前 ${n} 大` })),
    []
  )

  const { data: weightsRes, isLoading, error } = useSWR<{
    success: boolean
    data: IndexWeightData
  }>(
    tsCode ? ['indexWeights', tsCode, topN] : null,
    () =>
      indexMonitorApi
        .getWeights(tsCode, topN)
        .then((res) => res.data as unknown as {
          success: boolean
          data: IndexWeightData
        }),
    SWR_OPTIONS
  )
  const isError = error
  const weights = weightsRes?.data ?? null

  return (
    <section className="bg-card rounded-xl border border-border shadow-sm p-4 space-y-3">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <h2 className="text-base font-semibold text-foreground">成分权重</h2>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">指数</span>
            <SimpleSelect
              value={tsCode}
              options={selectOptions}
              onChange={setTsCode}
              ariaLabel="选择指数"
              testId="index-weight-select"
            />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">范围</span>
            <SimpleSelect
              value={String(topN)}
              options={topNOptions}
              onChange={(v) => setTopN(Number(v))}
              ariaLabel="选择范围"
              testId="index-weight-topn"
            />
          </div>
        </div>
      </div>

      {/* 集中度 */}
      {weights && weights.weights.length > 0 && (
        <div className="flex items-center gap-4 text-sm">
          <span className="text-muted-foreground">集中度：</span>
          <span className="text-foreground">
            前 5 合计 <span className="font-medium">{formatWeight(weights.concentration?.top5)}</span>
          </span>
          <span className="text-foreground">
            前 10 合计 <span className="font-medium">{formatWeight(weights.concentration?.top10)}</span>
          </span>
        </div>
      )}

      {/* 表格 */}
      {!tsCode ? (
        <div className="py-8 text-center text-muted-foreground text-sm">
          请选择指数
        </div>
      ) : isLoading ? (
        <div className="py-8 flex items-center justify-center text-muted-foreground text-sm">
          <Loader2 className="w-4 h-4 animate-spin mr-2" />
          加载权重数据...
        </div>
      ) : isError ? (
        <div className="py-8 flex flex-col items-center justify-center text-destructive text-sm">
          <AlertCircle className="w-5 h-5 mb-2" />
          权重数据加载失败
        </div>
      ) : !weights || weights.weights.length === 0 ? (
        <div className="py-8 text-center text-muted-foreground text-sm">
          暂无权重数据
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="px-4 py-2 text-left font-medium text-muted-foreground">排名</th>
                <th className="px-4 py-2 text-left font-medium text-muted-foreground">成分股</th>
                <th className="px-4 py-2 text-right font-medium text-muted-foreground">权重</th>
                <th className="px-4 py-2 text-right font-medium text-muted-foreground">操作</th>
              </tr>
            </thead>
            <tbody>
              {weights.weights.map((w, idx) => (
                <tr key={w.conCode} className="border-b border-border last:border-0">
                  <td className="px-4 py-2 text-muted-foreground">{idx + 1}</td>
                  <td className="px-4 py-2">
                    <div className="text-foreground">{w.name ?? w.conCode}</div>
                    <div className="text-xs text-muted-foreground">{w.conCode}</div>
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums text-foreground">
                    {formatWeight(w.weight)}
                  </td>
                  <td className="px-4 py-2 text-right">
                    <Link
                      href={`/dashboard/stock-analysis/${encodeURIComponent(w.conCode)}`}
                      className="inline-flex items-center gap-1 text-xs text-primary hover:text-primary-hover"
                    >
                      个股分析
                      <ArrowRight className="w-3 h-3" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
