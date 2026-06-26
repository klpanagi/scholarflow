import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { WorkflowStageStatus, type WorkflowStatus } from '../WorkflowStageStatus'

describe('WorkflowStageStatus', () => {
  const statuses: { status: WorkflowStatus; label: string }[] = [
    { status: 'pending', label: 'Pending' },
    { status: 'running', label: 'Running' },
    { status: 'completed', label: 'Completed' },
    { status: 'failed', label: 'Failed' },
    { status: 'cancelled', label: 'Cancelled' },
    { status: 'queued', label: 'Queued' },
    { status: 'paused', label: 'Paused' },
  ]

  it.each(statuses)('renders $status status with $label label', ({ status, label }) => {
    render(<WorkflowStageStatus status={status} />)
    expect(screen.getByText(label)).toBeInTheDocument()
  })

  it('renders the stage name when provided', () => {
    render(<WorkflowStageStatus status="running" name="Literature Review" />)
    expect(screen.getByText('Literature Review')).toBeInTheDocument()
  })

  it('renders progress bar for running status with progress', () => {
    const { container } = render(
      <WorkflowStageStatus status="running" progress={65} />,
    )
    const progressBar = container.querySelector('[style*="width"]')
    expect(progressBar).toBeInTheDocument()
    expect((progressBar as HTMLElement).style.width).toBe('65%')
  })

  it('hides progress bar when progress is undefined even for running', () => {
    const { container } = render(<WorkflowStageStatus status="running" />)
    expect(container.querySelector('[style*="width"]')).not.toBeInTheDocument()
  })

  it('hides progress bar for non-running statuses', () => {
    const { container } = render(
      <WorkflowStageStatus status="completed" progress={100} />,
    )
    expect(container.querySelector('[style*="width"]')).not.toBeInTheDocument()
  })

  it('renders different sizes', () => {
    const { container: sm } = render(<WorkflowStageStatus status="pending" size="sm" />)
    const { container: lg } = render(<WorkflowStageStatus status="pending" size="lg" />)
    const smSvg = sm.querySelector('svg')
    const lgSvg = lg.querySelector('svg')
    expect(smSvg?.getAttribute('class')).toContain('h-4')
    expect(lgSvg?.getAttribute('class')).toContain('h-6')
  })
})
