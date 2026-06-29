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

type DataTab =
  | 'data-status'
  | 'init'
  | 'ma-calc'
  | 'strength-calc'
  | 'broker-recommend';

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
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex gap-4 flex-wrap">
          <button
            data-testid="tab-data-status"
            onClick={() => setActiveTab('data-status')}
            className={`px-4 py-2 font-medium border-b-2 transition-colors ${
              activeTab === 'data-status'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            ● 数据状态
          </button>
          <button
            data-testid="tab-init"
            onClick={() => setActiveTab('init')}
            className={`px-4 py-2 font-medium border-b-2 transition-colors ${
              activeTab === 'init'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            数据初始化
          </button>
          <button
            data-testid="tab-ma-calc"
            onClick={() => setActiveTab('ma-calc')}
            className={`px-4 py-2 font-medium border-b-2 transition-colors ${
              activeTab === 'ma-calc'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            板块均线计算
          </button>
          <button
            data-testid="tab-strength-calc"
            onClick={() => setActiveTab('strength-calc')}
            className={`px-4 py-2 font-medium border-b-2 transition-colors ${
              activeTab === 'strength-calc'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            板块强度计算
          </button>
          <button
            data-testid="tab-broker-recommend"
            onClick={() => setActiveTab('broker-recommend')}
            className={`px-4 py-2 font-medium border-b-2 transition-colors ${
              activeTab === 'broker-recommend'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            券商金股同步
          </button>
        </nav>
      </div>

      {/* 内容区域 */}
      {activeTab === 'data-status' && <DataStatusPanel />}
      {activeTab === 'init' && <DataInitPanel />}
      {activeTab === 'ma-calc' && <SectorMACalculationPanel />}
      {activeTab === 'strength-calc' && <SectorStrengthCalculationPanel />}
      {activeTab === 'broker-recommend' && <BrokerRecommendSyncPanel />}
    </AdminLayoutWithSidebar>
  );
}
