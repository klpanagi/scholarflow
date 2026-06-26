import { Clock, Loader2, CheckCircle2, XCircle, Ban, Pause } from 'lucide-react'
import { cn } from '@/lib/utils'

// ----- Types -----

export type WorkflowStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'queued'
  | 'paused'

export interface WorkflowStageStatusProps {
  /** The stage execution status */
  status: WorkflowStatus
  /** Optional display name for the stage */
  name?: string
  /** Optional progress percentage (0-100) for running stages */
  progress?: number
  /** Size variant. Defaults to 'md'. */
  size?: 'sm' | 'md' | 'lg'
  /** Additional class names */
  className?: string
}

// ----- Status configs -----

interface StageStatusStyle {
  icon: React.ComponentType<{ className?: string }>
  color: string
  bg: string
  label: string
}

const stageStatusMap: Record<WorkflowStatus, StageStatusStyle> = {
  pending: {
    icon: Clock,
    color: 'text-navy-400 dark:text-navy-300',
    bg: 'bg-navy-500/10 dark:bg-navy-500/20',
    label: 'Pending',
  },
  running: {
    icon: Loader2,
    color: 'text-gold-500',
    bg: 'bg-gold-500/10 dark:bg-gold-500/20',
    label: 'Running',
  },
  completed: {
    icon: CheckCircle2,
    color: 'text-emerald-500',
    bg: 'bg-emerald-500/10 dark:bg-emerald-500/20',
    label: 'Completed',
  },
  failed: {
    icon: XCircle,
    color: 'text-red-500',
    bg: 'bg-red-500/10 dark:bg-red-500/20',
    label: 'Failed',
  },
  cancelled: {
    icon: Ban,
    color: 'text-navy-500 dark:text-navy-400',
    bg: 'bg-navy-500/10 dark:bg-navy-500/20',
    label: 'Cancelled',
  },
  queued: {
    icon: Clock,
    color: 'text-navy-400 dark:text-navy-300',
    bg: 'bg-navy-500/10 dark:bg-navy-500/20',
    label: 'Queued',
  },
  paused: {
    icon: Pause,
    color: 'text-amber-500',
    bg: 'bg-amber-500/10 dark:bg-amber-500/20',
    label: 'Paused',
  },
}

// ----- Size config -----

const sizeMap = {
  sm: { icon: 'h-4 w-4', container: 'h-8 w-8', text: 'text-xs', gap: 'gap-2' },
  md: { icon: 'h-5 w-5', container: 'h-10 w-10', text: 'text-sm', gap: 'gap-3' },
  lg: { icon: 'h-6 w-6', container: 'h-12 w-12', text: 'text-base', gap: 'gap-4' },
} as const

// ----- Progress bar -----

function ProgressBar({ value }: { value: number }) {
  const clamped = Math.max(0, Math.min(100, value))
  return (
    <div className="h-1.5 w-full max-w-[120px] overflow-hidden rounded-full bg-navy-200 dark:bg-navy-700">
      <div
        className="h-full rounded-full bg-gold-500 transition-all duration-700 ease-out"
        style={{ width: `${clamped}%` }}
      />
    </div>
  )
}

/**
 * WorkflowStageStatus — A compact stage status indicator for workflow pipelines.
 *
 * Shows a circular icon with status-appropriate color, an optional
 * stage name, the status label, and an optional progress bar
 * (useful for running stages).
 *
 * @example
 * ```tsx
 * <WorkflowStageStatus status="running" name="Literature Review" progress={65} />
 * <WorkflowStageStatus status="completed" name="Paper Review" />
 * <WorkflowStageStatus status="failed" name="Debate Stage" />
 * ```
 */
export function WorkflowStageStatus({
  status,
  name,
  progress,
  size = 'md',
  className,
}: WorkflowStageStatusProps) {
  const config = stageStatusMap[status]
  const sizes = sizeMap[size]
  const Icon = config.icon

  return (
    <div className={cn('flex items-center', sizes.gap, className)}>
      {/* Circular icon */}
      <div
        className={cn(
          'flex shrink-0 items-center justify-center rounded-full',
          sizes.container,
          config.bg,
        )}
      >
        <Icon
          className={cn(
            sizes.icon,
            config.color,
            status === 'running' && 'animate-spin',
          )}
        />
      </div>

      {/* Text + optional progress */}
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          {name && (
            <span
              className={cn(
                'truncate font-medium text-foreground',
                sizes.text,
              )}
            >
              {name}
            </span>
          )}
          <span
            className={cn(
              'shrink-0 font-medium',
              sizes.text,
              config.color,
            )}
          >
            {config.label}
          </span>
        </div>
        {status === 'running' && progress !== undefined && (
          <div className="mt-1">
            <ProgressBar value={progress} />
          </div>
        )}
      </div>
    </div>
  )
}

WorkflowStageStatus.displayName = 'WorkflowStageStatus'

export default WorkflowStageStatus
