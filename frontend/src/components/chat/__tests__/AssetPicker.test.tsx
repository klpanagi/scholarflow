import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { AssetPicker } from '../AssetPicker'
import type { AssetSummary } from '@/types/chat'

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockUseAssetLibrary = vi.fn()

vi.mock('@/hooks/useAssetLibrary', () => ({
  useAssetLibrary: () => mockUseAssetLibrary(),
}))

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const makeAsset = (overrides: Partial<AssetSummary> = {}): AssetSummary => ({
  id: 'asset-1',
  title: 'Attention Is All You Need',
  authors: ['Ashish Vaswani', 'Noam Shazeer'],
  abstract: '',
  doi: '10.xxxx/xxxxx',
  arxiv_id: '1706.03762',
  year: 2017,
  venue: 'NeurIPS',
  tags: [],
  doc_type: 'paper',
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
  ...overrides,
})

const asset1 = makeAsset({ id: 'asset-1', title: 'Attention Is All You Need', authors: ['Ashish Vaswani', 'Noam Shazeer'], year: 2017 })
const asset2 = makeAsset({ id: 'asset-2', title: 'BERT: Pre-training of Deep Bidirectional Transformers', authors: ['Jacob Devlin'], year: 2018, doc_type: 'preprint' })
const asset3 = makeAsset({ id: 'asset-3', title: 'Deep Residual Learning', authors: ['Kaiming He', 'Xiangyu Zhang', 'Shaoqing Ren'], year: 2016 })

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('AssetPicker', () => {
  const onChange = vi.fn()

  beforeEach(() => {
    onChange.mockReset()
  })

  it('renders asset list when data is loaded', () => {
    mockUseAssetLibrary.mockReturnValue({
      data: { items: [asset1, asset2], total: 2, page: 1, size: 20 },
      isLoading: false,
    })

    render(<AssetPicker value={[]} onChange={onChange} />)

    expect(screen.getByText('Attention Is All You Need')).toBeInTheDocument()
    expect(screen.getByText('BERT: Pre-training of Deep Bidirectional Transformers')).toBeInTheDocument()
  })

  it('shows counter with current selection', () => {
    mockUseAssetLibrary.mockReturnValue({
      data: { items: [asset1, asset2], total: 2, page: 1, size: 20 },
      isLoading: false,
    })

    render(<AssetPicker value={['asset-1']} onChange={onChange} />)

    expect(screen.getByText('1 / 20 selected')).toBeInTheDocument()
  })

  it('toggles selection on checkbox click', () => {
    mockUseAssetLibrary.mockReturnValue({
      data: { items: [asset1, asset2], total: 2, page: 1, size: 20 },
      isLoading: false,
    })

    render(<AssetPicker value={[]} onChange={onChange} />)

    fireEvent.click(screen.getByLabelText('Select paper: Attention Is All You Need'))
    expect(onChange).toHaveBeenCalledWith(['asset-1'])
  })

  it('deselects asset when already selected', () => {
    mockUseAssetLibrary.mockReturnValue({
      data: { items: [asset1, asset2], total: 2, page: 1, size: 20 },
      isLoading: false,
    })

    render(<AssetPicker value={['asset-1', 'asset-2']} onChange={onChange} />)

    fireEvent.click(screen.getByLabelText('Select paper: Attention Is All You Need'))
    expect(onChange).toHaveBeenCalledWith(['asset-2'])
  })

  it('disables checkboxes when at max capacity', () => {
    const assets = Array.from({ length: 20 }, (_, i) =>
      makeAsset({ id: `a-${i}`, title: `Paper ${i}`, authors: ['Author'], year: 2020 }),
    )

    mockUseAssetLibrary.mockReturnValue({
      data: { items: assets, total: 20, page: 1, size: 20 },
      isLoading: false,
    })

    render(<AssetPicker value={assets.map((a) => a.id)} onChange={onChange} max={20} />)

    expect(screen.getByText('20 / 20 selected')).toBeInTheDocument()
    expect(screen.getByText('Maximum of 20 papers reached. Remove one to add another.')).toBeInTheDocument()
  })

  it('shows loading skeleton when data is loading', () => {
    mockUseAssetLibrary.mockReturnValue({
      data: undefined,
      isLoading: true,
    })

    const { container } = render(<AssetPicker value={[]} onChange={onChange} />)
    const skeletons = container.querySelectorAll('.animate-pulse')
    expect(skeletons.length).toBeGreaterThan(0)
  })

  it('shows empty state when no assets exist', () => {
    mockUseAssetLibrary.mockReturnValue({
      data: { items: [], total: 0, page: 1, size: 20 },
      isLoading: false,
    })

    render(<AssetPicker value={[]} onChange={onChange} />)
    expect(screen.getByText('No papers yet. Upload some in the Assets page.')).toBeInTheDocument()
  })

  it('removes asset via badge X button', () => {
    mockUseAssetLibrary.mockReturnValue({
      data: { items: [asset1, asset2], total: 2, page: 1, size: 20 },
      isLoading: false,
    })

    render(<AssetPicker value={['asset-1']} onChange={onChange} />)

    fireEvent.click(screen.getByLabelText('Remove Attention Is All You Need'))
    expect(onChange).toHaveBeenCalledWith([])
  })

  it('shows doc_type badge for each asset', () => {
    mockUseAssetLibrary.mockReturnValue({
      data: { items: [asset2], total: 1, page: 1, size: 20 },
      isLoading: false,
    })

    render(<AssetPicker value={[]} onChange={onChange} />)

    expect(screen.getByText('preprint')).toBeInTheDocument()
  })

  it('shows author list truncated for many authors', () => {
    mockUseAssetLibrary.mockReturnValue({
      data: { items: [asset3], total: 1, page: 1, size: 20 },
      isLoading: false,
    })

    render(<AssetPicker value={[]} onChange={onChange} />)

    expect(screen.getByText('Kaiming He, Xiangyu Zhang, et al.')).toBeInTheDocument()
  })
})
