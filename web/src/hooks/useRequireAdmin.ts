"use client";

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../contexts/AuthContext';

/**
 * 管理员权限检查 Hook
 *
 * 验证当前用户是否为管理员，如果不是则重定向到 403 页面或首页。
 *
 * @param redirectTo - 重定向目标路径，默认为 '/403'
 *
 * @example
 * ```tsx
 * function AdminPage() {
 *   useRequireAdmin();
 *   return <div>Admin Content</div>;
 * }
 * ```
 */
export function useRequireAdmin(redirectTo: string = '/403'): void {
  const { isAdmin, isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    // 如果还在加载中，不执行任何操作
    if (isLoading) {
      return;
    }

    // 如果未登录，重定向到登录页
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }

    // 如果已登录但不是管理员，重定向到 403 页面
    if (!isAdmin) {
      router.push(redirectTo);
      return;
    }
  }, [isAdmin, isAuthenticated, isLoading, router, redirectTo]);
}

/**
 * 检查用户是否为管理员的 Hook（不重定向）
 *
 * @returns {Object} 包含 isAdmin, isLoading, isAuthenticated 状态
 *
 * @example
 * ```tsx
 * function MyComponent() {
 *   const { isAdmin, isLoading } = useAdminCheck();
 *
 *   if (isLoading) return <Loading />;
 *   if (!isAdmin) return <p>Access Denied</p>;
 *
 *   return <div>Admin Content</div>;
 * }
 * ```
 */
export function useAdminCheck() {
  const { isAdmin, isAuthenticated, isLoading, user } = useAuth();

  return {
    isAdmin,
    isAuthenticated,
    isLoading,
    user
  };
}

/**
 * 从后端 API 验证管理员权限
 *
 * 直接调用 /api/admin/check 端点验证权限，而不是依赖本地状态。
 *
 * @returns {Object} 包含 isAdmin, isLoading, error 状态
 *
 * @example
 * ```tsx
 * function SecureAdminPage() {
 *   const { isAdmin, isLoading, error } = useVerifyAdmin();
 *
 *   if (isLoading) return <Loading />;
 *   if (error || !isAdmin) return <p>Access Denied</p>;
 *
 *   return <div>Secure Admin Content</div>;
 * }
 * ```
 */
export function useVerifyAdmin() {
  const { accessToken, tokenType, isAuthenticated } = useAuth();
  const [isAdmin, setIsAdmin] = useState<boolean | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const verifyAdmin = useCallback(async () => {
    if (!isAuthenticated || !accessToken) {
      setIsAdmin(false);
      setIsLoading(false);
      return;
    }

    try {
      const response = await fetch(`/api/v1/admin/check`, {
        method: 'GET',
        headers: {
          'Authorization': `${tokenType} ${accessToken}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setIsAdmin(data.data.is_admin);
      } else {
        setIsAdmin(false);
        setError('Failed to verify admin permissions');
      }
    } catch (err) {
      setIsAdmin(false);
      setError('Network error while verifying permissions');
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated, accessToken, tokenType]);

  useEffect(() => {
    verifyAdmin();
  }, [verifyAdmin]);

  return { isAdmin, isLoading, error };
}
