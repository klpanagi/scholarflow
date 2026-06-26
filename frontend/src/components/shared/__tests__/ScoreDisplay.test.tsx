import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ScoreDisplay } from '../ScoreDisplay'

const mockScores = { quality: 8.5, novelty: 6.2, rigor: 7.8, clarity: 9.1 }

describe('ScoreDisplay', () => {
  it('renders all four score categories', () => {
    render(<ScoreDisplay scores={mockScores} />)
    expect(screen.getByText('Quality')).toBeInTheDocument()
    expect(screen.getByText('Novelty')).toBeInTheDocument()
    expect(screen.getByText('Rigor')).toBeInTheDocument()
    expect(screen.getByText('Clarity')).toBeInTheDocument()
  })

  it('renders score values', () => {
    render(<ScoreDisplay scores={mockScores} />)
    expect(screen.getByText('8.5')).toBeInTheDocument()
    expect(screen.getByText('6.2')).toBeInTheDocument()
    expect(screen.getByText('7.8')).toBeInTheDocument()
    expect(screen.getByText('9.1')).toBeInTheDocument()
  })

  it('renders grid layout by default', () => {
    const { container } = render(<ScoreDisplay scores={mockScores} />)
    const grid = container.firstChild as HTMLElement
    expect(grid.className).toContain('grid')
    expect(grid.className).toContain('grid-cols-2')
  })

  it('renders row layout', () => {
    const { container } = render(<ScoreDisplay scores={mockScores} layout="row" />)
    expect(container.firstChild?.className).toContain('flex-col')
    expect(container.firstChild?.className).not.toContain('grid')
  })

  it('clamps scores to 0-10 range', () => {
    render(<ScoreDisplay scores={{ quality: 15, novelty: -1, rigor: 5, clarity: 0 }} />)
    expect(screen.getByText('10.0')).toBeInTheDocument()
    const zeros = screen.getAllByText('0.0')
    expect(zeros.length).toBeGreaterThanOrEqual(2)
    expect(screen.getByText('5.0')).toBeInTheDocument()
  })

  it('renders sm size', () => {
    const { container } = render(<ScoreDisplay scores={mockScores} size="sm" />)
    const svgs = container.querySelectorAll('svg')
    expect(svgs.length).toBe(4)
    expect(svgs[0].getAttribute('width')).toBe('56')
  })

  it('applies className', () => {
    const { container } = render(
      <ScoreDisplay scores={mockScores} className="custom-class" />,
    )
    expect(container.firstChild).toHaveClass('custom-class')
  })
})
