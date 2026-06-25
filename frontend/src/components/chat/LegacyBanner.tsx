import { useState, useEffect, useCallback } from 'react'
import { AlertTriangle, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ChatSession } from '@/types/chat'

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface LegacyBannerProps {
  session: ChatSession
}

// ---------------------------------------------------------------------------
// localStorage helpers
// ---------------------------------------------------------------------------

const DISMISSED_KEY = 'academic-pal:legacy-banner-dismissed'

function getDismissedSet(): Set<string> {
  try {
    const raw = localStorage.getItem(DISMISSED_KEY)
    if (raw) {
      return new Set(JSON.parse(raw) as string[])
    }
  } catch {
    // ignore
  }
  return new Set()
}

function persistDismissed(set: Set<string>) {
  try {
    localStorage.setItem(DISMISSED_KEY, JSON.stringify([...set]))
  } catch {
    // ignore
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function LegacyBanner({ session }: LegacyBannerProps) {
  const [dismissed, setDismissed] = useState(() => getDismissedSet())

  // Sync on mount (in case another tab changed localStorage)
  useEffect(() => {
    setDismissed(getDismissedSet())
  }, [])

  const handleDismiss = useCallback(() => {
    setDismissed((prev) => {
      const next = new Set(prev)
      next.add(session.id)
      persistDismissed(next)
      return next
    })
  }, [session.id])

  // Only render for legacy sessions (no agent_config_id) that haven't been dismissed
  if (session.agent_config_id !== null || dismissed.has(session.id)) {
    return null
  }

  return (
    <div
      role="alert"
      className={cn(
        'flex items-start gap-3 mx-4 lg:mx-6 mb-3 p-3 rounded-lg',
        'bg-amber-500/10 border border-amber-500/20 text-amber-600 dark:text-amber-400',
      )}
    >
      <AlertTriangle
        aria-hidden="true"
        className="h-4 w-4 mt-0.5 shrink-0"
      />
      <p className="flex-1 text-xs leading-relaxed">
        This chat was created before agent-based routing was added. Responses may
        use a default model. Consider creating a new chat with a specific agent.
      </p>
      <button
        type="button"
        onClick={handleDismiss}
        className={cn(
          'shrink-0 rounded-md p-1 transition-colors',
          'hover:bg-amber-500/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        )}
        aria-label="Dismiss legacy banner"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  )
}
