'use client'

/**
 * 轻量下拉选择器（公共通用组件）
 *
 * 满足 E2E spec 的选择器约定：
 * - trigger 为 <button role="combobox">（spec 用 getByRole('button').filter({ hasText }) 命中）
 * - 选项为 <div role="option">（spec 用 getByRole('option', { name }) 命中）
 *
 * 项目无 shadcn Select / radix Select，故自实现一个最小可用版本。
 */
import React, { useEffect, useRef, useState } from 'react'
import { ChevronDownIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface SimpleSelectOption {
  value: string
  label: string
}

export interface SimpleSelectProps {
  value: string
  options: SimpleSelectOption[]
  onChange: (value: string) => void
  placeholder?: string
  /** 渲染 trigger 时附加的 data-testid（供 spec 退化定位） */
  testId?: string
  className?: string
  ariaLabel?: string
}

export default function SimpleSelect({
  value,
  options,
  onChange,
  placeholder = '请选择',
  testId,
  className,
  ariaLabel,
}: SimpleSelectProps) {
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const listboxId = `simple-select-listbox-${testId ?? 'default'}`

  // 点击外部关闭
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false)
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
    return
  }, [isOpen])

  const selected = options.find((opt) => opt.value === value)

  const handleSelect = (val: string) => {
    onChange(val)
    setIsOpen(false)
  }

  return (
    <div ref={containerRef} className={cn('relative inline-block', className)}>
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-controls={isOpen ? listboxId : undefined}
        aria-label={ariaLabel}
        data-testid={testId}
        onClick={() => setIsOpen((v) => !v)}
        className="inline-flex items-center justify-between gap-2 min-w-[140px] px-3 py-2 text-sm border border-border rounded-lg bg-card text-foreground hover:border-muted-foreground transition-colors focus:outline-none focus:ring-2 focus:ring-primary"
      >
        <span className={cn('truncate', !selected && 'text-muted-foreground')}>
          {selected ? selected.label : placeholder}
        </span>
        <ChevronDownIcon
          className={cn(
            'w-4 h-4 text-muted-foreground transition-transform',
            isOpen && 'rotate-180'
          )}
        />
      </button>

      {isOpen && (
        <ul
          role="listbox"
          id={listboxId}
          className="absolute z-50 left-0 mt-1 min-w-full w-max max-w-[280px] bg-popover/95 backdrop-blur-sm border border-border rounded-lg shadow-xl max-h-80 overflow-y-auto py-1"
        >
          {options.map((opt) => {
            const isSelected = opt.value === value
            return (
              <li key={opt.value} role="presentation">
                <div
                  role="option"
                  aria-selected={isSelected}
                  onClick={() => handleSelect(opt.value)}
                  className={cn(
                    'px-3 py-2 text-sm cursor-pointer transition-colors whitespace-nowrap',
                    isSelected
                      ? 'bg-primary/10 text-primary font-medium'
                      : 'text-foreground hover:bg-background'
                  )}
                >
                  {opt.label}
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
