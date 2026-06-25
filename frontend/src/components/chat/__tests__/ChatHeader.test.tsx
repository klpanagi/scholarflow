import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ChatHeader } from '../ChatHeader'
import type { ChatSession, AgentConfig, AssetSummary } from '@/types/chat'

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockUseAgentConfigs = vi.fn()
const mockUseAssetLibrary = vi.fn()

vi.mock('@/hooks/useAgentConfigs', () => ({
  useAgentConfigs: () => mockUseAgentConfigs(),
}))

vi.mock('@/hooks/useAssetLibrary', () => ({
  useAssetLibrary: (_q: string, _p: number, _s: number) => mockUseAssetLibrary(),
}))

// Mock Sheet components to avoid needing Dialog context
vi.mock('@/components/ui/sheet', () => ({
  Sheet: ({ children }: { children: React.ReactNode }) => <div data-testid="sheet">{children}</div>,
  SheetTrigger: ({ children, ...props }: { children: React.ReactNode; [key: string]: unknown }) => (
    <div data-testid="sheet-trigger" {...props}>{children}</div>
  ),
  SheetContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const makeSession = (overrides: Partial<ChatSession> = {}): ChatSession => ({
  id: 'sess-1',
  title: 'Test Session',
  model: 'openai/gpt-4o',
  provider: 'openrouter',
  system_prompt: null,
  agent_config_id: 'cfg-1',
  asset_ids: [],
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
  ...overrides,
})

const makeAgentConfig = (overrides: Partial<AgentConfig> = {}): AgentConfig => ({
  id: 'cfg-1',
  name: 'Research Agent',
  role: 'researcher',
  provider: 'openrouter',
  model: 'openai/gpt-4o',
  temperature: 0.7,
  max_tokens: 4096,
  strategy: 'default',
  variant: null,
  tools: ['search_papers'],
  system_prompt: '',
  is_default: true,
  skills: [],
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
  ...overrides,
})

const makeAsset = (overrides: Partial<AssetSummary> = {}): AssetSummary => ({
  id: 'asset-1',
  title: 'Attention Is All You Need',
  authors: ['Vaswani et al.'],
  abstract: null,
  doi: '10.48550/arXiv.1706.03762',
  arxiv_id: '1706.03762',
  year: 2017,
  venue: 'NeurIPS',
  tags: [],
  doc_type: 'paper',
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
  ...overrides,
})

const researcherAgent = makeAgentConfig({ id: 'cfg-1', name: 'Research Agent', role: 'researcher' })
const writerAgent = makeAgentConfig({ id: 'cfg-2', name: 'Writing Agent', role: 'writer' })
const asset1 = makeAsset({ id: 'asset-1', title: 'Attention Is All You Need' })
const asset2 = makeAsset({ id: 'asset-2', title: 'BERT: Pre-training of Deep Bidirectional Transformers' })

// ---------------------------------------------------------------------------
// Default props
// ---------------------------------------------------------------------------

const defaultProps = {
  availableModels: [],
  providers: [],
  showModelPicker: false,
  onToggleModelPicker: vi.fn(),
  modelSearchQuery: '',
  onModelSearchQueryChange: vi.fn(),
  onFork: vi.fn(),
  forkDisabled: false,
  onSelectModel: vi.fn(),
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ChatHeader', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseAgentConfigs.mockReturnValue({
      data: [researcherAgent, writerAgent],
      isLoading: false,
    })
    mockUseAssetLibrary.mockReturnValue({
      data: { items: [asset1, asset2], total: 2, page: 1, size: 100 },
      isLoading: false,
    })
  })

  it('renders the session title', () => {
    const session = makeSession({ title: 'My Research Chat' })
    render(<ChatHeader session={session} {...defaultProps} />)

    expect(screen.getByText('My Research Chat')).toBeInTheDocument()
  })

  it('renders "Untitled" when title is null', () => {
    const session = makeSession({ title: null })
    render(<ChatHeader session={session} {...defaultProps} />)

    expect(screen.getByText('Untitled')).toBeInTheDocument()
  })

  it('renders agent name and role badge', () => {
    const session = makeSession({ agent_config_id: 'cfg-1' })
    render(<ChatHeader session={session} {...defaultProps} />)

    expect(screen.getByText(/Research Agent/)).toBeInTheDocument()
    expect(screen.getByText(/Researcher/)).toBeInTheDocument()
  })

  it('renders "default" label when agent_config_id is null', () => {
    const session = makeSession({ agent_config_id: null })
    render(<ChatHeader session={session} {...defaultProps} />)

    expect(screen.getByText('default')).toBeInTheDocument()
  })

  it('renders "(agent unavailable)" when agent ID does not match any config', () => {
    const session = makeSession({ agent_config_id: 'cfg-nonexistent' })
    render(<ChatHeader session={session} {...defaultProps} />)

    expect(screen.getByText('(agent unavailable)')).toBeInTheDocument()
  })

  it('renders asset pills for attached papers', () => {
    const session = makeSession({ asset_ids: ['asset-1', 'asset-2'] })
    render(<ChatHeader session={session} {...defaultProps} />)

    expect(screen.getByText('Attention Is All You Need')).toBeInTheDocument()
    expect(screen.getByText(/BERT: Pre-training/)).toBeInTheDocument()
  })

  it('shows "(paper unavailable)" for asset IDs not in the library', () => {
    const session = makeSession({ asset_ids: ['asset-missing'] })
    render(<ChatHeader session={session} {...defaultProps} />)

    expect(screen.getByText('(paper unavailable)')).toBeInTheDocument()
  })

  it('does not render asset pills when asset_ids is empty', () => {
    const session = makeSession({ asset_ids: [] })
    render(<ChatHeader session={session} {...defaultProps} />)

    expect(screen.queryByText('Attention Is All You Need')).not.toBeInTheDocument()
  })

  it('renders provider and model badges', () => {
    const session = makeSession({ provider: 'openrouter', model: 'openai/gpt-4o' })
    render(<ChatHeader session={session} {...defaultProps} />)

    expect(screen.getByText('openrouter')).toBeInTheDocument()
    expect(screen.getByText('openai/gpt-4o')).toBeInTheDocument()
  })

  it('shows skeleton when agent configs are loading', () => {
    mockUseAgentConfigs.mockReturnValue({
      data: undefined,
      isLoading: true,
    })
    mockUseAssetLibrary.mockReturnValue({
      data: undefined,
      isLoading: true,
    })

    const session = makeSession({ agent_config_id: 'cfg-1', asset_ids: ['asset-1'] })
    const { container } = render(<ChatHeader session={session} {...defaultProps} />)

    const skeletons = container.querySelectorAll('.animate-pulse')
    expect(skeletons.length).toBeGreaterThan(0)
  })

  it('shows skeleton for asset pills when asset library is loading', () => {
    mockUseAssetLibrary.mockReturnValue({
      data: undefined,
      isLoading: true,
    })

    const session = makeSession({ asset_ids: ['asset-1', 'asset-2'] })
    const { container } = render(<ChatHeader session={session} {...defaultProps} />)

    const skeletons = container.querySelectorAll('.animate-pulse')
    expect(skeletons.length).toBeGreaterThan(0)
  })

  it('has accessible aria-label on agent badge', () => {
    const session = makeSession({ agent_config_id: 'cfg-1' })
    render(<ChatHeader session={session} {...defaultProps} />)

    expect(
      screen.getByLabelText('Agent: Research Agent (Researcher)'),
    ).toBeInTheDocument()
  })

  it('has accessible aria-label on asset pills', () => {
    const session = makeSession({ asset_ids: ['asset-1'] })
    render(<ChatHeader session={session} {...defaultProps} />)

    expect(
      screen.getByLabelText('Attached paper: Attention Is All You Need'),
    ).toBeInTheDocument()
  })

  it('has accessible aria-label on legacy default badge', () => {
    const session = makeSession({ agent_config_id: null })
    render(<ChatHeader session={session} {...defaultProps} />)

    expect(
      screen.getByLabelText('No agent assigned (legacy session)'),
    ).toBeInTheDocument()
  })

  it('sets title attribute on asset pills for tooltip', () => {
    const session = makeSession({ asset_ids: ['asset-1'] })
    render(<ChatHeader session={session} {...defaultProps} />)

    const pill = screen.getByText('Attention Is All You Need')
    expect(pill.closest('[title]')).toHaveAttribute(
      'title',
      'Attention Is All You Need',
    )
  })

  it('renders the fork button', () => {
    const session = makeSession()
    render(<ChatHeader session={session} {...defaultProps} />)

    expect(screen.getByText('Fork')).toBeInTheDocument()
  })

  it('renders the model switch button', () => {
    const session = makeSession()
    render(<ChatHeader session={session} {...defaultProps} />)

    expect(screen.getByText('Switch')).toBeInTheDocument()
  })
})
