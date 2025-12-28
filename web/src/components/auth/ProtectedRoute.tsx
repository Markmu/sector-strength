"use client";

import React from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import Loading from '@/components/ui/Loading';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRoles?: string[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requiredRoles = []
}) => {
  const { isAuthenticated, isLoading, user } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  React.useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        // 保存当前路径，登录后可以跳转回来
        router.push(`/login?redirect=${encodeURIComponent(pathname)}`);
      }
    }
  }, [isAuthenticated, isLoading, router, pathname]);

  // 检查角色权限
  const hasRequiredRole = requiredRoles.length === 0 ||
    (user && requiredRoles.some(role => user.role === role));

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loading />
      </div>
    );
  }

  if (!isAuthenticated) {
    return null; // 重定向到登录页，不显示任何内容
  }

  if (!hasRequiredRole) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-4">访问被拒绝</h1>
          <p className="text-gray-600">您没有权限访问此页面</p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
};

// HOC组件，方便使用
export const withAuth = <P extends object>(
  Component: React.ComponentType<P>,
  options: { requiredRoles?: string[] } = {}
) => {
  return function AuthenticatedComponent(props: P) {
    return (
      <ProtectedRoute requiredRoles={options.requiredRoles}>
        <Component {...props} />
      </ProtectedRoute>
    );
  };
};