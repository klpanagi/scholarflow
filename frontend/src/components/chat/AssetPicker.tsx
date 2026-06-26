import { useState } from 'react'
import { useAssetLibrary } from '@/hooks/useAssetLibrary'
import { Checkbox } from '@/components/ui/checkbox'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { Search, FileText, X, AlertTriangle } from 'lucide-react'

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface AssetPickerProps {
  /** Currently selected asset IDs. */
  value: string[]
  /** Callback when selection changes. */
  onChange: (ids: string[]) => void
  /** Maximum number of assets that can be selected. */
  max?: number
  /** Disable the whole picker. */
  disabled?: boolean
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function LoadingSkeleton() {
  return (
    <div className="space-y-2">
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="flex items-center gap-3 p-2">
          <Skeleton className="h-4 w-4 shrink-0 rounded-sm" />
          <div className="flex-1 space-y-1">
            <Skeleton className="h-3.5 w-3/4" />
            <Skeleton className="h-2.5 w-1/2" />
          </div>
        </div>
      ))}
    </div>
  )
}

function EmptyState({ hasQuery }: { hasQuery: boolean }) {
  return (
    <div className="flex flex-col items-center gap-3 py-8 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-muted/50">
        <FileText aria-hidden="true" className="h-6 w-6 text-muted-foreground/40" />
      </div>
      <p className="text-sm text-muted-foreground/60">
        {hasQuery
          ? 'No papers match your search.'
          : 'No papers yet. Upload some in the Assets page.'}
      </p>
    </div>
  )
}

function AssetRow({
  asset,
  selected,
  disabled,
  onToggle,
}: {
  asset: { id: string; title: string; authors: string[]; year: number | null; doc_type: string }
  selected: boolean
  disabled: boolean
  onToggle: () => void
}) {
  const authorStr =
    asset.authors.length > 2
      ? `${asset.authors[0]}, ${asset.authors[1]}, et al.`
      : asset.authors.join(', ')

  return (
    <label
      className={cn(
        'flex items-start gap-3 p-2.5 rounded-lg cursor-pointer transition-colors',
        'hover:bg-accent/50',
        disabled && !selected && 'opacity-40 cursor-not-allowed',
      )}
    >
      <Checkbox
        checked={selected}
        disabled={disabled && !selected}
        onCheckedChange={onToggle}
        aria-label={`Select paper: ${asset.title}`}
        className="mt-0.5"
      />
      <div className="flex-1 min-w-0 space-y-0.5">
        <p className="text-sm font-medium leading-snug line-clamp-2">{asset.title}</p>
        <div className="flex items-center gap-2 text-[11px] text-muted-foreground/50">
          {authorStr && <span className="truncate">{authorStr}</span>}
          {asset.year && <span>{asset.year}</span>}
        </div>
      </div>
      <Badge
        variant="outline"
        className="shrink-0 text-[9px] px-1.5 py-0 h-4 leading-none border-border/40 text-muted-foreground/50"
      >
        {asset.doc_type}
      </Badge>
    </label>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function AssetPicker({
  value,
  onChange,
  max = 20,
  disabled = false,
}: AssetPickerProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const { data: response, isLoading } = useAssetLibrary(searchQuery)

  const items = response?.items ?? []
  const selectedCount = value.length
  const atCapacity = selectedCount >= max

  const handleToggle = (id: string) => {
    if (value.includes(id)) {
      onChange(value.filter((v) => v !== id))
    } else {
      if (value.length >= max) return
      onChange([...value, id])
    }
  }

  const handleRemoveSelected = (id: string) => {
    onChange(value.filter((v) => v !== id))
  }

  return (
    <div className="space-y-2.5" role="group" aria-label="Attach papers">
      {/* Counter */}
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground/60">
          Papers (optional)
        </span>
        <span
          className={cn(
            'text-xs font-medium tabular-nums',
            atCapacity ? 'text-amber-500' : 'text-muted-foreground/40',
          )}
        >
          {selectedCount} / {max} selected
        </span>
      </div>

      {/* Selected badges */}
      {selectedCount > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {items
            .filter((a) => value.includes(a.id))
            .map((asset) => (
              <Badge
                key={asset.id}
                variant="secondary"
                className="gap-1 pr-1 text-xs"
              >
                <span className="truncate max-w-[160px]">{asset.title}</span>
                <button
                  type="button"
                  onClick={() => handleRemoveSelected(asset.id)}
                  disabled={disabled}
                  className="ml-0.5 rounded-full p-0.5 hover:bg-muted/60 transition-colors"
                  aria-label={`Remove ${asset.title}`}
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            ))}
        </div>
      )}

      {/* Capacity warning */}
      {atCapacity && (
        <div className="flex items-center gap-1.5 text-[11px] text-amber-500/80">
          <AlertTriangle aria-hidden="true" className="h-3 w-3" />
          Maximum of {max} papers reached. Remove one to add another.
        </div>
      )}

      {/* Search */}
      <div className="relative">
        <Search
          aria-hidden="true"
          className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground/40"
        />
        <Input
          placeholder="Search papers..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-8 h-9 text-sm"
          disabled={disabled}
          aria-label="Search papers"
        />
      </div>

      {/* List */}
      <div className="max-h-[200px] overflow-y-auto border border-border/30 rounded-lg">
        {isLoading ? (
          <div className="p-2">
            <LoadingSkeleton />
          </div>
        ) : items.length === 0 ? (
          <EmptyState hasQuery={searchQuery.trim().length > 0} />
        ) : (
          <div className="divide-y divide-border/20">
            {items.map((asset) => (
              <AssetRow
                key={asset.id}
                asset={asset}
                selected={value.includes(asset.id)}
                disabled={disabled || atCapacity}
                onToggle={() => handleToggle(asset.id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
