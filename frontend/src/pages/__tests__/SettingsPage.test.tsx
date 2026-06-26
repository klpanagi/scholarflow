import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { SettingsPage } from '../SettingsPage'

// Mock auth store
vi.mock('@/stores/auth', () => ({
  useAuthStore: vi.fn(() => ({
    user: null,
  })),
}))

// Mock react-hook-form
vi.mock('react-hook-form', () => ({
  useForm: vi.fn(() => ({
    register: vi.fn(() => ({})),
    handleSubmit: vi.fn((fn) => (e: any) => {
      e?.preventDefault?.()
      return fn({})
    }),
    formState: {
      errors: {},
      isSubmitting: false,
    },
    reset: vi.fn(),
  })),
}))

// Mock zodResolver
vi.mock('@hookform/resolvers/zod', () => ({
  zodResolver: vi.fn(() => (data: any) => ({ values: data, errors: {} })),
}))

// Mock @tanstack/react-query
vi.mock('@tanstack/react-query', () => ({
  useQuery: vi.fn(() => ({
    data: null,
    isLoading: false,
  })),
  useMutation: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
  })),
  useQueryClient: vi.fn(() => ({
    invalidateQueries: vi.fn(),
  })),
}))

describe('SettingsPage', () => {
  const renderSettings = () =>
    render(
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>,
    )

  it('renders settings title', () => {
    renderSettings()
    expect(screen.getByText('Settings')).toBeInTheDocument()
  })

  it('renders settings description', () => {
    renderSettings()
    expect(
      screen.getByText('Manage your account, API keys, and application preferences.'),
    ).toBeInTheDocument()
  })

  it('renders all sidebar tabs', () => {
    renderSettings()
    expect(screen.getByText('Profile')).toBeInTheDocument()
    expect(screen.getByText('API Keys')).toBeInTheDocument()
    expect(screen.getByText('Preferences')).toBeInTheDocument()
    expect(screen.getByText('Billing')).toBeInTheDocument()
  })

  it('renders profile section by default', () => {
    renderSettings()
    expect(screen.getByText('Personal Information')).toBeInTheDocument()
    expect(screen.getByText('Change Password')).toBeInTheDocument()
  })
})
