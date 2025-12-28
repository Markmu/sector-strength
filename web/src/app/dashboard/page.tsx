'use client';

import { DashboardLayout, DashboardHeader, DashboardContent, SectorHeatmap, RankingSection, RankingTabs, MarketIndexDisplay } from '@/components/dashboard';
import { Card, CardBody } from '@/components/ui';
import { useSWRConfig } from 'swr';

/**
 * Dashboard Page
 * 主仪表板页面，展示板块强度热力图和排名概览
 */
export default function DashboardPage() {
  const { mutate } = useSWRConfig();

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
      <DashboardHeader
        title="仪表板"
        subtitle="实时监控股市板块强度，发现投资机会"
        onRefresh={handleRefresh}
      />
      <DashboardContent>
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
      </DashboardContent>
    </DashboardLayout>
  );
}
