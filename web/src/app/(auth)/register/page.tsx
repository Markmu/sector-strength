"use client";

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import { AuthShell } from '@/components/auth/AuthShell';
import { CheckCircle2, LoaderCircle } from 'lucide-react';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface RegisterFormData {
  email: string;
  password: string;
  confirmPassword: string;
  username?: string;
}

interface FormErrors {
  email?: string;
  password?: string;
  confirmPassword?: string;
  username?: string;
  general?: string;
}

export default function RegisterPage() {
  const router = useRouter();
  const [formData, setFormData] = useState<RegisterFormData>({
    email: '',
    password: '',
    confirmPassword: '',
    username: ''
  });
  const [errors, setErrors] = useState<FormErrors>({});
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

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
    } else if (formData.password.length < 8) {
      newErrors.password = '密码长度至少8位';
    } else if (!/[A-Z]/.test(formData.password)) {
      newErrors.password = '密码必须包含大写字母';
    } else if (!/[a-z]/.test(formData.password)) {
      newErrors.password = '密码必须包含小写字母';
    } else if (!/[0-9]/.test(formData.password)) {
      newErrors.password = '密码必须包含数字';
    } else if (!/[!@#$%^&*(),.?":{}|<>]/.test(formData.password)) {
      newErrors.password = '密码必须包含特殊字符';
    }

    // 确认密码验证
    if (!formData.confirmPassword) {
      newErrors.confirmPassword = '请确认密码';
    } else if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = '两次输入的密码不一致';
    }

    // 用户名验证（可选）
    if (formData.username && formData.username.length > 50) {
      newErrors.username = '用户名长度不能超过50个字符';
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
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          email: formData.email,
          password: formData.password,
          username: formData.username
        })
      });

      const data = await response.json();

      if (response.ok) {
        setIsSuccess(true);
        setTimeout(() => {
          router.push('/login');
        }, 3000);
      } else {
        setErrors({ general: data.detail || '注册失败，请稍后重试' });
      }
    } catch (error) {
      setErrors({ general: '网络错误，请稍后重试' });
      console.error('Registration error:', error);
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

  if (isSuccess) {
    return (
      <AuthShell title="注册成功" description="账户已创建，请完成邮箱验证。">
        <div className="rounded-xl border border-fall/30 bg-fall/8 p-5 text-center">
          <CheckCircle2 className="mx-auto mb-3 h-7 w-7 text-fall" aria-hidden="true" />
          <p className="text-sm leading-6 text-muted-foreground">
            验证邮件已发送到您的邮箱，请查收并点击验证链接激活账户。
          </p>
          <div className="mt-4 flex items-center justify-center gap-2 text-xs font-medium text-muted-foreground">
            <LoaderCircle className="h-4 w-4 animate-spin text-primary" aria-hidden="true" />
            正在跳转到登录页面...
          </div>
        </div>
      </AuthShell>
    );
  }

  return (
    <AuthShell
      title="注册账户"
      description="创建账户，保存你的复盘入口。"
      footer={
        <p>
          已有账户？{' '}
          <Link href="/login" className="font-medium text-primary transition-colors hover:text-primary-hover">
            立即登录
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
            id="username"
            name="username"
            type="text"
            label="用户名（可选）"
            value={formData.username}
            onChange={handleInputChange}
            placeholder="输入用户名"
            error={errors.username}
            autoComplete="username"
          />

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
            helperText="至少 8 位，包含大小写字母、数字和特殊字符。"
            autoComplete="new-password"
            required
          />

          <Input
            id="confirmPassword"
            name="confirmPassword"
            type="password"
            label="确认密码"
            value={formData.confirmPassword}
            onChange={handleInputChange}
            placeholder="••••••••"
            error={errors.confirmPassword}
            autoComplete="new-password"
            required
          />

          <Button
            type="submit"
            disabled={isLoading}
            variant="primary"
            className="mt-2 w-full"
            loading={isLoading}
          >
            {isLoading ? '注册中...' : '注册账户'}
          </Button>
        </form>
    </AuthShell>
  );
}
