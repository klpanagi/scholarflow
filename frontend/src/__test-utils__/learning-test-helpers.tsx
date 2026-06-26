import { type ReactElement } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, type RenderResult } from '@testing-library/react'
import { ThemeProvider } from '@/components/theme/ThemeProvider'
import { vi } from 'vitest'

// ---------------------------------------------------------------------------
// localStorage polyfill – jsdom in newer Node.js does not provide it
// (ThemeProvider reads/writes localStorage for the active theme)
// ---------------------------------------------------------------------------

if (typeof window !== 'undefined' && !window.localStorage) {
  const store: Record<string, string> = {}
  Object.defineProperty(window, 'localStorage', {
    value: {
      getItem: (key: string) => store[key] ?? null,
      setItem: (key: string, value: string) => {
        store[key] = value
      },
      removeItem: (key: string) => {
        delete store[key]
      },
      clear: () => {
        Object.keys(store).forEach((k) => delete store[k])
      },
      get length() {
        return Object.keys(store).length
      },
      key: (index: number) => Object.keys(store)[index] ?? null,
    },
    writable: true,
    configurable: true,
  })
}

// ---------------------------------------------------------------------------
// Mocks – applied globally when this module is imported by any test file
// ---------------------------------------------------------------------------

vi.mock('framer-motion', async () => {
  const actual = await vi.importActual<typeof import('framer-motion')>('framer-motion')
  return {
    ...actual,
    motion: {
      div: ({ children, ...rest }: any) => <div {...rest}>{children}</div>,
      p: ({ children, ...rest }: any) => <p {...rest}>{children}</p>,
      path: (props: any) => <path {...props} />,
      circle: (props: any) => <circle {...props} />,
      g: (props: any) => <g {...props} />,
    },
  }
})

vi.mock('@/stores/auth', () => ({
  useAuthStore: vi.fn(() => ({
    user: { id: 'test-user-id', email: 'test@example.com', name: 'Test User' },
    isAuthenticated: true,
    accessToken: 'mock-access-token',
    refreshToken: 'mock-refresh-token',
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    refreshAuth: vi.fn(),
  })),
}))

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export interface RenderWithProvidersOptions {
  initialEntries?: string[]
  user?: { id: string; email: string } | null
}

/**
 * Creates a fresh QueryClient with retries disabled for testing.
 */
export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })
}

/**
 * Renders a React element wrapped with all providers required by the
 * Learning section.  Each call gets a *fresh* QueryClient so test
 * isolation is guaranteed.
 *
 * - MemoryRouter (configurable `initialEntries`, default `['/']`)
 * - QueryClientProvider (retry: false)
 * - ThemeProvider
 */
export function renderWithProviders(
  ui: ReactElement,
  options?: RenderWithProvidersOptions,
): RenderResult {
  const { initialEntries = ['/'] } = options ?? {}

  const queryClient = createQueryClient()

  return render(
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={initialEntries}>{ui}</MemoryRouter>
      </QueryClientProvider>
    </ThemeProvider>,
  )
}

/**
 * Returns a minimal mock user object suitable for testing.
 * Matches the shape consumed by the auth store mock.
 */
export function createMockUser(): { id: string; email: string } {
  return { id: 'test-user-id', email: 'test@example.com' }
}
