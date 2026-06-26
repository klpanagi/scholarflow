import { describe, it, expect } from 'vitest'
import { screen } from '@testing-library/react'
import { renderWithProviders } from '@/__test-utils__/learning-test-helpers'
import AssetsPage from '@/pages/learning/AssetsPage'

// ---------------------------------------------------------------------------
// Test suite for the Assets learning detail page
// ---------------------------------------------------------------------------

describe('AssetsPage (learning detail)', () => {
  it('renders PageHeader with "Assets" title', () => {
    renderWithProviders(<AssetsPage />)
    expect(screen.getByRole('heading', { name: 'Assets' })).toBeInTheDocument()
  })

  it('renders the difficulty badge "Beginner"', () => {
    renderWithProviders(<AssetsPage />)
    // "Beginner" may appear in both the badge and other context
    const beginnerElements = screen.getAllByText('Beginner')
    expect(beginnerElements.length).toBeGreaterThanOrEqual(1)
  })

  it('renders reading time text', () => {
    renderWithProviders(<AssetsPage />)
    // readingMinutes for assets is 5 (ceil(820/200) = 5)
    const minReadElements = screen.getAllByText(/min read/)
    expect(minReadElements.length).toBeGreaterThanOrEqual(1)
  })

  it('renders the breadcrumb "Learning > Assets"', () => {
    renderWithProviders(<AssetsPage />)
    expect(screen.getByText('Learning')).toBeInTheDocument()
    // The "Learning" text is a link to /learning
    const learningLink = screen.getByText('Learning').closest('a')
    expect(learningLink).toHaveAttribute('href', '/learning')
    // "Assets" appears in both the heading and breadcrumb
    const assetsElements = screen.getAllByText('Assets')
    expect(assetsElements.length).toBeGreaterThanOrEqual(2)
  })

  it('renders at least one paragraph from the text blocks', () => {
    renderWithProviders(<AssetsPage />)
    expect(
      screen.getByText(/Assets are the raw inputs/),
    ).toBeInTheDocument()
  })

  it('renders the list items (Upload, Object storage, etc.)', () => {
    renderWithProviders(<AssetsPage />)
    // These appear both in the diagram and list — use getAllByText
    expect(screen.getAllByText('Upload').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Object storage').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Text extraction').length).toBeGreaterThanOrEqual(1)
  })

  it('renders the diagram with role="img"', () => {
    renderWithProviders(<AssetsPage />)
    const diagram = screen.getByRole('img')
    expect(diagram).toBeInTheDocument()
    expect(diagram).toHaveAttribute(
      'aria-label',
      expect.stringContaining('Asset ingestion flow'),
    )
  })

  it('renders the callout with title "Supported formats"', () => {
    renderWithProviders(<AssetsPage />)
    expect(screen.getByText('Supported formats')).toBeInTheDocument()
  })

  it('renders "Open Asset Library" CTA', () => {
    renderWithProviders(<AssetsPage />)
    const cta = screen.getByText('Open Asset Library')
    expect(cta).toBeInTheDocument()
    const ctaLink = cta.closest('a')
    expect(ctaLink).toHaveAttribute('href', '/assets')
  })

  it('renders "Back to Learning" link', () => {
    renderWithProviders(<AssetsPage />)
    const backLink = screen.getByText('← Back to Learning')
    expect(backLink).toBeInTheDocument()
    const link = backLink.closest('a')
    expect(link).toHaveAttribute('href', '/learning')
  })
})
