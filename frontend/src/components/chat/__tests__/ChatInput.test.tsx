import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ChatInput } from '../ChatInput'

describe('ChatInput', () => {
  it('renders textarea with placeholder', () => {
    render(<ChatInput onSend={vi.fn()} />)
    const textarea = screen.getByPlaceholderText('Type a message...')
    expect(textarea).toBeInTheDocument()
  })

  it('renders send button', () => {
    render(<ChatInput onSend={vi.fn()} />)
    expect(screen.getByLabelText('Send message')).toBeInTheDocument()
  })

  it('renders attach file button', () => {
    render(<ChatInput onSend={vi.fn()} />)
    expect(screen.getByLabelText('Attach file')).toBeInTheDocument()
  })

  it('send button is disabled when input is empty', () => {
    render(<ChatInput onSend={vi.fn()} />)
    expect(screen.getByLabelText('Send message')).toBeDisabled()
  })

  it('shows streaming indicator when isStreaming is true', () => {
    render(<ChatInput onSend={vi.fn()} isStreaming={true} />)
    const pulseDot = document.querySelector('.animate-pulse')
    expect(pulseDot).toBeInTheDocument()
  })

  it('hides send button when streaming', () => {
    render(<ChatInput onSend={vi.fn()} isStreaming={true} />)
    expect(screen.queryByLabelText('Send message')).not.toBeInTheDocument()
  })

  it('disables textarea when disabled prop is true', () => {
    render(<ChatInput onSend={vi.fn()} disabled={true} />)
    expect(screen.getByPlaceholderText('Type a message...')).toBeDisabled()
  })

  it('renders helper text by default', () => {
    render(<ChatInput onSend={vi.fn()} />)
    expect(screen.getByText(/Enter to send/)).toBeInTheDocument()
  })

  it('renders char count when maxLength is set', () => {
    render(<ChatInput onSend={vi.fn()} maxLength={500} />)
    expect(screen.getByText('0/500')).toBeInTheDocument()
  })

  it('renders custom placeholder', () => {
    render(<ChatInput onSend={vi.fn()} placeholder="Ask anything..." />)
    expect(screen.getByPlaceholderText('Ask anything...')).toBeInTheDocument()
  })

  it('calls onSend when Enter is pressed with content', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn()
    render(<ChatInput onSend={onSend} />)

    const textarea = screen.getByPlaceholderText('Type a message...')
    await user.type(textarea, 'Hello')
    await user.keyboard('{Enter}')

    expect(onSend).toHaveBeenCalledWith('Hello', undefined)
  })

  it('does not call onSend when Enter is pressed with empty content', async () => {
    const user = userEvent.setup()
    const onSend = vi.fn()
    render(<ChatInput onSend={onSend} />)

    const textarea = screen.getByPlaceholderText('Type a message...')
    await user.type(textarea, '   ')
    await user.keyboard('{Enter}')

    expect(onSend).not.toHaveBeenCalled()
  })
})
