import React from 'react';
import { cn } from '@/lib/utils';
import { RefreshCw, ChevronRight } from 'lucide-react';

export interface DashboardHeaderProps {
  title?: string;
  subtitle?: string;
  actions?: React.ReactNode;
  className?: string;
  onRefresh?: () => void;
  showMarketStats?: boolean;
  breadcrumbs?: Array<{ label: string; href?: string }>;
}

export const DashboardHeader: React.FC<DashboardHeaderProps> = ({
  title = '仪表板',
  subtitle,
  actions,
  className,
  onRefresh,
  breadcrumbs,
}) => {
  const [isRefreshing, setIsRefreshing] = React.useState(false);

  const handleRefresh = async () => {
    if (isRefreshing || !onRefresh) return;
    setIsRefreshing(true);
    try {
      await onRefresh();
    } finally {
      setTimeout(() => setIsRefreshing(false), 500);
    }
  };

  return (
    <header
      className={cn(
        'w-full border-b border-border bg-card',
        className
      )}
    >
      <div className="mx-auto max-w-[1600px] px-4 py-4 md:px-6">
        <div className="flex items-start justify-between gap-4">
          {/* Left Section - Navigation & Title */}
          <div className="min-w-0 flex-1">
            {/* Breadcrumb Navigation */}
            {breadcrumbs && breadcrumbs.length > 0 && (
              <nav className="mb-1.5 hidden items-center gap-1.5 text-xs md:flex" aria-label="面包屑">
                {breadcrumbs.map((crumb, index) => (
                  <React.Fragment key={index}>
                    {index > 0 && (
                      <ChevronRight className="w-4 h-4 text-muted-foreground" />
                    )}
                    {crumb.href ? (
                      <a
                        href={crumb.href}
                        className="text-muted-foreground hover:text-foreground transition-colors font-medium"
                      >
                        {crumb.label}
                      </a>
                    ) : (
                      <span className="text-foreground font-semibold">{crumb.label}</span>
                    )}
                  </React.Fragment>
                ))}
              </nav>
            )}

            {/* Title Section */}
            <div>
              <h1 className="text-xl font-semibold tracking-tight text-foreground md:text-2xl">
                {title}
              </h1>
              {subtitle && (
                <p className="mt-1 max-w-[72ch] text-sm text-muted-foreground">
                  {subtitle}
                </p>
              )}
            </div>
          </div>

          {/* Right Section - Actions */}
          <div className="flex flex-shrink-0 items-center gap-2 pt-0.5">
            {/* Refresh Button */}
            {onRefresh && (
              <button
                onClick={handleRefresh}
                disabled={isRefreshing}
                className={cn(
                  "inline-flex h-9 items-center justify-center rounded-lg text-sm font-medium transition-colors",
                  "px-3 border border-border",
                  "bg-card hover:bg-secondary text-foreground",
                  "disabled:opacity-50 disabled:cursor-not-allowed",
                  isRefreshing && "text-primary"
                )}
                aria-label="刷新"
              >
                <RefreshCw className={cn("h-4 w-4 sm:mr-2", isRefreshing && "animate-spin")} />
                <span className="hidden sm:inline">刷新</span>
              </button>
            )}

            {actions}
          </div>
        </div>
      </div>
    </header>
  );
};

DashboardHeader.displayName = 'DashboardHeader';

export default DashboardHeader;
