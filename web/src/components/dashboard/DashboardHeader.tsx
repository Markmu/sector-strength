import React from 'react';
import { cn } from '@/lib/utils';
import { Home, RefreshCw, ChevronRight, Activity } from 'lucide-react';

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
        'w-full bg-card border-b border-border mb-6',
        className
      )}
    >
      <div className="px-4 py-4 md:px-6 md:py-5">
        <div className="flex items-center justify-between">
          {/* Left Section - Navigation & Title */}
          <div className="flex items-center gap-4 flex-1">
            {/* Breadcrumb Navigation */}
            {breadcrumbs && breadcrumbs.length > 0 && (
              <nav className="hidden md:flex items-center gap-2 text-sm">
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

            {/* Icon */}
            <div className="w-11 h-11 bg-primary rounded-xl flex items-center justify-center shadow-sm">
              <Home className="w-5 h-5 text-primary-foreground" />
            </div>

            {/* Title Section */}
            <div>
              <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-foreground font-display">
                {title}
              </h1>
              {subtitle && (
                <p className="text-sm md:text-base text-muted-foreground mt-1 font-medium flex items-center gap-2">
                  {subtitle}
                  <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-rise/10 text-rise text-xs font-semibold">
                    <Activity className="w-3 h-3" />
                  </span>
                </p>
              )}
            </div>
          </div>

          {/* Right Section - Actions */}
          <div className="flex items-center gap-2">
            {/* Refresh Button */}
            {onRefresh && (
              <button
                onClick={handleRefresh}
                disabled={isRefreshing}
                className={cn(
                  "inline-flex items-center justify-center rounded-xl text-sm font-semibold transition-colors",
                  "px-4 py-2.5 border border-border",
                  "bg-card hover:bg-secondary text-foreground",
                  "disabled:opacity-50 disabled:cursor-not-allowed",
                  isRefreshing && "animate-pulse"
                )}
                aria-label="刷新"
              >
                <RefreshCw className={cn("w-4 h-4 mr-2", isRefreshing && "animate-spin")} />
                刷新
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
