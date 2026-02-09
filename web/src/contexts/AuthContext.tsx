"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { AUTH_EXPIRED_EVENT } from '@/lib/authRedirect';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface User {
  id: string;
  email: string;
  username: string | null;
  is_active: boolean;
  role?: string;
}

interface AuthContextType {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  tokenType: string | null;
  isLoading: boolean;
  login: (email: string, password: string, rememberMe?: boolean) => Promise<void>;
  logout: () => Promise<void>;
  refreshAccessToken: () => Promise<void>;
  isAuthenticated: boolean;
  isAdmin: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: React.ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState<string | null>(null);
  const [tokenType, setTokenType] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const clearAuth = useCallback(() => {
    setUser(null);
    setAccessToken(null);
    setRefreshToken(null);
    setTokenType(null);
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('tokenType');
    localStorage.removeItem('expiresIn');
    localStorage.removeItem('user');
  }, []);

  // 从localStorage初始化认证状态
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        const savedAccessToken = localStorage.getItem('accessToken');
        const savedRefreshToken = localStorage.getItem('refreshToken');
        const savedTokenType = localStorage.getItem('tokenType');
        const savedUser = localStorage.getItem('user');
        const savedExpiresIn = localStorage.getItem('expiresIn');

        if (savedAccessToken && savedRefreshToken && savedTokenType && savedUser) {
          setAccessToken(savedAccessToken);
          setRefreshToken(savedRefreshToken);
          setTokenType(savedTokenType);
          setUser(JSON.parse(savedUser));

          // 检查token是否过期
          if (savedExpiresIn) {
            const expiresIn = parseInt(savedExpiresIn);
            const now = Date.now();
            const tokenExpiry = now + expiresIn * 1000;

            // 如果token将在5分钟内过期，尝试刷新
            if (tokenExpiry - now < 5 * 60 * 1000) {
              await refreshAccessToken();
            }
          }
        }
      } catch (error) {
        console.error('Failed to initialize auth:', error);
        clearAuth();
      } finally {
        setIsLoading(false);
      }
    };

    initializeAuth();
  }, []);

  useEffect(() => {
    const handleAuthExpired = () => {
      clearAuth();
    };

    window.addEventListener(AUTH_EXPIRED_EVENT, handleAuthExpired);
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, handleAuthExpired);
  }, [clearAuth]);

  // 刷新访问令牌
  const refreshAccessToken = useCallback(async () => {
    if (!refreshToken) return;

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          refresh_token: refreshToken
        })
      });

      if (response.ok) {
        const data = await response.json();
        setAccessToken(data.access_token);
        setRefreshToken(data.refresh_token);
        localStorage.setItem('accessToken', data.access_token);
        localStorage.setItem('refreshToken', data.refresh_token);
        localStorage.setItem('expiresIn', data.expires_in.toString());
      } else {
        // 刷新失败，需要重新登录
        throw new Error('Token refresh failed');
      }
    } catch (error) {
      console.error('Failed to refresh access token:', error);
      clearAuth();
      throw error;
    }
  }, [refreshToken]);

  // 检查token是否过期并刷新
  useEffect(() => {
    if (!accessToken || !refreshToken) return;

    const interval = setInterval(async () => {
      try {
        const now = Date.now();
        const savedExpiresIn = localStorage.getItem('expiresIn');

        if (savedExpiresIn) {
          const expiresIn = parseInt(savedExpiresIn);
          const tokenExpiry = now + expiresIn * 1000;

          // 如果token将在10分钟内过期，刷新它
          if (tokenExpiry - now < 10 * 60 * 1000) {
            await refreshAccessToken();
          }
        }
      } catch (error) {
        console.error('Auto token refresh failed:', error);
      }
    }, 60000); // 每分钟检查一次

    return () => clearInterval(interval);
  }, [accessToken, refreshToken, refreshAccessToken]);

  const login = async (email: string, password: string, rememberMe = false) => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          email,
          password,
          remember_me: rememberMe
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        // 后端返回的格式是 { error: { message: "..." } }
        const errorMessage = errorData.error?.message || errorData.detail || '登录失败，请检查邮箱和密码';
        throw new Error(errorMessage);
      }

      const data = await response.json();

      setAccessToken(data.access_token);
      setRefreshToken(data.refresh_token);
      setTokenType(data.token_type);
      setUser(data.user);

      // 保存到localStorage
      localStorage.setItem('accessToken', data.access_token);
      localStorage.setItem('refreshToken', data.refresh_token);
      localStorage.setItem('tokenType', data.token_type);
      localStorage.setItem('expiresIn', data.expires_in.toString());
      localStorage.setItem('user', JSON.stringify(data.user));

      router.push('/');
    } catch (error) {
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    if (!refreshToken) {
      clearAuth();
      router.push('/login');
      return;
    }

    try {
      // 调用后端注销API
      await fetch(`${API_BASE_URL}/api/v1/auth/logout`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `${tokenType} ${accessToken}`
        },
        body: JSON.stringify({
          refresh_token: refreshToken
        })
      });
    } catch (error) {
      console.error('Logout API call failed:', error);
    } finally {
      clearAuth();
      router.push('/login');
    }
  };

  const value: AuthContextType = {
    user,
    accessToken,
    refreshToken,
    tokenType,
    isLoading,
    login,
    logout,
    refreshAccessToken,
    isAuthenticated: !!user && !!accessToken,
    isAdmin: !!user && user.role === 'admin'
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
