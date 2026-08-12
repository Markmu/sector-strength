import React from 'react'
import { cn } from '@/lib/utils'

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'outlined' | 'elevated'
  padding?: 'none' | 'sm' | 'md' | 'lg'
}

export type CardHeaderProps = React.HTMLAttributes<HTMLDivElement>

export type CardBodyProps = React.HTMLAttributes<HTMLDivElement>

export type CardFooterProps = React.HTMLAttributes<HTMLDivElement>

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant = 'default', padding = 'md', children, ...props }, ref) => {
    const baseStyles = 'rounded-xl text-card-foreground'

    const variants = {
      default: 'bg-card border border-border shadow-subtle',
      outlined: 'bg-card border border-border',
      elevated: 'bg-card shadow-medium border border-border hover:border-primary/30 transition-[border-color,box-shadow] duration-200',
    }

    const paddings = {
      none: '',
      sm: 'p-3',
      md: 'p-4 md:p-5',
      lg: 'p-5 md:p-6',
    }

    return (
      <div
        className={cn(
          baseStyles,
          variants[variant],
          paddings[padding],
          className
        )}
        ref={ref}
        {...props}
      >
        {children}
      </div>
    )
  }
)

const CardHeader = React.forwardRef<HTMLDivElement, CardHeaderProps>(
  ({ className, children, ...props }, ref) => (
    <div
      className={cn('mb-4', className)}
      ref={ref}
      {...props}
    >
      {children}
    </div>
  )
)

const CardBody = React.forwardRef<HTMLDivElement, CardBodyProps>(
  ({ className, children, ...props }, ref) => (
    <div
      className={cn('', className)}
      ref={ref}
      {...props}
    >
      {children}
    </div>
  )
)

const CardFooter = React.forwardRef<HTMLDivElement, CardFooterProps>(
  ({ className, children, ...props }, ref) => (
    <div
      className={cn('mt-4 flex items-center', className)}
      ref={ref}
      {...props}
    >
      {children}
    </div>
  )
)

Card.displayName = 'Card'
CardHeader.displayName = 'CardHeader'
CardBody.displayName = 'CardBody'
CardFooter.displayName = 'CardFooter'

export { Card, CardHeader, CardBody, CardFooter }
