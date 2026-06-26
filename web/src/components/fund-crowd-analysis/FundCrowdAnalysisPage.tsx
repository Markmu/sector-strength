'use client'

/**
 * 基金扎堆分析主页面（plan-02，AC-01/02/03/04/06/07/08）
 *
 * 页面状态：
 * - scope: 口径（默认 'active' 仅主动，AC-02）
 * - search / debouncedSearch: 搜索词（AC-08 debounce 300ms）
 * - page: 当前页码
 *
 * 布局：
 * 1. 标题 + 报告期标识 + 口径切换
 * 2. 行业分布（AC-04）
 * 3. 扎堆度排行榜（AC-01/02/03/06/08）
 *
 * 状态分支：
 * - AC-07：rankings.hasData=false（持仓未同步）→ 整页空状态
 * - plan-03 接入：RETURN_STATE_STORAGE_KEY sessionStorage 返回状态恢复（本 plan 预留读取入口）
 */
import React, { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import {
  useFundCrowdRankings,
  useFundCrowdIndustryDistribution,
} from '@/hooks/useFundCrowdAnalysis'
import type { CrowdScope } from '@/lib/api'
import { SECTOR_TYPE_LABELS, type SectorType } from '@/types/sectorTypes'
import CrowdScopeSelector from './CrowdScopeSelector'
import CrowdSectorTypeSelector from './CrowdSectorTypeSelector'
import CrowdIndustryDistribution from './CrowdIndustryDistribution'
import CrowdRankingTable from './CrowdRankingTable'

const DEFAULT_PAGE_SIZE = 20
const SEARCH_DEBOUNCE_MS = 300
// plan-03 复用：返回状态承载 key（本 plan 仅预留读取入口，写入由 plan-03 实现）
const RETURN_STATE_STORAGE_KEY = 'fund-crowd-return-state'

export default function FundCrowdAnalysisPage() {
  const router = useRouter()
  const [scope, setScope] = useState<CrowdScope>('active') // AC-02 默认仅主动
  const [sectorType, setSectorType] = useState<SectorType>('industry') // 板块维度（分布图 + 排行榜分类列联动）
  const [search, setSearch] = useState('') // AC-08 搜索词（即时）
  const [debouncedSearch, setDebouncedSearch] = useState('') // debounce 后传给 API
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE)
  // AC-05 scroll 恢复（plan-03 Task 5，arch-check 非阻塞改进项）：
  // 把返回时要恢复的 scroll 位置挂在 ref 上，等 rankings 数据加载完成后由独立 useEffect 恢复。
  // 直接在 mount useEffect 里 scrollTo 会在 SWR 数据未到达、DOM 高度未恢复时滚动无效。
  const pendingScrollRef = useRef<{ x: number; y: number } | null>(null)

  // AC-05 返回状态恢复：plan-03 在离开时写入 sessionStorage，本页加载时读取并恢复。
  // scope/page/search 恢复由 plan-02 实现；plan-03 追加 scroll 恢复（arch-check 非阻塞改进项）。
  useEffect(() => {
    if (typeof window === 'undefined') return
    const saved = window.sessionStorage.getItem(RETURN_STATE_STORAGE_KEY)
    if (!saved) return
    try {
      const state = JSON.parse(saved) as {
        scope?: CrowdScope
        sectorType?: SectorType
        page?: number
        search?: string
        scrollX?: number
        scrollY?: number
      }
      if (state.scope) setScope(state.scope)
      if (state.sectorType) setSectorType(state.sectorType)
      if (state.page) setPage(state.page)
      if (state.search) {
        setSearch(state.search)
        setDebouncedSearch(state.search) // 同步设置，避免 debounce 闪烁
      }
      // scroll 恢复位置暂存到 ref，待 rankings 加载完成后由下方 useEffect 触发实际 scrollTo
      if (state.scrollX !== undefined || state.scrollY !== undefined) {
        pendingScrollRef.current = {
          x: state.scrollX ?? 0,
          y: state.scrollY ?? 0,
        }
      }
      window.sessionStorage.removeItem(RETURN_STATE_STORAGE_KEY)
    } catch {
      window.sessionStorage.removeItem(RETURN_STATE_STORAGE_KEY)
    }
  }, [])

  // debounce search（AC-08 实时过滤，避免逐字请求）
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      setDebouncedSearch(search)
      setPage(1) // 搜索变化时重置到第 1 页
    }, SEARCH_DEBOUNCE_MS)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [search])

  // 数据获取（rankings + industry-distribution 联动，scope 变化时两者都重发）
  const rankingsParams = {
    scope,
    sectorType,
    search: debouncedSearch || undefined,
    page,
    pageSize,
  }
  const { rankings, isLoading, isError } = useFundCrowdRankings(rankingsParams)
  const {
    distribution,
    isLoading: isIndustryLoading,
  } = useFundCrowdIndustryDistribution(scope, sectorType)

  // AC-05 scroll 恢复触发（plan-03 Task 5）：
  // 监听 rankings 加载完成（!isLoading 且有数据），DOM 高度恢复后再恢复滚动位置。
  // 配合 rAF + setTimeout(0) 双重保障浏览器布局/绘制完成。恢复后清空 ref 避免重复滚动。
  // 注意：DashboardLayout 的根容器是 h-screen overflow-hidden，实际滚动发生在 <main>
  // （flex-1 overflow-y-auto，见 components/layout/Layout.tsx:39-44）。window.scrollY 始终为 0，
  // 因此恢复目标是 document.querySelector('main').scrollTop，而非 window.scrollTo。
  useEffect(() => {
    if (pendingScrollRef.current === null) return
    if (isLoading) return // 等待 SWR 数据到达，DOM 高度恢复后再滚动
    const target = pendingScrollRef.current
    pendingScrollRef.current = null
    const scrollToRestore = () => {
      const main = document.querySelector('main')
      if (main) {
        main.scrollTop = target.y
      } else {
        window.scrollTo(target.x, target.y)
      }
    }
    requestAnimationFrame(() => {
      setTimeout(scrollToRestore, 0)
    })
  }, [isLoading, rankings])

  // AC-07：持仓数据未同步 → 整页空状态
  const isPortfolioEmpty = !isLoading && rankings?.hasData === false

  const handleScopeChange = (nextScope: CrowdScope) => {
    setScope(nextScope)
    setPage(1) // 切换口径重置到第 1 页
    // search 保留（用户搜索意图跨口径保持）
  }

  const handleSectorTypeChange = (nextSectorType: SectorType) => {
    setSectorType(nextSectorType)
    // 不重置 page：sector_type 只改分类列，不改扎堆股集合（fundCount/total 不变）
  }

  const handlePageChange = (nextPage: number) => {
    setPage(nextPage)
    if (typeof window !== 'undefined') {
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }

  const handlePageSizeChange = (nextSize: number) => {
    setPageSize(nextSize)
    setPage(1) // 切换每页条数重置到第 1 页
  }

  // AC-05 反查跳转（plan-03 Task 4）：记录当前口径/页码/搜索词/滚动位置到 sessionStorage，
  // 跳转 04 反查页并带 from=fund-crowd 标识。返回扎堆页时从 sessionStorage 恢复（含 scroll 恢复）。
  // from=fund-crowd 是前端路由层标识，不传给 04 API（api.ts:fundsApi.reverseLookup 不接收 from）。
  // 滚动位置：实际滚动发生在 <main>（DashboardLayout 根 h-screen overflow-hidden），
  // 故记录 main.scrollTop；window.scrollX/Y 在本布局下始终为 0。
  const handleReverseLookup = (stockSymbol: string) => {
    if (typeof window === 'undefined') return
    const main = document.querySelector('main')
    const returnState = {
      scope,
      sectorType,
      page,
      search, // 记录原始 search（非 debounced），返回后同步设置 debouncedSearch 避免闪烁
      scrollX: 0,
      scrollY: main ? main.scrollTop : window.scrollY,
    }
    window.sessionStorage.setItem(
      RETURN_STATE_STORAGE_KEY,
      JSON.stringify(returnState)
    )
    router.push(
      `/dashboard/funds/reverse-lookup?symbol=${encodeURIComponent(
        stockSymbol
      )}&from=fund-crowd`
    )
  }

  // AC-07 空状态：持仓数据未同步
  if (isPortfolioEmpty) {
    return (
      <div className="space-y-6">
        <header className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-foreground">基金扎堆分析</h1>
            <p className="text-sm text-muted-foreground mt-1">
              数据来源：基金定期报告披露的十大重仓股（按报告期聚合，仅供参考）
            </p>
          </div>
        </header>
        <div
          className="bg-card rounded-xl border border-border shadow-sm p-12 text-center"
          data-testid="crowd-empty-portfolio"
        >
          <p className="text-lg font-medium text-foreground mb-2">
            暂无基金持仓数据
          </p>
          <p className="text-sm text-muted-foreground">
            请联系管理员同步基金持仓数据
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* 标题 + 口径切换 + 报告期标识 */}
      <header className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-foreground">基金扎堆分析</h1>
          <p className="text-sm text-muted-foreground mt-1">
            数据来源：基金定期报告披露的十大重仓股（按报告期聚合，仅供参考）
          </p>
        </div>
        <div className="flex items-center gap-3">
          {rankings?.currentPeriod && (
            <span className="text-sm text-muted-foreground whitespace-nowrap">
              报告期 {rankings.currentPeriod}
            </span>
          )}
          <CrowdScopeSelector value={scope} onChange={handleScopeChange} />
        </div>
      </header>

      {/* 板块分布（AC-04，sector_type 切换联动分布图 + 排行榜分类列） */}
      <section className="bg-card rounded-xl border border-border shadow-sm p-4">
        <div className="flex items-center justify-between gap-3 mb-3">
          <h2
            data-testid="crowd-distribution-title"
            className="text-base font-semibold text-foreground"
          >
            {SECTOR_TYPE_LABELS[sectorType]}分布（按扎堆股数量占比）
          </h2>
          <CrowdSectorTypeSelector
            value={sectorType}
            onChange={handleSectorTypeChange}
          />
        </div>
        <CrowdIndustryDistribution
          distribution={distribution}
          isLoading={isIndustryLoading}
          sectorTypeLabel={SECTOR_TYPE_LABELS[sectorType]}
        />
      </section>

      {/* 排行榜（AC-01/02/03/06/08） */}
      <section className="bg-card rounded-xl border border-border shadow-sm p-4 space-y-4">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-base font-semibold text-foreground">
            扎堆度排行榜
            {rankings && rankings.total > 0 && (
              <span className="ml-2 text-sm text-muted-foreground">
                共 {rankings.total} 只
              </span>
            )}
          </h2>
        </div>

        {isError ? (
          <div className="p-8 text-center text-sm text-muted-foreground">
            加载失败，请重试
          </div>
        ) : (
          <CrowdRankingTable
            items={rankings?.items ?? []}
            total={rankings?.total ?? 0}
            page={rankings?.page ?? page}
            pageSize={rankings?.pageSize ?? DEFAULT_PAGE_SIZE}
            isLoading={isLoading}
            isError={isError}
            hasPrevPeriod={rankings?.hasPrevPeriod ?? false}
            search={search}
            sectorTypeLabel={SECTOR_TYPE_LABELS[sectorType]}
            onSearchChange={setSearch}
            onPageChange={handlePageChange}
            onPageSizeChange={handlePageSizeChange}
            onReverseLookup={handleReverseLookup}
          />
        )}
      </section>
    </div>
  )
}
