import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { AgentPicker } from '../AgentPicker'
import type { AgentConfig } from '@/types/chat'

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockUseAgentConfigs = vi.fn()

vi.mock('@/hooks/useAgentConfigs', () => ({
  useAgentConfigs: () => mockUseAgentConfigs(),
}))

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const makeAgent = (overrides: Partial<AgentConfig> = {}): AgentConfig => ({
  id: 'cfg-1',
  name: 'Research Agent',
  role: 'researcher',
  provider: 'openrouter',
  model: 'openai/gpt-4o',
  temperature: 0.7,
  max_tokens: 4096,
  strategy: 'default',
  variant: null,
  tools: ['search_papers', 'read_paper'],
  system_prompt: '',
  is_default: true,
  skills: [],
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
  ...overrides,
})

const researcherAgent = makeAgent({ id: 'cfg-1', name: 'Research Agent', role: 'researcher', is_default: true })
const writerAgent = makeAgent({ id: 'cfg-2', name: 'Writing Agent', role: 'writer', model: 'anthropic/claude-sonnet-4-20250514', is_default: false })
const reviewerAgent = makeAgent({ id: 'cfg-3', name: 'Review Agent', role: 'reviewer', model: 'openai/gpt-4o-mini', is_default: false, tools: ['search_papers', 'read_paper', 'citation_check', 'summarize', 'deep_analysis'] })

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('AgentPicker', () => {
  const onChange = vi.fn()

  beforeEach(() => {
    onChange.mockReset()
  })

  it('renders agent cards when data is loaded', () => {
    mockUseAgentConfigs.mockReturnValue({
      data: [researcherAgent, writerAgent],
      isLoading: false,
    })

    render(<AgentPicker value={null} onChange={onChange} />)

    expect(screen.getByText('Research Agent')).toBeInTheDocument()
    expect(screen.getByText('Writing Agent')).toBeInTheDocument()
  })

  it('calls onChange when an agent card is clicked', () => {
    mockUseAgentConfigs.mockReturnValue({
      data: [researcherAgent, writerAgent],
      isLoading: false,
    })

    render(<AgentPicker value={null} onChange={onChange} />)

    fireEvent.click(screen.getByLabelText('Select agent Research Agent'))
    expect(onChange).toHaveBeenCalledWith('cfg-1')
  })

  it('highlights the selected agent', () => {
    mockUseAgentConfigs.mockReturnValue({
      data: [researcherAgent, writerAgent],
      isLoading: false,
    })

    render(<AgentPicker value="cfg-2" onChange={onChange} />)

    const selectedBtn = screen.getByLabelText('Select agent Writing Agent')
    expect(selectedBtn).toHaveAttribute('aria-pressed', 'true')
  })

  it('shows loading skeleton when configs are loading', () => {
    mockUseAgentConfigs.mockReturnValue({
      data: undefined,
      isLoading: true,
    })

    const { container } = render(<AgentPicker value={null} onChange={onChange} />)
    const skeletons = container.querySelectorAll('.animate-pulse')
    expect(skeletons.length).toBeGreaterThan(0)
  })

  it('shows empty state when no configs exist', () => {
    mockUseAgentConfigs.mockReturnValue({
      data: [],
      isLoading: false,
    })

    render(<AgentPicker value={null} onChange={onChange} />)
    expect(screen.getByText('No agent configurations found.')).toBeInTheDocument()
  })

  it('filters agents by search query', () => {
    mockUseAgentConfigs.mockReturnValue({
      data: [researcherAgent, writerAgent],
      isLoading: false,
    })

    render(<AgentPicker value={null} onChange={onChange} />)

    const searchInput = screen.getByPlaceholderText('Search agents by name, role, or model...')
    fireEvent.change(searchInput, { target: { value: 'Writing' } })

    expect(screen.getByText('Writing Agent')).toBeInTheDocument()
    expect(screen.queryByText('Research Agent')).not.toBeInTheDocument()
  })

  it('shows role labels as section headers', () => {
    mockUseAgentConfigs.mockReturnValue({
      data: [researcherAgent, writerAgent],
      isLoading: false,
    })

    render(<AgentPicker value={null} onChange={onChange} />)

    const researcherElements = screen.getAllByText('Researcher')
    expect(researcherElements.length).toBeGreaterThanOrEqual(1)
    const writerElements = screen.getAllByText('Writer')
    expect(writerElements.length).toBeGreaterThanOrEqual(1)
  })

  it('shows default star for default agents', () => {
    mockUseAgentConfigs.mockReturnValue({
      data: [researcherAgent],
      isLoading: false,
    })

    render(<AgentPicker value={null} onChange={onChange} />)

    expect(screen.getByLabelText('Default agent')).toBeInTheDocument()
  })

  it('displays model badge on agent cards', () => {
    mockUseAgentConfigs.mockReturnValue({
      data: [researcherAgent],
      isLoading: false,
    })

    render(<AgentPicker value={null} onChange={onChange} />)

    expect(screen.getByText('openai/gpt-4o')).toBeInTheDocument()
  })

  it('truncates tool badges showing max 4', () => {
    mockUseAgentConfigs.mockReturnValue({
      data: [reviewerAgent],
      isLoading: false,
    })

    render(<AgentPicker value={null} onChange={onChange} />)

    expect(screen.getByText('+1')).toBeInTheDocument()
  })
})
