import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ConfirmDialog } from '../ConfirmDialog'

describe('ConfirmDialog', () => {
  const defaultProps = {
    open: true,
    onOpenChange: vi.fn(),
    title: 'Delete paper?',
    description: 'This action cannot be undone.',
    onConfirm: vi.fn(),
  }

  it('renders title and description', () => {
    render(<ConfirmDialog {...defaultProps} />)
    expect(screen.getByText('Delete paper?')).toBeInTheDocument()
    expect(screen.getByText('This action cannot be undone.')).toBeInTheDocument()
  })

  it('renders default confirm and cancel text', () => {
    render(<ConfirmDialog {...defaultProps} />)
    expect(screen.getByText('Confirm')).toBeInTheDocument()
    expect(screen.getByText('Cancel')).toBeInTheDocument()
  })

  it('renders custom button text', () => {
    render(
      <ConfirmDialog
        {...defaultProps}
        confirmText="Delete"
        cancelText="Keep"
      />,
    )
    expect(screen.getByText('Delete')).toBeInTheDocument()
    expect(screen.getByText('Keep')).toBeInTheDocument()
  })

  it('calls onOpenChange(false) when cancel is clicked', () => {
    const onOpenChange = vi.fn()
    render(<ConfirmDialog {...defaultProps} onOpenChange={onOpenChange} />)
    screen.getByText('Cancel').click()
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it('calls onConfirm when confirm is clicked', () => {
    const onConfirm = vi.fn()
    render(<ConfirmDialog {...defaultProps} onConfirm={onConfirm} />)
    screen.getByText('Confirm').click()
    expect(onConfirm).toHaveBeenCalledTimes(1)
  })

  it('disables buttons when loading', () => {
    render(<ConfirmDialog {...defaultProps} loading={true} />)
    expect(screen.getByText('Confirm').closest('button')).toBeDisabled()
    expect(screen.getByText('Cancel').closest('button')).toBeDisabled()
  })

  it('renders loader spinner when loading', () => {
    render(
      <ConfirmDialog {...defaultProps} loading={true} />,
    )
    // ModalShell uses createPortal, icon renders in document.body
    // lucide-react v0.294 doesn't auto-add lucide-* classes; className is mr-2 h-4 w-4 animate-spin
    expect(document.querySelector('.animate-spin')).toBeInTheDocument()
  })

  it('renders danger variant with destructive button', () => {
    render(<ConfirmDialog {...defaultProps} variant="danger" />)
    const confirmBtn = screen.getByText('Confirm')
    expect(confirmBtn.className).toContain('destructive')
  })
})
