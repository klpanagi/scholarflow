import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Sparkles,
  Network,
  Library,
  MessagesSquare,
  Workflow,
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
import { useReducedMotion, withReducedMotion, fadeInUp, pulseVariants } from '@/lib/motion'
import type { ContentBlock, ListBlock, CalloutBlock } from '@/content/learning'

// ---------------------------------------------------------------------------
// Icon map — maps string icon names from the content data to Lucide components
// ---------------------------------------------------------------------------
const LIST_ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  Network,
  Library,
  MessagesSquare,
  Workflow,
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
// SVG constants
// ---------------------------------------------------------------------------
const ARROW_COLOR = '#d4a574'
const NODE_COLOR = '#475569'

// ---------------------------------------------------------------------------
// Diagram component — hand-authored SVG of the Cult architecture
// ---------------------------------------------------------------------------

/** Corner node positions for the 4-corner layout */
const NODES = [
  { cx: 135, cy: 112, label: 'Agent registry', iconName: 'Network' },
  { cx: 465, cy: 112, label: 'Skill store', iconName: 'Library' },
  { cx: 135, cy: 288, label: 'Chat surface', iconName: 'MessagesSquare' },
  { cx: 465, cy: 288, label: 'Workflow engine', iconName: 'Workflow' },
] as const

/** Connecting lines from each corner node edge toward the center circle */
const CONNECTOR_LINES = [
  { from: '195,112.5', to: '258,165', delay: 0.3 },
  { from: '405,112.5', to: '342,165', delay: 0.5 },
  { from: '195,287.5', to: '258,235', delay: 0.7 },
  { from: '405,287.5', to: '342,235', delay: 0.9 },
] as const

/** Corner-node icon symbols as simple SVG path groups */
function NodeIcon({ iconName, cx, cy }: { iconName: string; cx: number; cy: number }) {
  switch (iconName) {
    case 'Network':
      return (
        <g>
          <line x1={cx - 6} y1={cy - 6} x2={cx} y2={cy + 2} stroke={ARROW_COLOR} strokeWidth={1.5} />
          <line x1={cx + 6} y1={cy - 6} x2={cx} y2={cy + 2} stroke={ARROW_COLOR} strokeWidth={1.5} />
          <line x1={cx - 6} y1={cy - 6} x2={cx + 6} y2={cy - 6} stroke={ARROW_COLOR} strokeWidth={1.5} />
          <circle cx={cx - 6} cy={cy - 6} r={3} fill={ARROW_COLOR} />
          <circle cx={cx + 6} cy={cy - 6} r={3} fill={ARROW_COLOR} />
          <circle cx={cx} cy={cy + 2} r={3} fill={ARROW_COLOR} />
        </g>
      )
    case 'Library':
      return (
        <g>
          <rect x={cx - 8} y={cy - 8} width={5} height={14} rx={1} fill={ARROW_COLOR} />
          <rect x={cx - 2} y={cy - 11} width={5} height={17} rx={1} fill={ARROW_COLOR} />
          <rect x={cx + 4} y={cy - 6} width={5} height={12} rx={1} fill={ARROW_COLOR} />
        </g>
      )
    case 'MessagesSquare':
      return (
        <g>
          <rect x={cx - 10} y={cy - 7} width={20} height={13} rx={3} fill="none" stroke={ARROW_COLOR} strokeWidth={1.5} />
          <polygon points={`${cx - 3},${cy + 6} ${cx},${cy + 10} ${cx + 3},${cy + 6}`} fill={ARROW_COLOR} />
        </g>
      )
    case 'Workflow':
      return (
        <g>
          <rect x={cx - 10} y={cy - 7} width={7} height={7} rx={1.5} fill={ARROW_COLOR} />
          <rect x={cx - 10} y={cy + 2} width={7} height={7} rx={1.5} fill={ARROW_COLOR} />
          <rect x={cx + 3} y={cy - 2} width={7} height={7} rx={1.5} fill={ARROW_COLOR} />
          <line x1={cx - 3} y1={cy} x2={cx + 3} y2={cy + 1} stroke={ARROW_COLOR} strokeWidth={1.5} />
          <line x1={cx - 6} y1={cy + 2} x2={cx - 6} y2={cy - 1} stroke={ARROW_COLOR} strokeWidth={1.5} />
        </g>
      )
    default:
      return null
  }
}

function CultArchitectureDiagram({ caption, prefersReduced }: { caption: string; prefersReduced: boolean }) {
  const lineProps = prefersReduced
    ? { initial: { pathLength: 1 }, animate: { pathLength: 1 } }
    : {
        initial: { pathLength: 0 },
        animate: { pathLength: 1 },
        transition: { duration: 1, ease: 'easeInOut' as const },
      }

  return (
    <motion.div
      variants={withReducedMotion(fadeInUp, prefersReduced)}
      initial="initial"
      animate="animate"
    >
    <figure className="my-8 flex flex-col items-center">
      <svg
        viewBox="0 0 600 400"
        role="img"
        aria-label={caption}
        className="w-full max-w-lg h-auto"
      >
        {/* Connector lines from each corner to center circle */}
        {CONNECTOR_LINES.map((line, i) => (
          <g key={`line-${i}`}>
            {/* Main line */}
            <motion.path
              d={`M ${line.from} L ${line.to}`}
              stroke={ARROW_COLOR}
              strokeWidth={2}
              fill="none"
              strokeLinecap="round"
              {...lineProps}
              transition={{ ...lineProps.transition, delay: line.delay }}
            />
            {/* Arrowhead */}
            <motion.path
              d={`M ${line.to} L ${Number(line.to.split(',')[0]) - 6},${Number(line.to.split(',')[1]) - 6} M ${line.to} L ${Number(line.to.split(',')[0]) + 6},${Number(line.to.split(',')[1]) - 6}`}
              stroke={ARROW_COLOR}
              strokeWidth={2}
              fill="none"
              strokeLinecap="round"
              strokeLinejoin="round"
              {...lineProps}
              transition={{ ...lineProps.transition, delay: line.delay + 0.1 }}
            />
          </g>
        ))}

        {/* Corner nodes */}
        {NODES.map((node, i) => (
          <motion.g
            key={`node-${i}`}
            initial={prefersReduced ? {} : { opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.2 + i * 0.15 }}
          >
            <rect
              x={node.cx - 60}
              y={node.cy - 32}
              width={120}
              height={64}
              rx={8}
              ry={8}
              fill={NODE_COLOR}
            />
            <NodeIcon iconName={node.iconName} cx={node.cx} cy={node.cy - 8} />
            <text
              x={node.cx}
              y={node.cy + 14}
              textAnchor="middle"
              fill={ARROW_COLOR}
              fontSize={11}
              fontWeight={600}
              fontFamily="system-ui, sans-serif"
            >
              {node.label}
            </text>
          </motion.g>
        ))}

        {/* Center circle — Cult hub */}
        <motion.circle
          cx={300}
          cy={200}
          r={55}
          fill={NODE_COLOR}
          stroke={ARROW_COLOR}
          strokeWidth={3}
          variants={prefersReduced ? {} : pulseVariants}
          animate="animate"
        />
        <text
          x={300}
          y={200}
          textAnchor="middle"
          dominantBaseline="central"
          fill="white"
          fontSize={18}
          fontWeight={700}
          fontFamily="system-ui, sans-serif"
        >
          Cult
        </text>
      </svg>
      <figcaption className="mt-3 text-center text-sm text-muted-foreground italic max-w-md">
        {caption}
      </figcaption>
    </figure>
    </motion.div>
  )
}

// ---------------------------------------------------------------------------
// Content block renderer
// ---------------------------------------------------------------------------

function ContentBlockRenderer({ block, prefersReduced }: { block: ContentBlock; prefersReduced: boolean }) {
  switch (block.type) {
    case 'text':
      return (
        <motion.div
          variants={withReducedMotion(fadeInUp, prefersReduced)}
          initial="initial"
          animate="animate"
        >
          <p className="prose prose-slate dark:prose-invert max-w-none text-base leading-relaxed text-foreground/90">
            {block.content}
          </p>
        </motion.div>
      )

    case 'list':
      return <ListBlockRenderer block={block} prefersReduced={prefersReduced} />

    case 'diagram':
      if (block.diagramId === 'cult-architecture') {
        return <CultArchitectureDiagram caption={block.caption} prefersReduced={prefersReduced} />
      }
      return null

    case 'callout':
      return <CalloutBlockRenderer block={block} prefersReduced={prefersReduced} />

    default:
      return null
  }
}

function ListBlockRenderer({ block, prefersReduced }: { block: ListBlock; prefersReduced: boolean }) {
  return (
    <motion.div
      variants={withReducedMotion(fadeInUp, prefersReduced)}
      initial="initial"
      animate="animate"
      className="grid gap-4 sm:grid-cols-2"
    >
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
    </motion.div>
  )
}

function CalloutBlockRenderer({ block, prefersReduced }: { block: CalloutBlock; prefersReduced: boolean }) {
  const style = CALLOUT_STYLES[block.variant]
  const Icon = style.icon

  return (
    <motion.div
      variants={withReducedMotion(fadeInUp, prefersReduced)}
      initial="initial"
      animate="animate"
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
    </motion.div>
  )
}

// ---------------------------------------------------------------------------
// Main page component
// ---------------------------------------------------------------------------

export default function CultPage() {
  const section = learningSections.find((s) => s.slug === 'cult')!
  const prefersReduced = useReducedMotion()

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
          <span className="font-medium text-foreground">The Cult</span>
        </nav>

        {/* Page header */}
        <PageHeader
          title={section.title}
          description={section.description}
          actions={
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
                <Sparkles className="h-5 w-5 text-primary" />
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
            <ContentBlockRenderer
              key={`block-${i}`}
              block={block}
              prefersReduced={prefersReduced}
            />
          ))}
        </div>

        {/* CTA footer */}
        <div className="flex flex-col items-start gap-4 border-t border-border/40 pt-6 sm:flex-row sm:items-center sm:justify-between">
          <Button asChild>
            <Link to="/cult">
              Open Cult Dashboard
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

CultPage.displayName = 'CultPage'
