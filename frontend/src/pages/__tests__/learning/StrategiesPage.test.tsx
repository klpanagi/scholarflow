import { describe, it, expect } from 'vitest'
import { screen, within } from '@testing-library/react'
import { renderWithProviders } from '@/__test-utils__/learning-test-helpers'
import StrategiesPage from '@/pages/learning/StrategiesPage'

describe('StrategiesPage', () => {
  it('renders "Agent Strategies" title', () => {
    renderWithProviders(<StrategiesPage />, {
      initialEntries: ['/learning/strategies'],
    })
    expect(
      screen.getByRole('heading', { name: /agent strategies/i }),
    ).toBeInTheDocument()
  })

  it('renders "Advanced" difficulty badge', () => {
    renderWithProviders(<StrategiesPage />, {
      initialEntries: ['/learning/strategies'],
    })
    expect(screen.getByText('Advanced')).toBeInTheDocument()
  })

  it('renders breadcrumb', () => {
    renderWithProviders(<StrategiesPage />, {
      initialEntries: ['/learning/strategies'],
    })
    const nav = screen.getByRole('navigation')
    expect(within(nav).getByText('Learning')).toBeInTheDocument()
    expect(within(nav).getByText('Agent Strategies')).toBeInTheDocument()
  })

  it('renders 4 strategy names: direct, critique, reflection, evaluator_optimizer', () => {
    renderWithProviders(<StrategiesPage />, {
      initialEntries: ['/learning/strategies'],
    })
    expect(screen.getAllByText('direct').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('critique').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('reflection').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('evaluator_optimizer').length).toBeGreaterThanOrEqual(1)
  })

  it('renders diagram with role="img"', () => {
    renderWithProviders(<StrategiesPage />, {
      initialEntries: ['/learning/strategies'],
    })
    const svg = document.querySelector('svg[role="img"]')
    expect(svg).toBeInTheDocument()
  })

  it('renders "Choosing a strategy" callout', () => {
    renderWithProviders(<StrategiesPage />, {
      initialEntries: ['/learning/strategies'],
    })
    expect(screen.getByText('Choosing a strategy')).toBeInTheDocument()
  })

  it('renders "View Workflows" CTA pointing to /workflows', () => {
    renderWithProviders(<StrategiesPage />, {
      initialEntries: ['/learning/strategies'],
    })
    const link = screen.getByRole('link', { name: /view workflows/i })
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute('href', '/workflows')
  })

  it('renders "Back to Learning" link', () => {
    renderWithProviders(<StrategiesPage />, {
      initialEntries: ['/learning/strategies'],
    })
    const link = screen.getByRole('link', { name: /back to learning/i })
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute('href', '/learning')
  })
})
