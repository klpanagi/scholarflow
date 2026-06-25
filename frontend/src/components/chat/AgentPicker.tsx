import { useState, useMemo } from 'react'
import { useAgentConfigs } from '@/hooks/useAgentConfigs'
import { ROLE_LABELS, type AgentConfig, type AgentRole } from '@/types/chat'
import { Skeleton } from '@/components/ui/skeleton'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { Bot, Search, Star, Cpu } from 'lucide-react'

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface AgentPickerProps {
  /** Currently selected agent config ID. */
  value: string | null
  /** Callback when the user selects an agent. */
  onChange: (id: string) => void
  /** Disable the whole picker (e.g. while creating session). */
  disabled?: boolean
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function groupByRole(configs: AgentConfig[]): Map<AgentRole, AgentConfig[]> {
  const map = new Map<AgentRole, AgentConfig[]>()
  for (const cfg of configs) {
    const role = cfg.role as AgentRole
    const arr = map.get(role) ?? []
    arr.push(cfg)
    map.set(role, arr)
  }
  // Stable sort: default agents first within each group
  for (const arr of map.values()) {
    arr.sort((a, b) => {
      if (a.is_default && !b.is_default) return -1
      if (!a.is_default && b.is_default) return 1
      return a.name.localeCompare(b.name)
    })
  }
  return map
}

/** Ordered list of roles to render (roles not in configs are skipped). */
const ROLE_ORDER: AgentRole[] = [
  'researcher',
  'writer',
  'reviewer',
  'deep_reviewer',
  'debater',
  'recommender',
  'manager',
  'revision',
  'review_writer',
]

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function LoadingSkeleton() {
  return (
    <div className="space-y-3">
      {[1, 2, 3].map((i) => (
        <div key={i} className="space-y-2">
          <Skeleton className="h-3 w-20" />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {[1, 2].map((j) => (
              <Skeleton key={j} className="h-[72px] w-full rounded-lg" />
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center gap-3 py-10 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-muted/50">
        <Bot aria-hidden="true" className="h-6 w-6 text-muted-foreground/40" />
      </div>
      <p className="text-sm text-muted-foreground/60">
        No agent configurations found.
      </p>
      <p className="text-xs text-muted-foreground/40">
        The backend will auto-seed default agents on first API call.
      </p>
    </div>
  )
}

function AgentCard({
  agent,
  selected,
  disabled,
  onSelect,
}: {
  agent: AgentConfig
  selected: boolean
  disabled: boolean
  onSelect: () => void
}) {
  const roleLabel = ROLE_LABELS[agent.role as AgentRole] ?? agent.role

  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onSelect}
      className={cn(
        'flex items-start gap-3 w-full text-left rounded-lg border p-3 transition-all duration-150',
        'hover:bg-accent/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        'disabled:opacity-40 disabled:cursor-not-allowed',
        selected
          ? 'border-primary/50 bg-primary/5 ring-1 ring-primary/20'
          : 'border-border/40 bg-card/50',
      )}
      aria-pressed={selected}
      aria-label={`Select agent ${agent.name}`}
    >
      {/* Icon */}
      <div
        className={cn(
          'flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition-colors',
          selected
            ? 'bg-primary/15 text-primary'
            : 'bg-muted/60 text-muted-foreground/50',
        )}
      >
        <Bot aria-hidden="true" className="h-4 w-4" />
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0 space-y-1">
        <div className="flex items-center gap-1.5">
          <span className="text-sm font-medium truncate">{agent.name}</span>
          {agent.is_default && (
            <Star
              aria-label="Default agent"
              className="h-3 w-3 shrink-0 fill-amber-400 text-amber-400"
            />
          )}
        </div>

        <div className="flex items-center gap-1.5 flex-wrap">
          <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4 leading-none">
            {roleLabel}
          </Badge>
          <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4 leading-none border-primary/20 text-primary/70">
            {agent.model}
          </Badge>
        </div>

        <div className="flex items-center gap-2 text-[10px] text-muted-foreground/40">
          <span className="flex items-center gap-1">
            <Cpu aria-hidden="true" className="h-3 w-3" />
            {agent.provider}
          </span>
          <span>temp {agent.temperature}</span>
          <span>max {agent.max_tokens.toLocaleString()}</span>
        </div>

        {agent.tools.length > 0 && (
          <div className="flex flex-wrap gap-1 pt-0.5">
            {agent.tools.slice(0, 4).map((tool) => (
              <span
                key={tool}
                className="inline-flex items-center rounded bg-navy-500/10 px-1.5 py-0.5 text-[9px] font-medium text-muted-foreground/60"
              >
                {tool}
              </span>
            ))}
            {agent.tools.length > 4 && (
              <span className="text-[9px] text-muted-foreground/30">
                +{agent.tools.length - 4}
              </span>
            )}
          </div>
        )}
      </div>
    </button>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function AgentPicker({ value, onChange, disabled = false }: AgentPickerProps) {
  const { data: configs, isLoading } = useAgentConfigs()
  const [searchQuery, setSearchQuery] = useState('')

  const grouped = useMemo(() => {
    if (!configs) return new Map<AgentRole, AgentConfig[]>()
    const filtered = searchQuery.trim()
      ? configs.filter(
          (c) =>
            c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            (ROLE_LABELS[c.role as AgentRole] ?? c.role)
              .toLowerCase()
              .includes(searchQuery.toLowerCase()) ||
            c.model.toLowerCase().includes(searchQuery.toLowerCase()),
        )
      : configs
    return groupByRole(filtered)
  }, [configs, searchQuery])

  const totalAgents = configs?.length ?? 0
  const hasResults = grouped.size > 0

  if (isLoading) {
    return <LoadingSkeleton />
  }

  if (totalAgents === 0) {
    return <EmptyState />
  }

  return (
    <div className="space-y-3" role="radiogroup" aria-label="Select an agent">
      {/* Search */}
      <div className="relative">
        <Search
          aria-hidden="true"
          className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground/40"
        />
        <Input
          placeholder="Search agents by name, role, or model..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-8 h-9 text-sm"
          disabled={disabled}
          aria-label="Search agents"
        />
      </div>

      {/* Grouped list */}
      {!hasResults && searchQuery.trim() ? (
        <p className="text-xs text-muted-foreground/40 text-center py-4">
          No agents match &ldquo;{searchQuery}&rdquo;
        </p>
      ) : (
        <div className="space-y-3 max-h-[320px] overflow-y-auto pr-1">
          {ROLE_ORDER.map((role) => {
            const agents = grouped.get(role)
            if (!agents || agents.length === 0) return null

            return (
              <div key={role}>
                <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/40 px-1 mb-1.5">
                  {ROLE_LABELS[role]}
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {agents.map((agent) => (
                    <AgentCard
                      key={agent.id}
                      agent={agent}
                      selected={value === agent.id}
                      disabled={disabled}
                      onSelect={() => onChange(agent.id)}
                    />
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
