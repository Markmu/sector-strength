"use client";

import React from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { useAuth } from '@/contexts/AuthContext'
import { ThemeToggle } from '@/components/ui/ThemeToggle'
import { Activity, ChevronLeft, LogOut } from 'lucide-react'

export interface SidebarItem {
  title: string
  href?: string
  icon?: React.ReactNode
  badge?: string | number
  active?: boolean
  children?: SidebarItem[]
}

export interface SidebarProps {
  items: SidebarItem[]
  className?: string
  collapsed?: boolean
  onCollapse?: (collapsed: boolean) => void
}

const Sidebar = ({ items, className, collapsed = false, onCollapse }: SidebarProps) => {
  const { user, logout, isAuthenticated } = useAuth()
  const pathname = usePathname()

  const handleLogout = async () => {
    try {
      await logout()
    } catch (error) {
      console.error('退出登录失败:', error)
    }
  }

  // 检查是否是激活的菜单项（精确匹配）
  const isActive = (href?: string) => {
    if (!href) return false
    // 精确匹配路径
    if (pathname === href) return true
    // 对于根路径，如果是 /dashboard 或 /dashboard/ 都视为匹配
    if (href === '/dashboard' && (pathname === '/dashboard' || pathname === '/dashboard/')) return true
    return false
  }

  const renderMenuItem = (item: SidebarItem, level = 0) => {
    const active = item.active ?? isActive(item.href)
    const hasChildren = item.children && item.children.length > 0

    return (
      <div key={item.title}>
        {item.href ? (
          <Link
            href={item.href}
            className={cn(
              'group flex min-h-9 items-center px-2.5 py-1.5 text-[13px] font-medium rounded-md transition-colors duration-200',
              active
                ? 'bg-primary-light text-primary'
                : 'text-muted-foreground hover:text-foreground hover:bg-secondary',
              level > 0 && 'pl-6',
              collapsed && level === 0 && 'justify-center'
            )}
          >
            {item.icon && (
              <span className={cn(
                'flex-shrink-0',
                collapsed ? 'mx-auto' : 'mr-3',
                active && 'text-primary'
              )}>
                {item.icon}
              </span>
            )}

            {!collapsed && (
              <>
                <span className="flex-1">{item.title}</span>
                {item.badge && (
                  <span className={cn(
                    'ml-2 inline-flex items-center rounded-md px-1.5 py-0.5 text-[11px] font-semibold tabular-nums',
                    active
                      ? 'bg-primary/12 text-primary'
                      : 'bg-secondary text-muted-foreground'
                  )}>
                    {item.badge}
                  </span>
                )}
              </>
            )}
          </Link>
        ) : (
          <div
            className={cn(
              'flex items-center px-3 py-2 text-sm font-medium text-faint cursor-default rounded-lg',
              level > 0 && 'pl-6',
              collapsed && level === 0 && 'justify-center'
            )}
          >
            {item.icon && (
              <span className={cn(
                'flex-shrink-0',
                collapsed ? 'mx-auto' : 'mr-3'
              )}>
                {item.icon}
              </span>
            )}

            {!collapsed && <span>{item.title}</span>}
          </div>
        )}

        {hasChildren && !collapsed && (
          <div className="mt-1 space-y-1">
            {item.children!.map(child => renderMenuItem(child, level + 1))}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className={cn('flex flex-col h-full bg-card', className)}>
      {/* Logo Section */}
      <div className="flex h-14 flex-shrink-0 items-center justify-between gap-2 border-b border-border px-3">
        <div className={cn('flex min-w-0 items-center gap-2.5', collapsed && 'mx-auto')}>
          <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <Activity className="h-4 w-4" />
          </div>
          {!collapsed && (
            <div className="min-w-0">
              <h2 className="truncate text-sm font-semibold tracking-tight text-foreground">板块强度</h2>
              <p className="text-[10px] font-medium text-muted-foreground">SIGNAL WORKBENCH</p>
            </div>
          )}
        </div>
        <button
          onClick={() => onCollapse?.(!collapsed)}
          className={cn('hidden h-8 w-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground md:inline-flex', collapsed && 'absolute left-14 translate-x-1/2 border border-border bg-card shadow-subtle')}
          aria-label={collapsed ? '展开侧边栏' : '收起侧边栏'}
          title={collapsed ? '展开侧边栏' : '收起侧边栏'}
        >
          <ChevronLeft className={cn('h-4 w-4 transition-transform duration-200', collapsed && 'rotate-180')} />
        </button>
      </div>

      {/* Navigation Menu */}
      <nav className="custom-scrollbar flex-1 space-y-1 overflow-y-auto px-2 py-3 min-h-0" aria-label="主导航">
        {items.map(item => renderMenuItem(item))}
      </nav>

      {/* Theme Section */}
      <div className="flex flex-shrink-0 border-t border-border p-3">
        <ThemeToggle
          compact={collapsed}
          className={collapsed ? 'mx-auto' : 'w-full justify-start'}
        />
      </div>

      {/* User Section */}
      {isAuthenticated && (
        <div className="border-t border-border p-3 flex-shrink-0">
          {collapsed ? (
            <div className="flex flex-col items-center space-y-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary-light text-sm font-semibold text-primary">
                {user?.email?.charAt(0).toUpperCase() || 'U'}
              </div>
              <button
                onClick={handleLogout}
                className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
                title="退出登录"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-md bg-primary-light text-sm font-semibold text-primary">
                  {user?.email?.charAt(0).toUpperCase() || 'U'}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-foreground truncate">
                    {user?.username || user?.email || '用户'}
                  </p>
                </div>
              </div>
              <button
                onClick={handleLogout}
                className="flex w-full items-center justify-center space-x-1.5 rounded-md px-2.5 py-2 text-xs font-medium text-muted-foreground transition-colors duration-200 hover:bg-destructive/10 hover:text-destructive"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span>退出登录</span>
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default Sidebar
