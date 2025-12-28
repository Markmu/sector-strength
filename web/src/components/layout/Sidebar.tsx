"use client";

import React from 'react'
import Link from 'next/link'
import { useRouter, usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { useAuth } from '@/contexts/AuthContext'
import { LogOut, User } from 'lucide-react'
import Button from '@/components/ui/Button'

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
  const router = useRouter()
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
              'group flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-all duration-200',
              active
                ? 'bg-gradient-to-r from-blue-600 to-blue-700 text-white shadow-md shadow-blue-200'
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100',
              level > 0 && 'pl-6',
              collapsed && level === 0 && 'justify-center'
            )}
          >
            {item.icon && (
              <span className={cn(
                'flex-shrink-0',
                collapsed ? 'mx-auto' : 'mr-3',
                active && 'text-white'
              )}>
                {item.icon}
              </span>
            )}

            {!collapsed && (
              <>
                <span className="flex-1">{item.title}</span>
                {item.badge && (
                  <span className={cn(
                    'ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                    active
                      ? 'bg-white/20 text-white'
                      : 'bg-primary-100 text-primary-800'
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
              'flex items-center px-3 py-2 text-sm font-medium text-gray-500 cursor-default rounded-lg',
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
    <div className={cn('flex flex-col h-full', className)}>
      {/* Logo Section */}
      <div className="flex items-center justify-between h-12 px-3 border-b border-gray-200 flex-shrink-0">
        {!collapsed && (
          <h2 className="text-base font-semibold text-gray-900">
            板块强度
          </h2>
        )}
        <button
          onClick={() => onCollapse?.(!collapsed)}
          className="p-1 rounded-md text-gray-500 hover:text-gray-900 hover:bg-gray-50"
        >
          <svg
            className={cn(
              'w-4 h-4 transition-transform duration-200',
              collapsed && 'rotate-180'
            )}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M11 19l-7-7 7-7m8 14l-7-7 7-7"
            />
          </svg>
        </button>
      </div>

      {/* Navigation Menu */}
      <nav className="flex-1 px-2 py-3 space-y-1 overflow-y-auto min-h-0">
        {items.map(item => renderMenuItem(item))}
      </nav>

      {/* User Section */}
      {isAuthenticated && (
        <div className="border-t border-gray-200 p-3 flex-shrink-0">
          {collapsed ? (
            <div className="flex flex-col items-center space-y-2">
              <div className="w-7 h-7 bg-primary-600 rounded-full flex items-center justify-center text-white text-sm font-medium">
                {user?.email?.charAt(0).toUpperCase() || 'U'}
              </div>
              <button
                onClick={handleLogout}
                className="p-1.5 rounded-md text-gray-500 hover:text-red-600 hover:bg-red-50"
                title="退出登录"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <div className="w-7 h-7 bg-primary-600 rounded-full flex items-center justify-center text-white text-sm font-medium flex-shrink-0">
                  {user?.email?.charAt(0).toUpperCase() || 'U'}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-gray-900 truncate">
                    {user?.username || user?.email || '用户'}
                  </p>
                </div>
              </div>
              <button
                onClick={handleLogout}
                className="w-full flex items-center justify-center space-x-1.5 px-2 py-1.5 text-xs text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors duration-200"
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