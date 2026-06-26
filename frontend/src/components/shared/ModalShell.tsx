import { useEffect, useCallback } from 'react'
import { createPortal } from 'react-dom'
import { X } from 'lucide-react'
import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

/**
 * Props for the ModalShell component.
 */
export interface ModalShellProps {
  /** Whether the modal is visible */
  open: boolean
  /** Called when the modal should open or close */
  onOpenChange: (open: boolean) => void
  /** Optional title rendered in the modal header */
  title?: ReactNode
  /** Optional description rendered below the title */
  description?: ReactNode
  /** Body content of the modal */
  children: ReactNode
  /** Optional footer content (e.g. action buttons) */
  footer?: ReactNode
  /** Modal width variant. Defaults to 'md'. */
  size?: 'sm' | 'md' | 'lg' | 'xl'
}

const sizeClasses: Record<string, string> = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-xl',
}

/**
 * ModalShell — A reusable modal dialog rendered via `createPortal` to
 * `document.body`.
 *
 * Features:
 * - ESC key and overlay click to close
 * - Smooth scale-in animation and backdrop blur
 * - Gold-accented close button
 * - Header, scrollable body, and optional footer sections
 *
 * @example
 * ```tsx
 * <ModalShell
 *   open={isOpen}
 *   onOpenChange={setIsOpen}
 *   title="Edit Paper"
 *   footer={<Button>Save</Button>}
 * >
 *   <p>Modal body content goes here.</p>
 * </ModalShell>
 * ```
 */
export function ModalShell({
  open,
  onOpenChange,
  title,
  description,
  children,
  footer,
  size = 'md',
}: ModalShellProps) {
  // Close on ESC key press
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onOpenChange(false)
      }
    },
    [onOpenChange],
  )

  useEffect(() => {
    if (!open) return
    document.addEventListener('keydown', handleKeyDown)
    // Prevent body scroll when modal is open
    const originalOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = originalOverflow
    }
  }, [open, handleKeyDown])

  if (!open) return null

  const dialog = (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby={title ? 'modal-title' : undefined}
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm animate-in"
        onClick={() => onOpenChange(false)}
        aria-hidden="true"
      />

      {/* Content */}
      <div
        className={cn(
          'relative w-full animate-in overflow-hidden rounded-xl border border-border/50 bg-card/60 shadow-2xl backdrop-blur-xl flex flex-col max-h-[85dvh]',
          sizeClasses[size],
        )}
        style={{ animationDuration: '200ms' }}
      >
        {/* Header */}
        {(title || description) && (
          <div className="flex shrink-0 items-start justify-between gap-4 border-b border-border/50 px-6 py-4">
            <div className="min-w-0 flex-1">
              {title && (
                <h2
                  id="modal-title"
                  className="text-lg font-semibold text-foreground"
                >
                  {title}
                </h2>
              )}
              {description && (
                <p className="mt-1 text-sm text-muted-foreground">
                  {description}
                </p>
              )}
            </div>
            <button
              type="button"
              onClick={() => onOpenChange(false)}
              className="flex shrink-0 items-center justify-center rounded-full p-1.5 text-gold-500 transition-colors hover:bg-gold-500/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold-500 focus-visible:ring-offset-2"
              aria-label="Close modal"
            >
              <X aria-hidden="true" className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* Body */}
        <div className="flex-1 min-h-0 overflow-y-auto px-6 py-4">{children}</div>

        {/* Footer */}
        {footer && (
          <div className="flex shrink-0 items-center justify-end gap-3 border-t border-border/50 px-6 py-4">
            {footer}
          </div>
        )}
      </div>
    </div>
  )

  if (typeof document === 'undefined') {
    return dialog
  }

  return createPortal(dialog, document.body)
}

ModalShell.displayName = 'ModalShell'

export default ModalShell
