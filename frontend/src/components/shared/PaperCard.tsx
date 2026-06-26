import { memo } from 'react'
import type React from 'react'
import { motion } from 'framer-motion'
import { BookOpen, Globe, Bookmark, Search, ExternalLink, Calendar, Hash } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useReducedMotion } from '@/lib/motion'
import { ScoreDisplay } from './ScoreDisplay'
import type { Scores } from './ScoreDisplay'

// ----- Types -----

export interface StoredPaper {
  id: string
  title: string
  abstract?: string
  year?: number
  authors?: string[]
  tags?: string[]
  field?: string
  scores?: Scores
  is_analyzed?: boolean
}

export interface ExternalPaper {
  id: string
  title: string
  year?: number
  authors?: string[]
  citation_count?: number
  source: 'arxiv' | 'semantic_scholar' | 'openalex' | 'crossref'
  url?: string
}

export type PaperCardProps = {
  /**
   * Optional click handler. Receives the paper so the parent can pass a
   * stable useCallback'd handler (which makes the React.memo wrap on this
   * component actually skip re-renders).
   */
  onClick?: (paper: StoredPaper | ExternalPaper) => void
  /** Additional class names */
  className?: string
} & (
  | { variant: 'stored'; paper: StoredPaper }
  | { variant: 'external'; paper: ExternalPaper }
)

// ----- Source config -----

interface SourceConfig {
  icon: React.ComponentType<{ className?: string }>
  label: string
  color: string
}

const sourceConfig: Record<string, SourceConfig> = {
  arxiv: {
    icon: BookOpen,
    label: 'arXiv',
    color: 'bg-red-500/10 text-red-500 border-red-500/20',
  },
  semantic_scholar: {
    icon: Search,
    label: 'Semantic Scholar',
    color: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
  },
  openalex: {
    icon: Globe,
    label: 'OpenAlex',
    color: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20',
  },
  crossref: {
    icon: Bookmark,
    label: 'CrossRef',
    color: 'bg-amber-500/10 text-amber-500 border-amber-500/20',
  },
}

// ----- Internal components -----

function SourceBadge({ source }: { source: string }) {
  const config = sourceConfig[source]
  if (!config) return null
  const Icon = config.icon
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-semibold',
        config.color,
      )}
    >
      <Icon className="h-3 w-3" />
      {config.label}
    </span>
  )
}

function TagsList({ tags }: { tags: string[] }) {
  if (tags.length === 0) return null
  const visible = tags.slice(0, 4)
  const remaining = tags.length - visible.length
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {visible.map((tag) => (
        <span
          key={tag}
          className="inline-flex items-center rounded-md bg-navy-500/10 px-2 py-0.5 text-[11px] font-medium text-navy-400 dark:text-navy-300"
        >
          {tag}
        </span>
      ))}
      {remaining > 0 && (
        <span className="text-[11px] text-muted-foreground">
          +{remaining}
        </span>
      )}
    </div>
  )
}

function AuthorsList({
  authors,
  max = 3,
}: {
  authors?: string[]
  max?: number
}) {
  if (!authors || authors.length === 0) return null
  const visible = authors.slice(0, max)
  const remaining = authors.length - visible.length
  return (
    <p className="truncate text-xs text-muted-foreground">
      {visible.join(', ')}
      {remaining > 0 && ` et al.`}
    </p>
  )
}

// ----- PaperCard -----

/**
 * PaperCard — A dual-variant card for displaying academic papers.
 *
 * - **stored**: For papers in the user's library (shows tags, scores if analyzed)
 * - **external**: For search results from academic APIs (shows source, citations)
 *
 * Features glassmorphism styling with hover glow and gold accent border.
 *
 * @example
 * ```tsx
 * // Stored variant
 * <PaperCard
 *   variant="stored"
 *   paper={{ id: '1', title: '...', authors: ['...'], scores: { quality: 8, novelty: 7, rigor: 9, clarity: 8 } }}
 * />
 *
 * // External variant
 * <PaperCard
 *   variant="external"
 *   paper={{ id: '2', title: '...', source: 'arxiv', citation_count: 42 }}
 * />
 * ```
 */
function PaperCardImpl(props: PaperCardProps) {
  const { onClick, className, ...rest } = props
  const prefersReduced = useReducedMotion()

  const hoverMotion = prefersReduced
    ? {}
    : {
        whileHover: { y: -2 },
        transition: { duration: 0.2, ease: 'easeOut' as const },
      }

  // ----- Stored variant -----
  if (rest.variant === 'stored') {
    const { paper } = rest
    const handleClick = onClick ? () => onClick(paper) : undefined
    return (
      <motion.div
        role="button"
        tabIndex={onClick ? 0 : undefined}
        onClick={handleClick}
        onKeyDown={
          onClick
            ? (e: React.KeyboardEvent) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  onClick(paper)
                }
              }
            : undefined
        }
        className={cn(
          'group relative overflow-hidden rounded-xl',
          'border border-border/40 bg-card/60 backdrop-blur-xl',
          'p-5',
          'transition-[border-color,box-shadow] duration-200',
          'hover:border-gold-500/50 hover:shadow-lg hover:shadow-gold-500/5',
          onClick && 'cursor-pointer',
          className,
        )}
        {...hoverMotion}
      >
        {/* Gold accent line */}
        <div className="absolute inset-x-0 top-0 h-0.5 scale-x-0 bg-gradient-to-r from-transparent via-gold-500/60 to-transparent transition-transform duration-300 group-hover:scale-x-100" />

        <div className="flex flex-col gap-3">
          {/* Header: field + analyzed badge */}
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <h3 className="line-clamp-2 text-sm font-semibold text-foreground leading-snug">
                {paper.title}
              </h3>
              <AuthorsList authors={paper.authors} />
            </div>
            {paper.is_analyzed && (
              <span className="shrink-0 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-500">
                Analyzed
              </span>
            )}
          </div>

          {/* Meta: year + tags */}
          <div className="flex flex-wrap items-center gap-3">
            {paper.year && (
              <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                <Calendar className="h-3 w-3" />
                {paper.year}
              </span>
            )}
            {paper.tags && <TagsList tags={paper.tags} />}
          </div>

          {/* Abstract preview */}
          {paper.abstract && (
            <p className="line-clamp-2 text-xs text-muted-foreground/80">
              {paper.abstract}
            </p>
          )}

          {/* Scores */}
          {paper.scores && paper.is_analyzed && (
            <div className="border-t border-border/30 pt-3">
              <ScoreDisplay scores={paper.scores} size="sm" />
            </div>
          )}
        </div>
      </motion.div>
    )
  }

  // ----- External variant -----
  const { paper } = rest
  const handleClick = onClick ? () => onClick(paper) : undefined
  return (
    <motion.div
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onClick={handleClick}
      onKeyDown={
        onClick
          ? (e: React.KeyboardEvent) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                onClick(paper)
              }
            }
          : undefined
      }
      className={cn(
        'group relative overflow-hidden rounded-xl',
        'border border-border/40 bg-card/60 backdrop-blur-xl',
        'p-5',
        'transition-[border-color,box-shadow] duration-200',
        'hover:border-gold-500/50 hover:shadow-lg hover:shadow-gold-500/5',
        onClick && 'cursor-pointer',
        className,
      )}
      {...hoverMotion}
    >
      {/* Gold accent line */}
      <div className="absolute inset-x-0 top-0 h-0.5 scale-x-0 bg-gradient-to-r from-transparent via-gold-500/60 to-transparent transition-transform duration-300 group-hover:scale-x-100" />

      <div className="flex flex-col gap-3">
        {/* Header: source badge + external link */}
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <h3 className="line-clamp-2 text-sm font-semibold text-foreground leading-snug">
              {paper.title}
            </h3>
            <AuthorsList authors={paper.authors} />
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <SourceBadge source={paper.source} />
            {paper.url && (
              <ExternalLink className="h-3.5 w-3.5 text-muted-foreground/60" />
            )}
          </div>
        </div>

        {/* Meta: year + citation count */}
        <div className="flex flex-wrap items-center gap-3">
          {paper.year && (
            <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
              <Calendar className="h-3 w-3" />
              {paper.year}
            </span>
          )}
          {paper.citation_count !== undefined && paper.citation_count !== null && (
            <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
              <Hash className="h-3 w-3" />
              {paper.citation_count.toLocaleString()} citations
            </span>
          )}
        </div>
      </div>
    </motion.div>
  )
}

export const PaperCard = /* @__PURE__ */ memo(PaperCardImpl)
PaperCard.displayName = 'PaperCard'

export default PaperCard
