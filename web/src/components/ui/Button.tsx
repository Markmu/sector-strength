import React from 'react'
import { cn } from '@/lib/utils'

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  icon?: React.ReactNode
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', loading, icon, children, disabled, ...props }, ref) => {
    const baseStyles = 'inline-flex items-center justify-center font-medium transition-all duration-200 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed rounded-lg'

    const variants = {
      primary: 'bg-gradient-to-r from-cyan-400 to-cyan-500 text-white hover:from-cyan-500 hover:to-cyan-600 shadow-sm hover:shadow-md',
      secondary: 'bg-[#f1f3f5] text-[#1a1a2e] hover:bg-[#dee2e6]',
      outline: 'border border-[#dee2e6] bg-white text-[#1a1a2e] hover:bg-[#f8f9fb] hover:border-cyan-400',
      ghost: 'text-[#6c757d] hover:text-[#1a1a2e] hover:bg-[#f1f3f5]',
      danger: 'bg-red-500 text-white hover:bg-red-600 shadow-sm',
    }

    const sizes = {
      sm: 'px-3 py-1.5 text-sm rounded-md',
      md: 'px-5 py-2.5 text-base rounded-lg',
      lg: 'px-6 py-3 text-lg rounded-lg',
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
          <svg className="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        )}
        {icon && !loading && <span className="mr-2">{icon}</span>}
        {children}
      </button>
    )
  }
)

Button.displayName = 'Button'

export default Button
