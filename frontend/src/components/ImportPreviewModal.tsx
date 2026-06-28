import { useState, useCallback } from 'react'
import { CheckCircle2, AlertTriangle, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ModalShell } from '@/components/shared/ModalShell'
import { confirmImport } from '@/lib/api'
import type {
  ImportPreviewPayload,
  ImportConflictPayload,
  ImportDecisionPayload,
  ImportResultPayload,
} from '@/types/chat'

// ────────────────────────────────────────────────────────────────────────────
// Props
// ────────────────────────────────────────────────────────────────────────────

interface ImportPreviewModalProps {
  preview: ImportPreviewPayload
  onClose: () => void
  onComplete: (result: ImportResultPayload) => void
}

// ────────────────────────────────────────────────────────────────────────────
// Conflict Card
// ────────────────────────────────────────────────────────────────────────────

function ConflictCard({
  conflict,
  decision,
  onDecisionChange,
}: {
  conflict: ImportConflictPayload
  decision: 'skip' | 'overwrite'
  onDecisionChange: (action: 'skip' | 'overwrite') => void
}) {
  return (
    <div className="mb-3 rounded-lg border border-border/50 bg-card p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-amber-500" />
          <span className="font-medium text-foreground">{conflict.name}</span>
          <Badge variant="outline" className="text-[10px]">
            {conflict.type === 'skill' ? 'Skill' : 'Agent Config'}
          </Badge>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex cursor-pointer items-center gap-1.5 text-xs">
            <input
              type="radio"
              name={conflict.conflict_id}
              checked={decision === 'skip'}
              onChange={() => onDecisionChange('skip')}
              className="accent-[hsl(var(--primary))]"
            />
            Skip
          </label>
          <label className="flex cursor-pointer items-center gap-1.5 text-xs">
            <input
              type="radio"
              name={conflict.conflict_id}
              checked={decision === 'overwrite'}
              onChange={() => onDecisionChange('overwrite')}
              className="accent-[hsl(var(--primary))]"
            />
            Overwrite
          </label>
        </div>
      </div>

      {conflict.differences.length > 0 && (
        <div className="rounded-md bg-muted/30 p-3">
          <p className="mb-1 text-xs font-medium text-muted-foreground">Differences:</p>
          <div className="space-y-1">
            {conflict.differences.map((field) => {
              const existing = conflict.existing[field]
              const incoming = conflict.incoming[field]
              return (
                <div key={field} className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-muted-foreground">{field}: </span>
                    <span className="font-mono text-destructive">
                      {String(existing ?? '\u2014')}
                    </span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">{field}: </span>
                    <span className="font-mono text-emerald-500">
                      {String(incoming ?? '\u2014')}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

// ────────────────────────────────────────────────────────────────────────────
// Main Modal
// ────────────────────────────────────────────────────────────────────────────

export default function ImportPreviewModal({
  preview,
  onClose,
  onComplete,
}: ImportPreviewModalProps) {
  const [decisions, setDecisions] = useState<Record<string, 'skip' | 'overwrite'>>({})
  const [isConfirming, setIsConfirming] = useState(false)
  const [result, setResult] = useState<ImportResultPayload | null>(null)

  const hasConflicts = preview.conflicts.length > 0

  const handleDecisionChange = useCallback(
    (conflictId: string, action: 'skip' | 'overwrite') => {
      setDecisions((prev) => ({ ...prev, [conflictId]: action }))
    },
    [],
  )

  const handleConfirm = useCallback(async () => {
    setIsConfirming(true)
    try {
      const decisionList: ImportDecisionPayload[] = preview.conflicts.map((c) => ({
        conflict_id: c.conflict_id,
        action: decisions[c.conflict_id] || 'skip',
      }))
      const importResult = await confirmImport({
        staging_token: preview.staging_token,
        decisions: decisionList,
      })
      setResult(importResult)
      setTimeout(() => {
        onComplete(importResult)
      }, 2000)
    } catch {
      setIsConfirming(false)
    }
  }, [preview, decisions, onComplete])

  const summary = preview.summary as Record<string, any> | undefined

  // ── Success state ──────────────────────────────────────────────────────
  if (result) {
    return (
      <ModalShell open onOpenChange={onClose} title="Import Complete" size="md">
        <div className="flex flex-col items-center gap-4 py-8">
          <CheckCircle2 className="h-12 w-12 text-emerald-500" />
          <p className="text-lg font-semibold text-foreground">Import Successful</p>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="rounded-lg bg-muted/50 p-3 text-center">
              <p className="text-2xl font-bold text-foreground">{result.skills_created}</p>
              <p className="text-xs text-muted-foreground">Skills created</p>
            </div>
            <div className="rounded-lg bg-muted/50 p-3 text-center">
              <p className="text-2xl font-bold text-foreground">{result.skills_updated}</p>
              <p className="text-xs text-muted-foreground">Skills updated</p>
            </div>
            <div className="rounded-lg bg-muted/50 p-3 text-center">
              <p className="text-2xl font-bold text-foreground">
                {result.agent_configs_created}
              </p>
              <p className="text-xs text-muted-foreground">Agents created</p>
            </div>
            <div className="rounded-lg bg-muted/50 p-3 text-center">
              <p className="text-2xl font-bold text-foreground">
                {result.agent_configs_updated}
              </p>
              <p className="text-xs text-muted-foreground">Agents updated</p>
            </div>
          </div>
          {result.errors.length > 0 && (
            <div className="w-full rounded-lg bg-destructive/10 p-3">
              <p className="text-xs font-medium text-destructive">Errors:</p>
              {result.errors.map((e, i) => (
                <p key={i} className="text-xs text-destructive/80">
                  {e}
                </p>
              ))}
            </div>
          )}
          <p className="text-xs text-muted-foreground">Closing automatically...</p>
        </div>
      </ModalShell>
    )
  }

  // ── Preview / Conflict state ───────────────────────────────────────────
  return (
    <ModalShell
      open
      onOpenChange={onClose}
      title="Import Preview"
      description="Review the items to be imported and resolve any conflicts."
      size="lg"
      footer={
        <div className="flex w-full items-center justify-between">
          <Button variant="outline" onClick={onClose} disabled={isConfirming}>
            Cancel
          </Button>
          <Button onClick={handleConfirm} disabled={isConfirming}>
            {isConfirming ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Importing...
              </>
            ) : (
              'Confirm Import'
            )}
          </Button>
        </div>
      }
    >
      <div className="space-y-6">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="rounded-lg border border-border/50 bg-muted/30 p-3 text-center">
            <p className="text-2xl font-bold text-foreground">
              {summary?.skills?.new ?? 0}
            </p>
            <p className="text-xs text-muted-foreground">New skills</p>
          </div>
          <div className="rounded-lg border border-border/50 bg-muted/30 p-3 text-center">
            <p className="text-2xl font-bold text-foreground">
              {summary?.skills?.conflicts ?? 0}
            </p>
            <p className="text-xs text-muted-foreground">Skill conflicts</p>
          </div>
          <div className="rounded-lg border border-border/50 bg-muted/30 p-3 text-center">
            <p className="text-2xl font-bold text-foreground">
              {summary?.agent_configs?.new ?? 0}
            </p>
            <p className="text-xs text-muted-foreground">New agents</p>
          </div>
          <div className="rounded-lg border border-border/50 bg-muted/30 p-3 text-center">
            <p className="text-2xl font-bold text-foreground">
              {summary?.agent_configs?.conflicts ?? 0}
            </p>
            <p className="text-xs text-muted-foreground">Agent conflicts</p>
          </div>
        </div>

        {!hasConflicts && (
          <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-4 text-center">
            <CheckCircle2 className="mx-auto mb-2 h-8 w-8 text-emerald-500" />
            <p className="font-medium text-foreground">All items will be imported as new</p>
            <p className="text-sm text-muted-foreground">
              No name conflicts detected. Click &ldquo;Confirm Import&rdquo; to proceed.
            </p>
          </div>
        )}

        {hasConflicts && (
          <div className="space-y-4">
            <h4 className="text-sm font-medium text-foreground">Resolve Conflicts</h4>

            {preview.conflicts.filter((c) => c.type === 'skill').length > 0 && (
              <div>
                <h5 className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Skills
                </h5>
                {preview.conflicts
                  .filter((c) => c.type === 'skill')
                  .map((conflict) => (
                    <ConflictCard
                      key={conflict.conflict_id}
                      conflict={conflict}
                      decision={decisions[conflict.conflict_id] || 'skip'}
                      onDecisionChange={(action) =>
                        handleDecisionChange(conflict.conflict_id, action)
                      }
                    />
                  ))}
              </div>
            )}

            {preview.conflicts.filter((c) => c.type === 'agent_config').length > 0 && (
              <div>
                <h5 className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Agents
                </h5>
                {preview.conflicts
                  .filter((c) => c.type === 'agent_config')
                  .map((conflict) => (
                    <ConflictCard
                      key={conflict.conflict_id}
                      conflict={conflict}
                      decision={decisions[conflict.conflict_id] || 'skip'}
                      onDecisionChange={(action) =>
                        handleDecisionChange(conflict.conflict_id, action)
                      }
                    />
                  ))}
              </div>
            )}
          </div>
        )}
      </div>
    </ModalShell>
  )
}
