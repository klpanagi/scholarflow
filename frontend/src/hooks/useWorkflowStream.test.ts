import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useWorkflowStream, type ExecutionEvent } from './useWorkflowStream'

// Mock the auth store
vi.mock('@/stores/auth', () => ({
  useAuthStore: {
    getState: () => ({ accessToken: 'test-token' }),
  },
}))

function makeEvent(
  event_id: number,
  event_type: string,
  data: Record<string, unknown> = {},
): ExecutionEvent {
  return {
    event_id,
    execution_id: 'exec-1',
    event_type,
    timestamp: new Date().toISOString(),
    data,
  }
}

function sseChunk(events: ExecutionEvent[]): Uint8Array {
  const parts = events.map(
    (ev) => `id: ${ev.event_id}\ndata: ${JSON.stringify(ev)}\n\n`,
  )
  return new TextEncoder().encode(parts.join(''))
}

describe('useWorkflowStream', () => {
  let mockFetch: ReturnType<typeof vi.fn>
  let readerController: ReadableStreamDefaultController | null

  beforeEach(() => {
    readerController = null
    mockFetch = vi.fn()
    globalThis.fetch = mockFetch as unknown as typeof fetch
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  function createMockStream(): ReadableStream {
    return new ReadableStream({
      start(controller) {
        readerController = controller
      },
    })
  }

  it('connects to SSE endpoint with token', () => {
    const stream = createMockStream()
    mockFetch.mockResolvedValue({
      ok: true,
      body: stream,
    })

    renderHook(() => useWorkflowStream('exec-1', { enabled: true }))

    expect(mockFetch).toHaveBeenCalledTimes(1)
    const callUrl = mockFetch.mock.calls[0][0] as string
    expect(callUrl).toContain('/api/workflows/results/exec-1/stream')
    expect(callUrl).toContain('token=test-token')
  })

  it('sets isConnected to true on successful connection', async () => {
    const stream = createMockStream()
    mockFetch.mockResolvedValue({
      ok: true,
      body: stream,
    })

    const { result } = renderHook(() => useWorkflowStream('exec-1'))

    await waitFor(() => {
      expect(result.current.isConnected).toBe(true)
    })
  })

  it('receives and stores events from the stream', async () => {
    const stream = createMockStream()
    mockFetch.mockResolvedValue({
      ok: true,
      body: stream,
    })

    const { result } = renderHook(() => useWorkflowStream('exec-1'))

    await waitFor(() => {
      expect(result.current.isConnected).toBe(true)
    })

    const ev1 = makeEvent(1, 'NODE_STARTED', { node_name: 'search' })
    const ev2 = makeEvent(2, 'NODE_COMPLETED', { node_name: 'search' })

    act(() => {
      const chunk = sseChunk([ev1, ev2])
      readerController?.enqueue(chunk)
    })

    await waitFor(() => {
      expect(result.current.events).toHaveLength(2)
    })

    expect(result.current.events[0].event_type).toBe('NODE_STARTED')
    expect(result.current.events[1].event_type).toBe('NODE_COMPLETED')
  })

  it('sets error and disconnects on 410 Gone', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 410,
    })

    const { result } = renderHook(() => useWorkflowStream('exec-1'))

    await waitFor(() => {
      expect(result.current.error).toBe('Execution already completed')
    })

    expect(result.current.isConnected).toBe(false)
  })

  it('stops reconnecting after terminal event', async () => {
    const stream = createMockStream()
    mockFetch.mockResolvedValueOnce({
      ok: true,
      body: stream,
    })
    // Second fetch should NOT be called
    const secondFetch = vi.fn()
    mockFetch.mockImplementationOnce(secondFetch)

    const { result } = renderHook(() => useWorkflowStream('exec-1'))

    await waitFor(() => {
      expect(result.current.isConnected).toBe(true)
    })

    const terminal = makeEvent(3, 'EXECUTION_COMPLETED', { status: 'completed' })

    act(() => {
      readerController?.enqueue(sseChunk([terminal]))
      readerController?.close()
    })

    await waitFor(() => {
      expect(result.current.isConnected).toBe(false)
    })

    expect(result.current.events).toHaveLength(1)
    // Should not try to reconnect after terminal
    expect(mockFetch).toHaveBeenCalledTimes(1)
  })

  it('applies filter to events', async () => {
    const stream = createMockStream()
    mockFetch.mockResolvedValue({
      ok: true,
      body: stream,
    })

    const filter = (ev: ExecutionEvent) =>
      ev.event_type.startsWith('NODE_') || ev.event_type.startsWith('STAGE_')

    const { result } = renderHook(() =>
      useWorkflowStream('exec-1', { filter }),
    )

    await waitFor(() => {
      expect(result.current.isConnected).toBe(true)
    })

    act(() => {
      readerController?.enqueue(
        sseChunk([
          makeEvent(1, 'heartbeat'),
          makeEvent(2, 'NODE_STARTED', { node_name: 'search' }),
          makeEvent(3, 'NODE_COMPLETED', { node_name: 'search' }),
          makeEvent(4, 'tool.call'),
          makeEvent(5, 'STAGE_COMPLETED'),
        ]),
      )
    })

    await waitFor(() => {
      expect(result.current.events).toHaveLength(3)
    })

    expect(result.current.events.map((e) => e.event_type)).toEqual([
      'NODE_STARTED',
      'NODE_COMPLETED',
      'STAGE_COMPLETED',
    ])
  })

  it('deduplicates events by event_id', async () => {
    const stream = createMockStream()
    mockFetch.mockResolvedValue({
      ok: true,
      body: stream,
    })

    const { result } = renderHook(() => useWorkflowStream('exec-1'))

    await waitFor(() => {
      expect(result.current.isConnected).toBe(true)
    })

    const ev = makeEvent(1, 'NODE_STARTED')

    act(() => {
      readerController?.enqueue(sseChunk([ev]))
    })

    await waitFor(() => {
      expect(result.current.events).toHaveLength(1)
    })

    // Push the same event again (simulates replay dupe)
    act(() => {
      readerController?.enqueue(sseChunk([ev]))
    })

    // Wait a bit to ensure no duplicate added
    await new Promise((r) => setTimeout(r, 50))
    expect(result.current.events).toHaveLength(1)
  })

  it('disconnect cleans up the stream', async () => {
    const stream = createMockStream()
    mockFetch.mockResolvedValue({
      ok: true,
      body: stream,
    })

    const { result } = renderHook(() => useWorkflowStream('exec-1'))

    await waitFor(() => {
      expect(result.current.isConnected).toBe(true)
    })

    act(() => {
      result.current.disconnect()
    })

    expect(result.current.isConnected).toBe(false)
  })

  it('does not connect when enabled is false', () => {
    renderHook(() => useWorkflowStream('exec-1', { enabled: false }))

    expect(mockFetch).not.toHaveBeenCalled()
  })

  it('handles SSE comments and heartbeats gracefully', async () => {
    const stream = createMockStream()
    mockFetch.mockResolvedValue({
      ok: true,
      body: stream,
    })

    const { result } = renderHook(() => useWorkflowStream('exec-1'))

    await waitFor(() => {
      expect(result.current.isConnected).toBe(true)
    })

    // Send heartbeat comment + event
    const heartbeatChunk = new TextEncoder().encode(
      ': heartbeat\n\n' +
      `id: 1\ndata: ${JSON.stringify(makeEvent(1, 'NODE_STARTED'))}\n\n`,
    )

    act(() => {
      readerController?.enqueue(heartbeatChunk)
    })

    await waitFor(() => {
      expect(result.current.events).toHaveLength(1)
    })
  })
})
