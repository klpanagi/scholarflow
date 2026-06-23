import { useState, useRef, useCallback, useEffect } from 'react'
import { useAuthStore } from '@/stores/auth'

// --- Types matching backend ExecutionEvent ---

export interface ExecutionEvent {
  event_id: number
  execution_id: string
  event_type: string
  timestamp: string
  data: Record<string, unknown>
}

export type EventFilter = (ev: ExecutionEvent) => boolean

export interface UseWorkflowStreamOptions {
  /** Whether to connect immediately (default: true) */
  enabled?: boolean
  /** Optional filter for events to include in the events array */
  filter?: EventFilter
  /** Max events to keep in memory (default: 5000) */
  maxEvents?: number
  /** Reconnect delay base in ms (default: 1000) */
  reconnectDelay?: number
  /** Max reconnect delay in ms (default: 30000) */
  maxReconnectDelay?: number
}

export interface UseWorkflowStreamReturn {
  /** All events received so far (may be filtered) */
  events: ExecutionEvent[]
  /** Whether the SSE connection is currently open */
  isConnected: boolean
  /** Error message if connection failed */
  error: string | null
  /** Manually start connecting (if enabled=false) */
  connect: () => void
  /** Manually disconnect */
  disconnect: () => void
  /** Clear all stored events */
  clearEvents: () => void
}

const TERMINAL_EVENT_TYPES = new Set([
  'EXECUTION_COMPLETED',
  'EXECUTION_FAILED',
  'EXECUTION_CANCELLED',
])

export function useWorkflowStream(
  executionId: string,
  options: UseWorkflowStreamOptions = {},
): UseWorkflowStreamReturn {
  const {
    enabled = true,
    filter,
    maxEvents = 5000,
    reconnectDelay = 1000,
    maxReconnectDelay = 30000,
  } = options

  const [events, setEvents] = useState<ExecutionEvent[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const abortRef = useRef<AbortController | null>(null)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const lastEventIdRef = useRef<number>(0)
  const mountedRef = useRef(true)
  // Track whether we've received a terminal event — stop reconnecting
  const terminalRef = useRef(false)

  const disconnect = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }
    if (abortRef.current) {
      abortRef.current.abort()
      abortRef.current = null
    }
    setIsConnected(false)
  }, [])

  const clearEvents = useCallback(() => {
    setEvents([])
    lastEventIdRef.current = 0
  }, [])

  const connect = useCallback(() => {
    if (!executionId || terminalRef.current) return

    disconnect()

    const abortController = new AbortController()
    abortRef.current = abortController
    let attempt = 0

    const doConnect = async () => {
      if (!mountedRef.current || terminalRef.current) return

      const token = useAuthStore.getState().accessToken
      const url = `/api/workflows/results/${executionId}/stream?token=${encodeURIComponent(token || '')}`

      try {
        const response = await fetch(url, {
          headers: {
            'Last-Event-ID': String(lastEventIdRef.current),
          },
          signal: abortController.signal,
        })

        if (!response.ok) {
          // 410 = completed, no reconnection needed
          if (response.status === 410) {
            terminalRef.current = true
            setError('Execution already completed')
            setIsConnected(false)
            return
          }
          throw new Error(`SSE connection failed: ${response.status}`)
        }

        if (!mountedRef.current) return

        setIsConnected(true)
        setError(null)
        attempt = 0 // reset backoff on successful connection

        const reader = response.body?.getReader()
        if (!reader) throw new Error('No reader available')

        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const parts = buffer.split('\n\n')
          buffer = parts.pop() || '' // keep incomplete chunk in buffer

          for (const part of parts) {
            if (!part.trim() || part.startsWith(':')) continue // comment or heartbeat

            const dataLine = part.match(/^data: (.+)/ms)

            if (!dataLine) continue

            let parsed: ExecutionEvent
            try {
              parsed = JSON.parse(dataLine[1]) as ExecutionEvent
            } catch {
              continue // skip unparseable data
            }

            lastEventIdRef.current = parsed.event_id

            if (filter && !filter(parsed)) continue

            setEvents((prev) => {
              // Deduplicate by event_id
              if (prev.length > 0 && prev[prev.length - 1].event_id >= parsed.event_id) {
                return prev
              }
              const next = [...prev, parsed]
              // Trim to maxEvents
              if (next.length > maxEvents) {
                return next.slice(next.length - maxEvents)
              }
              return next
            })

            // Check for terminal event
            if (TERMINAL_EVENT_TYPES.has(parsed.event_type)) {
              terminalRef.current = true
              setIsConnected(false)
              return
            }
          }
        }
      } catch (err: unknown) {
        if (err instanceof Error && err.name === 'AbortError') return

        if (!mountedRef.current || terminalRef.current) return

        setError(err instanceof Error ? err.message : 'Connection lost')
        setIsConnected(false)

        // Exponential backoff reconnection
        const delay = Math.min(reconnectDelay * 2 ** attempt, maxReconnectDelay)
        attempt++

        reconnectTimerRef.current = setTimeout(() => {
          if (mountedRef.current && !terminalRef.current) {
            doConnect()
          }
        }, delay)
        return
      }

      // Stream ended without terminal event — reconnect
      if (mountedRef.current && !terminalRef.current) {
        setIsConnected(false)
        const delay = Math.min(reconnectDelay * 2 ** attempt, maxReconnectDelay)
        attempt++
        reconnectTimerRef.current = setTimeout(() => {
          if (mountedRef.current && !terminalRef.current) {
            doConnect()
          }
        }, delay)
      }
    }

    doConnect()
  }, [executionId, disconnect, filter, maxEvents, reconnectDelay, maxReconnectDelay])

  useEffect(() => {
    mountedRef.current = true
    terminalRef.current = false

    if (enabled && executionId) {
      connect()
    }

    return () => {
      mountedRef.current = false
      disconnect()
    }
  }, [enabled, executionId, connect, disconnect])

  return {
    events,
    isConnected,
    error,
    connect,
    disconnect,
    clearEvents,
  }
}
