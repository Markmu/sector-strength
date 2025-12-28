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
    <main
      className={cn(
        'flex-1',
        'px-4 py-6 md:px-6 md:py-8',
        'animate-slide-up',
        className
      )}
    >
      <div className="max-w-7xl mx-auto space-y-6">
        {children}
      </div>
    </main>
  );
};

DashboardContent.displayName = 'DashboardContent';

export default DashboardContent;
