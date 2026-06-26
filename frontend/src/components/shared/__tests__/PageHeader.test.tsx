import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { PageHeader } from '../PageHeader'

describe('PageHeader', () => {
  it('renders title', () => {
    render(<PageHeader title="My Papers" />)
    expect(screen.getByText('My Papers')).toBeInTheDocument()
  })

  it('renders description when provided', () => {
    render(
      <PageHeader title="My Papers" description="Manage your publications" />,
    )
    expect(screen.getByText('Manage your publications')).toBeInTheDocument()
  })

  it('renders actions when provided', () => {
    render(
      <PageHeader
        title="My Papers"
        actions={<button>Add Paper</button>}
      />,
    )
    expect(screen.getByText('Add Paper')).toBeInTheDocument()
  })

  it('does not render actions container when empty', () => {
    const { container } = render(<PageHeader title="My Papers" />)
    // The actions slot div should not exist
    const actionDivs = container.querySelectorAll('.shrink-0')
    // The gold accent line also uses shrink-0, but it's not in an actions div
    expect(actionDivs.length).toBe(0)
  })

  it('renders with font-display on title', () => {
    const { container } = render(<PageHeader title="My Papers" />)
    const h1 = container.querySelector('h1')
    expect(h1?.className).toContain('font-display')
  })

  it('renders gold accent line', () => {
    const { container } = render(<PageHeader title="My Papers" />)
    const accentLine = container.querySelector('.bg-gold-500')
    expect(accentLine).toBeInTheDocument()
  })
})
