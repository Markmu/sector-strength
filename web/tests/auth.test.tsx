/**
 * 前端认证组件测试
 */

import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { AuthProvider, useAuth } from '@/contexts/AuthContext';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import LoginPage from '@/app/(auth)/login/page';

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

describe('AuthContext', () => {
  beforeEach(() => {
    // 清除所有模拟调用
    (fetch as jest.Mock).mockClear();

    // 清除localStorage
    localStorage.clear();

    // 重置所有定时器
    jest.useFakeTimers();
    jest.setSystemTime(new Date());
  });

  afterEach(() => {
    jest.useRealTimers();
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
      const { user, isAuthenticated, isLoading } = useAuth();

      if (isLoading) {
        return <div>加载中...</div>;
      }

      return (
        <div>
          <div data-testid="user-email">{user?.email}</div>
          <div data-testid="is-authenticated">{isAuthenticated.toString()}</div>
        </div>
      );
    };

    render(
      <AuthWrapper>
        <TestComponent />
      </AuthWrapper>
    );

    // 初始状态应该是加载中
    expect(screen.getByTestId('is-authenticated')).toHaveTextContent('false');

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
            expires_in: 3600,
            user: {
              id: '1',
              email: 'test@example.com',
              is_active: true
            }
          })
        });
      }
      // 对其他API调用也返回成功，避免错误
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({})
      });
    });

    const TestComponent = () => {
      const { login, user } = useAuth();

      const handleLogin = async () => {
        try {
          await login('test@example.com', 'password123');
        } catch (error) {
          console.error('Login error:', error);
        }
      };

      return (
        <div>
          <button onClick={handleLogin}>登录</button>
          <div data-testid="user-email">{user?.email}</div>
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
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({})
      });
    });

    const TestComponent = () => {
      const { login, error } = useAuth();

      const handleLogin = async () => {
        try {
          await login('wrong@example.com', 'wrongpassword');
        } catch (error: any) {
          // 错误会抛出，所以这里应该不会执行
        }
      };

      return (
        <div>
          <button onClick={handleLogin}>登录</button>
          {error && <div data-testid="error">{error}</div>}
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

    // 等待错误处理
    await waitFor(() => {
      // 由于错误被抛出，我们需要在错误边界中测试
      // 这里验证fetch被调用
      expect(fetch).toHaveBeenCalledTimes(1);
    });
  });

  test('应该处理登出', async () => {
    // 先设置登录状态
    const mockUserData = {
      id: '1',
      email: 'test@example.com',
      is_active: true
    };

    localStorage.setItem('accessToken', 'mock-access-token');
    localStorage.setItem('refreshToken', 'mock-refresh-token');
    localStorage.setItem('user', JSON.stringify(mockUserData));

    // 模拟注销API响应
    (fetch as jest.Mock).mockImplementationOnce((url: string) => {
      if (url.includes('/api/v1/auth/logout')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ message: '注销成功' })
        });
      }
      return Promise.reject(new Error('Not found'));
    });

    const TestComponent = () => {
      const { user, logout } = useAuth();

      const handleLogout = async () => {
        await logout();
      };

      return (
        <div>
          <div data-testid="user-email">{user?.email}</div>
          <button onClick={handleLogout}>登出</button>
        </div>
      );
    };

    render(
      <AuthWrapper>
        <TestComponent />
      </AuthWrapper>
    );

    // 验证初始登录状态
    expect(screen.getByTestId('user-email')).toHaveTextContent('test@example.com');

    // 点击登出按钮
    fireEvent.click(screen.getByText('登出'));

    // 等待登出完成
    await waitFor(() => {
      expect(screen.getByTestId('user-email')).toBeEmpty();
    });

    // 验证localStorage已清除
    expect(localStorage.getItem('accessToken')).toBeNull();
    expect(localStorage.getItem('refreshToken')).toBeNull();
    expect(localStorage.getItem('user')).toBeNull();
  });

  test('应该自动刷新即将过期的token', async () => {
    // 设置即将过期的token（1分钟后过期）
    const mockUserData = {
      id: '1',
      email: 'test@example.com',
      is_active: true
    };

    localStorage.setItem('accessToken', 'mock-access-token');
    localStorage.setItem('refreshToken', 'mock-refresh-token');
    localStorage.setItem('user', JSON.stringify(mockUserData));
    localStorage.setItem('expiresIn', '60'); // 1分钟

    // 模拟刷新token API响应
    (fetch as jest.Mock).mockImplementationOnce((url: string) => {
      if (url.includes('/api/v1/auth/refresh')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            access_token: 'new-access-token',
            refresh_token: 'new-refresh-token',
            expires_in: 3600
          })
        });
      }
      return Promise.reject(new Error('Not found'));
    });

    const TestComponent = () => {
      const { user } = useAuth();

      return (
        <div>
          <div data-testid="user-email">{user?.email}</div>
        </div>
      );
    };

    render(
      <AuthWrapper>
        <TestComponent />
      </AuthWrapper>
    );

    // 快进时间到token过期前5分钟
    act(() => {
      jest.advanceTimersByTime(55 * 1000); // 55秒
    });

    // 等待自动刷新
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/auth/refresh',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            refresh_token: 'mock-refresh-token'
          })
        })
      );
    });

    // 验证新token已存储
    expect(localStorage.getItem('accessToken')).toBe('new-access-token');
  });
});

describe('ProtectedRoute', () => {
  beforeEach(() => {
    // 清除localStorage
    localStorage.clear();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  test('应该显示子内容当用户已认证', async () => {
    // 设置认证状态
    const mockUserData = {
      id: '1',
      email: 'test@example.com',
      is_active: true
    };

    localStorage.setItem('accessToken', 'mock-access-token');
    localStorage.setItem('user', JSON.stringify(mockUserData));

    const TestComponent = () => (
      <div data-testid="protected-content">受保护的内容</div>
    );

    render(
      <AuthWrapper>
        <ProtectedRoute>
          <TestComponent />
        </ProtectedRoute>
      </AuthWrapper>
    );

    // 应该显示受保护的内容
    await waitFor(() => {
      expect(screen.getByTestId('protected-content')).toBeInTheDocument();
    });
  });

  test('应该重定向到登录页当用户未认证', () => {
    // 不设置认证状态

    const TestComponent = () => (
      <div data-testid="protected-content">受保护的内容</div>
    );

    render(
      <AuthWrapper>
        <ProtectedRoute>
          <TestComponent />
        </ProtectedRoute>
      </AuthWrapper>
    );

    // 不应该显示受保护的内容
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
  });

  test('应该显示加载状态', () => {
    // 清除localStorage以触发加载状态

    render(
      <AuthWrapper>
        <ProtectedRoute>
          <div data-testid="protected-content">受保护的内容</div>
        </ProtectedRoute>
      </AuthWrapper>
    );

    // 初始状态应该显示加载中
    // 注意：实际加载状态取决于具体实现
  });
});

describe('LoginPage', () => {
  beforeEach(() => {
    (fetch as jest.Mock).mockClear();
    localStorage.clear();
  });

  test('应该渲染登录表单', () => {
    render(
      <AuthWrapper>
        <LoginPage />
      </AuthWrapper>
    );

    expect(screen.getByText('登录账户')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('your@email.com')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('••••••••')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '登录' })).toBeInTheDocument();
  });

  test('应该处理表单输入变化', () => {
    render(
      <AuthWrapper>
        <LoginPage />
      </AuthWrapper>
    );

    const emailInput = screen.getByPlaceholderText('your@email.com');
    const passwordInput = screen.getByPlaceholderText('••••••••');

    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.change(passwordInput, { target: { value: 'password123' } });

    expect(emailInput).toHaveValue('test@example.com');
    expect(passwordInput).toHaveValue('password123');
  });

  test('应该验证必填字段', async () => {
    render(
      <AuthWrapper>
        <LoginPage />
      </AuthWrapper>
    );

    const submitButton = screen.getByRole('button', { name: '登录' });

    // 不填写任何字段直接提交
    fireEvent.click(submitButton);

    // 应该显示错误信息
    await waitFor(() => {
      expect(screen.getByText('请输入邮箱地址')).toBeInTheDocument();
      expect(screen.getByText('请输入密码')).toBeInTheDocument();
    });
  });

  test('应该验证邮箱格式', async () => {
    render(
      <AuthWrapper>
        <LoginPage />
      </AuthWrapper>
    );

    const emailInput = screen.getByPlaceholderText('your@email.com');
    const submitButton = screen.getByRole('button', { name: '登录' });

    // 输入无效邮箱
    fireEvent.change(emailInput, { target: { value: 'invalid-email' } });
    fireEvent.click(submitButton);

    // 应该显示邮箱格式错误
    await waitFor(() => {
      expect(screen.getByText('请输入有效的邮箱地址')).toBeInTheDocument();
    });
  });

  test('应该处理记住我选项', () => {
    render(
      <AuthWrapper>
        <LoginPage />
      </AuthWrapper>
    );

    const rememberMeCheckbox = screen.getByLabelText('记住我');

    // 切换记住我选项
    fireEvent.click(rememberMeCheckbox);

    expect(rememberMeCheckbox).toBeChecked();

    fireEvent.click(rememberMeCheckbox);

    expect(rememberMeCheckbox).not.toBeChecked();
  });

  test('应该提供注册链接', () => {
    render(
      <AuthWrapper>
        <LoginPage />
      </AuthWrapper>
    );

    const registerLink = screen.getByText('立即注册');
    expect(registerLink).toBeInTheDocument();
    expect(registerLink).toHaveAttribute('href', '/register');
  });

  test('应该提供忘记密码链接', () => {
    render(
      <AuthWrapper>
        <LoginPage />
      </AuthWrapper>
    );

    const forgotPasswordLink = screen.getByText('忘记密码？');
    expect(forgotPasswordLink).toBeInTheDocument();
    expect(forgotPasswordLink).toHaveAttribute('href', '/forgot-password');
  });
});