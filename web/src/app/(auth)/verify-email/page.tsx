"use client";

import React, { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { Loading } from '@/components/ui/Loading';
import { AuthShell } from '@/components/auth/AuthShell';
import { AlertCircle, CheckCircle2, LoaderCircle } from 'lucide-react';

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get('token');
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');

  useEffect(() => {
    const verifyEmail = async () => {
      if (!token) {
        setStatus('error');
        setMessage('验证令牌缺失');
        return;
      }

      try {
        const response = await fetch(`/api/auth/verify/${token}`, {
          method: 'GET'
        });

        const data = await response.json();

        if (response.ok) {
          setStatus('success');
          setMessage(data.message);
        } else {
          setStatus('error');
          setMessage(data.detail || '验证失败');
        }
      } catch (error) {
        setStatus('error');
        setMessage('网络错误，请稍后重试');
        console.error('Verification error:', error);
      }
    };

    verifyEmail();
  }, [token]);

  return (
    <AuthShell title="邮箱验证" description="确认邮箱后即可登录并使用完整功能。">
      <div className="rounded-xl border border-border bg-card p-5 text-center shadow-subtle">
        {status === 'loading' && (
          <div className="space-y-4">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-primary-light">
              <LoaderCircle className="h-6 w-6 animate-spin text-primary" aria-hidden="true" />
            </div>
            <h2 className="text-base font-semibold text-foreground">正在验证您的邮箱...</h2>
            <p className="text-sm text-muted-foreground">请稍候，系统正在处理验证请求。</p>
          </div>
        )}

        {status === 'success' && (
          <div className="space-y-4">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-fall/10">
              <CheckCircle2 className="h-6 w-6 text-fall" aria-hidden="true" />
            </div>
            <h2 className="text-base font-semibold text-foreground mb-2">验证成功</h2>
            <p className="text-sm text-muted-foreground">{message}</p>
            <Loading text="正在跳转到登录页面..." />
          </div>
        )}

        {status === 'error' && (
          <div className="space-y-4">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-destructive/10">
              <AlertCircle className="h-6 w-6 text-destructive" aria-hidden="true" />
            </div>
            <h2 className="text-base font-semibold text-foreground mb-2">验证失败</h2>
            <p className="text-sm text-muted-foreground">{message}</p>
            <div className="mt-6">
              <a
                href="/login"
                className="inline-flex h-9 items-center rounded-lg bg-primary px-4 text-sm font-medium text-primary-foreground shadow-subtle transition-colors hover:bg-primary-hover"
              >
                返回登录页面
              </a>
            </div>
          </div>
        )}
      </div>
    </AuthShell>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={
      <div className="min-h-[100dvh] flex items-center justify-center bg-background">
        <Loading />
      </div>
    }>
      <VerifyEmailContent />
    </Suspense>
  );
}
