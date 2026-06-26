import { useState, useCallback, useRef } from 'react'
import { api } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'

// Re-export types from the canonical types module so existing consumers
// that import from this file keep working without changes.
export type { ChatSession, ChatMessage, CreateSessionParams } from '../types/chat'
import type { ChatSession, ChatMessage, CreateSessionParams } from '../types/chat'

export interface AvailableModel {
  id: string
  provider: string
}

/**
 * Internal implementation that accepts the new `CreateSessionParams` object.
 */
async function createSessionImpl(
  params: CreateSessionParams,
  setSessions: React.Dispatch<React.SetStateAction<ChatSession[]>>,
  setCurrentSession: React.Dispatch<React.SetStateAction<ChatSession | null>>,
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>,
): Promise<ChatSession> {
  try {
    const { data } = await api.post<ChatSession>('/chat/sessions', {
      title: params.title || null,
      agent_config_id: params.agentConfigId,
      asset_ids: params.assetIds ?? [],
      system_prompt: params.systemPrompt || null,
    })
    setSessions((prev) => [data, ...prev])
    setCurrentSession(data)
    setMessages([])
    return data
  } catch (err) {
    console.error('Failed to create session:', err)
    throw err
  }
}

export function useChat() {
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const [availableModels, setAvailableModels] = useState<AvailableModel[]>([])
  const abortRef = useRef<AbortController | null>(null)

  const fetchSessions = useCallback(async () => {
    try {
      const { data } = await api.get<ChatSession[]>('/chat/sessions')
      setSessions(data)
    } catch (err) {
      console.error('Failed to fetch sessions:', err)
    }
  }, [])

  /**
   * Create a new chat session.
   *
   * **Preferred (Phase 3+)**: pass a `CreateSessionParams` object.
   *
   * ```ts
   * createSession({ agentConfigId: '...', title: 'My Chat', assetIds: [...] })
   * ```
   *
   * @deprecated The legacy positional-arg form
   *   `createSession(model, provider, title?, systemPrompt?)` is still accepted
   *   for backward compatibility but will be removed in **Phase 4**.
   *   The call site in `ChatPage.tsx:handleCreateSession` MUST be updated in
   *   Phase 4 to use the new object signature.
   */
  const createSession = useCallback(
    (
      paramsOrModel: CreateSessionParams | string,
      provider?: string,
      title?: string,
      systemPrompt?: string,
    ): Promise<ChatSession> => {
      if (typeof paramsOrModel === 'string') {
        // ---- Legacy positional-arg form ----
        if (import.meta.env.DEV) {
          console.warn(
            '[useChat.createSession] Positional args are deprecated. ' +
              'Use createSession({ agentConfigId, ... }) instead. ' +
              'This form will be removed in Phase 4.',
          )
        }
        return createSessionImpl(
          {
            agentConfigId: '',
            model: paramsOrModel,
            provider: provider ?? 'opencode',
            title,
            systemPrompt,
          },
          setSessions,
          setCurrentSession,
          setMessages,
        )
      }

      // ---- New object form (Phase 3+) ----
      return createSessionImpl(
        paramsOrModel,
        setSessions,
        setCurrentSession,
        setMessages,
      )
    },
    [],
  )

  const deleteSession = useCallback(
    async (sessionId: string): Promise<boolean> => {
      try {
        await api.delete(`/chat/sessions/${sessionId}`)
        setSessions((prev) => prev.filter((s) => s.id !== sessionId))
        if (currentSession?.id === sessionId) {
          setCurrentSession(null)
          setMessages([])
        }
        return true
      } catch (err) {
        console.error('Failed to delete session:', err)
        return false
      }
    },
    [currentSession],
  )

  const clearAllSessions = useCallback(async (): Promise<number> => {
    try {
      const { data } = await api.delete<{ deleted: number }>('/chat/sessions')
      const deleted = data?.deleted ?? 0
      setSessions([])
      setCurrentSession(null)
      setMessages([])
      return deleted
    } catch (err) {
      console.error('Failed to clear all sessions:', err)
      return -1
    }
  }, [])

  const selectSession = useCallback(async (session: ChatSession) => {
    try {
      const { data } = await api.get<ChatSession>(`/chat/sessions/${session.id}`)
      setCurrentSession(data)
      const { data: msgs } = await api.get<ChatMessage[]>(`/chat/sessions/${session.id}/messages`)
      setMessages(msgs)
    } catch (err) {
      console.error('Failed to load session:', err)
    }
  }, [])

  const fetchModels = useCallback(async () => {
    try {
      const { data } = await api.get('/chat/models')
      const models: AvailableModel[] = []
      if (data && typeof data === 'object') {
        for (const [prov, providerModels] of Object.entries(data)) {
          if (Array.isArray(providerModels)) {
            for (const model of providerModels) {
              const modelId = typeof model === 'string' ? model : (model as { id?: string })?.id || String(model)
              models.push({ id: modelId, provider: prov })
            }
          }
        }
      }
      setAvailableModels(models)
    } catch (err) {
      console.error('Failed to fetch models:', err)
    }
  }, [])

  const sendMessage = useCallback(async (content: string, parentMessageId?: string) => {
    if (!currentSession) return

    const userMsg: ChatMessage = {
      id: `temp-${Date.now()}`,
      session_id: currentSession.id,
      role: 'user',
      content,
      parent_message_id: parentMessageId || null,
      timestamp: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, userMsg])

    setIsStreaming(true)
    setStreamingContent('')

    const abortController = new AbortController()
    abortRef.current = abortController

    try {
      const token = useAuthStore.getState().accessToken
      const response = await fetch(`/api/chat/sessions/${currentSession.id}/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ content, parent_message_id: parentMessageId || null }),
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
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data === '[DONE]') break
            try {
              const parsed = JSON.parse(data)
              if (parsed.content) {
                fullContent += parsed.content
                setStreamingContent(fullContent)
              }
            } catch {
              // Skip unparseable SSE lines
            }
          }
        }
      }

      const assistantMsg: ChatMessage = {
        id: `temp-assistant-${Date.now()}`,
        session_id: currentSession.id,
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
        console.error('Stream error:', err)
      }
    } finally {
      setIsStreaming(false)
      abortRef.current = null
    }
  }, [currentSession])

  const stopStreaming = useCallback(() => {
    abortRef.current?.abort()
  }, [])

  const forkSession = useCallback(async (fromMessageId: string, title?: string) => {
    if (!currentSession) return
    try {
      const { data } = await api.post<ChatSession>(`/chat/sessions/${currentSession.id}/fork`, {
        from_message_id: fromMessageId,
        title: title || null,
      })
      setSessions((prev) => [data, ...prev])
      setCurrentSession(data)
      const { data: msgs } = await api.get<ChatMessage[]>(`/chat/sessions/${data.id}/messages`)
      setMessages(msgs)
      return data
    } catch (err) {
      console.error('Failed to fork session:', err)
      throw err
    }
  }, [currentSession])

  const uploadFile = useCallback(async (file: File) => {
    if (!currentSession) return
    const formData = new FormData()
    formData.append('file', file)
    try {
      const { data } = await api.post(`/chat/sessions/${currentSession.id}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return data as { file_key: string; file_name: string }
    } catch (err) {
      console.error('Failed to upload file:', err)
      throw err
    }
  }, [currentSession])

  return {
    sessions,
    currentSession,
    messages,
    isStreaming,
    streamingContent,
    availableModels,
    fetchSessions,
    createSession,
    deleteSession,
    clearAllSessions,
    selectSession,
    fetchModels,
    sendMessage,
    stopStreaming,
    forkSession,
    uploadFile,
  }
}
