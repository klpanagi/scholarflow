import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { LoadingState } from '../LoadingState'

describe('LoadingState', () => {
  function svgClass(container: HTMLElement): string {
    return container.querySelector('svg')?.getAttribute('class') ?? ''
  }

  it('renders with default size', () => {
    const { container } = render(<LoadingState />)
    const svg = container.querySelector('svg')
    expect(svg).toBeInTheDocument()
    expect(svgClass(container)).toContain('h-8')
  })

  it('renders label when provided', () => {
    render(<LoadingState label="Loading papers..." />)
    expect(screen.getByText('Loading papers...')).toBeInTheDocument()
  })

  it('has status role and aria-live', () => {
    render(<LoadingState label="Loading" />)
    const status = screen.getByRole('status')
    expect(status).toHaveAttribute('aria-live', 'polite')
  })

  it('has sr-only text for screen readers', () => {
    render(<LoadingState label="Loading papers" />)
    expect(screen.getByText('Loading: Loading papers')).toBeInTheDocument()
  })

  it('renders sm size', () => {
    const { container } = render(<LoadingState size="sm" />)
    expect(svgClass(container)).toContain('h-4')
  })

  it('renders lg size', () => {
    const { container } = render(<LoadingState size="lg" />)
    expect(svgClass(container)).toContain('h-12')
  })

  it('applies className', () => {
    const { container } = render(<LoadingState className="custom-wrapper" />)
    expect(container.firstChild).toHaveClass('custom-wrapper')
  })
})
