import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { PaperCard } from '../PaperCard'
import type { StoredPaper, ExternalPaper } from '../PaperCard'

describe('PaperCard', () => {
  const storedPaper: StoredPaper = {
    id: '1',
    title: 'Deep Learning in NLP',
    authors: ['Alice Smith', 'Bob Jones'],
    year: 2024,
    abstract: 'A comprehensive survey of deep learning methods.',
    tags: ['NLP', 'deep-learning', 'survey', 'transformer', 'extra'],
    is_analyzed: true,
    scores: { quality: 8, novelty: 7, rigor: 9, clarity: 8 },
  }

  const externalPaper: ExternalPaper = {
    id: '2',
    title: 'Attention Is All You Need',
    authors: ['Vaswani et al.'],
    year: 2017,
    source: 'arxiv',
    citation_count: 100000,
    url: 'https://arxiv.org/abs/1706.03762',
  }

  // ----- Stored variant -----

  it('renders title for stored variant', () => {
    render(<PaperCard variant="stored" paper={storedPaper} />)
    expect(screen.getByText('Deep Learning in NLP')).toBeInTheDocument()
  })

  it('renders authors for stored variant', () => {
    render(<PaperCard variant="stored" paper={storedPaper} />)
    expect(screen.getByText('Alice Smith, Bob Jones')).toBeInTheDocument()
  })

  it('renders year for stored variant', () => {
    render(<PaperCard variant="stored" paper={storedPaper} />)
    expect(screen.getByText('2024')).toBeInTheDocument()
  })

  it('renders abstract for stored variant', () => {
    render(<PaperCard variant="stored" paper={storedPaper} />)
    expect(screen.getByText('A comprehensive survey of deep learning methods.')).toBeInTheDocument()
  })

  it('renders analyzed badge when is_analyzed is true', () => {
    render(<PaperCard variant="stored" paper={storedPaper} />)
    expect(screen.getByText('Analyzed')).toBeInTheDocument()
  })

  it('hides analyzed badge when is_analyzed is false', () => {
    render(<PaperCard variant="stored" paper={{ ...storedPaper, is_analyzed: false }} />)
    expect(screen.queryByText('Analyzed')).not.toBeInTheDocument()
  })

  it('renders tags with overflow count', () => {
    render(<PaperCard variant="stored" paper={storedPaper} />)
    expect(screen.getByText('NLP')).toBeInTheDocument()
    expect(screen.getByText('+1')).toBeInTheDocument()
  })

  it('calls onClick when clicked', () => {
    const onClick = vi.fn()
    render(<PaperCard variant="stored" paper={storedPaper} onClick={onClick} />)
    screen.getByText('Deep Learning in NLP').closest('[role="button"]')?.click()
    expect(onClick).toHaveBeenCalledTimes(1)
  })

  it('renders scores section when paper is analyzed with scores', () => {
    render(<PaperCard variant="stored" paper={storedPaper} />)
    const eights = screen.getAllByText('8.0')
    expect(eights.length).toBeGreaterThanOrEqual(2)
  })

  // ----- External variant -----

  it('renders title for external variant', () => {
    render(<PaperCard variant="external" paper={externalPaper} />)
    expect(screen.getByText('Attention Is All You Need')).toBeInTheDocument()
  })

  it('renders source badge for external variant', () => {
    render(<PaperCard variant="external" paper={externalPaper} />)
    expect(screen.getByText('arXiv')).toBeInTheDocument()
  })

  it('renders citation count for external variant', () => {
    render(<PaperCard variant="external" paper={externalPaper} />)
    expect(screen.getByText('100,000 citations')).toBeInTheDocument()
  })

  it('renders external link icon when URL present', () => {
    const { container } = render(<PaperCard variant="external" paper={externalPaper} />)
    expect(container.querySelector('.lucide-external-link')).toBeInTheDocument()
  })

  it('hides citation count when undefined', () => {
    render(
      <PaperCard
        variant="external"
        paper={{ ...externalPaper, citation_count: undefined }}
      />,
    )
    expect(screen.queryByText(/citations/)).not.toBeInTheDocument()
  })

  it('hides abstract for external variant', () => {
    render(
      <PaperCard
        variant="external"
        paper={externalPaper}
      />,
    )
    expect(screen.queryByText('A comprehensive')).not.toBeInTheDocument()
  })
})
