import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { HealthStatus, type ProviderHealth } from '../HealthStatus'

const mockProviders: ProviderHealth[] = [
  { name: 'OpenAI', status: 'healthy', latency: 342 },
  { name: 'Anthropic', status: 'degraded', latency: 1200 },
  { name: 'Google', status: 'unhealthy' },
  { name: 'Meta', status: 'unknown', latency: 500 },
]

describe('HealthStatus', () => {
  it('renders all provider names', () => {
    render(<HealthStatus providers={mockProviders} />)
    expect(screen.getByText('OpenAI')).toBeInTheDocument()
    expect(screen.getByText('Anthropic')).toBeInTheDocument()
    expect(screen.getByText('Google')).toBeInTheDocument()
    expect(screen.getByText('Meta')).toBeInTheDocument()
  })

  it('renders status labels', () => {
    render(<HealthStatus providers={mockProviders} />)
    expect(screen.getByText('Healthy')).toBeInTheDocument()
    expect(screen.getByText('Degraded')).toBeInTheDocument()
    expect(screen.getByText('Unhealthy')).toBeInTheDocument()
    expect(screen.getByText('Unknown')).toBeInTheDocument()
  })

  it('renders latency in ms when < 1s', () => {
    render(<HealthStatus providers={mockProviders} />)
    expect(screen.getByText((content) => content.includes('342ms'))).toBeInTheDocument()
  })

  it('renders latency in seconds when >= 1s', () => {
    render(<HealthStatus providers={mockProviders} />)
    expect(screen.getByText((content) => content.includes('1.2s'))).toBeInTheDocument()
  })

  it('shows empty state when no providers', () => {
    render(<HealthStatus providers={[]} />)
    expect(screen.getByText('No providers configured')).toBeInTheDocument()
  })

  it('renders compact variant', () => {
    const { container } = render(
      <HealthStatus providers={mockProviders} variant="compact" />,
    )
    expect(container.firstChild?.className).toContain('space-y-1.5')
  })

  it('renders with role="list" on provider container', () => {
    render(<HealthStatus providers={mockProviders} />)
    expect(screen.getByRole('list')).toBeInTheDocument()
  })

  it('renders provider items with role="listitem"', () => {
    render(<HealthStatus providers={mockProviders} />)
    const items = screen.getAllByRole('listitem')
    expect(items).toHaveLength(4)
  })
})
