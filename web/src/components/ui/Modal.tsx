'use client';

import React, { useEffect, useRef } from 'react'
import { cn } from '@/lib/utils'
import Button from './Button'
import { X } from 'lucide-react'

export interface ModalProps {
  open: boolean
  onClose: () => void
  title?: string
  children: React.ReactNode
  footer?: React.ReactNode
  size?: 'sm' | 'md' | 'lg' | 'xl'
  closeOnOverlay?: boolean
  showCloseButton?: boolean
  className?: string
}

const Modal = ({
  open,
  onClose,
  title,
  children,
  footer,
  size = 'md',
  closeOnOverlay = true,
  showCloseButton = true,
  className
}: ModalProps) => {
  const modalRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    if (open) {
      document.addEventListener('keydown', handleEscape)
      document.body.style.overflow = 'hidden'
    }

    return () => {
      document.removeEventListener('keydown', handleEscape)
      document.body.style.overflow = 'unset'
    }
  }, [open, onClose])

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        closeOnOverlay &&
        modalRef.current &&
        !modalRef.current.contains(event.target as Node)
      ) {
        onClose()
      }
    }

    if (open) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [open, onClose, closeOnOverlay])

  if (!open) return null

  const sizeClasses = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl'
  }

  return (
    <div className="fixed inset-0 z-50 overflow-auto bg-foreground/35 flex items-center justify-center p-4">
      <div
        ref={modalRef}
        className={cn(
          'relative w-full rounded-xl border border-border bg-card text-card-foreground shadow-elevated',
          sizeClasses[size],
          className
        )}
      >
        {(title || showCloseButton) && (
          <div className="flex items-center justify-between px-5 py-4 border-b border-border">
            {title && (
              <h3 className="text-base font-semibold text-foreground">
                {title}
              </h3>
            )}
            {showCloseButton && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onClose}
                icon={<X className="h-4 w-4" />}
                aria-label="关闭"
              />
            )}
          </div>
        )}

        <div className="px-6 py-4">
          {children}
        </div>

        {footer && (
          <div className="px-5 py-4 border-t border-border">
            {footer}
          </div>
        )}
      </div>
    </div>
  )
}

export default Modal
