import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { StatusBadge, type StatusType } from '../StatusBadge'

describe('StatusBadge', () => {
  const statuses: StatusType[] = [
    'pending', 'running', 'completed', 'failed', 'cancelled',
    'queued', 'paused', 'error', 'success', 'warning', 'info',
  ]

  it.each(statuses)('renders %s status with correct label', (status) => {
    const { container } = render(<StatusBadge status={status} />)
    const expectedLabel = status.charAt(0).toUpperCase() + status.slice(1)
    expect(screen.getByText(expectedLabel)).toBeInTheDocument()
    expect(container.querySelector('svg')).toBeInTheDocument()
  })

  it('renders custom label when provided', () => {
    render(<StatusBadge status="running" label="In Progress" />)
    expect(screen.getByText('In Progress')).toBeInTheDocument()
    expect(screen.queryByText('Running')).not.toBeInTheDocument()
  })

  it('renders outline variant', () => {
    const { container } = render(<StatusBadge status="completed" variant="outline" />)
    const badge = container.firstChild as HTMLElement
    expect(badge.className).toContain('border')
    expect(badge.className).not.toContain('rounded-full')
  })

  it('applies additional className', () => {
    const { container } = render(<StatusBadge status="info" className="custom-class" />)
    expect(container.firstChild).toHaveClass('custom-class')
  })

  it('does not spin non-running icons', () => {
    const { container } = render(<StatusBadge status="completed" />)
    const svg = container.querySelector('svg')
    expect(svg?.className).not.toContain('animate-spin')
  })

  it('spins the icon when status is running', () => {
    const { container } = render(<StatusBadge status="running" />)
    const svg = container.querySelector('svg')
    expect(svg?.getAttribute('class')).toContain('animate-spin')
  })
})
