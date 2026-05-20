"use client";

import React from 'react';
import { Loader2 } from 'lucide-react';

/**
 * AdminButton 组件
 *
 * 管理员页面按钮组件
 *
 * @example
 * ```tsx
 * <AdminButton variant="primary" loading={isLoading}>
 *   提交
 * </AdminButton>
 * ```
 */

type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost' | 'outline';
type ButtonSize = 'small' | 'middle' | 'large';

interface AdminButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** 按钮类型 */
  variant?: ButtonVariant;
  /** 按钮大小 */
  size?: ButtonSize;
  /** 是否加载中 */
  loading?: boolean;
  /** 图标 */
  icon?: React.ReactNode;
  /** 子元素 */
  children: React.ReactNode;
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    'bg-primary text-primary-foreground hover:bg-primary-hover shadow-sm',
  secondary:
    'bg-secondary text-foreground hover:bg-border',
  danger:
    'bg-destructive text-destructive-foreground hover:bg-destructive shadow-sm',
  ghost: 'bg-transparent text-muted-foreground hover:text-foreground hover:bg-secondary',
  outline:
    'bg-transparent text-foreground border-border hover:bg-background hover:border-primary',
};

const sizeClasses: Record<ButtonSize, string> = {
  small: 'px-3 py-1.5 text-sm',
  middle: 'px-4 py-2 text-sm',
  large: 'px-6 py-3 text-base',
};

const iconSizeClasses: Record<ButtonSize, string> = {
  small: 'h-4 w-4',
  middle: 'h-5 w-5',
  large: 'h-5 w-5',
};

export default function AdminButton({
  variant = 'primary',
  size = 'middle',
  loading = false,
  icon,
  children,
  disabled,
  className = '',
  ...props
}: AdminButtonProps) {
  const isDisabled = disabled || loading;

  return (
    <button
      disabled={isDisabled}
      className={`
        inline-flex items-center justify-center gap-2
        border rounded-lg font-medium
        transition-all duration-200
        focus:outline-none focus:ring-2 focus:ring-primary/30
        disabled:opacity-50 disabled:cursor-not-allowed
        ${variantClasses[variant]}
        ${sizeClasses[size]}
        ${className}
      `}
      {...props}
    >
      {loading ? (
        <Loader2 className={`${iconSizeClasses[size]} animate-spin`} />
      ) : icon ? (
        <span className={icon && children ? '' : ''}>{icon}</span>
      ) : null}
      {children}
    </button>
  );
}
