import { describe, it, expect } from 'vitest'
import { screen } from '@testing-library/react'
import { renderWithProviders } from '@/__test-utils__/learning-test-helpers'
import SkillsPage from '@/pages/learning/SkillsPage'

describe('SkillsPage — learning detail page', () => {
  it('renders "Default Skills" title', () => {
    renderWithProviders(<SkillsPage />, { initialEntries: ['/learning/skills'] })
    expect(
      screen.getByRole('heading', { name: /default skills/i }),
    ).toBeInTheDocument()
  })

  it('renders "Intermediate" difficulty badge', () => {
    renderWithProviders(<SkillsPage />, { initialEntries: ['/learning/skills'] })
    expect(screen.getByText('Intermediate')).toBeInTheDocument()
  })

  it('renders breadcrumb', () => {
    renderWithProviders(<SkillsPage />, { initialEntries: ['/learning/skills'] })
    const breadcrumbLink = screen.getByRole('link', { name: 'Learning' })
    expect(breadcrumbLink).toBeInTheDocument()
    expect(breadcrumbLink).toHaveAttribute('href', '/learning')
  })

  it('renders 10 skill names', () => {
    renderWithProviders(<SkillsPage />, { initialEntries: ['/learning/skills'] })
    expect(screen.getAllByText('eu-horizon').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('academic-writing').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('project-management').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('literature-review').length).toBeGreaterThanOrEqual(1)
  })

  it('renders diagram with role="img"', () => {
    renderWithProviders(<SkillsPage />, { initialEntries: ['/learning/skills'] })
    const diagram = screen.getByRole('img')
    expect(diagram).toBeInTheDocument()
  })

  it('renders "Custom skills" callout', () => {
    renderWithProviders(<SkillsPage />, { initialEntries: ['/learning/skills'] })
    expect(screen.getByText('Custom skills')).toBeInTheDocument()
  })

  it('renders "Browse Skills" CTA pointing to /cult/skills', () => {
    renderWithProviders(<SkillsPage />, { initialEntries: ['/learning/skills'] })
    const link = screen.getByRole('link', { name: /browse skills/i })
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute('href', '/cult/skills')
  })

  it('renders "Back to Learning" link', () => {
    renderWithProviders(<SkillsPage />, { initialEntries: ['/learning/skills'] })
    const link = screen.getByRole('link', { name: /back to learning/i })
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute('href', '/learning')
  })
})
