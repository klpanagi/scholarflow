import { motion, useReducedMotion } from 'framer-motion'
import { memo } from 'react'
import { cn } from '@/lib/utils'

// ----- Types -----

export interface Scores {
  quality: number
  novelty: number
  rigor: number
  clarity: number
}

export interface ScoreDisplayProps {
  /** The four academic scores (0-10 range) */
  scores: Scores
  /** Size variant. Defaults to 'md'. */
  size?: 'sm' | 'md' | 'lg'
  /** Layout direction. Defaults to 'grid'. */
  layout?: 'grid' | 'row'
  /** Additional class names */
  className?: string
}

// ----- Size config -----

const sizeConfig = {
  sm: { svg: 56, stroke: 4, label: 'text-[10px]', value: 'text-xs', gap: 'gap-2' },
  md: { svg: 72, stroke: 5, label: 'text-xs', value: 'text-sm', gap: 'gap-3' },
  lg: { svg: 96, stroke: 6, label: 'text-sm', value: 'text-base', gap: 'gap-4' },
} as const

// ----- Color helpers -----

function scoreColor(score: number): string {
  if (score >= 9) return 'stroke-emerald-500'
  if (score >= 7) return 'stroke-gold-500'
  if (score >= 5) return 'stroke-amber-500'
  return 'stroke-red-500'
}

function scoreTextColor(score: number): string {
  if (score >= 9) return 'text-emerald-500'
  if (score >= 7) return 'text-gold-500'
  if (score >= 5) return 'text-amber-500'
  return 'text-red-500'
}

// ----- Radial SVG -----

function ScoreRadial({
  label,
  score,
  size,
}: {
  label: string
  score: number
  size: 'sm' | 'md' | 'lg'
}) {
  const cfg = sizeConfig[size]
  const prefersReduced = useReducedMotion()
  const clamped = Math.max(0, Math.min(10, score))
  const progress = clamped / 10
  const center = cfg.svg / 2
  const radius = center - cfg.stroke
  const circumference = 2 * Math.PI * radius
  const offset = circumference * (1 - progress)
  const trackColor = 'stroke-navy-200 dark:stroke-navy-700'

  return (
    <div
      className="flex flex-col items-center gap-1"
      role="meter"
      aria-label={`${label} score`}
      aria-valuemin={0}
      aria-valuemax={10}
      aria-valuenow={clamped}
      aria-valuetext={`${label}: ${clamped.toFixed(1)} out of 10`}
    >
      <div className="relative" style={{ width: cfg.svg, height: cfg.svg }} aria-hidden="true">
        {/* Background ring */}
        <svg
          width={cfg.svg}
          height={cfg.svg}
          className="-rotate-90"
          viewBox={`0 0 ${cfg.svg} ${cfg.svg}`}
        >
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            strokeWidth={cfg.stroke}
            className={trackColor}
          />
          <motion.circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            strokeWidth={cfg.stroke}
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={prefersReduced ? false : { strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: offset }}
            transition={prefersReduced ? { duration: 0 } : { duration: 1, ease: 'easeOut' }}
            className={cn(scoreColor(clamped))}
          />
        </svg>
        {/* Center value */}
        <div className="absolute inset-0 flex items-center justify-center">
          <span
            className={cn(
              'font-semibold tabular-nums',
              scoreTextColor(clamped),
              cfg.value,
            )}
          >
            {clamped.toFixed(1)}
          </span>
        </div>
      </div>
      <span
        className={cn(
          'font-medium capitalize text-muted-foreground',
          cfg.label,
        )}
      >
        {label}
      </span>
    </div>
  )
}

// ----- Linear progress bar -----

function ScoreBar({
  label,
  score,
}: {
  label: string
  score: number
}) {
  const clamped = Math.max(0, Math.min(10, score))
  const pct = (clamped / 10) * 100

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium capitalize text-muted-foreground">
          {label}
        </span>
        <span
          className={cn(
            'text-xs font-semibold tabular-nums',
            scoreTextColor(clamped),
          )}
        >
          {clamped.toFixed(1)}
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-navy-200 dark:bg-navy-700">
        <div
          className={cn(
            'h-full rounded-full transition-all duration-700 ease-out',
            scoreColor(clamped).replace('stroke-', 'bg-'),
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

// ----- ScoreDisplay -----

const LABELS: { key: keyof Scores; label: string }[] = [
  { key: 'quality', label: 'Quality' },
  { key: 'novelty', label: 'Novelty' },
  { key: 'rigor', label: 'Rigor' },
  { key: 'clarity', label: 'Clarity' },
]

/**
 * ScoreDisplay — A 4-score display for academic metrics.
 *
 * Shows quality, novelty, rigor, and clarity scores using either
 * SVG radial progress bars (grid layout) or linear progress bars
 * (row layout). Each score ranges from 0-10 with color coding:
 * red (0-4), amber (5-6), gold (7-8), emerald (9-10).
 *
 * @example
 * ```tsx
 * <ScoreDisplay
 *   scores={{ quality: 8.5, novelty: 6.2, rigor: 7.8, clarity: 9.1 }}
 *   size="md"
 * />
 * ```
 */
function ScoreDisplayImpl({
  scores,
  size = 'md',
  layout = 'grid',
  className,
}: ScoreDisplayProps) {
  const cfg = sizeConfig[size]

  if (layout === 'row') {
    return (
      <div className={cn('flex flex-col', cfg.gap, className)}>
        {LABELS.map(({ key, label }) => (
          <ScoreBar key={key} label={label} score={scores[key]} />
        ))}
      </div>
    )
  }

  return (
    <div className={cn('grid grid-cols-2', cfg.gap, className)}>
      {LABELS.map(({ key, label }) => (
        <ScoreRadial
          key={key}
          label={label}
          score={scores[key]}
          size={size}
        />
      ))}
    </div>
  )
}

export const ScoreDisplay = /* @__PURE__ */ memo(ScoreDisplayImpl)
ScoreDisplay.displayName = 'ScoreDisplay'

export default ScoreDisplay
