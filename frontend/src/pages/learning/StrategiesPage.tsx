import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Swords,
  Zap,
  MessageSquare,
  RefreshCw,
  IterationCw,
  ChevronRight,
  ArrowRight,
  CheckCircle,
  Info,
  AlertTriangle,
} from 'lucide-react'
import { learningSections } from '@/content/learning'
import { PageMotion } from '@/components/shared/PageMotion'
import { PageHeader } from '@/components/shared/PageHeader'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { useReducedMotion } from '@/lib/motion'
import type { ContentBlock, ListBlock, CalloutBlock } from '@/content/learning'

const STRATEGY_ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  Zap,
  MessageSquare,
  RefreshCw,
  IterationCw,
}

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

const LANES = [
  { x: 130, label: 'direct', costLabel: '1x' },
  { x: 290, label: 'critique', costLabel: '2x' },
  { x: 450, label: 'reflection', costLabel: '2.5x' },
  { x: 610, label: 'evaluator_optimizer', costLabel: '8x' },
] as const

const NODE_RADIUS = 18
const GOLD_FILL = '#D4A017'
const NAVY_STROKE = '#1B2A4A'
const ARROW_NAVY = '#334155'

const TOP_Y = 90
const DRAFT_Y = 190
const MID_Y = 280
const BOTTOM_Y = 380

function Defs() {
  return (
    <defs>
      <marker
        id="arrowhead"
        markerWidth={10}
        markerHeight={8}
        refX={9}
        refY={4}
        orient="auto"
      >
        <path d="M 0 0 L 10 4 L 0 8 Z" fill={ARROW_NAVY} />
      </marker>
    </defs>
  )
}

function Arrow({ y1, y2 }: { y1: number; y2: number }) {
  const tipY = y2 - NODE_RADIUS - 2
  return (
    <g>
      <motion.path
        d={`M 0 ${y1 + NODE_RADIUS + 2} L 0 ${tipY}`}
        stroke={ARROW_NAVY}
        strokeWidth={2.5}
        fill="none"
        strokeLinecap="round"
        markerEnd="url(#arrowhead)"
      />
    </g>
  )
}

function Node({ cy, label }: { cy: number; label: string }) {
  return (
    <g>
      <motion.circle
        cx={0}
        cy={cy}
        r={NODE_RADIUS}
        fill={GOLD_FILL}
        stroke={NAVY_STROKE}
        strokeWidth={2}
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
      />
      <text
        x={0}
        y={cy + 1}
        textAnchor="middle"
        fill="white"
        fontSize={10}
        fontWeight={600}
        fontFamily="system-ui, sans-serif"
      >
        {label}
      </text>
    </g>
  )
}

function LoopArrow() {
  return (
    <motion.path
      d={`M 0 ${MID_Y - NODE_RADIUS - 2} C 80 ${MID_Y - NODE_RADIUS - 2} 80 ${TOP_Y + NODE_RADIUS + 2} 0 ${TOP_Y + NODE_RADIUS + 2}`}
      stroke={ARROW_NAVY}
      strokeWidth={2.5}
      fill="none"
      strokeLinecap="round"
      markerEnd="url(#arrowhead)"
    />
  )
}

function StrategyFlowDiagram({ caption }: { caption: string }) {
  const prefersReduced = useReducedMotion()

  return (
    <figure className="my-8 flex flex-col items-center">
      <svg
        viewBox="0 0 800 460"
        role="img"
        aria-label={caption}
        className="w-full max-w-3xl h-auto"
      >
        <Defs />

        {/* Lane labels at top */}
        {LANES.map((lane) => (
          <text
            key={lane.label}
            x={lane.x}
            y={35}
            textAnchor="middle"
            fill="#64748b"
            fontSize={11}
            fontWeight={600}
            fontFamily="system-ui, sans-serif"
            style={{ textTransform: 'uppercase', letterSpacing: '1px' }}
          >
            {lane.label}
          </text>
        ))}

        {/* Lane 1 — direct: Prompt → Answer */}
        <g transform={`translate(${LANES[0].x}, 0)`}>
          <Arrow y1={TOP_Y} y2={BOTTOM_Y} />
          <Node cy={TOP_Y} label="Prompt" />
          <Node cy={BOTTOM_Y} label="Answer" />
        </g>

        {/* Lane 2 — critique: Prompt → Draft → Critique → Revised */}
        <g transform={`translate(${LANES[1].x}, 0)`}>
          <Arrow y1={TOP_Y} y2={DRAFT_Y} />
          <Arrow y1={DRAFT_Y} y2={MID_Y} />
          <Arrow y1={MID_Y} y2={BOTTOM_Y} />
          <Node cy={TOP_Y} label="Prompt" />
          <Node cy={DRAFT_Y} label="Draft" />
          <Node cy={MID_Y} label="Critique" />
          <Node cy={BOTTOM_Y} label="Revised" />
        </g>

        {/* Lane 3 — reflection: Prompt → Draft → Reflect → Honest Draft */}
        <g transform={`translate(${LANES[2].x}, 0)`}>
          <Arrow y1={TOP_Y} y2={DRAFT_Y} />
          <Arrow y1={DRAFT_Y} y2={MID_Y} />
          <Arrow y1={MID_Y} y2={BOTTOM_Y} />
          <Node cy={TOP_Y} label="Prompt" />
          <Node cy={DRAFT_Y} label="Draft" />
          <Node cy={MID_Y} label="Reflect" />
          <Node cy={BOTTOM_Y} label="Honest" />
        </g>

        {/* Lane 4 — evaluator_optimizer: Generator ↔ Evaluator → Final */}
        <g transform={`translate(${LANES[3].x}, 0)`}>
          {/* Generator → Evaluator (straight) */}
          <Arrow y1={TOP_Y} y2={MID_Y} />
          {/* Evaluator → Generator (loop back) */}
          {prefersReduced ? (
            <path
              d={`M 0 ${MID_Y - NODE_RADIUS - 2} C 80 ${MID_Y - NODE_RADIUS - 2} 80 ${TOP_Y + NODE_RADIUS + 2} 0 ${TOP_Y + NODE_RADIUS + 2}`}
              stroke={ARROW_NAVY}
              strokeWidth={2.5}
              fill="none"
              strokeLinecap="round"
              markerEnd="url(#arrowhead)"
            />
          ) : (
            <LoopArrow />
          )}
          {/* Evaluator → Final (straight) */}
          <Arrow y1={MID_Y} y2={BOTTOM_Y} />
          <Node cy={TOP_Y} label="Generator" />
          <Node cy={MID_Y} label="Evaluator" />
          <Node cy={BOTTOM_Y} label="Final" />
        </g>

        {/* Cost labels on the far right */}
        {LANES.map((lane) => (
          <text
            key={`cost-${lane.label}`}
            x={lane.x + 65}
            y={BOTTOM_Y + 4}
            textAnchor="start"
            fill="#64748b"
            fontSize={13}
            fontWeight={700}
            fontFamily="system-ui, sans-serif"
          >
            {lane.costLabel}
          </text>
        ))}
      </svg>
      <figcaption className="mt-3 text-center text-sm text-muted-foreground italic max-w-2xl">
        {caption}
      </figcaption>
    </figure>
  )
}

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
      if (block.diagramId === 'strategy-flow') {
        return <StrategyFlowDiagram caption={block.caption} />
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
    <div className="grid gap-4 grid-cols-1 md:grid-cols-2">
      {block.items.map((item, i) => {
        const Icon = item.icon ? STRATEGY_ICON_MAP[item.icon] : null
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
  const style = CALLOUT_STYLES[block.variant] ?? CALLOUT_STYLES.info
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
        {Icon && <Icon className={cn('mt-0.5 h-5 w-5 shrink-0', style.iconColor)} />}
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

export default function StrategiesPage() {
  const section = learningSections.find((s) => s.slug === 'strategies')!

  return (
    <PageMotion>
      <div className="space-y-8">
        <nav className="flex items-center gap-1.5 text-sm text-muted-foreground">
          <Link
            to="/learning"
            className="transition-colors hover:text-foreground"
          >
            Learning
          </Link>
          <ChevronRight className="h-3.5 w-3.5" />
          <span className="font-medium text-foreground">Agent Strategies</span>
        </nav>

        <PageHeader
          title={section.title}
          description={section.description}
          actions={
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
                <Swords className="h-5 w-5 text-primary" />
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

        <div className="space-y-6">
          {section.sections.map((block, i) => (
            <ContentBlockRenderer key={`block-${i}`} block={block} />
          ))}
        </div>

        <div className="flex flex-col items-start gap-4 border-t border-border/40 pt-6 sm:flex-row sm:items-center sm:justify-between">
          <Button asChild>
            <Link to="/workflows">
              View Workflows
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

StrategiesPage.displayName = 'StrategiesPage'
