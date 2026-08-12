import React from 'react'
import { LoaderCircle } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  icon?: React.ReactNode
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', loading, icon, children, disabled, ...props }, ref) => {
    const baseStyles = 'inline-flex items-center justify-center whitespace-nowrap font-medium transition-[background-color,border-color,color,box-shadow,transform] duration-200 focus:outline-none disabled:pointer-events-none disabled:opacity-50 active:translate-y-px rounded-lg'

    const variants = {
      primary: 'bg-primary text-primary-foreground hover:bg-primary-hover shadow-subtle',
      secondary: 'border border-transparent bg-secondary text-secondary-foreground hover:border-border hover:bg-muted',
      outline: 'border border-border bg-card text-foreground hover:border-primary/50 hover:bg-secondary',
      ghost: 'text-muted-foreground hover:text-foreground hover:bg-secondary',
      danger: 'bg-destructive text-destructive-foreground hover:bg-destructive/90 shadow-subtle',
    }

    const sizes = {
      sm: 'h-8 px-3 text-xs rounded-md',
      md: 'h-9 px-4 text-sm rounded-lg',
      lg: 'h-10 px-5 text-sm rounded-lg',
    }

    return (
      <button
        className={cn(
          baseStyles,
          variants[variant],
          sizes[size],
          className
        )}
        ref={ref}
        disabled={disabled || loading}
        {...props}
      >
        {loading && (
          <LoaderCircle className="-ml-0.5 mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
        )}
        {icon && !loading && <span className="mr-2">{icon}</span>}
        {children}
      </button>
    )
  }
)

Button.displayName = 'Button'

export default Button
