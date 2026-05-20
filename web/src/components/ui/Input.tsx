import React from 'react'
import { cn } from '@/lib/utils'

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  helperText?: string
  startIcon?: React.ReactNode
  endIcon?: React.ReactNode
  fullWidth?: boolean
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({
    className,
    type = 'text',
    label,
    error,
    helperText,
    startIcon,
    endIcon,
    fullWidth = true,
    id,
    ...props
  }, ref) => {
    const inputId = id || `input-${React.useId()}`

    const baseStyles = 'block w-full px-4 py-2.5 text-sm border rounded-lg transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-primary-light disabled:opacity-50 disabled:cursor-not-allowed'

    const variants = {
      default: 'border-border bg-card text-foreground placeholder-faint focus:border-primary focus:ring-primary-light',
      error: 'border-red-300 bg-red-50 text-red-900 placeholder-red-300 focus:border-red-500 focus:ring-red-100',
    }

    return (
      <div className={cn(fullWidth && 'w-full', className)}>
        {label && (
          <label
            htmlFor={inputId}
            className="block text-sm font-medium text-foreground mb-1.5"
          >
            {label}
          </label>
        )}

        <div className="relative">
          {startIcon && (
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <span className="text-faint">{startIcon}</span>
            </div>
          )}

          <input
            type={type}
            id={inputId}
            className={cn(
              baseStyles,
              variants[error ? 'error' : 'default'],
              startIcon && 'pl-10',
              endIcon && 'pr-10',
              className
            )}
            ref={ref}
            {...props}
          />

          {endIcon && (
            <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
              <span className="text-faint">{endIcon}</span>
            </div>
          )}
        </div>

        {error && (
          <p className="mt-1.5 text-sm text-red-600">
            {error}
          </p>
        )}

        {helperText && !error && (
          <p className="mt-1.5 text-sm text-muted-foreground">
            {helperText}
          </p>
        )}
      </div>
    )
  }
)

Input.displayName = 'Input'

export default Input
