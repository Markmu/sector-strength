'use client';

import { useState } from 'react';
import { DashboardHeader } from '@/components/dashboard';
import AdminSidebar from '@/components/admin/AdminSidebar';
import { AdminLayoutWithSidebar } from '@/components/layouts/AdminLayout';
import DataInitPanel from '@/components/admin/DataInitPanel';
import SectorMACalculationPanel from '@/components/admin/SectorMACalculationPanel';
import SectorStrengthCalculationPanel from '@/components/admin/SectorStrengthCalculationPanel';
import DataStatusPanel from '@/components/admin/DataStatusPanel';
import BrokerRecommendSyncPanel from '@/components/admin/BrokerRecommendSyncPanel';
import IndexSyncPanel from '@/components/index-monitor/IndexSyncPanel';
import MarketMetricsSyncPanel from '@/components/market-metrics/MarketMetricsSyncPanel';
import MarginSyncPanel from '@/components/market-margin/MarginSyncPanel';

type DataTab =
  | 'data-status'
  | 'init'
  | 'ma-calc'
  | 'strength-calc'
  | 'broker-recommend'
  | 'index-data'
  | 'market-metrics'
  | 'market-margin';

/**
 * 数据管理页面
 */
export default function DataManagementPage() {
  const [activeTab, setActiveTab] = useState<DataTab>('data-status');

  return (
    <AdminLayoutWithSidebar sidebar={<AdminSidebar />}>
      <DashboardHeader
        title="数据管理"
        subtitle="数据初始化和计算管理"
      />

      {/* Tab 切换 */}
      <div className="border-b border-border mb-6">
        <nav className="flex gap-4 flex-wrap">
          <button
            data-testid="tab-data-status"
            onClick={() => setActiveTab('data-status')}
            className={`px-4 py-2 font-medium border-b-2 transition-colors ${
              activeTab === 'data-status'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            数据状态
          </button>
          <button
            data-testid="tab-init"
            onClick={() => setActiveTab('init')}
            className={`px-4 py-2 font-medium border-b-2 transition-colors ${
              activeTab === 'init'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            数据初始化
          </button>
          <button
            data-testid="tab-ma-calc"
            onClick={() => setActiveTab('ma-calc')}
            className={`px-4 py-2 font-medium border-b-2 transition-colors ${
              activeTab === 'ma-calc'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            板块均线计算
          </button>
          <button
            data-testid="tab-strength-calc"
            onClick={() => setActiveTab('strength-calc')}
            className={`px-4 py-2 font-medium border-b-2 transition-colors ${
              activeTab === 'strength-calc'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            板块强度计算
          </button>
          <button
            data-testid="tab-broker-recommend"
            onClick={() => setActiveTab('broker-recommend')}
            className={`px-4 py-2 font-medium border-b-2 transition-colors ${
              activeTab === 'broker-recommend'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            券商金股同步
          </button>
          <button
            data-testid="tab-index-data"
            onClick={() => setActiveTab('index-data')}
            className={`px-4 py-2 font-medium border-b-2 transition-colors ${
              activeTab === 'index-data'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            指数数据
          </button>
          <button
            data-testid="tab-market-metrics"
            onClick={() => setActiveTab('market-metrics')}
            className={`px-4 py-2 font-medium border-b-2 transition-colors ${
              activeTab === 'market-metrics'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            市场量价
          </button>
          <button
            data-testid="tab-market-margin"
            onClick={() => setActiveTab('market-margin')}
            className={`px-4 py-2 font-medium border-b-2 transition-colors ${
              activeTab === 'market-margin'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            融资融券
          </button>
        </nav>
      </div>

      {/* 内容区域 */}
      {activeTab === 'data-status' && <DataStatusPanel />}
      {activeTab === 'init' && <DataInitPanel />}
      {activeTab === 'ma-calc' && <SectorMACalculationPanel />}
      {activeTab === 'strength-calc' && <SectorStrengthCalculationPanel />}
      {activeTab === 'broker-recommend' && <BrokerRecommendSyncPanel />}
      {activeTab === 'index-data' && <IndexSyncPanel />}
      {activeTab === 'market-metrics' && <MarketMetricsSyncPanel />}
      {activeTab === 'market-margin' && <MarginSyncPanel />}
    </AdminLayoutWithSidebar>
  );
}
