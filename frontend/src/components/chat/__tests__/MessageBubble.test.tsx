import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MessageBubble, MessageBubbleSkeleton } from '../MessageBubble'

describe('MessageBubble', () => {
  // ----- User role -----

  it('renders user message content', () => {
    render(<MessageBubble role="user" content="Hello!" />)
    expect(screen.getByText('Hello!')).toBeInTheDocument()
  })

  it('shows "You" label for user role', () => {
    render(<MessageBubble role="user" content="Hi" />)
    expect(screen.getByText('You')).toBeInTheDocument()
  })

  it('does not show assistant label for user', () => {
    render(<MessageBubble role="user" content="Hi" />)
    expect(screen.queryByText('Assistant')).not.toBeInTheDocument()
  })

  // ----- Assistant role -----

  it('renders assistant message content as string', () => {
    render(<MessageBubble role="assistant" content="How can I help?" />)
    expect(screen.getByText('How can I help?')).toBeInTheDocument()
  })

  it('shows "Assistant" label for assistant role', () => {
    render(<MessageBubble role="assistant" content="Hi" />)
    expect(screen.getByText('Assistant')).toBeInTheDocument()
  })

  it('renders model badge when provided', () => {
    render(
      <MessageBubble role="assistant" content="Hi" model="gpt-4" />,
    )
    expect(screen.getByText('gpt-4')).toBeInTheDocument()
  })

  it('renders provider badge when provided', () => {
    render(
      <MessageBubble role="assistant" content="Hi" provider="openai" />,
    )
    expect(screen.getByText('openai')).toBeInTheDocument()
  })

  it('shows streaming cursor when isStreaming is true', () => {
    render(
      <MessageBubble role="assistant" content="Thinking" isStreaming={true} />,
    )
    expect(screen.getByLabelText('Streaming response')).toBeInTheDocument()
  })

  // ----- System role -----

  it('renders system message', () => {
    render(<MessageBubble role="system" content="System message" />)
    expect(screen.getByText('System message')).toBeInTheDocument()
  })

  it('hides avatar for system role', () => {
    const { container } = render(
      <MessageBubble role="system" content="System message" />,
    )
    // No "You" or "Assistant" label
    expect(screen.queryByText('You')).not.toBeInTheDocument()
    expect(screen.queryByText('Assistant')).not.toBeInTheDocument()
    // No Bot icon
    expect(container.querySelector('.lucide-bot')).not.toBeInTheDocument()
  })

  // ----- Timestamp -----

  it('renders timestamp when provided as Date', () => {
    const date = new Date('2024-01-15T10:30:00')
    render(<MessageBubble role="user" content="Hi" timestamp={date} />)
    expect(screen.getByText('10:30 AM')).toBeInTheDocument()
  })

  it('renders timestamp when provided as string', () => {
    render(
      <MessageBubble
        role="user"
        content="Hi"
        timestamp="2024-01-15T10:30:00"
      />,
    )
    expect(screen.getByText('10:30 AM')).toBeInTheDocument()
  })

  it('hides timestamp when not provided', () => {
    render(<MessageBubble role="user" content="Hi" />)
    expect(screen.queryByText('AM')).not.toBeInTheDocument()
  })
})

describe('MessageBubbleSkeleton', () => {
  it('renders skeleton with animate-pulse', () => {
    const { container } = render(<MessageBubbleSkeleton />)
    const pulseElements = container.querySelectorAll('.animate-pulse')
    expect(pulseElements.length).toBeGreaterThan(0)
  })
})
