/**
 * 前端认证组件测试 - 简化版
 * 专注于核心功能测试
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from '@/contexts/AuthContext';

// 模拟 fetch API
global.fetch = jest.fn();

// 包装组件以提供AuthContext
const AuthWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <AuthProvider>
      {children}
    </AuthProvider>
  );
};

describe('AuthContext 核心功能', () => {
  beforeEach(() => {
    // 清除所有模拟调用
    (fetch as jest.Mock).mockClear();
    // 清除localStorage
    localStorage.clear();
  });

  test('应该从localStorage初始化认证状态', async () => {
    // 设置localStorage模拟数据
    const mockUserData = {
      id: '1',
      email: 'test@example.com',
      is_active: true
    };

    localStorage.setItem('accessToken', 'mock-access-token');
    localStorage.setItem('refreshToken', 'mock-refresh-token');
    localStorage.setItem('tokenType', 'bearer');
    localStorage.setItem('user', JSON.stringify(mockUserData));
    localStorage.setItem('expiresIn', '3600');

    // 测试组件
    const TestComponent = () => {
      const { user, isAuthenticated } = useAuth();

      return (
        <div>
          <div data-testid="user-email">{user?.email || 'no-user'}</div>
          <div data-testid="is-authenticated">{isAuthenticated.toString()}</div>
        </div>
      );
    };

    render(
      <AuthWrapper>
        <TestComponent />
      </AuthWrapper>
    );

    // 等待认证状态初始化
    await waitFor(() => {
      expect(screen.getByTestId('user-email')).toHaveTextContent('test@example.com');
      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('true');
    });
  });

  test('应该处理登录成功', async () => {
    // 模拟登录API响应
    (fetch as jest.Mock).mockImplementation((url: string) => {
      if (url.includes('/api/v1/auth/login')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            access_token: 'new-access-token',
            refresh_token: 'new-refresh-token',
            token_type: 'bearer',
            expires_in: 3600,  // 确保这个值存在
            user: {
              id: '1',
              email: 'test@example.com',
              is_active: true
            }
          }),
          headers: new Headers()
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({}),
        headers: new Headers()
      });
    });

    const TestComponent = () => {
      const { login, user } = useAuth();

      return (
        <div>
          <button onClick={() => login('test@example.com', 'password123')}>登录</button>
          <div data-testid="user-email">{user?.email || 'no-user'}</div>
        </div>
      );
    };

    render(
      <AuthWrapper>
        <TestComponent />
      </AuthWrapper>
    );

    // 点击登录按钮
    fireEvent.click(screen.getByText('登录'));

    // 等待登录完成
    await waitFor(() => {
      expect(screen.getByTestId('user-email')).toHaveTextContent('test@example.com');
    });

    // 验证localStorage已更新
    expect(localStorage.getItem('accessToken')).toBe('new-access-token');
    expect(localStorage.getItem('refreshToken')).toBe('new-refresh-token');
  });

  test('应该处理登录失败', async () => {
    // 模拟登录API错误响应
    (fetch as jest.Mock).mockImplementation((url: string) => {
      if (url.includes('/api/v1/auth/login')) {
        return Promise.resolve({
          ok: false,
          json: () => Promise.resolve({
            detail: '邮箱或密码错误'
          })
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
    });

    const TestComponent = () => {
      const { login } = useAuth();

      return (
        <div>
          <button onClick={async () => {
            try {
              await login('wrong@example.com', 'wrongpassword');
            } catch (error) {
              // 期望的错误
            }
          }}>登录</button>
        </div>
      );
    };

    render(
      <AuthWrapper>
        <TestComponent />
      </AuthWrapper>
    );

    // 点击登录按钮
    fireEvent.click(screen.getByText('登录'));

    // 等待操作完成
    await waitFor(() => {
      expect(fetch).toHaveBeenCalled();
    });
  });

  test('应该处理登出', async () => {
    // 模拟注销API响应
    (fetch as jest.Mock).mockImplementation((url: string) => {
      if (url.includes('/api/v1/auth/logout')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ message: '注销成功' }),
          headers: new Headers()
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}), headers: new Headers() });
    });

    // 先通过登录获得认证状态
    const TestComponent = () => {
      const { user, logout, login } = useAuth();

      React.useEffect(() => {
        // 组件挂载时自动登录
        login('test@example.com', 'password123');
      }, []);

      return (
        <div>
          <div data-testid="user-email">{user?.email || 'no-user'}</div>
          <button onClick={() => logout()}>登出</button>
        </div>
      );
    };

    render(
      <AuthWrapper>
        <TestComponent />
      </AuthWrapper>
    );

    // 等待登录完成
    await waitFor(() => {
      expect(screen.getByTestId('user-email')).toHaveTextContent('test@example.com');
    });

    // 点击登出按钮
    fireEvent.click(screen.getByText('登出'));

    // 等待登出完成
    await waitFor(() => {
      expect(screen.getByTestId('user-email')).toHaveTextContent('no-user');
    });

    // 验证localStorage已清除
    expect(localStorage.getItem('accessToken')).toBeNull();
    expect(localStorage.getItem('refreshToken')).toBeNull();
    expect(localStorage.getItem('user')).toBeNull();
  });
});
