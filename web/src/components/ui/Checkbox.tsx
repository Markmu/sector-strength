'use client'

import React from 'react'
import { cn } from '@/lib/utils'

export interface CheckboxProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string
}

const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, label, id, checked, defaultChecked, onCheckedChange, ...props }, ref) => {
    const checkboxId = id || `checkbox-${React.useId()}`

    // 处理受控和非受控模式
    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      if (onCheckedChange) {
        onCheckedChange(e.target.checked)
      }
      if (props.onChange) {
        props.onChange(e)
      }
    }

    return (
      <div className={cn('inline-flex items-center', className)}>
        <div className="relative flex items-center">
          <input
            type="checkbox"
            id={checkboxId}
            ref={ref}
            checked={checked}
            defaultChecked={defaultChecked}
            onChange={handleChange}
            className={cn(
              'peer h-4 w-4 cursor-pointer appearance-none rounded border border-[#dee2e6]',
              'bg-white transition-all duration-200',
              'checked:border-cyan-500 checked:bg-cyan-500',
              'focus:outline-none focus:ring-2 focus:ring-cyan-100 focus:ring-offset-0',
              'disabled:cursor-not-allowed disabled:opacity-50'
            )}
            {...props}
          />
          {/* 自定义复选标记 */}
          <svg
            className={cn(
              'pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2',
              'h-3 w-3 text-white opacity-0 transition-opacity duration-200',
              'peer-checked:opacity-100'
            )}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={3}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
          </svg>
        </div>
        {label && (
          <label
            htmlFor={checkboxId}
            className="ml-2 text-sm text-[#1a1a2e] cursor-pointer select-none"
          >
            {label}
          </label>
        )}
      </div>
    )
  }
)

Checkbox.displayName = 'Checkbox'

export { Checkbox }
export default Checkbox
