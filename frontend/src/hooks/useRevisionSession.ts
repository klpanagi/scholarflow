import { useState, useCallback, useRef } from 'react'
import { api } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'

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

export function useRevisionSession() {
  const [session, setSession] = useState<RevisionSession | null>(null)
  const [messages, setMessages] = useState<RevisionMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const abortRef = useRef<AbortController | null>(null)

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

  const sendMessage = useCallback(async (content: string) => {
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

    const abortController = new AbortController()
    abortRef.current = abortController

    try {
      const token = useAuthStore.getState().accessToken
      const response = await fetch(`/api/revisions/sessions/${session.id}/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ content }),
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
              console.error('Stream error:', parsed.content)
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
      } else {
        console.error('Revision stream error:', err)
      }
    } finally {
      setIsStreaming(false)
      abortRef.current = null
    }
  }, [session])

  const stopStreaming = useCallback(() => {
    abortRef.current?.abort()
  }, [])

  return {
    session,
    messages,
    isLoading,
    isStreaming,
    streamingContent,
    loadSession,
    sendMessage,
    stopStreaming,
  }
}
