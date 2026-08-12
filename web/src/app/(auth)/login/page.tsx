"use client";

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import { AuthShell } from '@/components/auth/AuthShell';

interface LoginFormData {
  email: string;
  password: string;
}

interface FormErrors {
  email?: string;
  password?: string;
  general?: string;
}

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();

  // 读取"记住密码"保存的凭据，页面加载时自动回填
  const [formData, setFormData] = useState<LoginFormData>(() => {
    if (typeof window === 'undefined') {
      return { email: '', password: '' };
    }
    const savedEmail = localStorage.getItem('rememberedEmail');
    const savedPassword = localStorage.getItem('rememberedPassword');
    if (savedEmail && savedPassword) {
      return { email: savedEmail, password: savedPassword };
    }
    return { email: '', password: '' };
  });
  const [errors, setErrors] = useState<FormErrors>({});
  const [isLoading, setIsLoading] = useState(false);
  const [rememberMe, setRememberMe] = useState(() => {
    if (typeof window === 'undefined') return false;
    return localStorage.getItem('rememberedEmail') !== null;
  });

  const validateForm = (): boolean => {
    const newErrors: FormErrors = {};

    // 邮箱验证
    if (!formData.email) {
      newErrors.email = '请输入邮箱地址';
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = '请输入有效的邮箱地址';
    }

    // 密码验证
    if (!formData.password) {
      newErrors.password = '请输入密码';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setIsLoading(true);
    setErrors({});

    try {
      await login(formData.email, formData.password, rememberMe);

      // 记住密码：勾选则存凭据，取消则清除
      if (rememberMe) {
        localStorage.setItem('rememberedEmail', formData.email);
        localStorage.setItem('rememberedPassword', formData.password);
      } else {
        localStorage.removeItem('rememberedEmail');
        localStorage.removeItem('rememberedPassword');
      }

      // 登录成功后导航到dashboard
      const urlParams = new URLSearchParams(window.location.search);
      const redirect = urlParams.get('redirect');
      router.push(redirect || '/dashboard');
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '登录失败，请检查邮箱和密码';
      setErrors({ general: message });
      console.error('Login error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));

    // 清除对应的错误信息
    if (errors[name as keyof FormErrors]) {
      setErrors(prev => ({
        ...prev,
        [name]: undefined
      }));
    }
  };

  return (
    <AuthShell
      title="登录账户"
      description="继续查看板块强度、趋势与资金信号。"
      footer={
        <p>
          还没有账户？{' '}
          <Link href="/register" className="font-medium text-primary transition-colors hover:text-primary-hover">
            立即注册
          </Link>
        </p>
      }
    >
        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          {errors.general && (
            <div className="rounded-lg border border-destructive/30 bg-destructive/8 p-3 text-sm text-destructive" role="alert">
              {errors.general}
            </div>
          )}

          <Input
            id="email"
            name="email"
            type="email"
            label="邮箱地址"
            value={formData.email}
            onChange={handleInputChange}
            placeholder="your@email.com"
            error={errors.email}
            autoComplete="email"
            required
          />

          <Input
            id="password"
            name="password"
            type="password"
            label="密码"
            value={formData.password}
            onChange={handleInputChange}
            placeholder="••••••••"
            error={errors.password}
            autoComplete="current-password"
            required
          />

          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <input
                id="remember-me"
                name="remember-me"
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="h-4 w-4 rounded border-input accent-primary"
              />
              <label htmlFor="remember-me" className="ml-2 block text-sm text-foreground">
                记住密码
              </label>
            </div>

            <div className="text-sm">
              <Link href="/forgot-password" className="font-medium text-primary transition-colors hover:text-primary-hover">
                忘记密码？
              </Link>
            </div>
          </div>

          <Button
            type="submit"
            disabled={isLoading}
            variant="primary"
            className="mt-2 w-full"
            loading={isLoading}
          >
            {isLoading ? '登录中...' : '登录'}
          </Button>
        </form>
    </AuthShell>
  );
}
