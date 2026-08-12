'use client'

/**
 * 股东分析面板主页面（plan-04）
 *
 * 页面状态：
 * - reportPeriod: 当前选中报告期（默认 null → useShareholderOverview 不传 period 取后端最新期）
 * - selectedGroupIds: 当前选中监控组（多选）
 *
 * 布局：
 * 1. 标题 + 报告期选择器
 * 2. 监控组概览卡片
 * 3. 持仓详情区（仅选中组时展示）
 *
 * 交互：
 * - 首次加载 → overview（默认最新期）→ 渲染概览卡片，详情区展示"请选择监控组"
 * - 点击组 → 更新 selectedGroupIds → HoldingsDetail 加载
 * - 切换报告期 → 清空 selectedGroupIds → 重载 overview
 * - 空 report_periods → "暂无股东数据，请联系管理员同步数据"
 */
import React, { useMemo, useState } from 'react'
import { useShareholderOverview } from '@/hooks/useShareholderAnalysis'
import ReportPeriodSelector from './ReportPeriodSelector'
import GroupOverviewCards from './GroupOverviewCards'
import HoldingsDetail from './HoldingsDetail'
import HolderSearchBar from './HolderSearchBar'

export default function ShareholderAnalysisPage() {
  const [reportPeriod, setReportPeriod] = useState<string | null>(null)
  const [selectedGroupIds, setSelectedGroupIds] = useState<number[]>([])
  // 单股东维度（与监控组互斥：选股东清空监控组，选监控组清空股东）
  const [selectedHolderName, setSelectedHolderName] = useState<string | null>(
    null
  )

  // overview（reportPeriod=null 时取后端默认最新期）
  const { overview, isLoading, isError } = useShareholderOverview(
    reportPeriod ?? undefined
  )

  // 后端返回的最新期，作为未选择时的 fallback currentPeriod
  const effectivePeriod =
    reportPeriod ?? overview?.currentPeriod ?? ''
  const hasPrevPeriod = overview?.hasPrevPeriod ?? false

  // 切换报告期 → 清空选中组与股东
  const handlePeriodChange = (period: string) => {
    setReportPeriod(period)
    setSelectedGroupIds([])
    setSelectedHolderName(null)
  }

  // 选中股东 → 清空监控组（互斥）
  const handleHolderSelect = (holderName: string) => {
    setSelectedHolderName(holderName)
    setSelectedGroupIds([])
  }

  // 选中监控组 → 清空股东（互斥）
  const handleGroupSelect = (groupIds: number[]) => {
    setSelectedHolderName(null)
    setSelectedGroupIds(groupIds)
  }

  const isEmpty =
    !isLoading && !isError && overview && overview.reportPeriods.length === 0

  // 选中的组 id（用于详情查询）
  const sortedSelectedGroupIds = useMemo(
    () => [...selectedGroupIds].sort((a, b) => a - b),
    [selectedGroupIds]
  )

  return (
    <div className="space-y-6">
      {/* 标题 + 报告期选择器 */}
      <header className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-foreground">股东分析</h1>
          <p className="text-sm text-muted-foreground mt-1">
            数据来源：十大流通股东（报告期数据，仅供参考）
          </p>
        </div>
        {overview && overview.reportPeriods.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground whitespace-nowrap">
              报告期
            </span>
            <ReportPeriodSelector
              periods={overview.reportPeriods}
              value={reportPeriod ?? overview.currentPeriod}
              onChange={handlePeriodChange}
            />
          </div>
        )}
      </header>

      {/* 加载态 */}
      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary mx-auto mb-3" />
            <p className="text-sm text-muted-foreground">加载中...</p>
          </div>
        </div>
      )}

      {/* 错误态 */}
      {isError && (
        <div className="bg-card rounded-xl border border-warning/30 p-8 text-center">
          <p className="text-base font-medium text-warning mb-1">
            加载失败，请重试
          </p>
          <p className="text-sm text-muted-foreground">
            网络请求异常，请检查网络连接后刷新页面
          </p>
        </div>
      )}

      {/* 空状态：无股东数据（AC-08 / L3） */}
      {isEmpty && (
        <div className="bg-card rounded-xl border border-border shadow-sm p-12 text-center">
          <p className="text-lg font-medium text-foreground mb-2">
            暂无股东数据
          </p>
          <p className="text-sm text-muted-foreground">
            请联系管理员同步数据
          </p>
        </div>
      )}

      {/* 主体内容 */}
      {!isLoading && !isError && overview && overview.reportPeriods.length > 0 && (
        <>
          {/* 股东搜索框（单股东持仓查询入口，与监控组互斥） */}
          <HolderSearchBar
            value={selectedHolderName}
            onHolderSelect={handleHolderSelect}
            onClear={() => setSelectedHolderName(null)}
          />

          {/* 监控组概览卡片 */}
          <GroupOverviewCards
            groups={overview.groups}
            selectedGroupIds={selectedGroupIds}
            onGroupSelect={handleGroupSelect}
            hasPrevPeriod={hasPrevPeriod}
          />

          {/* 持仓详情区：单股东维度优先，否则监控组维度 */}
          {selectedHolderName ? (
            <HoldingsDetail
              key={`holder__${effectivePeriod}__${selectedHolderName}`}
              holderName={selectedHolderName}
              reportPeriod={effectivePeriod}
              hasPrevPeriod={hasPrevPeriod}
            />
          ) : sortedSelectedGroupIds.length > 0 ? (
            <HoldingsDetail
              key={`${effectivePeriod}__${sortedSelectedGroupIds.join(',')}`}
              groupIds={sortedSelectedGroupIds}
              reportPeriod={effectivePeriod}
              hasPrevPeriod={hasPrevPeriod}
            />
          ) : (
            <div className="bg-card rounded-xl border border-dashed border-border p-12 text-center">
              <p className="text-base font-medium text-muted-foreground">
                请选择监控组或搜索股东
              </p>
              <p className="text-sm text-muted-foreground mt-1">
                点击上方监控组卡片，或在搜索框输入股东名称查看持仓详情
              </p>
            </div>
          )}
        </>
      )}
    </div>
  )
}
