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
    const generatedId = React.useId()
    const inputId = id || `input-${generatedId}`

    const errorId = `${inputId}-error`
    const helperId = `${inputId}-helper`
    const baseStyles = 'block h-9 w-full rounded-lg border px-3 text-sm transition-[background-color,border-color,box-shadow] duration-200 focus:outline-none focus:ring-2 focus:ring-ring/20 disabled:cursor-not-allowed disabled:bg-muted disabled:text-muted-foreground'

    const variants = {
      default: 'border-input bg-card text-foreground placeholder:text-faint focus:border-primary',
      error: 'border-destructive bg-destructive/5 text-foreground placeholder:text-faint focus:border-destructive focus:ring-destructive/15',
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
            aria-invalid={Boolean(error)}
            aria-describedby={error ? errorId : helperText ? helperId : undefined}
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
          <p id={errorId} className="mt-1.5 text-xs font-medium text-destructive" role="alert">
            {error}
          </p>
        )}

        {helperText && !error && (
          <p id={helperId} className="mt-1.5 text-xs text-muted-foreground">
            {helperText}
          </p>
        )}
      </div>
    )
  }
)

Input.displayName = 'Input'

export default Input
