'use client';

import React, { useMemo } from 'react';
import { cn } from '@/lib/utils';
import { Settings, ScatterChart, LineChart, LandmarkIcon, Users, UsersRound, Star, ArrowDownUp, TrendingUp, Flame, Home } from 'lucide-react';
import Layout from '@/components/layout/Layout';
import Sidebar, { SidebarItem } from '@/components/layout/Sidebar';
import { useAuth } from '@/contexts/AuthContext';

export interface DashboardLayoutProps {
  children: React.ReactNode;
  className?: string;
}

// 基础菜单项（所有用户可见）
const baseSidebarItems: SidebarItem[] = [
  {
    title: '首页',
    href: '/dashboard',
    icon: <Home className="w-5 h-5" />,
  },
  {
    title: '强度分析',
    href: '/dashboard/analysis',
    icon: <ScatterChart className="w-5 h-5" />,
  },
  {
    title: '板块分析',
    href: '/dashboard/sector-analysis',
    icon: <LineChart className="w-5 h-5" />,
  },
  {
    title: '板块资金流',
    href: '/dashboard/sector-fund-flow',
    icon: <ArrowDownUp className="w-5 h-5" />,
  },
  {
    title: 'ETF 监控',
    href: '/dashboard/etf-monitor',
    icon: <TrendingUp className="w-5 h-5" />,
  },
  {
    title: '连板天梯',
    href: '/dashboard/limit',
    icon: <Flame className="w-5 h-5" />,
  },
  {
    title: '基金分析',
    href: '/dashboard/funds',
    icon: <LandmarkIcon className="w-5 h-5" />,
  },
  {
    title: '股东分析',
    href: '/dashboard/shareholder-analysis',
    icon: <Users className="w-5 h-5" />,
  },
  {
    title: '基金扎堆分析',
    href: '/dashboard/fund-crowd-analysis',
    icon: <UsersRound className="w-5 h-5" />,
  },
  {
    title: '券商每月荐股',
    href: '/dashboard/broker-recommend-analysis',
    icon: <Star className="w-5 h-5" />,
  },
];

// 管理员专用菜单项
const adminSidebarItems: SidebarItem[] = [
  {
    title: '数据管理',
    href: '/dashboard/admin',
    icon: <Settings className="w-5 h-5" />,
  },
];

/**
 * DashboardLayout - 仪表板主布局组件
 * 包含侧边栏导航和主内容区域
 * 根据用户角色动态显示管理员菜单项
 */
export const DashboardLayout: React.FC<DashboardLayoutProps> = ({
  children,
  className,
}) => {
  const [sidebarCollapsed, setSidebarCollapsed] = React.useState(false);
  const { isAdmin } = useAuth();

  // 根据用户角色动态生成菜单项
  const sidebarItems = useMemo(() => {
    const items = [...baseSidebarItems];
    if (isAdmin) {
      items.push(...adminSidebarItems);
    }
    return items;
  }, [isAdmin]);

  const sidebar = (
    <Sidebar
      items={sidebarItems}
      collapsed={sidebarCollapsed}
      onCollapse={setSidebarCollapsed}
    />
  );

  return (
    <Layout
      sidebar={sidebar}
      sidebarCollapsed={sidebarCollapsed}
      className={cn(
        'animate-fade-in',
        className
      )}
    >
      {children}
    </Layout>
  );
};

DashboardLayout.displayName = 'DashboardLayout';

export default DashboardLayout;
