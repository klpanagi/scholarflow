import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ModalShell } from '../ModalShell'

describe('ModalShell', () => {
  it('renders nothing when open is false', () => {
    const { container } = render(
      <ModalShell open={false} onOpenChange={vi.fn()}>
        <p>Content</p>
      </ModalShell>,
    )
    expect(container.innerHTML).toBe('')
  })

  it('renders content when open is true', () => {
    render(
      <ModalShell open={true} onOpenChange={vi.fn()}>
        <p>Modal content</p>
      </ModalShell>,
    )
    expect(screen.getByText('Modal content')).toBeInTheDocument()
  })

  it('renders title when provided', () => {
    render(
      <ModalShell open={true} onOpenChange={vi.fn()} title="Edit Paper">
        <p>Content</p>
      </ModalShell>,
    )
    expect(screen.getByText('Edit Paper')).toBeInTheDocument()
  })

  it('renders description when provided', () => {
    render(
      <ModalShell
        open={true}
        onOpenChange={vi.fn()}
        description="Edit your paper details"
      >
        <p>Content</p>
      </ModalShell>,
    )
    expect(screen.getByText('Edit your paper details')).toBeInTheDocument()
  })

  it('renders footer when provided', () => {
    render(
      <ModalShell
        open={true}
        onOpenChange={vi.fn()}
        footer={<button>Save</button>}
      >
        <p>Content</p>
      </ModalShell>,
    )
    expect(screen.getByText('Save')).toBeInTheDocument()
  })

  it('has dialog role and aria-modal', () => {
    render(
      <ModalShell open={true} onOpenChange={vi.fn()}>
        <p>Content</p>
      </ModalShell>,
    )
    const dialog = screen.getByRole('dialog')
    expect(dialog).toHaveAttribute('aria-modal', 'true')
  })

  it('has close button with aria-label when title exists', () => {
    render(
      <ModalShell open={true} onOpenChange={vi.fn()} title="Test">
        <p>Content</p>
      </ModalShell>,
    )
    expect(screen.getByLabelText('Close modal')).toBeInTheDocument()
  })

  it('renders with aria-labelledby when title provided', () => {
    render(
      <ModalShell open={true} onOpenChange={vi.fn()} title="My Title">
        <p>Content</p>
      </ModalShell>,
    )
    const dialog = screen.getByRole('dialog')
    expect(dialog).toHaveAttribute('aria-labelledby', 'modal-title')
  })

  // Portal behavior: content renders in document.body
  it('renders content via portal to body when document exists', () => {
    render(
      <ModalShell open={true} onOpenChange={vi.fn()}>
        <p>Portal content</p>
      </ModalShell>,
    )
    expect(document.body.querySelector('p')?.textContent).toBe('Portal content')
  })
})
