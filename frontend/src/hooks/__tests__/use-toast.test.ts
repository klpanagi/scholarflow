import { describe, it, expect, vi, beforeEach } from 'vitest'
import { toast, useToast } from '../use-toast'

// Mock sonner — keep module-level refs for assertion
const mockSonnerToast = vi.fn()
const mockSonnerError = vi.fn()
mockSonnerToast.error = mockSonnerError

vi.mock('sonner', () => ({ toast: Object.assign(vi.fn(), { error: vi.fn() }) }))

beforeEach(() => {
  mockSonnerToast.mockClear()
  mockSonnerError.mockClear()
})

describe('toast', () => {
  it('calls sonner toast for default variant', async () => {
    const sonner = await import('sonner')
    toast({ title: 'Hello', description: 'World' })
    expect(sonner.toast).toHaveBeenCalledWith('Hello', {
      description: 'World',
    })
  })

  it('calls sonner toast.error for destructive variant', async () => {
    const sonner = await import('sonner')
    toast({ title: 'Error', description: 'Something failed', variant: 'destructive' })
    expect(sonner.toast.error).toHaveBeenCalledWith('Error', {
      description: 'Something failed',
    })
  })
})

describe('useToast', () => {
  it('returns toast, toasts, and dismiss', () => {
    const result = useToast()
    expect(result).toHaveProperty('toast')
    expect(result).toHaveProperty('toasts')
    expect(result).toHaveProperty('dismiss')
    expect(Array.isArray(result.toasts)).toBe(true)
  })
})
