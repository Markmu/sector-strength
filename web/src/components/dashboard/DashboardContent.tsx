import React from 'react';
import { cn } from '@/lib/utils';

export interface DashboardContentProps {
  children: React.ReactNode;
  className?: string;
}

/**
 * DashboardContent - 仪表板主内容区域容器
 * 提供响应式内容区域，支持移动端和桌面端
 */
export const DashboardContent: React.FC<DashboardContentProps> = ({
  children,
  className,
}) => {
  return (
    <div
      className={cn(
        'flex-1',
        'px-4 py-4 md:px-6 md:py-5',
        className
      )}
    >
      <div className="mx-auto max-w-7xl space-y-5">
        {children}
      </div>
    </div>
  );
};

DashboardContent.displayName = 'DashboardContent';

export default DashboardContent;
