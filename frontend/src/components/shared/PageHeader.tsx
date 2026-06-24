import type React from 'react'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'
import { fadeInUp, withReducedMotion, useReducedMotion } from '@/lib/motion'

/**
 * Props for the PageHeader component.
 */
export interface PageHeaderProps {
  /** Page title displayed in the display (Playfair Display) font */
  title: string
  /** Optional supporting description below the title */
  description?: string
  /** Slot for action buttons / controls rendered on the right side */
  actions?: React.ReactNode
  /** Additional class names for the wrapper */
  className?: string
}

/**
 * PageHeader — A reusable page header with a Playfair Display title,
 * optional description, and an actions slot.
 *
 * Includes a subtle gold accent line beneath the title for visual hierarchy.
 *
 * @example
 * ```tsx
 * <PageHeader
 *   title="My Papers"
 *   description="Manage your academic publications"
 *   actions={<Button>Add Paper</Button>}
 * />
 * ```
 */
export function PageHeader({
  title,
  description,
  actions,
  className,
}: PageHeaderProps) {
  const prefersReduced = useReducedMotion()

  return (
    <motion.div
      variants={withReducedMotion(fadeInUp, prefersReduced)}
      initial="hidden"
      animate="visible"
      className={cn('mb-8', className)}
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <h1 className="font-display text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
            {title}
          </h1>
          <div className="h-0.5 w-12 rounded-full bg-gold-500" />
          {description && (
            <p className="pt-1 text-sm text-muted-foreground">
              {description}
            </p>
          )}
        </div>
        {actions && (
          <div className="flex shrink-0 items-center gap-3">
            {actions}
          </div>
        )}
      </div>
    </motion.div>
  )
}

PageHeader.displayName = 'PageHeader'

export default PageHeader
