"use client";

import React from 'react';

/**
 * LoadingSpinner 组件
 *
 * 加载状态指示器
 *
 * @example
 * ```tsx
 * <LoadingSpinner size="large" />
 * ```
 */

type SpinnerSize = 'small' | 'medium' | 'large';
type SpinnerColor = 'blue' | 'gray' | 'white';

interface LoadingSpinnerProps {
  /** 大小 */
  size?: SpinnerSize;
  /** 颜色 */
  color?: SpinnerColor;
  /** 是否全屏显示 */
  fullscreen?: boolean;
  /** 自定义类名 */
  className?: string;
  /** 文本提示 */
  text?: string;
}

const sizeClasses: Record<SpinnerSize, string> = {
  small: 'h-4 w-4 border-2',
  medium: 'h-8 w-8 border-3',
  large: 'h-12 w-12 border-4',
};

const colorClasses: Record<SpinnerColor, {
  border: string;
  borderTop: string;
}> = {
  blue: {
    border: 'border-blue-200',
    borderTop: 'border-t-blue-600',
  },
  gray: {
    border: 'border-gray-200',
    borderTop: 'border-t-gray-600',
  },
  white: {
    border: 'border-white/30',
    borderTop: 'border-t-white',
  },
};

export default function LoadingSpinner({
  size = 'medium',
  color = 'blue',
  fullscreen = false,
  className = '',
  text,
}: LoadingSpinnerProps) {
  const colors = colorClasses[color];
  const spinnerSize = sizeClasses[size];

  const spinnerElement = (
    <div className={`flex flex-col items-center justify-center gap-3 ${className}`}>
      {/* 旋转动画 */}
      <div
        className={`${spinnerSize} ${colors.border} ${colors.borderTop} rounded-full animate-spin`}
        role="status"
        aria-label="加载中"
      >
        <span className="sr-only">加载中...</span>
      </div>

      {/* 文本提示 */}
      {text && (
        <p className="text-sm text-gray-600">{text}</p>
      )}
    </div>
  );

  if (fullscreen) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-white/80 backdrop-blur-sm">
        {spinnerElement}
      </div>
    );
  }

  return spinnerElement;
}
