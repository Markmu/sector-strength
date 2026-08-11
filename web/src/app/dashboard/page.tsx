'use client';

import { DashboardLayout, DashboardHeader, DashboardContent, SectorHeatmap, RankingSection, RankingTabs, MarketIndexDisplay } from '@/components/dashboard';
import { Card, CardBody } from '@/components/ui';
import { Disclaimer } from '@/components/ui/Disclaimer';
import { useSWRConfig } from 'swr';
import Link from 'next/link';
import { BarChart3Icon } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import IndexMonitorPage from '@/components/index-monitor/IndexMonitorPage';

/**
 * Dashboard Page
 * 主仪表板页面：管理员看关键指数监控面板（AC-01/11），非管理员看原有通用内容。
 */
export default function DashboardPage() {
  const { mutate } = useSWRConfig();
  const { isAdmin } = useAuth();

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
                  通过热力图直观查看各板块的强度分布，颜色越绿表示越强势，越红表示越弱势。
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
