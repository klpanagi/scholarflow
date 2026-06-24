import type React from 'react'
import { useRef, useState, useCallback, useEffect } from 'react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Send, Paperclip } from 'lucide-react'

/**
 * Props for the ChatInput component — a textarea-based chat input
 * with send and file-upload buttons.
 */
export interface ChatInputProps {
  /** Called when the user sends a message (Enter or Send click) */
  onSend: (content: string, files?: File[]) => void
  /** Disables the input and buttons */
  disabled?: boolean
  /** Placeholder text for the textarea */
  placeholder?: string
  /** Max content length */
  maxLength?: number
  /** Accepted file types for the file upload. Default: '.pdf,.docx,.txt,.md' */
  acceptFileTypes?: string
  /** When true, shows a pulsing streaming indicator */
  isStreaming?: boolean
  /** Additional classes for the outer wrapper */
  className?: string
}

/**
 * ChatInput — a chat message composer with auto-resizing textarea,
 * file upload trigger, and send button.
 *
 * Features:
 * - Auto-resizes the textarea as the user types
 * - Enter sends, Shift+Enter inserts newline
 * - Gold accent focus ring on the textarea
 * - File upload via hidden `<input type="file">`
 * - Streaming indicator (pulsing dot)
 *
 * @example
 * ```tsx
 * <ChatInput
 *   onSend={(content, files) => handleSend(content, files)}
 *   disabled={isLoading}
 *   isStreaming={isStreaming}
 * />
 * ```
 */
export function ChatInput({
  onSend,
  disabled = false,
  placeholder = 'Type a message...',
  maxLength,
  acceptFileTypes = '.pdf,.docx,.txt,.md',
  isStreaming = false,
  className,
}: ChatInputProps) {
  const [value, setValue] = useState('')
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  /* ── Auto-resize textarea ── */
  const adjustHeight = useCallback(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = '0px'
    const scrollHeight = el.scrollHeight
    el.style.height = `${Math.min(scrollHeight, 200)}px`
  }, [])

  useEffect(() => {
    adjustHeight()
  }, [value, adjustHeight])

  /* ── Handlers ── */
  const handleSend = useCallback(() => {
    const trimmed = value.trim()
    if (!trimmed || disabled) return

    onSend(trimmed, selectedFiles.length > 0 ? selectedFiles : undefined)

    setValue('')
    setSelectedFiles([])

    // Reset textarea height
    const el = textareaRef.current
    if (el) {
      el.style.height = 'auto'
    }
  }, [value, selectedFiles, disabled, onSend])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend],
  )

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files
      if (files && files.length > 0) {
        setSelectedFiles((prev) => [...prev, ...Array.from(files)])
      }
      // Reset so the same file can be re-selected
      e.target.value = ''
    },
    [],
  )

  const handleRemoveFile = useCallback((index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index))
  }, [])

  /* ── Characters remaining ── */
  const charCount = value.length
  const isNearLimit = maxLength !== undefined && charCount > maxLength * 0.85
  const isOverLimit = maxLength !== undefined && charCount > maxLength

  return (
    <div className={cn('space-y-2', className)}>
      {/* ── Selected file chips ── */}
      {selectedFiles.length > 0 && (
        <div className="flex flex-wrap gap-2 px-1">
          {selectedFiles.map((file, idx) => (
            <span
              key={`${file.name}-${idx}`}
              className={cn(
                'inline-flex items-center gap-1.5 rounded-full px-3 py-1',
                'bg-gold-500/10 border border-gold-500/20',
                'text-xs font-medium text-gold-700 dark:text-gold-300',
              )}
            >
              <Paperclip aria-hidden="true" className="h-3 w-3 shrink-0" />
              <span className="max-w-[150px] truncate">{file.name}</span>
        <button
          type="button"
          onClick={() => handleRemoveFile(idx)}
          className="ml-0.5 inline-flex h-4 w-4 items-center justify-center rounded-full hover:bg-gold-500/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring transition-colors"
          aria-label={`Remove ${file.name}`}
        >
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M18 6 6 18" /><path d="m6 6 12 12" />
          </svg>
        </button>
            </span>
          ))}
        </div>
      )}

      {/* ── Input row ── */}
      <div
        className={cn(
          'relative flex items-end gap-2 rounded-2xl',
          'bg-card/60 backdrop-blur-xl border border-border/50',
          'has-[textarea:focus]:border-gold-500/50 has-[textarea:focus]:ring-1 has-[textarea:focus]:ring-gold-500/20',
          'transition-all duration-200',
          'px-3 py-2.5',
        )}
      >
        {/* ── File upload button ── */}
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled}
          className={cn(
            'flex h-9 w-9 shrink-0 items-center justify-center rounded-lg',
            'text-muted-foreground/60 hover:text-gold-500 hover:bg-gold-500/10',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
            'disabled:opacity-30 disabled:pointer-events-none',
            'transition-colors duration-150',
          )}
          aria-label="Attach file"
        >
          <Paperclip aria-hidden="true" className="h-4 w-4" />
        </button>

        {/* ── Hidden file input ── */}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={acceptFileTypes}
          onChange={handleFileChange}
          className="hidden"
          tabIndex={-1}
        />

        {/* ── Textarea ── */}
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          maxLength={maxLength}
          disabled={disabled}
          rows={1}
          className={cn(
            'flex-1 resize-none bg-transparent',
            'px-1 py-1.5',
            'text-sm leading-relaxed text-foreground placeholder:text-muted-foreground/40',
            'outline-none border-none ring-0',
            'disabled:cursor-not-allowed disabled:opacity-50',
          )}
          aria-label="Chat message input"
        />

        {/* ── Streaming indicator ── */}
        {isStreaming && (
          <div className="flex h-9 w-9 shrink-0 items-center justify-center">
            <span className="flex h-2.5 w-2.5 rounded-full bg-gold-500 animate-pulse" />
          </div>
        )}

        {/* ── Send button ── */}
        {!isStreaming && (
          <Button
            type="button"
            size="icon"
            variant="default"
            onClick={handleSend}
            disabled={disabled || !value.trim()}
            className={cn(
              'h-9 w-9 shrink-0 rounded-lg',
              'bg-gold-500 text-white hover:bg-gold-600',
              'disabled:bg-navy-200 disabled:text-navy-400 dark:disabled:bg-navy-700',
              'transition-all duration-150',
            )}
            aria-label="Send message"
          >
            <Send aria-hidden="true" className="h-4 w-4" />
          </Button>
        )}
      </div>

      {/* ── Footer: char count + helper ── */}
      <div className="flex items-center justify-between px-1">
        <span className="text-[11px] text-muted-foreground/40">
          {placeholder && !value && (
            <>Enter to send · Shift+Enter for newline</>
          )}
        </span>

        {maxLength !== undefined && (
          <span
            className={cn(
              'text-[11px] tabular-nums transition-colors',
              isOverLimit && 'text-destructive font-medium',
              isNearLimit && !isOverLimit && 'text-amber-500',
              !isNearLimit && 'text-muted-foreground/40',
            )}
          >
            {charCount}/{maxLength}
          </span>
        )}
      </div>
    </div>
  )
}

ChatInput.displayName = 'ChatInput'

export default ChatInput
