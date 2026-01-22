'use client'

import { HelpCircle } from 'lucide-react'
import type { HelpButtonProps } from './HelpButton.types'

export function HelpButton({ onClick, className = '' }: HelpButtonProps) {
  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center justify-center w-8 h-8 rounded-full bg-gray-100 hover:bg-gray-200 transition-colors ${className}`}
      aria-label="查看帮助"
      title="查看板块强弱分类说明"
      type="button"
    >
      <HelpCircle className="w-5 h-5 text-gray-600" strokeWidth={2} />
    </button>
  )
}
