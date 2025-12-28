"use client";

import React from 'react';
import { LogOut, User, Settings } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

/**
 * AdminHeader 组件
 *
 * 管理员页面顶部栏，显示用户信息和操作按钮
 *
 * @example
 * ```tsx
 * <AdminHeader
 *   title="管理员控制台"
 *   onLogout={() => {}}
 * />
 * ```
 */

interface AdminHeaderProps {
  /** 页面标题 */
  title?: string;
  /** 子标题 */
  subtitle?: string;
  /** 额外操作按钮 */
  actions?: React.ReactNode;
  /** 自定义类名 */
  className?: string;
}

export default function AdminHeader({
  title = '管理员控制台',
  subtitle,
  actions,
  className = '',
}: AdminHeaderProps) {
  const { user, logout } = useAuth();

  const handleLogout = async () => {
    try {
      await logout();
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  return (
    <header className={`flex items-center justify-between border-b border-gray-200 bg-white px-6 py-4 ${className}`}>
      {/* 左侧：标题 */}
      <div className="flex flex-col">
        <h1 className="text-xl font-semibold text-gray-900">{title}</h1>
        {subtitle && (
          <p className="mt-1 text-sm text-gray-600">{subtitle}</p>
        )}
      </div>

      {/* 右侧：用户信息和操作 */}
      <div className="flex items-center gap-4">
        {/* 额外操作按钮 */}
        {actions && <div className="flex items-center gap-2">{actions}</div>}

        {/* 用户信息 */}
        <div className="flex items-center gap-3 rounded-lg bg-gray-50 px-3 py-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-600">
            <User className="h-4 w-4 text-white" />
          </div>
          <div className="text-sm">
            <div className="font-medium text-gray-900">{user?.email}</div>
            <div className="text-xs text-gray-500">管理员</div>
          </div>
        </div>

        {/* 退出登录按钮 */}
        <button
          onClick={handleLogout}
          className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-100"
          title="退出登录"
        >
          <LogOut className="h-4 w-4" />
          <span className="hidden sm:inline">退出</span>
        </button>
      </div>
    </header>
  );
}
