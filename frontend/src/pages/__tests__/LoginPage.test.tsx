import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import LoginPage from '../LoginPage'

// Mock auth store
vi.mock('@/stores/auth', () => ({
  useAuthStore: vi.fn(() => ({
    user: null,
    login: vi.fn(),
    isAuthenticated: false,
  })),
}))

// Mock react-hook-form
vi.mock('react-hook-form', () => ({
  useForm: vi.fn(() => ({
    register: vi.fn(() => ({})),
    handleSubmit: vi.fn((fn) => (e: any) => {
      e?.preventDefault?.()
      return fn({ email: '', password: '' })
    }),
    formState: {
      errors: {},
      isSubmitting: false,
    },
  })),
}))

// Mock zodResolver
vi.mock('@hookform/resolvers/zod', () => ({
  zodResolver: vi.fn(() => (data: any) => ({ values: data, errors: {} })),
}))

describe('LoginPage', () => {
  const renderLogin = () =>
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    )

  it('renders welcome heading', () => {
    renderLogin()
    expect(screen.getByText('Welcome back')).toBeInTheDocument()
  })

  it('renders sign-in description', () => {
    renderLogin()
    expect(
      screen.getByText('Sign in to continue your research'),
    ).toBeInTheDocument()
  })

  it('renders email input', () => {
    renderLogin()
    expect(screen.getByPlaceholderText('researcher@university.edu')).toBeInTheDocument()
  })

  it('renders password input', () => {
    renderLogin()
    expect(screen.getByPlaceholderText('Enter your password')).toBeInTheDocument()
  })

  it('renders sign in button', () => {
    renderLogin()
    expect(screen.getByText('Sign in')).toBeInTheDocument()
  })

  it('renders Google and GitHub OAuth buttons', () => {
    renderLogin()
    expect(screen.getByText('Google')).toBeInTheDocument()
    expect(screen.getByText('GitHub')).toBeInTheDocument()
  })

  it('renders sign up link', () => {
    renderLogin()
    expect(screen.getByText('Sign up')).toBeInTheDocument()
  })
})
