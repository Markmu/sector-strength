import React from 'react'
import { cn } from '@/lib/utils'
import { LoaderCircle } from 'lucide-react'

export interface LoadingProps {
  size?: 'sm' | 'md' | 'lg'
  color?: 'primary' | 'secondary' | 'white'
  text?: string
  overlay?: boolean
  className?: string
}

const Loading = ({
  size = 'md',
  color = 'primary',
  text,
  overlay = false,
  className
}: LoadingProps) => {
  const sizes = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8'
  }

  const colors = {
    primary: 'text-primary-600',
    secondary: 'text-muted-foreground',
    white: 'text-primary-foreground'
  }

  const loadingSpinner = (
    <LoaderCircle
      className={cn(
        'animate-spin',
        sizes[size],
        colors[color],
        className
      )}
      aria-hidden="true"
    />
  )

  if (overlay) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/35 p-4">
        <div className="flex flex-col items-center space-y-3 rounded-xl border border-border bg-card p-6 shadow-elevated">
          {loadingSpinner}
          {text && (
            <p className="text-sm text-muted-foreground">{text}</p>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-center justify-center">
      <div className="flex flex-col items-center space-y-2">
        {loadingSpinner}
        {text && (
          <p className="text-sm text-muted-foreground">{text}</p>
        )}
      </div>
    </div>
  )
}

export default Loading
export { Loading }
