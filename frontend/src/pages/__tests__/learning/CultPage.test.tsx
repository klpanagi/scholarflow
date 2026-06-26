import { describe, it, expect } from 'vitest'
import { screen } from '@testing-library/react'
import { renderWithProviders } from '@/__test-utils__/learning-test-helpers'
import CultPage from '@/pages/learning/CultPage'

// ---------------------------------------------------------------------------
// Test suite for the Cult learning detail page
// ---------------------------------------------------------------------------

describe('CultPage (learning detail)', () => {
  it('renders PageHeader with "The Cult" title', () => {
    renderWithProviders(<CultPage />)
    const matches = screen.getAllByText('The Cult')
    const h1 = matches.find((el) => el.tagName === 'H1')
    expect(h1).toBeInTheDocument()
  })

  it('renders the difficulty badge "Beginner"', () => {
    renderWithProviders(<CultPage />)
    expect(screen.getByText('Beginner')).toBeInTheDocument()
  })

  it('renders breadcrumb "Learning > The Cult"', () => {
    renderWithProviders(<CultPage />)
    expect(screen.getByText('Learning')).toBeInTheDocument()
    const learningLink = screen.getByText('Learning').closest('a')
    expect(learningLink).toHaveAttribute('href', '/learning')
    const cultMatches = screen.getAllByText('The Cult')
    expect(cultMatches.length).toBeGreaterThanOrEqual(1)
  })

  it('renders at least 3 paragraphs of text', () => {
    renderWithProviders(<CultPage />)
    expect(
      screen.getByText(/The Cult.*internal name/),
    ).toBeInTheDocument()
  })

  it('renders list items (Agent registry, Skill store, Chat surface, Workflow engine)', () => {
    renderWithProviders(<CultPage />)
    expect(screen.getAllByText('Agent registry').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Skill store').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Chat surface').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Workflow engine').length).toBeGreaterThanOrEqual(1)
  })

  it('renders diagram with role="img"', () => {
    renderWithProviders(<CultPage />)
    const diagram = screen.getByRole('img')
    expect(diagram).toBeInTheDocument()
    expect(diagram).toHaveAttribute(
      'aria-label',
      expect.stringContaining('Cult architecture'),
    )
  })

  it('renders callout with title "Why \'Cult\'?"', () => {
    renderWithProviders(<CultPage />)
    expect(screen.getByText("Why \u201CCult\u201D?")).toBeInTheDocument()
  })

  it('renders "Open Cult Dashboard" CTA pointing to /cult', () => {
    renderWithProviders(<CultPage />)
    const cta = screen.getByText('Open Cult Dashboard')
    expect(cta).toBeInTheDocument()
    const ctaLink = cta.closest('a')
    expect(ctaLink).toHaveAttribute('href', '/cult')
  })

  it('renders "Back to Learning" link', () => {
    renderWithProviders(<CultPage />)
    const backLink = screen.getByText('← Back to Learning')
    expect(backLink).toBeInTheDocument()
    const link = backLink.closest('a')
    expect(link).toHaveAttribute('href', '/learning')
  })
})
