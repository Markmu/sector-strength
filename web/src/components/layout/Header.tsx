import React from 'react'
import { cn } from '@/lib/utils'
import { Activity, LogOut } from 'lucide-react'

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
  return (
    <header
      className={cn(
        'w-full bg-card border-b border-border mb-6',
        className
      )}
    >
      <div className="px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Left Section - Logo & Title */}
          <div className="flex items-center gap-4 flex-1">
            {/* Logo Mark */}
            <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center shadow-sm">
              <Activity className="w-5 h-5 text-primary-foreground" />
            </div>

            {/* Title Section */}
            {title && (
              <div className="flex flex-col">
                <h1 className="text-xl sm:text-2xl font-bold text-foreground tracking-tight font-display">
                  {title}
                </h1>
                {subtitle && (
                  <p className="text-xs sm:text-sm text-muted-foreground font-medium mt-0.5 flex items-center gap-2">
                    {subtitle}
                    {showMarketStatus && (
                      <>
                        <span className="text-border">/</span>
                        <span className="text-rise">
                          市场状态
                        </span>
                      </>
                    )}
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Right Section - Actions & User */}
          <div className="flex items-center gap-3">
            {actions}

            {/* User Section */}
            {showUser && (
              <div className="flex items-center gap-2 pl-3 border-l border-border">
                <div className="flex items-center gap-3 px-3 py-2 rounded-xl cursor-pointer">
                  <div className="w-9 h-9 bg-primary rounded-xl flex items-center justify-center text-primary-foreground font-semibold text-sm shadow-sm">
                    {userName.charAt(0).toUpperCase()}
                  </div>
                  <div className="hidden lg:block text-left">
                    <div className="text-sm font-semibold text-foreground">{userName}</div>
                    <div className="text-xs text-muted-foreground">管理员</div>
                  </div>
                </div>
              </div>
            )}

            {/* Logout Button */}
            <button
              onClick={() => {/* Add logout logic */}}
              className="p-2.5 rounded-xl hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors"
              title="退出登录"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {/* Bottom separator */}
      <div className="border-b border-border" />
    </header>
  )
}

export default Header
