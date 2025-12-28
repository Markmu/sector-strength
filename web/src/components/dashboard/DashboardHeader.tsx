import React from 'react';
import { cn } from '@/lib/utils';
import { Home, RefreshCw, Settings, Bell, ChevronRight, TrendingUp, TrendingDown, Activity } from 'lucide-react';

export interface DashboardHeaderProps {
  title?: string;
  subtitle?: string;
  actions?: React.ReactNode;
  className?: string;
  onRefresh?: () => void;
  showMarketStats?: boolean;
  breadcrumbs?: Array<{ label: string; href?: string }>;
}

/**
 * DashboardHeader - 现代化仪表板头部组件
 * 采用金融专业风格设计
 */
export const DashboardHeader: React.FC<DashboardHeaderProps> = ({
  title = '仪表板',
  subtitle,
  actions,
  className,
  onRefresh,
  showMarketStats = true,
  breadcrumbs,
}) => {
  const [isRefreshing, setIsRefreshing] = React.useState(false);
  const [scrolled, setScrolled] = React.useState(false);

  React.useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 10);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

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
        'sticky top-0 z-30 w-full transition-all duration-300',
        scrolled
          ? 'bg-white/90 backdrop-blur-lg shadow-md border-b border-gray-200/50'
          : 'bg-white/95 backdrop-blur-sm shadow-subtle border-b border-gray-100',
        className
      )}
    >
      {/* Top accent bar */}
      <div className="h-0.5 bg-gradient-financial shimmer" />

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
                      <ChevronRight className="w-4 h-4 text-gray-400" />
                    )}
                    {crumb.href ? (
                      <a
                        href={crumb.href}
                        className="text-gray-500 hover:text-gray-900 transition-colors font-medium"
                      >
                        {crumb.label}
                      </a>
                    ) : (
                      <span className="text-gray-900 font-semibold">{crumb.label}</span>
                    )}
                  </React.Fragment>
                ))}
              </nav>
            )}

            {/* Icon */}
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-financial rounded-xl blur-md opacity-30" />
              <div className="relative w-11 h-11 bg-gradient-financial rounded-xl flex items-center justify-center shadow-lg">
                <Home className="w-5 h-5 text-white" />
              </div>
            </div>

            {/* Title Section */}
            <div>
              <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-gray-900 font-display">
                {title}
              </h1>
              {subtitle && (
                <p className="text-sm md:text-base text-gray-500 mt-1 font-medium flex items-center gap-2">
                  {subtitle}
                  <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-finance-success/10 text-finance-success text-xs font-semibold">
                    <Activity className="w-3 h-3" />
                    实时数据
                  </span>
                </p>
              )}
            </div>
          </div>

          {/* Center Section - Market Stats */}
          {showMarketStats && false && (
            <div className="hidden lg:flex items-center gap-4">
              {/* Market Indicator 1 */}
              <div className="flex items-center gap-3 px-4 py-2.5 rounded-xl bg-gradient-to-br from-finance-success/10 to-finance-success/5 border border-finance-success/20">
                <div className="relative">
                  <div className="absolute inset-0 bg-finance-success/20 rounded-full blur-md"></div>
                  <TrendingUp className="relative w-5 h-5 text-finance-success" />
                </div>
                <div className="text-left">
                  <div className="text-xxs text-gray-500 uppercase tracking-wider font-semibold">沪深300</div>
                  <div className="text-lg font-bold text-finance-success">+2.34%</div>
                </div>
              </div>

              {/* Market Indicator 2 */}
              <div className="flex items-center gap-3 px-4 py-2.5 rounded-xl bg-gradient-to-br from-finance-danger/10 to-finance-danger/5 border border-finance-danger/20">
                <div className="relative">
                  <div className="absolute inset-0 bg-finance-danger/20 rounded-full blur-md"></div>
                  <TrendingDown className="relative w-5 h-5 text-finance-danger" />
                </div>
                <div className="text-left">
                  <div className="text-xxs text-gray-500 uppercase tracking-wider font-semibold">创业板</div>
                  <div className="text-lg font-bold text-finance-danger">-0.87%</div>
                </div>
              </div>

              {/* Market Indicator 3 */}
              <div className="flex items-center gap-3 px-4 py-2.5 rounded-xl bg-gradient-to-br from-finance-accent/10 to-finance-accent/5 border border-finance-accent/20">
                <div className="relative">
                  <div className="absolute inset-0 bg-finance-accent/20 rounded-full blur-md"></div>
                  <Activity className="relative w-5 h-5 text-finance-accent" />
                </div>
                <div className="text-left">
                  <div className="text-xxs text-gray-500 uppercase tracking-wider font-semibold">成交量</div>
                  <div className="text-lg font-bold text-finance-accent">3,820亿</div>
                </div>
              </div>
            </div>
          )}

          {/* Right Section - Actions */}
          <div className="flex items-center gap-2">
            {/* Settings Button */}
            <button className="p-2.5 rounded-xl hover:bg-gray-100 text-gray-500 hover:text-gray-700 transition-all">
              <Settings className="w-5 h-5" />
            </button>

            {/* Notification Button */}
            <button className="relative p-2.5 rounded-xl hover:bg-gray-100 text-gray-500 hover:text-gray-700 transition-all">
              <Bell className="w-5 h-5" />
              <span className="absolute top-2 right-2 flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-finance-accent opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-finance-accent"></span>
              </span>
            </button>

            {/* Refresh Button */}
            {onRefresh && (
              <button
                onClick={handleRefresh}
                disabled={isRefreshing}
                className={cn(
                  "inline-flex items-center justify-center rounded-xl text-sm font-semibold transition-all",
                  "px-4 py-2.5 border border-gray-200",
                  "bg-white hover:bg-gray-50 text-gray-700 hover:text-gray-900",
                  "shadow-sm hover:shadow-medium",
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

      {/* Bottom gradient line */}
      <div className="h-px bg-gradient-to-r from-transparent via-gray-200 to-transparent opacity-60" />
    </header>
  );
};

DashboardHeader.displayName = 'DashboardHeader';

export default DashboardHeader;
