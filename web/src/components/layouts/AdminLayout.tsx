"use client";

import React from 'react';
import { Menu, ShieldAlert } from 'lucide-react';
import { useRequireAdmin, useAdminCheck } from '@/hooks/useRequireAdmin';
import Button from '@/components/ui/Button';
import { ThemeToggle } from '@/components/ui/ThemeToggle';

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
      <div className="min-h-[100dvh] flex items-center justify-center bg-background">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">正在验证权限...</p>
        </div>
      </div>
    );
  }

  // 如果未登录或不是管理员，显示禁止访问页面
  // （useRequireAdmin 会处理重定向，但作为额外保护）
  if (!isAuthenticated || !isAdmin) {
    return (
      <div className="min-h-[100dvh] flex items-center justify-center bg-background">
        <div className="max-w-md w-full bg-card shadow-lg rounded-lg p-8 text-center">
          <div className="flex justify-center mb-4">
            <div className="p-3 bg-destructive/10 rounded-full">
              <ShieldAlert className="w-12 h-12 text-destructive" />
            </div>
          </div>
          <h1 className="text-2xl font-bold text-foreground mb-2">访问被拒绝</h1>
          <p className="text-muted-foreground mb-6">
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
  const [sidebarOpen, setSidebarOpen] = React.useState(false);

  if (isLoading) {
    return (
      <div className="min-h-[100dvh] flex items-center justify-center bg-background">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">正在验证权限...</p>
        </div>
      </div>
    );
  }

  if (!isAdmin) {
    return (
      <div className="min-h-[100dvh] flex items-center justify-center bg-background">
        <div className="max-w-md w-full bg-card shadow-lg rounded-lg p-8 text-center">
          <div className="flex justify-center mb-4">
            <div className="p-3 bg-destructive/10 rounded-full">
              <ShieldAlert className="w-12 h-12 text-destructive" />
            </div>
          </div>
          <h1 className="text-2xl font-bold text-foreground mb-2">访问被拒绝</h1>
          <p className="text-muted-foreground mb-6">此页面仅限管理员访问。</p>
          <Button onClick={() => window.location.href = '/'} variant="primary">
            返回首页
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-[100dvh] bg-background">
      {sidebarOpen && (
        <button
          type="button"
          className="fixed inset-0 z-30 bg-foreground/24 md:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-label="关闭导航"
        />
      )}
      <div className={`fixed inset-y-0 left-0 z-40 transition-transform duration-200 md:static md:z-auto md:translate-x-0 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        {sidebar}
      </div>
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex h-14 flex-shrink-0 items-center justify-between border-b border-border bg-card px-3 sm:px-4 md:px-5">
          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={() => setSidebarOpen(true)}
              className="inline-flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground md:hidden"
              aria-label="打开导航"
            >
              <Menu className="h-5 w-5" />
            </button>
            <span className="text-xs font-medium text-muted-foreground">管理控制台</span>
          </div>
          <ThemeToggle compact />
        </div>
        <main className="custom-scrollbar min-w-0 flex-1 overflow-y-auto p-4 md:p-5">
          <div className="mx-auto max-w-[1600px]">{children}</div>
        </main>
      </div>
    </div>
  );
}
