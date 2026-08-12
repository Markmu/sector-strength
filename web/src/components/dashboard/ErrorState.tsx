import React from 'react';
import { cn } from '@/lib/utils';
import { AlertCircle, RefreshCw } from 'lucide-react';

export interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
}

/**
 * ErrorState - 错误状态显示组件
 */
export const ErrorState: React.FC<ErrorStateProps> = ({
  title = '加载失败',
  message = '请稍后重试',
  onRetry,
  className,
}) => {
  return (
    <div className={cn('flex flex-col items-center justify-center py-12 text-center', className)}>
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-destructive/10">
        <AlertCircle className="h-6 w-6 text-destructive" />
      </div>
      <h3 className="text-lg font-semibold text-foreground mb-2">{title}</h3>
      <p className="text-sm text-muted-foreground mb-4 max-w-md">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex h-9 items-center justify-center rounded-lg bg-primary px-4 text-sm font-medium text-primary-foreground shadow-subtle transition-colors hover:bg-primary-hover"
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          重试
        </button>
      )}
    </div>
  );
};

ErrorState.displayName = 'ErrorState';

export default ErrorState;
