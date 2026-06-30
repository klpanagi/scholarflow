import { useState, useCallback, useRef, useEffect } from 'react'
import { api } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'

export type RevisionErrorType = 'network' | 'timeout' | 'sse' | 'unknown'

export interface RevisionError {
  message: string
  type: RevisionErrorType
}

export interface RevisionSession {
  id: string
  workflow_execution_id: string
  user_id: string
  agent_config_id?: string | null
  title: string
  created_at: string
  updated_at: string
}

export interface RevisionMessage {
  id: string
  revision_session_id: string
  role: 'user' | 'assistant'
  content: string
  extra_metadata?: Record<string, unknown> | null
  timestamp: string
}

export interface AttachedFile {
  file_key: string
  file_name: string
  uploaded_at: string
}

const selectionsKey = (sessionId: string) => `revision-session-${sessionId}-selections`
const attachmentsKey = (sessionId: string) => `revision-session-${sessionId}-attachments`

export function useRevisionSession() {
  const [session, setSession] = useState<RevisionSession | null>(null)
  const [messages, setMessages] = useState<RevisionMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const [availableStageIds, setAvailableStageIdsState] = useState<string[]>([])
  const [selectedStageIds, setSelectedStageIdsState] = useState<Set<string>>(new Set())
  const [attachedFiles, setAttachedFiles] = useState<AttachedFile[]>([])
  const [error, setError] = useState<RevisionError | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Hydrate from sessionStorage when the active session changes
  useEffect(() => {
    if (!session) {
      setSelectedStageIdsState(new Set())
      setAttachedFiles([])
      return
    }

    try {
      const selectionsRaw = sessionStorage.getItem(selectionsKey(session.id))
      if (selectionsRaw) {
        const parsed = JSON.parse(selectionsRaw)
        if (Array.isArray(parsed)) {
          setSelectedStageIdsState(new Set(parsed as string[]))
        } else {
          setSelectedStageIdsState(new Set())
        }
      } else {
        setSelectedStageIdsState(new Set())
      }
    } catch (err) {
      console.error('Failed to hydrate selected stages:', err)
      setSelectedStageIdsState(new Set())
    }

    try {
      const attachmentsRaw = sessionStorage.getItem(attachmentsKey(session.id))
      if (attachmentsRaw) {
        const parsed = JSON.parse(attachmentsRaw)
        if (Array.isArray(parsed)) {
          setAttachedFiles(parsed as AttachedFile[])
        } else {
          setAttachedFiles([])
        }
      } else {
        setAttachedFiles([])
      }
    } catch (err) {
      console.error('Failed to hydrate attachments:', err)
      setAttachedFiles([])
    }
  }, [session])

  useEffect(() => {
    if (!session) return
    try {
      sessionStorage.setItem(
        selectionsKey(session.id),
        JSON.stringify(Array.from(selectedStageIds)),
      )
    } catch (err) {
      console.error('Failed to persist selected stages:', err)
    }
  }, [selectedStageIds, session])

  useEffect(() => {
    if (!session) return
    try {
      sessionStorage.setItem(attachmentsKey(session.id), JSON.stringify(attachedFiles))
    } catch (err) {
      console.error('Failed to persist attachments:', err)
    }
  }, [attachedFiles, session])

  useEffect(() => {
    return () => {
      abortRef.current?.abort()
      if (timeoutRef.current) clearTimeout(timeoutRef.current)
    }
  }, [])

  const clearError = useCallback(() => setError(null), [])

  const setAvailableStageIds = useCallback((ids: string[]) => {
    setAvailableStageIdsState(ids)
    setSelectedStageIdsState((prev) => {
      // First time stages are loaded: default to ALL selected
      if (prev.size === 0) {
        return new Set(ids)
      }
      const pruned = new Set<string>()
      prev.forEach((id) => {
        if (ids.includes(id)) pruned.add(id)
      })
      return pruned
    })
  }, [])

  const setSelectedStageIds = useCallback(
    (updater: (prev: Set<string>) => Set<string>) => {
      setSelectedStageIdsState((prev) => {
        const next = updater(prev)
        return new Set(next)
      })
    },
    [],
  )

  const toggleStage = useCallback((stageId: string) => {
    setSelectedStageIdsState((prev) => {
      const next = new Set(prev)
      if (next.has(stageId)) {
        next.delete(stageId)
      } else {
        next.add(stageId)
      }
      return next
    })
  }, [])

  const uploadFile = useCallback(
    async (file: File): Promise<{ file_key: string; file_name: string }> => {
      if (!session) {
        throw new Error('No active revision session')
      }
      const formData = new FormData()
      formData.append('file', file)
      const token = useAuthStore.getState().accessToken
      const response = await fetch(`/api/revisions/sessions/${session.id}/upload`, {
        method: 'POST',
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: formData,
      })
      if (!response.ok) {
        throw new Error(`Upload failed: ${response.status}`)
      }
      const data = (await response.json()) as { file_key: string; file_name: string }
      return data
    },
    [session],
  )

  const attachFile = useCallback((file: { file_key: string; file_name: string }) => {
    const entry: AttachedFile = {
      file_key: file.file_key,
      file_name: file.file_name,
      uploaded_at: new Date().toISOString(),
    }
    setAttachedFiles((prev) => [...prev, entry])
  }, [])

  const removeAttachedFile = useCallback((index: number) => {
    setAttachedFiles((prev) => prev.filter((_, i) => i !== index))
  }, [])

  const loadSession = useCallback(async (sessionId: string) => {
    setIsLoading(true)
    try {
      const { data } = await api.get<RevisionSession>(`/revisions/sessions/${sessionId}`)
      setSession(data)
      const { data: msgs } = await api.get<RevisionMessage[]>(`/revisions/sessions/${sessionId}/messages`)
      setMessages(msgs)
    } catch (err) {
      console.error('Failed to load revision session:', err)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  const sendMessage = useCallback(
    async (content: string, fileRefs?: string[]) => {
      if (!session) return

      const userMsg: RevisionMessage = {
        id: `temp-${Date.now()}`,
        revision_session_id: session.id,
        role: 'user',
        content,
        timestamp: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, userMsg])
      setIsStreaming(true)
      setStreamingContent('')
      setError(null)

      setAttachedFiles([])

      const abortController = new AbortController()
      abortRef.current = abortController

      const STREAM_TIMEOUT_MS = 30_000

      timeoutRef.current = setTimeout(() => {
        abortController.abort()
      }, STREAM_TIMEOUT_MS)

      try {
        const token = useAuthStore.getState().accessToken
        const response = await fetch(`/api/revisions/sessions/${session.id}/stream`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ content, file_keys: fileRefs ?? [] }),
          signal: abortController.signal,
        })

        if (!response.ok) {
          throw new Error(`Stream failed: ${response.status}`)
        }

        const reader = response.body?.getReader()
        if (!reader) throw new Error('No reader')

        const decoder = new TextDecoder()
        let fullContent = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const chunk = decoder.decode(value, { stream: true })
          const lines = chunk.split('\n')

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue
            const data = line.slice(6)
            if (data === '[DONE]') continue
            try {
              const parsed = JSON.parse(data)
              if (parsed.type === 'token' && parsed.content) {
                fullContent += parsed.content
                setStreamingContent(fullContent)
              } else if (parsed.type === 'error') {
                setError({ message: parsed.content || 'Stream error from server', type: 'sse' })
              }
            } catch {}
          }
        }

        const assistantMsg: RevisionMessage = {
          id: `temp-assistant-${Date.now()}`,
          revision_session_id: session.id,
          role: 'assistant',
          content: fullContent,
          timestamp: new Date().toISOString(),
        }
        setMessages((prev) => [...prev, assistantMsg])
        setStreamingContent('')
      } catch (err: unknown) {
        if (err instanceof Error && err.name === 'AbortError') {
          setStreamingContent('')
          const isTimeout = abortController.signal.aborted && timeoutRef.current === null
          setError({
            message: isTimeout ? 'Response timed out. Please try again.' : 'Request was cancelled.',
            type: isTimeout ? 'timeout' : 'unknown',
          })
        } else if (err instanceof TypeError && err.message.includes('fetch')) {
          setError({ message: 'Network error. Check your connection.', type: 'network' })
        } else {
          setError({
            message: err instanceof Error ? err.message : 'Something went wrong.',
            type: 'unknown',
          })
        }
      } finally {
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current)
          timeoutRef.current = null
        }
        setIsStreaming(false)
        abortRef.current = null
      }
    },
    [session],
  )

  const stopStreaming = useCallback(() => {
    abortRef.current?.abort()
  }, [])

  return {
    session,
    messages,
    isLoading,
    isStreaming,
    streamingContent,
    error,
    clearError,
    availableStageIds,
    selectedStageIds,
    attachedFiles,
    loadSession,
    sendMessage,
    stopStreaming,
    setAvailableStageIds,
    setSelectedStageIds,
    toggleStage,
    uploadFile,
    attachFile,
    removeAttachedFile,
  }
}
