import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  renderWithProviders,
  createQueryClient,
  createMockUser,
} from '@/__test-utils__/learning-test-helpers'

import { learningSections } from '@/content/learning'
import LearningPage from '@/pages/LearningPage'

// ---------------------------------------------------------------------------
// Smoke test — renders the LearningPage and checks all 6 section titles
// ---------------------------------------------------------------------------

it('smoke — LearningPage renders all 6 section titles', () => {
  renderWithProviders(<LearningPage />)
  for (const section of learningSections) {
    expect(screen.getByText(section.title)).toBeInTheDocument()
  }
})

// ---------------------------------------------------------------------------
// Infrastructure tests — verify the test wrapper behaves as expected
// ---------------------------------------------------------------------------

describe('test infrastructure', () => {
  it('renders trivial content through renderWithProviders', () => {
    renderWithProviders(<div>test</div>)
    expect(screen.getByText('test')).toBeInTheDocument()
  })

  it('creates fresh QueryClient instances per call', () => {
    const qc1 = createQueryClient()
    const qc2 = createQueryClient()
    expect(qc1).not.toBe(qc2)
  })
})
