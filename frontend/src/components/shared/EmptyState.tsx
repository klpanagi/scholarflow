import type React from 'react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'

/**
 * Props for the EmptyState component.
 */
export interface EmptyStateProps {
  /** Lucide icon component to display */
  icon?: React.ComponentType<{ className?: string }>
  /** Headline text */
  title: string
  /** Supporting description */
  description?: string
  /** Optional call-to-action configuration */
  action?: {
    label: string
    onClick?: () => void
    href?: string
  }
  /** Additional class names for the wrapper */
  className?: string
}

/**
 * EmptyState — A centered empty-state placeholder with an icon, title,
 * description, and optional call-to-action button.
 *
 * Use it when lists, search results, or filtered views have no data to show.
 *
 * @example
 * ```tsx
 * <EmptyState
 *   icon={Inbox}
 *   title="No papers yet"
 *   description="Upload your first paper to get started."
 *   action={{ label: "Upload paper", onClick: handleUpload }}
 * />
 * ```
 */
export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  const ActionTag = action?.href ? 'a' : Button

  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center px-6 py-16 text-center',
        className,
      )}
    >
      {Icon && (
        <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-gold-500/10">
          <Icon className="h-7 w-7 text-gold-500" />
        </div>
      )}

      <h3 className="mb-2 text-lg font-semibold text-foreground">
        {title}
      </h3>

      {description && (
        <p className="mb-6 max-w-sm text-sm text-muted-foreground">
          {description}
        </p>
      )}

      {action && (
        <ActionTag
          {...(action.href
            ? { href: action.href, className: cn('inline-flex items-center justify-center rounded-md bg-gold-500 px-4 py-2 text-sm font-medium text-white hover:bg-gold-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold-500 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50') }
            : {
                onClick: action.onClick,
                variant: 'default' as const,
                className: 'bg-gold-500 text-white hover:bg-gold-600 focus-visible:ring-gold-500',
              })}
        >
          {action.label}
        </ActionTag>
      )}
    </div>
  )
}

EmptyState.displayName = 'EmptyState'

export default EmptyState
