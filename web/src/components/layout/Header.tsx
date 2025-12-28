import React from 'react'
import { cn } from '@/lib/utils'
import Button from '@/components/ui/Button'
import { TrendingUp, Activity, ChevronDown, User, LogOut, Bell } from 'lucide-react'

export interface HeaderProps {
  title?: string
  subtitle?: string
  actions?: React.ReactNode
  className?: string
  showUser?: boolean
  userName?: string
  onUserClick?: () => void
  showMarketStatus?: boolean
}

const Header = ({
  title,
  subtitle,
  actions,
  className,
  showUser = true,
  userName = '用户',
  onUserClick,
  showMarketStatus = true,
}: HeaderProps) => {
  const [scrolled, setScrolled] = React.useState(false)

  React.useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 10)
    }

    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return (
    <header
      className={cn(
        'sticky top-0 z-40 w-full transition-all duration-300',
        scrolled
          ? 'bg-white/80 backdrop-blur-md shadow-md border-b border-gray-200/50'
          : 'bg-white/95 backdrop-blur-sm shadow-subtle border-b border-gray-100',
        className
      )}
    >
      {/* Top indicator bar - financial style */}
      <div className="h-0.5 bg-gradient-financial shimmer" />

      <div className="px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Left Section - Logo & Title */}
          <div className="flex items-center gap-4 flex-1">
            {/* Logo Mark */}
            <div className="relative group">
              <div className="absolute inset-0 bg-gradient-financial rounded-xl blur-lg opacity-40 group-hover:opacity-60 transition-opacity" />
              <div className="relative w-10 h-10 bg-gradient-financial rounded-xl flex items-center justify-center shadow-lg">
                <Activity className="w-5 h-5 text-white" />
              </div>
              {/* Live indicator */}
              <div className="absolute -top-1 -right-1 flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-finance-success opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-finance-success"></span>
              </div>
            </div>

            {/* Title Section */}
            {title && (
              <div className="flex flex-col">
                <h1 className="text-xl sm:text-2xl font-bold text-gray-900 tracking-tight font-display">
                  {title}
                </h1>
                {subtitle && (
                  <p className="text-xs sm:text-sm text-gray-500 font-medium mt-0.5 flex items-center gap-2">
                    {subtitle}
                    {showMarketStatus && (
                      <>
                        <span className="text-gray-300">•</span>
                        <span className="flex items-center gap-1.5 text-finance-success">
                          <span className="relative flex h-2 w-2">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-finance-success opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-2 w-2 bg-finance-success"></span>
                          </span>
                          市场交易中
                        </span>
                      </>
                    )}
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Center Section - Market Stats (optional) */}
          {showMarketStatus && false && (
            <div className="hidden md:flex items-center gap-6 px-6">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-finance-success/10 border border-finance-success/20">
                <TrendingUp className="w-4 h-4 text-finance-success" />
                <div className="flex flex-col">
                  <span className="text-xxs text-gray-500 uppercase tracking-wider font-semibold">上证</span>
                  <span className="text-sm font-bold text-finance-success">+1.24%</span>
                </div>
              </div>
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-finance-danger/10 border border-finance-danger/20">
                <TrendingUp className="w-4 h-4 text-finance-danger rotate-180" />
                <div className="flex flex-col">
                  <span className="text-xxs text-gray-500 uppercase tracking-wider font-semibold">深证</span>
                  <span className="text-sm font-bold text-finance-danger">-0.32%</span>
                </div>
              </div>
            </div>
          )}

          {/* Right Section - Actions & User */}
          <div className="flex items-center gap-3">
            {/* Notification Bell */}
            <button className="relative p-2 rounded-lg hover:bg-gray-100 transition-colors group">
              <Bell className="w-5 h-5 text-gray-600 group-hover:text-gray-900 transition-colors" />
              <span className="absolute top-1 right-1 h-2 w-2 rounded-full bg-finance-accent"></span>
            </button>

            {actions}

            {/* User Section */}
            {showUser && (
              <div className="flex items-center gap-2 pl-3 border-l border-gray-200">
                <div className="flex items-center gap-3 px-3 py-2 rounded-xl hover:bg-gray-50 transition-all cursor-pointer group">
                  <div className="relative">
                    <div className="w-9 h-9 bg-gradient-financial rounded-xl flex items-center justify-center text-white font-semibold text-sm shadow-md group-hover:shadow-glow transition-all">
                      {userName.charAt(0).toUpperCase()}
                    </div>
                    <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-finance-success rounded-full border-2 border-white"></div>
                  </div>
                  <div className="hidden lg:block text-left">
                    <div className="text-sm font-semibold text-gray-900">{userName}</div>
                    <div className="text-xs text-gray-500">管理员</div>
                  </div>
                  <ChevronDown className="w-4 h-4 text-gray-400 group-hover:text-gray-600 transition-colors" />
                </div>
              </div>
            )}

            {/* Logout Button */}
            <button
              onClick={() => {/* Add logout logic */}}
              className="p-2.5 rounded-xl hover:bg-red-50 text-gray-400 hover:text-red-600 transition-all"
              title="退出登录"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {/* Bottom gradient line for depth */}
      <div className="h-px bg-gradient-to-r from-transparent via-gray-200 to-transparent opacity-50" />
    </header>
  )
}

export default Header
