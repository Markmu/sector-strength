"use client";

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import {
  LayoutDashboard,
  Database,
  ListTodo,
  Users,
  ChevronLeft,
  ChevronRight,
  Activity,
  LogOut,
  Landmark,
  ArrowLeft,
  UserCheck,
  BarChart3,
} from 'lucide-react';

/**
 * 管理员侧边栏导航项
 */
interface NavItem {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  href: string;
  description?: string;
}

const navItems: NavItem[] = [
  {
    id: 'dashboard',
    label: '仪表板',
    icon: LayoutDashboard,
    href: '/dashboard/admin',
    description: '系统概览和统计',
  },
  {
    id: 'data',
    label: '数据管理',
    icon: Database,
    href: '/dashboard/admin/data',
    description: '数据初始化和更新',
  },
  {
    id: 'tasks',
    label: '任务监控',
    icon: ListTodo,
    href: '/dashboard/admin/tasks',
    description: '异步任务状态和日志',
  },
  {
    id: 'fund-init',
    label: '基金同步',
    icon: Landmark,
    href: '/dashboard/admin/fund-init',
    description: '基金数据采集和同步',
  },
  {
    id: 'top10-holder-init',
    label: '股票持仓同步',
    icon: UserCheck,
    href: '/dashboard/admin/top10-holder-init',
    description: '十大流通股东数据采集和同步',
  },
  {
    id: 'etf-init',
    label: 'ETF 数据同步',
    icon: BarChart3,
    href: '/dashboard/admin/etf-init',
    description: 'ETF 份额采集与历史回填',
  },
  {
    id: 'shareholder-groups',
    label: '股东分组管理',
    icon: Users,
    href: '/dashboard/admin/shareholder-groups',
    description: '股东分组和匹配规则管理',
  },
  {
    id: 'users',
    label: '用户管理',
    icon: Users,
    href: '/dashboard/admin/users',
    description: '用户和权限管理',
  },
];

/**
 * 管理员侧边栏组件
 */
interface AdminSidebarProps {
  className?: string;
}

export default function AdminSidebar({ className = '' }: AdminSidebarProps) {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();
  const { logout } = useAuth();

  return (
    <aside
      className={`
        flex flex-col bg-card border-r border-border
        transition-all duration-300
        ${collapsed ? 'w-16' : 'w-64'}
        ${className}
      `}
    >
      {/* Logo - 点击回到主仪表板 */}
      <div className="flex items-center justify-between h-16 px-4 border-b border-border gap-1">
        <Link
          href="/dashboard"
          className={`
            group flex items-center gap-2 rounded-lg transition-colors
            hover:bg-secondary
            ${collapsed ? 'p-1.5 flex-1 justify-center' : 'flex-1 min-w-0 px-2 py-1.5'}
          `}
          title="返回主仪表板"
          aria-label="返回主仪表板"
        >
          <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center flex-shrink-0">
            <Activity className="w-5 h-5 text-white" />
          </div>
          {!collapsed && (
            <>
              <span className="font-semibold text-foreground truncate">管理控制台</span>
              <ArrowLeft className="w-4 h-4 text-muted-foreground ml-auto flex-shrink-0 transition-transform group-hover:-translate-x-0.5" />
            </>
          )}
        </Link>
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-1.5 hover:bg-secondary rounded-lg transition-colors flex-shrink-0"
          title={collapsed ? '展开' : '收起'}
          aria-label={collapsed ? '展开侧边栏' : '收起侧边栏'}
        >
          {collapsed ? (
            <ChevronRight className="w-5 h-5 text-muted-foreground" />
          ) : (
            <ChevronLeft className="w-5 h-5 text-muted-foreground" />
          )}
        </button>
      </div>

      {/* 导航菜单 */}
      <nav className="flex-1 overflow-y-auto py-4 px-2 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          // 精确匹配：优先完全匹配，其次匹配以 / 结尾的路径（避免父路径误高亮）
          const isActive = pathname === item.href ||
            (pathname.startsWith(item.href + '/') && item.href !== '/dashboard/admin');

          return (
            <Link
              key={item.id}
              href={item.href}
              className={`
                flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors
                ${isActive
                  ? 'bg-primary-light text-primary'
                  : 'text-foreground hover:bg-secondary'
                }
                ${collapsed ? 'justify-center' : ''}
              `}
              title={collapsed ? item.label : item.description}
            >
              <Icon className={`w-5 h-5 flex-shrink-0 ${isActive ? 'text-primary' : 'text-muted-foreground'}`} />
              {!collapsed && (
                <div className="flex-1 min-w-0">
                  <div className="font-medium truncate">{item.label}</div>
                  {!collapsed && item.description && (
                    <div className="text-xs text-muted-foreground truncate">{item.description}</div>
                  )}
                </div>
              )}
            </Link>
          );
        })}
      </nav>

      {/* 底部退出登录 */}
      <div className="p-2 border-t border-border">
        <button
          onClick={logout}
          className={`
            w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors
            ${collapsed ? 'justify-center' : ''}
            text-destructive hover:bg-destructive/10
          `}
          title={collapsed ? '退出登录' : '退出登录'}
        >
          <LogOut className="w-5 h-5 flex-shrink-0" />
          {!collapsed && <span className="font-medium">退出登录</span>}
        </button>
      </div>
    </aside>
  );
}
