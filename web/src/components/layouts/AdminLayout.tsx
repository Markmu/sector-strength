"use client";

import React from 'react';
import { ShieldAlert } from 'lucide-react';
import { useRequireAdmin, useAdminCheck } from '@/hooks/useRequireAdmin';
import Button from '@/components/ui/Button';

interface AdminLayoutProps {
  children: React.ReactNode;
}

/**
 * 管理员布局组件
 *
 * 包含权限检查，只允许管理员用户访问。
 * 非管理员用户会看到 403 禁止访问页面。
 *
 * @example
 * ```tsx
 * <AdminLayout>
 *   <AdminDashboard />
 * </AdminLayout>
 * ```
 */
export default function AdminLayout({ children }: AdminLayoutProps) {
  // 使用 useRequireAdmin 进行权限检查和自动重定向
  useRequireAdmin();

  // 使用 useAdminCheck 获取状态（不重定向）
  const { isAdmin, isLoading, isAuthenticated } = useAdminCheck();

  // 加载状态
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">正在验证权限...</p>
        </div>
      </div>
    );
  }

  // 如果未登录或不是管理员，显示禁止访问页面
  // （useRequireAdmin 会处理重定向，但作为额外保护）
  if (!isAuthenticated || !isAdmin) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full bg-white shadow-lg rounded-lg p-8 text-center">
          <div className="flex justify-center mb-4">
            <div className="p-3 bg-red-100 rounded-full">
              <ShieldAlert className="w-12 h-12 text-red-600" />
            </div>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">访问被拒绝</h1>
          <p className="text-gray-600 mb-6">
            您没有访问此页面的权限。此页面仅限管理员访问。
          </p>
          <div className="space-y-3">
            <Button onClick={() => window.history.back()} variant="outline" className="w-full">
              返回上一页
            </Button>
            <Button
              onClick={() => window.location.href = '/'}
              variant="primary"
              className="w-full"
            >
              返回首页
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // 管理员用户可以访问内容
  return <>{children}</>;
}

/**
 * 带有侧边栏的管理员布局
 * 用于需要侧边栏导航的管理员页面
 */
export function AdminLayoutWithSidebar({
  children,
  sidebar
}: {
  children: React.ReactNode;
  sidebar: React.ReactNode;
}) {
  // 使用 useRequireAdmin 进行权限检查和自动重定向
  useRequireAdmin();

  // 使用 useAdminCheck 获取状态
  const { isAdmin, isLoading } = useAdminCheck();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">正在验证权限...</p>
        </div>
      </div>
    );
  }

  if (!isAdmin) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full bg-white shadow-lg rounded-lg p-8 text-center">
          <div className="flex justify-center mb-4">
            <div className="p-3 bg-red-100 rounded-full">
              <ShieldAlert className="w-12 h-12 text-red-600" />
            </div>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">访问被拒绝</h1>
          <p className="text-gray-600 mb-6">此页面仅限管理员访问。</p>
          <Button onClick={() => window.location.href = '/'} variant="primary">
            返回首页
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-gray-50">
      {sidebar}
      <main className="flex-1 overflow-y-auto p-6">
        {children}
      </main>
    </div>
  );
}
