import { Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

/**
 * Props for the LoadingState component.
 */
export interface LoadingStateProps {
  /** Optional label displayed below the spinner */
  label?: string
  /** Spinner size variant. Defaults to 'md'. */
  size?: 'sm' | 'md' | 'lg'
  /** Additional class names to apply to the wrapper */
  className?: string
}

const sizeMap = {
  sm: { icon: 'h-4 w-4', text: 'text-xs' },
  md: { icon: 'h-8 w-8', text: 'text-sm' },
  lg: { icon: 'h-12 w-12', text: 'text-base' },
} as const

/**
 * LoadingState — A centered spinner with an optional descriptive label.
 *
 * Use it whenever data is being fetched or an async operation is in progress.
 *
 * @example
 * ```tsx
 * <LoadingState label="Loading papers..." size="md" />
 * ```
 */
export function LoadingState({
  label,
  size = 'md',
  className,
}: LoadingStateProps) {
  const { icon: iconSize, text: textSize } = sizeMap[size]

  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center py-16',
        className,
      )}
      role="status"
      aria-live="polite"
    >
      <Loader2
        className={cn('mb-3 animate-spin text-gold-500', iconSize)}
      />
      {label && (
        <p className={cn('font-medium text-muted-foreground', textSize)}>
          {label}
        </p>
      )}
      <span className="sr-only">Loading{label ? `: ${label}` : '…'}</span>
    </div>
  )
}

LoadingState.displayName = 'LoadingState'

export default LoadingState
