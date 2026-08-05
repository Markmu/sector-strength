"use client";

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import { Card, CardBody } from '@/components/ui/Card';
import Loading from '@/components/ui/Loading';

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
    } catch (error: any) {
      setErrors({ general: error.message || '登录失败，请检查邮箱和密码' });
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
    <div className="min-h-screen flex items-center justify-center bg-background">
      <Card className="w-full max-w-md p-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-foreground mb-2">登录账户</h1>
          <p className="text-muted-foreground">欢迎回到 Sector Strength</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {errors.general && (
            <div className="p-3 bg-destructive/10 border border-destructive/30 text-destructive rounded-md text-sm">
              {errors.general}
            </div>
          )}

          <div>
            <label htmlFor="email" className="block text-sm font-medium text-foreground mb-1">
              邮箱地址 <span className="text-red-500">*</span>
            </label>
            <Input
              id="email"
              name="email"
              type="email"
              value={formData.email}
              onChange={handleInputChange}
              placeholder="your@email.com"
              className={errors.email ? 'border-destructive' : ''}
              required
            />
            {errors.email && (
              <p className="mt-1 text-sm text-destructive">{errors.email}</p>
            )}
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-foreground mb-1">
              密码 <span className="text-red-500">*</span>
            </label>
            <Input
              id="password"
              name="password"
              type="password"
              value={formData.password}
              onChange={handleInputChange}
              placeholder="••••••••"
              className={errors.password ? 'border-destructive' : ''}
              required
            />
            {errors.password && (
              <p className="mt-1 text-sm text-destructive">{errors.password}</p>
            )}
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <input
                id="remember-me"
                name="remember-me"
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-border rounded"
              />
              <label htmlFor="remember-me" className="ml-2 block text-sm text-foreground">
                记住密码
              </label>
            </div>

            <div className="text-sm">
              <Link href="/forgot-password" className="font-medium text-primary-600 hover:text-primary-500">
                忘记密码？
              </Link>
            </div>
          </div>

          <Button
            type="submit"
            disabled={isLoading}
            variant="secondary"
            className="w-full bg-primary hover:bg-primary-hover text-primary-foreground font-semibold py-3"
          >
            {isLoading ? (
              <>
                <Loading className="mr-2" />
                登录中...
              </>
            ) : (
              '登录'
            )}
          </Button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-sm text-muted-foreground">
            还没有账户？{' '}
            <Link href="/register" className="font-medium text-primary-600 hover:text-primary-500">
              立即注册
            </Link>
          </p>
        </div>
      </Card>
    </div>
  );
}