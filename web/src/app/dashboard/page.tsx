'use client';

import { DashboardLayout, DashboardHeader, DashboardContent, SectorHeatmap, RankingSection, RankingTabs, MarketIndexDisplay } from '@/components/dashboard';
import { Card, CardBody } from '@/components/ui';
import { Disclaimer } from '@/components/ui/Disclaimer';
import { useSWRConfig } from 'swr';
import Link from 'next/link';
import { BarChart3Icon } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import IndexMonitorPage from '@/components/index-monitor/IndexMonitorPage';
import MarketMetricsPanel from '@/components/market-metrics/MarketMetricsPanel';
import MarginPanel from '@/components/market-margin/MarginPanel';

/**
 * Dashboard Page
 * 主仪表板页面：管理员看关键指数监控面板（AC-01/11），非管理员看原有通用内容。
 */
export default function DashboardPage() {
  const { mutate } = useSWRConfig();
  const { isAdmin, isLoading } = useAuth();

  // 手动刷新所有 dashboard 数据
  const handleRefresh = () => {
    // 刷新所有匹配 /api/v1/* 的数据
    mutate(
      (key) => typeof key === 'string' && key.startsWith('/api/v1/'),
      undefined,
      { revalidate: true }
    );
  };

  return (
    <DashboardLayout>
      {isAdmin ? (
        // 管理员：关键指数监控面板（plan-04，AC-01/11）
        <DashboardContent>
          <IndexMonitorPage />
        </DashboardContent>
      ) : (
        // 非管理员：原有通用内容（AC-11）
        <>
          <DashboardHeader
            title="仪表板"
            subtitle="实时监控股市板块强度，发现投资机会"
            onRefresh={handleRefresh}
          />
          <DashboardContent>
            {/* 快捷入口 */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <Link href="/dashboard/funds" className="group">
                <Card variant="outlined" className="hover:shadow-md hover:border-primary/50 transition-all h-full">
                  <CardBody className="p-4 flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                      <BarChart3Icon className="w-5 h-5 text-primary" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-foreground text-sm group-hover:text-primary transition-colors">
                        基金分析
                      </h3>
                      <p className="text-xs text-muted-foreground">查看基金列表与持仓明细</p>
                    </div>
                  </CardBody>
                </Card>
              </Link>
            </div>

            {/* 市场量价面板（plan-07）：快捷入口后、市场强度前。
                isLoading 期间 AuthContext 首帧 user=null → isAdmin 不可靠，
                故等认证就绪后再渲染，避免管理员首页过渡帧误显普通分支面板。 */}
            {!isLoading && <MarketMetricsPanel />}

            {/* 融资融券面板（17 期 plan-07）：市场量价面板后、市场强度前，
                仅普通用户首页（spec REQ-7 冻结，管理员 IndexMonitorPage 分支不动）。
                沿用 !isLoading 认证就绪守卫，避免过渡帧误显。 */}
            {!isLoading && <MarginPanel />}

            {/* 市场强度指数 - Story 4-4 实现 */}
            <Card>
              <CardBody className="p-6">
                <h3 className="text-xl font-bold text-foreground mb-4">
                  市场强度指数
                </h3>
                <p className="text-sm text-muted-foreground mb-6">
                  综合指数反映市场整体强弱状态，基于所有板块强度计算。
                </p>
                <MarketIndexDisplay />
              </CardBody>
            </Card>

            {/* 板块热力图 - Story 4-2 实现 */}
            <Card>
              <CardBody className="p-6">
                <h3 className="text-xl font-bold text-foreground mb-4">
                  板块强度热力图
                </h3>
                <p className="text-sm text-muted-foreground mb-6">
                  通过热力图直观查看各板块的强度分布，红色表示强势，绿色表示弱势。
                </p>
                <SectorHeatmap />
              </CardBody>
            </Card>

            {/* 排名列表 - Story 4-3 实现 */}
            <div className="mt-6">
              {/* 桌面端: 双列布局 */}
              <div className="hidden lg:block">
                <RankingSection />
              </div>

              {/* 移动端: Tab 切换 */}
              <div className="lg:hidden">
                <RankingTabs />
              </div>
            </div>

            {/* 免责声明 */}
            <Disclaimer showSeparator={true} />
          </DashboardContent>
        </>
      )}
    </DashboardLayout>
  );
}
