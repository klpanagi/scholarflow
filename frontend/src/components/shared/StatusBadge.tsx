import { memo } from 'react'
import type React from 'react'
import { motion } from 'framer-motion'
import {
  Clock,
  Loader2,
  CheckCircle2,
  XCircle,
  Ban,
  Pause,
  AlertCircle,
  AlertTriangle,
  Info,
  Star,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useReducedMotion } from '@/lib/motion'

// ----- Types -----

export type StatusType =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'queued'
  | 'paused'
  | 'error'
  | 'success'
  | 'warning'
  | 'info'
  | 'default'

export interface StatusBadgeProps {
  /** The status to display */
  status: StatusType
  /** Display variant. Defaults to 'default'. */
  variant?: 'default' | 'outline'
  /** Optional label override (defaults to the status name capitalized) */
  label?: string
  /** Additional class names */
  className?: string
}

// ----- Status config -----

interface StatusConfig {
  icon: React.ComponentType<{ className?: string }>
  color: string
  bg: string
  border: string
}

const statusConfigMap: Record<StatusType, StatusConfig> = {
  pending: {
    icon: Clock,
    color: 'text-navy-400 dark:text-navy-300',
    bg: 'bg-navy-500/10',
    border: 'border-navy-500/20',
  },
  running: {
    icon: Loader2,
    color: 'text-gold-500',
    bg: 'bg-gold-500/10',
    border: 'border-gold-500/20',
  },
  completed: {
    icon: CheckCircle2,
    color: 'text-emerald-500',
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/20',
  },
  failed: {
    icon: XCircle,
    color: 'text-red-500',
    bg: 'bg-red-500/10',
    border: 'border-red-500/20',
  },
  cancelled: {
    icon: Ban,
    color: 'text-navy-500 dark:text-navy-400',
    bg: 'bg-navy-500/10',
    border: 'border-navy-500/20',
  },
  queued: {
    icon: Clock,
    color: 'text-navy-400 dark:text-navy-300',
    bg: 'bg-navy-500/10',
    border: 'border-navy-500/20',
  },
  paused: {
    icon: Pause,
    color: 'text-amber-500',
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/20',
  },
  error: {
    icon: AlertCircle,
    color: 'text-red-500',
    bg: 'bg-red-500/10',
    border: 'border-red-500/20',
  },
  success: {
    icon: CheckCircle2,
    color: 'text-emerald-500',
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/20',
  },
  warning: {
    icon: AlertTriangle,
    color: 'text-amber-500',
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/20',
  },
  info: {
    icon: Info,
    color: 'text-navy-400 dark:text-navy-300',
    bg: 'bg-navy-500/10',
    border: 'border-navy-500/20',
  },
  default: {
    icon: Star,
    color: 'text-gold-500',
    bg: 'bg-gold-500/10',
    border: 'border-gold-500/20',
  },
}

function capitalize(label: string): string {
  return label.charAt(0).toUpperCase() + label.slice(1)
}

/**
 * StatusBadge — A unified status badge component.
 *
 * Maps status strings to consistent icons and colors. Supports
 * 'default' (filled tint background) and 'outline' variants.
 *
 * @example
 * ```tsx
 * <StatusBadge status="completed" />
 * <StatusBadge status="running" variant="outline" label="In Progress" />
 * ```
 */
function StatusBadgeImpl({
  status,
  variant = 'default',
  label,
  className,
}: StatusBadgeProps) {
  const config = statusConfigMap[status]
  const prefersReduced = useReducedMotion()
  const Icon = config.icon
  const displayLabel = label ?? capitalize(status)
  const isRunning = status === 'running'

  if (variant === 'outline') {
    const Comp = isRunning ? motion.span : 'span'
    return (
      <Comp
        className={cn(
          'inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs font-medium',
          config.border,
          config.color,
          className,
        )}
        aria-label={`Status: ${displayLabel}`}
        {...(isRunning && !prefersReduced
          ? {
              animate: { scale: [1, 1.04, 1] },
              transition: {
                duration: 2,
                ease: 'easeInOut',
                repeat: Infinity,
                repeatType: 'reverse' as const,
              },
            }
          : {})}
      >
        <Icon
          aria-hidden="true"
          className={cn(
            'h-3.5 w-3.5 shrink-0',
            isRunning && 'animate-spin',
          )}
        />
        {displayLabel}
      </Comp>
    )
  }

  const Comp = isRunning ? motion.span : 'span'
  return (
    <Comp
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold',
        config.bg,
        config.color,
        className,
      )}
      aria-label={`Status: ${displayLabel}`}
      {...(isRunning && !prefersReduced
        ? {
            animate: { scale: [1, 1.04, 1] },
            transition: {
              duration: 2,
              ease: 'easeInOut',
              repeat: Infinity,
              repeatType: 'reverse' as const,
            },
          }
        : {})}
    >
      <Icon
        aria-hidden="true"
        className={cn(
          'h-3.5 w-3.5 shrink-0',
          isRunning && 'animate-spin',
        )}
      />
      {displayLabel}
    </Comp>
  )
}

export const StatusBadge = /* @__PURE__ */ memo(StatusBadgeImpl)
StatusBadge.displayName = 'StatusBadge'

export default StatusBadge
