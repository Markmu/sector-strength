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

    const baseStyles = 'block w-full px-3 py-2 text-sm border rounded-md transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed'

    const variants = {
      default: 'border-gray-300 bg-white text-gray-900 placeholder-gray-500 focus:border-primary-500 focus:ring-primary-500',
      error: 'border-danger-300 bg-danger-50 text-danger-900 placeholder-danger-300 focus:border-danger-500 focus:ring-danger-500',
    }

    return (
      <div className={cn(fullWidth && 'w-full', className)}>
        {label && (
          <label
            htmlFor={inputId}
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            {label}
          </label>
        )}

        <div className="relative">
          {startIcon && (
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <span className="text-gray-500 sm:text-sm">{startIcon}</span>
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
              <span className="text-gray-500 sm:text-sm">{endIcon}</span>
            </div>
          )}
        </div>

        {error && (
          <p className="mt-1 text-sm text-danger-600">
            {error}
          </p>
        )}

        {helperText && !error && (
          <p className="mt-1 text-sm text-gray-500">
            {helperText}
          </p>
        )}
      </div>
    )
  }
)

Input.displayName = 'Input'

export default Input