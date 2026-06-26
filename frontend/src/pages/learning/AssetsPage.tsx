import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  FileText,
  Upload,
  Database,
  FileSearch,
  Scissors,
  Search,
  Info,
  CheckCircle,
  AlertTriangle,
  ChevronRight,
  ArrowRight,
} from 'lucide-react'
import { learningSections } from '@/content/learning'
import { PageMotion } from '@/components/shared/PageMotion'
import { PageHeader } from '@/components/shared/PageHeader'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { ContentBlock, ListBlock, CalloutBlock } from '@/content/learning'

// ---------------------------------------------------------------------------
// Icon map — maps string icon names from the content data to Lucide components
// ---------------------------------------------------------------------------
const LIST_ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  Upload,
  Database,
  FileSearch,
  Scissors,
  Search,
}

// ---------------------------------------------------------------------------
// Callout variant configuration
// ---------------------------------------------------------------------------
const CALLOUT_STYLES = {
  info: {
    border: 'border-l-blue-500',
    bg: 'bg-blue-50/50 dark:bg-blue-950/10',
    icon: Info,
    iconColor: 'text-blue-600 dark:text-blue-400',
  },
  tip: {
    border: 'border-l-emerald-500',
    bg: 'bg-emerald-50/50 dark:bg-emerald-950/10',
    icon: CheckCircle,
    iconColor: 'text-emerald-600 dark:text-emerald-400',
  },
  warning: {
    border: 'border-l-amber-500',
    bg: 'bg-amber-50/50 dark:bg-amber-950/10',
    icon: AlertTriangle,
    iconColor: 'text-amber-600 dark:text-amber-400',
  },
} as const

// ---------------------------------------------------------------------------
// Diagram component — hand-authored SVG of the asset ingestion pipeline
// ---------------------------------------------------------------------------

const ARROW_COLOR = '#d4a574'
const NODE_COLOR = '#64748b'
const SVG_HEIGHT = 580
const SVG_WIDTH = 400
const COL_CENTER = SVG_WIDTH / 2

/** Y-centers for the 5 pipeline stages */
const STAGE_Y = [70, 165, 260, 355, 450]

function Arrow({ y1, y2 }: { y1: number; y2: number }) {
  const arrowTip = y2 - 8
  return (
    <g>
      <motion.path
        d={`M ${COL_CENTER} ${y1} L ${COL_CENTER} ${arrowTip}`}
        stroke={ARROW_COLOR}
        strokeWidth={2.5}
        fill="none"
        strokeLinecap="round"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 1.5, ease: 'easeInOut' }}
      />
      {/* Arrowhead */}
      <motion.path
        d={`M ${COL_CENTER - 6} ${arrowTip} L ${COL_CENTER} ${y2} L ${COL_CENTER + 6} ${arrowTip}`}
        stroke={ARROW_COLOR}
        strokeWidth={2.5}
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 1.5, ease: 'easeInOut' }}
      />
    </g>
  )
}

function DiagramNode({
  cx,
  cy,
  label,
  shape,
}: {
  cx: number
  cy: number
  label: string
  shape: 'circle' | 'rect'
}) {
  const rectW = 170
  const rectH = 48
  const rx = 10
  const x = cx - rectW / 2
  const y = cy - rectH / 2

  return (
    <g>
      {shape === 'circle' ? (
        <motion.circle
          cx={cx}
          cy={cy}
          r={28}
          fill={NODE_COLOR}
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
        />
      ) : (
        <motion.g
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5 }}
        >
          <rect
            x={x}
            y={y}
            width={rectW}
            height={rectH}
            rx={rx}
            ry={rx}
            fill={NODE_COLOR}
          />
        </motion.g>
      )}
      <text
        x={cx}
        y={cy + 4}
        textAnchor="middle"
        fill="white"
        fontSize={13}
        fontWeight={600}
        fontFamily="system-ui, sans-serif"
      >
        {label}
      </text>
    </g>
  )
}

function AssetPipelineDiagram({ caption }: { caption: string }) {
  return (
    <figure className="my-8 flex flex-col items-center">
      <svg
        viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`}
        role="img"
        aria-label={caption}
        className="w-full max-w-sm h-auto"
      >
        {/* Connector arrows between stages */}
        <Arrow y1={STAGE_Y[0] + 28} y2={STAGE_Y[1] - 24} />
        <Arrow y1={STAGE_Y[1] + 24} y2={STAGE_Y[2] - 24} />
        <Arrow y1={STAGE_Y[2] + 24} y2={STAGE_Y[3] - 24} />
        <Arrow y1={STAGE_Y[3] + 24} y2={STAGE_Y[4] - 24} />

        {/* Stage 1 — Upload (circle with pulse) */}
        <DiagramNode cx={COL_CENTER} cy={STAGE_Y[0]} label="Upload" shape="circle" />

        {/* Stage 2 — Object storage (rect with fadeIn) */}
        <DiagramNode cx={COL_CENTER} cy={STAGE_Y[1]} label="Object storage" shape="rect" />

        {/* Stage 3 — Text extraction (path with pathLength) */}
        <g>
          <motion.path
            d={`M ${COL_CENTER - 85} ${STAGE_Y[2] - 24} L ${COL_CENTER + 85} ${STAGE_Y[2] - 24} L ${COL_CENTER + 85} ${STAGE_Y[2] + 24} L ${COL_CENTER - 85} ${STAGE_Y[2] + 24} Z`}
            fill={NODE_COLOR}
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 1, ease: 'easeInOut' }}
          />
          <text
            x={COL_CENTER}
            y={STAGE_Y[2] + 4}
            textAnchor="middle"
            fill="white"
            fontSize={13}
            fontWeight={600}
            fontFamily="system-ui, sans-serif"
          >
            Text extraction
          </text>
        </g>

        {/* Stage 4 — Chunking (rect) */}
        <DiagramNode cx={COL_CENTER} cy={STAGE_Y[3]} label="Chunking" shape="rect" />

        {/* Stage 5 — Vector indexing (circle) */}
        <DiagramNode cx={COL_CENTER} cy={STAGE_Y[4]} label="Vector indexing" shape="circle" />
      </svg>
      <figcaption className="mt-3 text-center text-sm text-muted-foreground italic max-w-md">
        {caption}
      </figcaption>
    </figure>
  )
}

// ---------------------------------------------------------------------------
// Content block renderer
// ---------------------------------------------------------------------------

function ContentBlockRenderer({ block }: { block: ContentBlock }) {
  switch (block.type) {
    case 'text':
      return (
        <p className="prose prose-slate dark:prose-invert max-w-none text-base leading-relaxed text-foreground/90">
          {block.content}
        </p>
      )

    case 'list':
      return <ListBlockRenderer block={block} />

    case 'diagram':
      if (block.diagramId === 'asset-pipeline') {
        return <AssetPipelineDiagram caption={block.caption} />
      }
      return null

    case 'callout':
      return <CalloutBlockRenderer block={block} />

    default:
      return null
  }
}

function ListBlockRenderer({ block }: { block: ListBlock }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {block.items.map((item, i) => {
        const Icon = item.icon ? LIST_ICON_MAP[item.icon] : null
        return (
          <Card
            key={`${item.label}-${i}`}
            className="border-border/40 bg-card/60 backdrop-blur-sm transition-shadow hover:shadow-md"
          >
            <CardContent className="flex items-start gap-3 p-4">
              {Icon && (
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                  <Icon className="h-4.5 w-4.5 text-primary" />
                </div>
              )}
              <div className="min-w-0">
                <h4 className="text-sm font-semibold text-foreground">
                  {item.label}
                </h4>
                <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">
                  {item.description}
                </p>
              </div>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}

function CalloutBlockRenderer({ block }: { block: CalloutBlock }) {
  const style = CALLOUT_STYLES[block.variant]
  const Icon = style.icon

  return (
    <div
      className={cn(
        'rounded-lg border border-l-4 p-4',
        style.bg,
        style.border,
        'border-border/40',
      )}
    >
      <div className="flex items-start gap-3">
        <Icon className={cn('mt-0.5 h-5 w-5 shrink-0', style.iconColor)} />
        <div>
          <h4 className="text-sm font-semibold text-foreground">{block.title}</h4>
          <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
            {block.content}
          </p>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main page component
// ---------------------------------------------------------------------------

export default function AssetsPage() {
  const section = learningSections.find((s) => s.slug === 'assets')!

  return (
    <PageMotion>
      <div className="space-y-8">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-1.5 text-sm text-muted-foreground">
          <Link
            to="/learning"
            className="transition-colors hover:text-foreground"
          >
            Learning
          </Link>
          <ChevronRight className="h-3.5 w-3.5" />
          <span className="font-medium text-foreground">Assets</span>
        </nav>

        {/* Page header */}
        <PageHeader
          title={section.title}
          description={section.description}
          actions={
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
                <FileText className="h-5 w-5 text-primary" />
              </div>
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
                  {section.difficulty}
                </span>
                <span className="text-xs text-muted-foreground">
                  · {section.readingMinutes} min read
                </span>
              </div>
            </div>
          }
        />

        {/* Content blocks */}
        <div className="space-y-6">
          {section.sections.map((block, i) => (
            <ContentBlockRenderer key={`block-${i}`} block={block} />
          ))}
        </div>

        {/* CTA footer */}
        <div className="flex flex-col items-start gap-4 border-t border-border/40 pt-6 sm:flex-row sm:items-center sm:justify-between">
          <Button asChild>
            <Link to="/assets">
              Open Asset Library
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
          <Button variant="ghost" asChild>
            <Link to="/learning">← Back to Learning</Link>
          </Button>
        </div>
      </div>
    </PageMotion>
  )
}

AssetsPage.displayName = 'AssetsPage'
