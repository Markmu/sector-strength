import React from 'react'
import { cn } from '@/lib/utils'

export interface LayoutProps {
  children: React.ReactNode
  className?: string
  header?: React.ReactNode
  sidebar?: React.ReactNode
  footer?: React.ReactNode
  sidebarCollapsed?: boolean
  sidebarOpen?: boolean
  onSidebarClose?: () => void
}

const Layout = ({
  children,
  className,
  header,
  sidebar,
  footer,
  sidebarCollapsed = false,
  sidebarOpen = false,
  onSidebarClose
}: LayoutProps) => {
  return (
    <div className={cn('min-h-[100dvh] bg-background flex flex-col overflow-hidden', className)}>
      {header && (
        <header className="bg-card border-b border-border sticky top-0 z-30 flex-shrink-0">
          {header}
        </header>
      )}

      <div className={cn('flex flex-1 min-h-0', sidebar ? 'overflow-hidden' : '')}>
        {sidebar && sidebarOpen && (
          <button
            type="button"
            className="fixed inset-0 z-30 bg-foreground/24 md:hidden"
            onClick={onSidebarClose}
            aria-label="关闭导航"
          />
        )}

        {sidebar && (
          <aside className={cn(
            'fixed inset-y-0 left-0 z-40 h-[100dvh] bg-card border-r border-border flex flex-col transition-transform duration-200 flex-shrink-0 md:static md:z-auto md:h-full md:translate-x-0 md:transition-[width]',
            sidebarOpen ? 'translate-x-0' : '-translate-x-full',
            sidebarCollapsed ? 'w-16' : 'w-64'
          )}>
            {sidebar}
          </aside>
        )}

        <main className={cn(
          'flex-1 min-w-0 overflow-y-auto custom-scrollbar',
          sidebar ? 'p-0' : 'p-4 md:p-6'
        )}>
          {children}
        </main>
      </div>

      {footer && (
        <footer className="bg-card border-t border-border py-4 flex-shrink-0">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            {footer}
          </div>
        </footer>
      )}
    </div>
  )
}

export default Layout
