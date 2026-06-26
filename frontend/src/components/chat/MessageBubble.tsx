import type React from 'react'
import { cn } from '@/lib/utils'
import { MarkdownRenderer } from '@/components/MarkdownRenderer'
import { Bot } from 'lucide-react'

/**
 * Props for the MessageBubble component — a single chat message renderer
 * that adapts its appearance based on role (user / assistant / system).
 */
export interface MessageBubbleProps {
  /** Message sender role */
  role: 'user' | 'assistant' | 'system'
  /** Message content. Strings are rendered as-is (markdown for assistant). */
  content: string | React.ReactNode
  /** Optional timestamp displayed below the bubble */
  timestamp?: Date | string
  /** When true, shows a blinking streaming cursor at the end of content */
  isStreaming?: boolean
  /** Model name badge shown for assistant messages */
  model?: string
  /** Provider badge shown for assistant messages */
  provider?: string
}

/* ────────────────────────────────────────────── */
/*  Helpers                                       */
/* ────────────────────────────────────────────── */

function formatTimestamp(ts: Date | string): string {
  const date = typeof ts === 'string' ? new Date(ts) : ts
  if (isNaN(date.getTime())) return ''
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function getInitials(): string {
  // Placeholder — can be wired to the user's actual name later
  return 'U'
}

/* ────────────────────────────────────────────── */
/*  Skeleton (used by MessageList)                */
/* ────────────────────────────────────────────── */

/**
 * A shimmer skeleton bubble for loading states.
 */
export function MessageBubbleSkeleton() {
  return (
    <div className="flex gap-3 animate-pulse">
      <div className="h-8 w-8 shrink-0 rounded-full bg-navy-200 dark:bg-navy-700" />
      <div className="max-w-[75%] space-y-2">
        <div className="h-3 w-20 rounded bg-navy-200 dark:bg-navy-700" />
        <div className="rounded-2xl rounded-tl-md bg-navy-100 dark:bg-navy-800/50 p-4">
          <div className="space-y-2">
            <div className="h-3 w-56 rounded bg-navy-200 dark:bg-navy-700" />
            <div className="h-3 w-40 rounded bg-navy-200 dark:bg-navy-700" />
            <div className="h-3 w-48 rounded bg-navy-200 dark:bg-navy-700" />
          </div>
        </div>
      </div>
    </div>
  )
}

/* ────────────────────────────────────────────── */
/*  Component                                     */
/* ────────────────────────────────────────────── */

/**
 * MessageBubble — renders a single chat message with role-specific styling.
 *
 * - **User**: right-aligned, gold accent border, initial-letter avatar.
 * - **Assistant**: left-aligned, glass-morphism card, Bot icon avatar.
 * - **System**: centered, muted, compact.
 *
 * Assistant content is rendered through <MarkdownRenderer> for rich text.
 * When `isStreaming` is true a blinking cursor (▌) is appended.
 *
 * @example
 * ```tsx
 * <MessageBubble
 *   role="assistant"
 *   content="Hello! How can I help?"
 *   timestamp={new Date()}
 *   model="gpt-4"
 *   provider="openai"
 * />
 * ```
 */
export function MessageBubble({
  role,
  content,
  timestamp,
  isStreaming,
  model,
  provider,
}: MessageBubbleProps) {
  const isUser = role === 'user'
  const isAssistant = role === 'assistant'
  const isSystem = role === 'system'

  return (
    <div
      className={cn(
        'flex gap-3 w-full',
        isUser && 'flex-row-reverse',
        isSystem && 'justify-center',
      )}
    >
      {/* ── Avatar ── */}
      {!isSystem && (
        <div
          className={cn(
            'flex h-8 w-8 shrink-0 items-center justify-center rounded-full ring-1 ring-border/50',
            isUser && 'bg-gold-500/15 text-gold-600 dark:text-gold-400',
            isAssistant && 'bg-navy-100 dark:bg-navy-700 text-navy-600 dark:text-navy-300',
          )}
          aria-hidden
        >
          {isUser ? (
            <span aria-hidden="true" className="text-xs font-bold leading-none select-none">
              {getInitials()}
            </span>
          ) : (
            <Bot aria-hidden="true" className="h-4 w-4" />
          )}
        </div>
      )}

      {/* ── Bubble column ── */}
      <div
        className={cn(
          'max-w-[80%] min-w-0 space-y-1',
          isSystem && 'text-center max-w-[90%]',
        )}
      >
        {/* ── Meta row (role label + badges) ── */}
        {!isSystem && (
          <div
            className={cn(
              'flex items-center gap-2 px-1',
              isUser && 'flex-row-reverse',
            )}
          >
            <span className="text-[11px] font-medium text-muted-foreground/70 select-none">
              {isUser ? 'You' : 'Assistant'}
            </span>

            {isAssistant && model && (
              <span className="rounded bg-gold-500/10 px-1.5 py-0.5 text-[10px] font-medium leading-none text-gold-600 dark:text-gold-400 select-none">
                {model}
              </span>
            )}

            {isAssistant && provider && (
              <span className="rounded bg-navy-100 px-1.5 py-0.5 text-[10px] font-medium leading-none text-navy-500 dark:bg-navy-700 dark:text-navy-300 select-none">
                {provider}
              </span>
            )}
          </div>
        )}

        {/* ── Bubble body ── */}
        <div
          className={cn(
            'relative',
            isUser && [
              'rounded-2xl rounded-tr-md',
              'bg-gold-500/8 border border-gold-500/15',
              'dark:bg-gold-500/10 dark:border-gold-500/20',
              'px-4 py-3',
            ],
            isAssistant && [
              'rounded-2xl rounded-tl-md',
              'bg-card/70 backdrop-blur-xl border border-border/40',
              'shadow-xs',
              'px-4 py-3',
            ],
            isSystem && [
              'rounded-lg bg-muted/40 px-4 py-2',
            ],
          )}
        >
          {/* ── Content ── */}
          <div className={cn(
            'text-sm leading-relaxed',
            isUser && 'text-foreground',
          )}>
            {isAssistant && typeof content === 'string' ? (
              <MarkdownRenderer content={content} streaming={!!isStreaming} />
            ) : typeof content === 'string' ? (
              <p className="whitespace-pre-wrap break-words">{content}</p>
            ) : (
              content
            )}

            {/* Streaming cursor */}
            {isStreaming && (
              <span
                className="inline-flex items-center ml-0.5 h-4"
                aria-label="Streaming response"
              >
                <span className="inline-block w-[2px] h-4 bg-gold-500 rounded-full animate-[blink_1s_step-end_infinite]" />
              </span>
            )}
          </div>
        </div>

        {/* ── Timestamp ── */}
        {timestamp && (
          <div className={cn('px-1', isUser && 'text-right')}>
            <span className="text-[11px] text-muted-foreground/40 select-none">
              {formatTimestamp(timestamp)}
            </span>
          </div>
        )}
      </div>
    </div>
  )
}

MessageBubble.displayName = 'MessageBubble'

export default MessageBubble
