import { useAgentConfigs } from '@/hooks/useAgentConfigs'
import { useAssetLibrary } from '@/hooks/useAssetLibrary'
import { ROLE_LABELS, type AgentRole, type ChatSession } from '@/types/chat'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import {
  SheetTrigger,
} from '@/components/ui/sheet'
import {
  Bot,
  FileText,
  GitFork,
  ChevronDown,
  Menu,
  Search,
} from 'lucide-react'
import { Input } from '@/components/ui/input'

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface ChatHeaderProps {
  /** The active chat session. */
  session: ChatSession
  /** Available model list for the switcher dropdown. */
  availableModels: { id: string; provider: string }[]
  /** Providers derived from availableModels. */
  providers: string[]
  /** Whether the model switcher dropdown is open. */
  showModelPicker: boolean
  /** Callback to toggle the model switcher. */
  onToggleModelPicker: () => void
  /** Search query for the model switcher. */
  modelSearchQuery: string
  /** Callback to set the model search query. */
  onModelSearchQueryChange: (query: string) => void
  /** Fork handler. */
  onFork: () => void
  /** Whether the fork button should be disabled (no messages). */
  forkDisabled: boolean
  /** Callback to select a model. */
  onSelectModel: (modelId: string) => void
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function AgentBadgeSkeleton() {
  return <Skeleton className="h-5 w-24 rounded-full" />
}

function AssetPillSkeleton() {
  return <Skeleton className="h-5 w-20 rounded-full" />
}

function AgentBadge({
  agentConfigId,
  configs,
  isLoading,
}: {
  agentConfigId: string | null
  configs: { id: string; name: string; role: string }[] | undefined
  isLoading: boolean
}) {
  if (isLoading) return <AgentBadgeSkeleton />

  // Legacy session — no agent assigned
  if (agentConfigId === null) {
    return (
      <Badge
        variant="outline"
        className="text-[10px] px-1.5 py-0 h-5 border-muted-foreground/20 text-muted-foreground/60 bg-muted/30 leading-none"
        aria-label="No agent assigned (legacy session)"
      >
        default
      </Badge>
    )
  }

  const agent = configs?.find((c) => c.id === agentConfigId)

  if (!agent) {
    return (
      <Badge
        variant="outline"
        className="text-[10px] px-1.5 py-0 h-5 border-amber-500/20 text-amber-500/70 bg-amber-500/5 leading-none"
        aria-label="Agent unavailable"
      >
        <Bot aria-hidden="true" className="h-2.5 w-2.5 mr-1" />
        (agent unavailable)
      </Badge>
    )
  }

  const roleLabel = ROLE_LABELS[agent.role as AgentRole] ?? agent.role

  return (
    <Badge
      variant="outline"
      className="text-[10px] px-1.5 py-0 h-5 border-primary/20 text-primary dark:text-primary bg-primary/5 leading-none gap-1"
      aria-label={`Agent: ${agent.name} (${roleLabel})`}
    >
      <Bot aria-hidden="true" className="h-2.5 w-2.5" />
      {agent.name}
      <span className="text-muted-foreground/50 font-normal">/ {roleLabel}</span>
    </Badge>
  )
}

function AssetPills({
  assetIds,
  assets,
  isLoading,
}: {
  assetIds: string[]
  assets: { id: string; title: string }[] | undefined
  isLoading: boolean
}) {
  if (assetIds.length === 0) return null

  if (isLoading) {
    return (
      <div className="flex items-center gap-1.5 overflow-x-auto scrollbar-none">
        {assetIds.slice(0, 3).map((id) => (
          <AssetPillSkeleton key={id} />
        ))}
      </div>
    )
  }

  return (
    <div className="flex items-center gap-1.5 overflow-x-auto scrollbar-none">
      {assetIds.map((id) => {
        const asset = assets?.find((a) => a.id === id)
        const label = asset?.title ?? '(paper unavailable)'
        return (
          <span
            key={id}
            className={cn(
              'inline-flex items-center gap-1 rounded-full px-2 py-0.5',
              'bg-muted/50 border border-border/40',
              'text-[10px] text-muted-foreground/70 whitespace-nowrap max-w-[160px]',
              'cursor-default select-none',
            )}
            title={label}
            aria-label={`Attached paper: ${label}`}
          >
            <FileText aria-hidden="true" className="h-2.5 w-2.5 shrink-0" />
            <span className="truncate">{label}</span>
          </span>
        )
      })}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function ChatHeader({
  session,
  availableModels,
  providers,
  showModelPicker,
  onToggleModelPicker,
  modelSearchQuery,
  onModelSearchQueryChange,
  onFork,
  forkDisabled,
  onSelectModel,
}: ChatHeaderProps) {
  const { data: agentConfigs, isLoading: configsLoading } = useAgentConfigs()
  const { data: assetLibrary, isLoading: assetsLoading } = useAssetLibrary(
    '',
    1,
    100,
  )

  const attachedAssets = assetLibrary?.items

  return (
    <div className="flex items-center justify-between border-b border-border/40 px-4 lg:px-6 h-14 shrink-0 bg-card/20 backdrop-blur-sm">
      {/* Left side: mobile menu + title + agent badge + asset pills */}
      <div className="flex items-center gap-3 min-w-0">
        <SheetTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden -ml-2.5 h-10 w-10 shrink-0"
            aria-label="Open conversations"
          >
            <Menu aria-hidden="true" className="h-4 w-4" />
          </Button>
        </SheetTrigger>
        <h2 className="text-sm font-semibold truncate">
          {session.title || 'Untitled'}
        </h2>
        <AgentBadge
          agentConfigId={session.agent_config_id}
          configs={agentConfigs}
          isLoading={configsLoading}
        />
        <AssetPills
          assetIds={session.asset_ids}
          assets={attachedAssets}
          isLoading={assetsLoading}
        />
        <Badge
          variant="outline"
          className="hidden sm:inline-flex text-[10px] px-1.5 py-0 h-5 border-primary/20 text-primary dark:text-primary bg-primary/5 leading-none"
        >
          {session.provider}
        </Badge>
        <Badge
          variant="secondary"
          className="hidden sm:inline-flex text-[10px] px-1.5 py-0 h-5 leading-none"
        >
          {session.model}
        </Badge>
      </div>

      {/* Right side: fork + model switcher */}
      <div className="flex items-center gap-1">
        <Button
          variant="ghost"
          size="sm"
          onClick={onFork}
          className="text-xs gap-1.5 text-muted-foreground/50 hover:text-foreground h-8"
          disabled={forkDisabled}
        >
          <GitFork aria-hidden="true" className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Fork</span>
        </Button>
        <div className="relative">
          <Button
            variant="ghost"
            size="sm"
            onClick={onToggleModelPicker}
            className="text-xs gap-1 text-muted-foreground/50 hover:text-foreground h-8"
          >
            Switch <ChevronDown aria-hidden="true" className="h-3 w-3" />
          </Button>
          {showModelPicker && (
            <div className="absolute right-0 top-full mt-1 w-72 bg-popover border rounded-xl shadow-lg z-50 p-2 animate-in fade-in zoom-in-95">
              <div className="relative mb-2">
                <Search aria-hidden="true" className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground/40" />
                <Input
                  placeholder="Search models..."
                  value={modelSearchQuery}
                  onChange={(e) => onModelSearchQueryChange(e.target.value)}
                  className="pl-8 h-9 text-sm"
                  aria-label="Search models"
                />
              </div>
              <div className="max-h-60 overflow-y-auto space-y-0.5">
                {providers.length === 0 && (
                  <p className="text-xs text-muted-foreground/40 px-2 py-4 text-center">
                    No models available
                  </p>
                )}
                {providers.map((provider) => {
                  const providerModels = availableModels.filter(
                    (m) =>
                      m.provider === provider &&
                      (modelSearchQuery === '' ||
                        m.id.toLowerCase().includes(modelSearchQuery.toLowerCase())),
                  )
                  if (providerModels.length === 0) return null
                  return (
                    <div key={provider}>
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/40 px-2 py-1.5">
                        {provider}
                      </p>
                      {providerModels.map((m) => (
                        <button
                          key={m.id}
                          onClick={() => onSelectModel(m.id)}
                          className="w-full text-left px-3 py-2 rounded-lg text-sm hover:bg-accent transition-colors"
                        >
                          <span className="font-medium">{m.id}</span>
                        </button>
                      ))}
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
