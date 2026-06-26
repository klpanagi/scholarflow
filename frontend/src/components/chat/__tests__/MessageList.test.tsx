import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MessageList, type ChatListMessage } from '../MessageList'

const mockMessages: ChatListMessage[] = [
  {
    id: '1',
    role: 'user',
    content: 'Hello',
    timestamp: new Date('2024-01-15T10:00:00'),
  },
  {
    id: '2',
    role: 'assistant',
    content: 'Hi there!',
    timestamp: new Date('2024-01-15T10:00:30'),
  },
]

describe('MessageList', () => {
  it('renders messages', () => {
    render(<MessageList messages={mockMessages} />)
    expect(screen.getByText('Hello')).toBeInTheDocument()
    expect(screen.getByText('Hi there!')).toBeInTheDocument()
  })

  it('renders date group labels', () => {
    render(<MessageList messages={mockMessages} />)
    // Date will be formatted as "Jan 15, 2024" since mock time isn't frozen
    expect(screen.getByText('Jan 15, 2024')).toBeInTheDocument()
  })

  it('renders empty state when no messages', () => {
    render(<MessageList messages={[]} />)
    expect(screen.getByText('Start a conversation')).toBeInTheDocument()
  })

  it('renders custom empty state', () => {
    render(
      <MessageList
        messages={[]}
        emptyState={<div>Custom empty state</div>}
      />,
    )
    expect(screen.getByText('Custom empty state')).toBeInTheDocument()
  })

  it('renders loading skeletons when isLoading is true', () => {
    const { container } = render(
      <MessageList messages={[]} isLoading={true} />,
    )
    const skeletons = container.querySelectorAll('.animate-pulse')
    expect(skeletons.length).toBeGreaterThan(0)
  })

  it('does not show empty state when loading', () => {
    render(<MessageList messages={[]} isLoading={true} />)
    expect(screen.queryByText('Start a conversation')).not.toBeInTheDocument()
  })
})
