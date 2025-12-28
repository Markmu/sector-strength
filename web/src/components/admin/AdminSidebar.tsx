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
        flex flex-col bg-white border-r border-gray-200
        transition-all duration-300
        ${collapsed ? 'w-16' : 'w-64'}
        ${className}
      `}
    >
      {/* Logo */}
      <div className="flex items-center justify-between h-16 px-4 border-b border-gray-200">
        {!collapsed && (
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-purple-600 rounded-lg flex items-center justify-center">
              <Activity className="w-5 h-5 text-white" />
            </div>
            <span className="font-semibold text-gray-900">管理控制台</span>
          </div>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
          title={collapsed ? '展开' : '收起'}
        >
          {collapsed ? (
            <ChevronRight className="w-5 h-5 text-gray-500" />
          ) : (
            <ChevronLeft className="w-5 h-5 text-gray-500" />
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
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-700 hover:bg-gray-100'
                }
                ${collapsed ? 'justify-center' : ''}
              `}
              title={collapsed ? item.label : item.description}
            >
              <Icon className={`w-5 h-5 flex-shrink-0 ${isActive ? 'text-blue-600' : 'text-gray-500'}`} />
              {!collapsed && (
                <div className="flex-1 min-w-0">
                  <div className="font-medium truncate">{item.label}</div>
                  {!collapsed && item.description && (
                    <div className="text-xs text-gray-500 truncate">{item.description}</div>
                  )}
                </div>
              )}
            </Link>
          );
        })}
      </nav>

      {/* 底部退出登录 */}
      <div className="p-2 border-t border-gray-200">
        <button
          onClick={logout}
          className={`
            w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors
            ${collapsed ? 'justify-center' : ''}
            text-red-600 hover:bg-red-50
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
