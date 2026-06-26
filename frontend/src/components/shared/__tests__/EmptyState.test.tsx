import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { EmptyState } from '../EmptyState'
import { Inbox } from 'lucide-react'

describe('EmptyState', () => {
  it('renders title', () => {
    render(<EmptyState title="No papers yet" />)
    expect(screen.getByText('No papers yet')).toBeInTheDocument()
  })

  it('renders description when provided', () => {
    render(
      <EmptyState title="No papers" description="Upload your first paper to get started." />,
    )
    expect(
      screen.getByText('Upload your first paper to get started.'),
    ).toBeInTheDocument()
  })

  it('renders icon when provided', () => {
    const { container } = render(
      <EmptyState title="Empty" icon={Inbox} />,
    )
    expect(container.querySelector('.lucide-inbox')).toBeInTheDocument()
  })

  it('renders action button with onClick', () => {
    const onClick = vi.fn()
    render(
      <EmptyState
        title="Empty"
        action={{ label: 'Upload', onClick }}
      />,
    )
    const btn = screen.getByText('Upload')
    expect(btn).toBeInTheDocument()
    btn.click()
    expect(onClick).toHaveBeenCalledTimes(1)
  })

  it('renders action link when href is provided', () => {
    render(
      <EmptyState
        title="Empty"
        action={{ label: 'Go to Settings', href: '/settings' }}
      />,
    )
    const link = screen.getByText('Go to Settings')
    expect(link.tagName).toBe('A')
    expect(link).toHaveAttribute('href', '/settings')
  })
})
