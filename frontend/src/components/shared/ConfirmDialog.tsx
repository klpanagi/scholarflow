import { AlertTriangle, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { ModalShell } from './ModalShell'

/**
 * Props for the ConfirmDialog component.
 */
export interface ConfirmDialogProps {
  /** Whether the confirmation dialog is visible */
  open: boolean
  /** Called when the dialog should open or close */
  onOpenChange: (open: boolean) => void
  /** Title displayed in the dialog header */
  title: string
  /** Description / body message explaining what's being confirmed */
  description: string
  /** Label for the confirm button. Defaults to 'Confirm' */
  confirmText?: string
  /** Label for the cancel button. Defaults to 'Cancel' */
  cancelText?: string
  /** Visual variant. Defaults to 'neutral'. */
  variant?: 'danger' | 'neutral'
  /** Callback invoked when the user confirms */
  onConfirm: () => void | Promise<void>
  /** Whether the confirm action is in progress (shows spinner) */
  loading?: boolean
}

/**
 * ConfirmDialog — A confirmation modal built on top of ModalShell.
 *
 * Supports two visual variants:
 * - `danger`: red destructive button, alert icon
 * - `neutral`: gold accent button, info icon
 *
 * Includes a loading state that disables the confirm button and shows a
 * spinner while the async action is in progress.
 *
 * @example
 * ```tsx
 * <ConfirmDialog
 *   open={isOpen}
 *   onOpenChange={setIsOpen}
 *   title="Delete paper?"
 *   description="This action cannot be undone."
 *   variant="danger"
 *   confirmText="Delete"
 *   onConfirm={handleDelete}
 *   loading={isDeleting}
 * />
 * ```
 */
export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  variant = 'neutral',
  onConfirm,
  loading = false,
}: ConfirmDialogProps) {
  const isDanger = variant === 'danger'

  const handleConfirm = async () => {
    await onConfirm()
  }

  return (
    <ModalShell
      open={open}
      onOpenChange={onOpenChange}
      size="sm"
      footer={
        <>
          <Button
            type="button"
            variant="ghost"
            onClick={() => onOpenChange(false)}
            disabled={loading}
          >
            {cancelText}
          </Button>
          <Button
            type="button"
            variant={isDanger ? 'destructive' : 'default'}
            onClick={handleConfirm}
            disabled={loading}
            className={cn(
              !isDanger &&
                'bg-gold-500 text-white hover:bg-gold-600 focus-visible:ring-gold-500',
            )}
          >
            {loading && (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            )}
            {confirmText}
          </Button>
        </>
      }
    >
      <div className="flex items-start gap-4">
        <div
          className={cn(
            'flex h-10 w-10 shrink-0 items-center justify-center rounded-full',
            isDanger
              ? 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400'
              : 'bg-gold-500/10 text-gold-500',
          )}
        >
          {isDanger ? (
            <AlertTriangle className="h-5 w-5" />
          ) : (
            <AlertTriangle className="h-5 w-5" />
          )}
        </div>
        <div className="min-w-0">
          <p className="text-sm font-medium text-foreground">{title}</p>
          <p className="mt-1 text-sm text-muted-foreground">
            {description}
          </p>
        </div>
      </div>
    </ModalShell>
  )
}

ConfirmDialog.displayName = 'ConfirmDialog'

export default ConfirmDialog
