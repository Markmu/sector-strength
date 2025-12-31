import React from 'react'
import { cn } from '@/lib/utils'

export interface LayoutProps {
  children: React.ReactNode
  className?: string
  header?: React.ReactNode
  sidebar?: React.ReactNode
  footer?: React.ReactNode
  sidebarCollapsed?: boolean
}

const Layout = ({
  children,
  className,
  header,
  sidebar,
  footer,
  sidebarCollapsed = false
}: LayoutProps) => {
  return (
    <div className={cn('h-screen bg-[#f8f9fb] flex flex-col overflow-hidden', className)}>
      {header && (
        <header className="bg-white border-b border-[#e9ecef] sticky top-0 z-30 flex-shrink-0">
          {header}
        </header>
      )}

      <div className={cn('flex flex-1 min-h-0', sidebar ? 'overflow-hidden' : '')}>
        {sidebar && (
          <aside className={cn(
            'h-full bg-white border-r border-[#e9ecef] flex flex-col transition-all duration-200 flex-shrink-0',
            sidebarCollapsed ? 'w-16' : 'w-64'
          )}>
            {sidebar}
          </aside>
        )}

        <main className={cn(
          'flex-1 overflow-y-auto custom-scrollbar',
          sidebar ? 'p-6' : 'p-4 md:p-6'
        )}>
          {children}
        </main>
      </div>

      {footer && (
        <footer className="bg-white border-t border-[#e9ecef] py-4 flex-shrink-0">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            {footer}
          </div>
        </footer>
      )}
    </div>
  )
}

export default Layout
