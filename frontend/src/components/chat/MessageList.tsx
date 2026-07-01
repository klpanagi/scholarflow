import type React from 'react'
import { useRef, useEffect, useMemo } from 'react'
import { useStickToBottom } from 'use-stick-to-bottom'
import { cn } from '@/lib/utils'
import { MessageBubble, MessageBubbleSkeleton } from './MessageBubble'
import type { MessageBubbleProps } from './MessageBubble'
import { Bot, MessageSquare } from 'lucide-react'

/**
 * Internal message shape used by the list. Wraps bubble props
 * with a required `id` for React keys and `timestamp` for date grouping.
 */
export type ChatListMessage = MessageBubbleProps & {
  id: string
  timestamp: Date | string
}

/* ────────────────────────────────────────────── */
/*  Date grouping helpers                          */
/* ────────────────────────────────────────────── */

function isSameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  )
}

function formatDateHeader(raw: Date | string): string {
  const date = typeof raw === 'string' ? new Date(raw) : raw
  if (isNaN(date.getTime())) return ''

  const now = new Date()
  const yesterday = new Date(now)
  yesterday.setDate(yesterday.getDate() - 1)

  if (isSameDay(date, now)) return 'Today'
  if (isSameDay(date, yesterday)) return 'Yesterday'

  const sameYear = date.getFullYear() === now.getFullYear()
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: sameYear ? undefined : 'numeric',
  })
}

interface DateGroup {
  label: string
  messages: ChatListMessage[]
}

function groupByDate(messages: ChatListMessage[]): DateGroup[] {
  const groups: DateGroup[] = []

  for (const msg of messages) {
    const label = formatDateHeader(msg.timestamp!)
    const last = groups[groups.length - 1]

    if (last && last.label === label) {
      last.messages.push(msg)
    } else {
      groups.push({ label, messages: [msg] })
    }
  }

  return groups
}

/* ────────────────────────────────────────────── */
/*  Props                                         */
/* ────────────────────────────────────────────── */

export interface MessageListProps {
  /** Ordered array of chat messages to display */
  messages: ChatListMessage[]
  /** When true, shows skeleton loading placeholders */
  isLoading?: boolean
  /** When true, passes streaming state to the last assistant bubble */
  isStreaming?: boolean
  /** When true, shows a thinking indicator while the agent processes */
  isThinking?: boolean
  /** Error message from a failed stream, shown as an error banner */
  streamError?: string | null
  /** Custom empty state node. Defaults to a centered placeholder. */
  emptyState?: React.ReactNode
  /** Additional classes for the outer wrapper */
  className?: string
  /** Callback when user scrolls to top (for pagination) */
  onScrollToTop?: () => void
}

/* ────────────────────────────────────────────── */
/*  Component                                     */
/* ────────────────────────────────────────────── */

/**
 * MessageList — a scrollable container for chat messages with auto-scroll
 * to bottom, date-grouped headers, skeleton loading, and empty state.
 *
 * Uses `use-stick-to-bottom` for smooth sticky-to-bottom behavior that
 * works correctly with streaming content and respects user scroll position.
 *
 * @example
 * ```tsx
 * <MessageList
 *   messages={messages}
 *   isLoading={isLoading}
 *   isStreaming={isStreaming}
 *   emptyState={<EmptyState icon={MessageSquare} title="Start a conversation" />}
 * />
 * ```
 */
export function MessageList({
  messages,
  isLoading = false,
  isStreaming = false,
  isThinking = false,
  streamError = null,
  emptyState,
  className,
  onScrollToTop,
}: MessageListProps) {
  const { scrollRef, contentRef, isAtBottom, scrollToBottom } = useStickToBottom({
    initial: 'smooth' as const,
    resize: 'smooth' as const,
  })

  const topObserverRef = useRef<IntersectionObserver | null>(null)
  const topSentinelRef = useRef<HTMLDivElement | null>(null)

  // IntersectionObserver for scroll-to-top detection (pagination)
  useEffect(() => {
    if (!onScrollToTop || !topSentinelRef.current) return

    topObserverRef.current = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) {
          onScrollToTop()
        }
      },
      { threshold: 0.1 },
    )

    topObserverRef.current.observe(topSentinelRef.current)

    return () => {
      topObserverRef.current?.disconnect()
    }
  }, [onScrollToTop, messages.length])

  // Group messages by date
  const dateGroups = useMemo(() => groupByDate(messages), [messages])

  /* ── Empty state ── */
  if (!isLoading && messages.length === 0) {
    return (
      <div className={cn('flex flex-col items-center justify-center py-24', className)}>
        {emptyState ?? (
          <div className="flex flex-col items-center gap-3 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-gold-500/10">
              <MessageSquare aria-hidden="true" className="h-6 w-6 text-gold-500" />
            </div>
            <p className="text-sm font-medium text-muted-foreground">
              Start a conversation
            </p>
            <p className="max-w-[240px] text-xs text-muted-foreground/60">
              Send a message to begin chatting with the assistant.
            </p>
          </div>
        )}
      </div>
    )
  }

  /* ── Loading state ── */
  if (isLoading) {
    return (
      <div
        role="status"
        aria-live="polite"
        className={cn('flex flex-col gap-5 p-4', className)}
      >
        <MessageBubbleSkeleton />
        <MessageBubbleSkeleton />
        <MessageBubbleSkeleton />
      </div>
    )
  }

  /* ── Message list ── */
  return (
    <div
      ref={scrollRef}
      className={cn(
        'flex-1 overflow-y-auto overscroll-contain',
        'scrollbar-thin scrollbar-thumb-navy-200 dark:scrollbar-thumb-navy-700',
        className,
      )}
    >
      {/* Top sentinel for pagination detection */}
      {onScrollToTop && <div ref={topSentinelRef} className="h-px" />}

      <div
        ref={contentRef}
        role="log"
        aria-live="polite"
        aria-atomic="false"
        aria-relevant="additions text"
        aria-label="Chat messages"
        className="flex flex-col gap-5 p-4 pb-8"
      >
        {dateGroups.map((group) => (
          <div key={group.label} className="flex flex-col gap-3">
            {/* Date header */}
            <div className="flex items-center gap-3 px-1">
              <div className="h-px flex-1 bg-border/40" />
              <span className="shrink-0 text-[11px] font-medium tracking-wide text-muted-foreground/50 select-none uppercase">
                {group.label}
              </span>
              <div className="h-px flex-1 bg-border/40" />
            </div>

            {/* Messages in this date group */}
            {group.messages.map((msg, idx) => (
              <MessageBubble
                key={msg.id}
                role={msg.role}
                content={msg.content}
                timestamp={msg.timestamp}
                model={msg.model}
                provider={msg.provider}
                isStreaming={
                  isStreaming &&
                  idx === group.messages.length - 1 &&
                  msg.role === 'assistant'
                }
              />
            ))}
          </div>
        ))}

        {/* ── Thinking indicator ── */}
        {isThinking && !isStreaming && !streamError && (
          <div className="flex gap-3" aria-label="Agent is thinking">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-navy-100 dark:bg-navy-700 ring-1 ring-border/50">
              <Bot aria-hidden="true" className="h-4 w-4 text-navy-600 dark:text-navy-300" />
            </div>
            <div className="max-w-[80%] space-y-1">
              <span className="text-[11px] font-medium text-muted-foreground/70 select-none">
                Assistant
              </span>
              <div className="rounded-2xl rounded-tl-md bg-card/70 backdrop-blur-xl border border-border/40 shadow-xs px-5 py-4">
                <div className="flex items-center gap-1.5">
                  <span className="flex h-2 w-2 rounded-full bg-gold-500 animate-pulse" />
                  <span className="flex h-2 w-2 rounded-full bg-gold-500/60 animate-pulse [animation-delay:200ms]" />
                  <span className="flex h-2 w-2 rounded-full bg-gold-500/30 animate-pulse [animation-delay:400ms]" />
                  <span className="ml-1 text-xs text-muted-foreground/50">Thinking...</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── Error banner ── */}
        {streamError && (
          <div className="flex gap-3" role="alert">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-red-100 dark:bg-red-900/30 ring-1 ring-border/50">
              <Bot aria-hidden="true" className="h-4 w-4 text-red-500" />
            </div>
            <div className="max-w-[80%] space-y-1">
              <span className="text-[11px] font-medium text-muted-foreground/70 select-none">
                Assistant
              </span>
              <div className="rounded-2xl rounded-tl-md bg-red-50/80 dark:bg-red-950/30 border border-red-200/50 dark:border-red-800/40 shadow-xs px-4 py-3">
                <p className="text-sm text-red-700 dark:text-red-400 leading-relaxed">
                  {streamError}
                </p>
                <p className="text-xs text-red-500/60 mt-1">Response failed. Try sending your message again.</p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Scroll-to-bottom button when user has scrolled up */}
      {!isAtBottom && messages.length > 0 && (
        <button
          type="button"
          onClick={() => scrollToBottom()}
          className={cn(
            'fixed bottom-24 left-1/2 -translate-x-1/2 z-10',
            'flex items-center gap-1.5 rounded-full px-4 py-2',
            'bg-card/90 backdrop-blur-lg border border-border/50 shadow-lg',
            'text-xs font-medium text-muted-foreground',
            'hover:bg-accent hover:text-accent-foreground',
            'transition-all duration-200',
            'animate-in',
          )}
          aria-label="Scroll to bottom"
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="text-gold-500"
          >
            <path d="m6 9 6 6 6-6" />
          </svg>
          New messages
        </button>
      )}
    </div>
  )
}

MessageList.displayName = 'MessageList'

export default MessageList
