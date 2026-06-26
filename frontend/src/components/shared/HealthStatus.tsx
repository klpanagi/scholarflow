import { cn } from '@/lib/utils'

// ----- Types -----

export interface ProviderHealth {
  name: string
  status: 'healthy' | 'degraded' | 'unhealthy' | 'unknown'
  latency?: number
}

export interface HealthStatusProps {
  /** Array of LLM providers and their health statuses */
  providers: ProviderHealth[]
  /** Layout variant. Defaults to 'grid'. */
  variant?: 'grid' | 'compact'
  /** Additional class names for the wrapper */
  className?: string
}

// ----- Status visual config -----

interface StatusStyle {
  dot: string
  bg: string
  text: string
  label: string
}

const statusStyles: Record<ProviderHealth['status'], StatusStyle> = {
  healthy: {
    dot: 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]',
    bg: 'bg-emerald-500/10',
    text: 'text-emerald-500',
    label: 'Healthy',
  },
  degraded: {
    dot: 'bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.5)]',
    bg: 'bg-amber-500/10',
    text: 'text-amber-500',
    label: 'Degraded',
  },
  unhealthy: {
    dot: 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]',
    bg: 'bg-red-500/10',
    text: 'text-red-500',
    label: 'Unhealthy',
  },
  unknown: {
    dot: 'bg-navy-400 shadow-[0_0_8px_rgba(100,116,139,0.5)]',
    bg: 'bg-navy-400/10',
    text: 'text-navy-400',
    label: 'Unknown',
  },
}

const statusOrder: ProviderHealth['status'][] = [
  'healthy',
  'degraded',
  'unhealthy',
  'unknown',
]

/** Sort providers so unhealthy/degraded appear first */
function sortProviders(a: ProviderHealth, b: ProviderHealth): number {
  return statusOrder.indexOf(a.status) - statusOrder.indexOf(b.status)
}

function formatLatency(ms?: number): string | null {
  if (ms === undefined || ms === null) return null
  if (ms < 1000) return `${Math.round(ms)}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

// ----- Dot Component -----

function StatusDot({ status }: { status: ProviderHealth['status'] }) {
  const style = statusStyles[status]
  return (
    <span className="relative flex h-3 w-3 shrink-0">
      <span
        className={cn(
          'absolute inline-flex h-full w-full animate-ping rounded-full opacity-40',
          style.dot,
        )}
      />
      <span
        className={cn(
          'relative inline-flex h-3 w-3 rounded-full',
          style.dot,
        )}
      />
    </span>
  )
}

// ----- HealthStatus -----

/**
 * HealthStatus — A redesigned LLM provider health indicator.
 *
 * Displays each provider as a card with a status dot, provider name,
 * and optional latency. Supports grid and compact variants with
 * glassmorphism styling and gold accent hover effects.
 *
 * @example
 * ```tsx
 * <HealthStatus
 *   providers={[
 *     { name: 'OpenAI', status: 'healthy', latency: 342 },
 *     { name: 'Anthropic', status: 'degraded', latency: 1200 },
 *   ]}
 * />
 * ```
 */
export function HealthStatus({
  providers,
  variant = 'grid',
  className,
}: HealthStatusProps) {
  if (providers.length === 0) {
    return (
      <div
        className={cn(
          'rounded-lg border border-border/50 bg-card/40 px-5 py-8 text-center text-sm text-muted-foreground backdrop-blur-xl',
          className,
        )}
      >
        No providers configured
      </div>
    )
  }

  const sorted = [...providers].sort(sortProviders)

  if (variant === 'compact') {
    return (
      <div className={cn('space-y-1.5', className)} role="list">
        {sorted.map((provider) => {
          const style = statusStyles[provider.status]
          const latency = formatLatency(provider.latency)
          return (
            <div
              key={provider.name}
              role="listitem"
              className={cn(
                'flex items-center justify-between rounded-lg px-3 py-2',
                'border border-border/30 bg-card/40 backdrop-blur-xl',
                'transition-all duration-200',
                'hover:border-gold-500/40 hover:shadow-sm',
              )}
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <StatusDot status={provider.status} />
                <span className="truncate text-sm font-medium text-foreground">
                  {provider.name}
                </span>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {latency && (
                  <span className="text-xs tabular-nums text-muted-foreground">
                    {latency}
                  </span>
                )}
                <span
                  className={cn(
                    'rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider',
                    style.bg,
                    style.text,
                  )}
                >
                  {style.label}
                </span>
              </div>
            </div>
          )
        })}
      </div>
    )
  }

  // Grid variant
  return (
    <div
      className={cn(
        'grid gap-3 sm:grid-cols-2 lg:grid-cols-3',
        className,
      )}
      role="list"
    >
      {sorted.map((provider) => {
        const style = statusStyles[provider.status]
        const latency = formatLatency(provider.latency)
        return (
          <div
            key={provider.name}
            role="listitem"
            className={cn(
              'group relative overflow-hidden rounded-xl',
              'border border-border/40 bg-card/60 backdrop-blur-xl',
              'p-4 transition-all duration-200',
              'hover:border-gold-500/50 hover:shadow-lg hover:shadow-gold-500/5',
            )}
          >
            {/* Subtle gold accent line on hover */}
            <div className="absolute inset-x-0 top-0 h-0.5 scale-x-0 bg-gradient-to-r from-transparent via-gold-500/60 to-transparent transition-transform duration-300 group-hover:scale-x-100" />

            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3 min-w-0">
                <div className={cn('flex h-10 w-10 shrink-0 items-center justify-center rounded-full', style.bg)}>
                  <StatusDot status={provider.status} />
                </div>
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-foreground">
                    {provider.name}
                  </p>
                  {latency && (
                    <p className="mt-0.5 text-xs tabular-nums text-muted-foreground">
                      {latency} latency
                    </p>
                  )}
                </div>
              </div>
              <span
                className={cn(
                  'shrink-0 rounded-full px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wider',
                  style.bg,
                  style.text,
                )}
              >
                {style.label}
              </span>
            </div>
          </div>
        )
      })}
    </div>
  )
}

HealthStatus.displayName = 'HealthStatus'

export default HealthStatus
