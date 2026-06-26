import { describe, it, expect } from 'vitest'
import { screen } from '@testing-library/react'
import { renderWithProviders } from '@/__test-utils__/learning-test-helpers'
import ConfigsPage from '@/pages/learning/ConfigsPage'

// ---------------------------------------------------------------------------
// Test suite for the Configs learning detail page
// ---------------------------------------------------------------------------

describe('ConfigsPage (learning detail)', () => {
  it('renders "Agent Configurations" title in the page header', () => {
    renderWithProviders(<ConfigsPage />)
    // Title appears both in the breadcrumb (<span>) and the page header (<h1>)
    const titleElements = screen.getAllByText('Agent Configurations')
    expect(titleElements.length).toBeGreaterThanOrEqual(2)
    // The <h1> is the page header title
    const h1 = titleElements.find((el) => el.tagName === 'H1')
    expect(h1).toBeInTheDocument()
  })

  it('renders "Intermediate" difficulty badge', () => {
    renderWithProviders(<ConfigsPage />)
    const intermediateElements = screen.getAllByText('Intermediate')
    expect(intermediateElements.length).toBeGreaterThanOrEqual(1)
  })

  it('renders breadcrumb with Learning and Agent Configurations', () => {
    renderWithProviders(<ConfigsPage />)
    expect(screen.getByText('Learning')).toBeInTheDocument()
    const learningLink = screen.getByText('Learning').closest('a')
    expect(learningLink).toHaveAttribute('href', '/learning')
    const titles = screen.getAllByText('Agent Configurations')
    expect(titles.length).toBeGreaterThanOrEqual(2)
  })

  it('renders at least 5 config names', () => {
    renderWithProviders(<ConfigsPage />)
    expect(screen.getByText('Proposal Writer')).toBeInTheDocument()
    expect(screen.getByText('Proposal Reviewer')).toBeInTheDocument()
    expect(screen.getByText('Project Manager')).toBeInTheDocument()
    expect(screen.getByText('Review Writer')).toBeInTheDocument()
    expect(screen.getByText('Default Researcher')).toBeInTheDocument()
  })

  it('renders diagram with role="img"', () => {
    renderWithProviders(<ConfigsPage />)
    const diagram = screen.getByRole('img')
    expect(diagram).toBeInTheDocument()
    expect(diagram).toHaveAttribute(
      'aria-label',
      expect.stringContaining('Configuration resolution'),
    )
  })

  it('renders "Don\'t edit the seeds in place" callout (warning variant)', () => {
    renderWithProviders(<ConfigsPage />)
    // The callout title uses Unicode RIGHT SINGLE QUOTATION MARK (U+2019)
    expect(
      screen.getByText((content) =>
        content.includes('Don') && content.includes('t edit the seeds in place'),
      ),
    ).toBeInTheDocument()
  })

  it('renders "Manage Configurations" CTA pointing to /cult/configs', () => {
    renderWithProviders(<ConfigsPage />)
    const cta = screen.getByText('Manage Configurations')
    expect(cta).toBeInTheDocument()
    const ctaLink = cta.closest('a')
    expect(ctaLink).toHaveAttribute('href', '/cult/configs')
  })

  it('renders "Back to Learning" link', () => {
    renderWithProviders(<ConfigsPage />)
    const backLink = screen.getByText('← Back to Learning')
    expect(backLink).toBeInTheDocument()
    const link = backLink.closest('a')
    expect(link).toHaveAttribute('href', '/learning')
  })
})
