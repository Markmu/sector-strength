"use client";

import React from 'react';

/**
 * AdminCard 组件
 *
 * 管理员页面的卡片容器组件
 *
 * @example
 * ```tsx
 * <AdminCard title="标题">
 *   <p>卡片内容</p>
 * </AdminCard>
 * ```
 */

interface AdminCardProps {
  /** 卡片标题 */
  title?: string;
  /** 卡片副标题 */
  subtitle?: string;
  /** 额外操作（显示在标题右侧） */
  actions?: React.ReactNode;
  /** 是否显示边框 */
  bordered?: boolean;
  /** 自定义类名 */
  className?: string;
  /** 子元素 */
  children: React.ReactNode;
}

export default function AdminCard({
  title,
  subtitle,
  actions,
  bordered = true,
  className = '',
  children,
}: AdminCardProps) {
  return (
    <div
      className={`rounded-xl bg-card p-6 shadow-sm ${
        bordered ? 'border border-border' : ''
      } ${className}`}
    >
      {/* 标题栏 */}
      {(title || actions) && (
        <div className="mb-4 flex items-center justify-between">
          <div>
            {title && (
              <h3 className="text-lg font-semibold text-foreground">{title}</h3>
            )}
            {subtitle && (
              <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
            )}
          </div>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
      )}

      {/* 内容 */}
      <div className="text-foreground">{children}</div>
    </div>
  );
}
