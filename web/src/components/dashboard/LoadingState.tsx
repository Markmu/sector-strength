import React from 'react';
import { cn } from '@/lib/utils';

export interface LoadingStateProps {
  message?: string;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

/**
 * LoadingState - 加载状态指示器组件
 */
export const LoadingState: React.FC<LoadingStateProps> = ({
  message = '加载中...',
  className,
  size = 'md',
}) => {
  const sizes = {
    sm: 'h-4 w-4',
    md: 'h-8 w-8',
    lg: 'h-12 w-12',
  };

  return (
    <div className={cn('flex flex-col items-center justify-center py-12', className)}>
      <div
        className={cn('animate-pulse rounded-lg border border-primary/25 bg-primary-light', sizes[size])}
        aria-hidden="true"
      />
      {message && (
        <p className="mt-4 text-sm text-muted-foreground">{message}</p>
      )}
    </div>
  );
};

LoadingState.displayName = 'LoadingState';

export default LoadingState;
