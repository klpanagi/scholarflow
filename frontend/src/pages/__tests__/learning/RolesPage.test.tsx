import { describe, it, expect } from 'vitest'
import { screen } from '@testing-library/react'
import { renderWithProviders } from '@/__test-utils__/learning-test-helpers'
import RolesPage from '@/pages/learning/RolesPage'

// ---------------------------------------------------------------------------
// Test suite for the Roles learning detail page
// ---------------------------------------------------------------------------

describe('RolesPage (learning detail)', () => {
  it('renders "Agent Roles" title', () => {
    renderWithProviders(<RolesPage />)
    const titles = screen.getAllByText('Agent Roles')
    expect(titles.length).toBeGreaterThanOrEqual(1)
  })

  it('renders "Intermediate" difficulty badge', () => {
    renderWithProviders(<RolesPage />)
    expect(screen.getByText('Intermediate')).toBeInTheDocument()
  })

  it('renders breadcrumb "Learning > Agent Roles"', () => {
    renderWithProviders(<RolesPage />)
    expect(screen.getByText('Learning')).toBeInTheDocument()
    const learningLink = screen.getByText('Learning').closest('a')
    expect(learningLink).toHaveAttribute('href', '/learning')
    const titles = screen.getAllByText('Agent Roles')
    expect(titles.length).toBeGreaterThanOrEqual(1)
  })

  it('renders 9 role names', () => {
    renderWithProviders(<RolesPage />)
    // Each role name appears in both the list grid and the SVG diagram,
    // so getAllByText should find at least one instance
    const roles = [
      'researcher',
      'writer',
      'reviewer',
      'deep_reviewer',
      'recommender',
      'revision',
      'manager',
      'debater',
      'review_writer',
    ]
    for (const role of roles) {
      const elements = screen.getAllByText(role)
      expect(elements.length).toBeGreaterThanOrEqual(1)
    }
  })

  it('renders diagram with role="img"', () => {
    renderWithProviders(<RolesPage />)
    const diagram = screen.getByRole('img')
    expect(diagram).toBeInTheDocument()
    expect(diagram).toHaveAttribute(
      'aria-label',
      expect.stringContaining('Role graph'),
    )
  })

  it('renders "Debater variants" callout', () => {
    renderWithProviders(<RolesPage />)
    expect(screen.getByText('Debater variants')).toBeInTheDocument()
  })

  it('renders "Browse Agents" CTA pointing to /cult/agents', () => {
    renderWithProviders(<RolesPage />)
    const cta = screen.getByText('Browse Agents')
    expect(cta).toBeInTheDocument()
    const ctaLink = cta.closest('a')
    expect(ctaLink).toHaveAttribute('href', '/cult/agents')
  })

  it('renders "Back to Learning" link', () => {
    renderWithProviders(<RolesPage />)
    const backLink = screen.getByText('← Back to Learning')
    expect(backLink).toBeInTheDocument()
    const link = backLink.closest('a')
    expect(link).toHaveAttribute('href', '/learning')
  })
})
