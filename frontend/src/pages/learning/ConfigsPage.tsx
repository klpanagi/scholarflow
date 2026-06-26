import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Settings2,
  FileText,
  ClipboardCheck,
  KanbanSquare,
  FileSignature,
  Swords,
  Search,
  PenLine,
  Sparkles,
  Microscope,
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
  FileText,
  ClipboardCheck,
  KanbanSquare,
  FileSignature,
  Swords,
  Search,
  PenLine,
  Sparkles,
  Microscope,
}

// ---------------------------------------------------------------------------
// Callout variant configuration
// ---------------------------------------------------------------------------
const CALLOUT_STYLES = {
  info: {
    border: 'border-l-blue-500',
    bg: 'bg-blue-50/50 dark:bg-blue-950/10',
    icon: AlertTriangle,
    iconColor: 'text-blue-600 dark:text-blue-400',
  },
  tip: {
    border: 'border-l-emerald-500',
    bg: 'bg-emerald-50/50 dark:bg-emerald-950/10',
    icon: AlertTriangle,
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
// Diagram — configuration resolution pipeline
// ---------------------------------------------------------------------------

const SVG_WIDTH = 500
const SVG_HEIGHT = 600
const COL_CENTER = SVG_WIDTH / 2

/** Gold — input stage */
const GOLD = '#d4a574'
/** Navy / slate — process stages */
const NAVY = '#475569'
/** Emerald — output stage */
const EMERALD = '#10b981'

const ARROW_COLOR = '#94a3b8'

/** Y-centers for the 5 pipeline stages */
const STAGE_Y = [65, 170, 285, 410, 525]

const BOX_W = 180
const BOX_H = 48

const stageLabels = ['config_id', 'DB lookup', 'Skill concat', 'Agent class', 'Runnable instance']
const stageColors = [GOLD, NAVY, NAVY, NAVY, EMERALD]

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

function HorizontalArrow({ x1, x2, y }: { x1: number; x2: number; y: number }) {
  const arrowTip = x2 - 8
  return (
    <g>
      <motion.path
        d={`M ${x1} ${y} L ${arrowTip} ${y}`}
        stroke={ARROW_COLOR}
        strokeWidth={2}
        fill="none"
        strokeLinecap="round"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 1.2, ease: 'easeInOut' }}
      />
      {/* Arrowhead */}
      <motion.path
        d={`M ${arrowTip} ${y - 5} L ${x2} ${y} L ${arrowTip} ${y + 5}`}
        stroke={ARROW_COLOR}
        strokeWidth={2}
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 1.2, ease: 'easeInOut' }}
      />
    </g>
  )
}

function DiagramNode({
  cx,
  cy,
  label,
  color,
}: {
  cx: number
  cy: number
  label: string
  color: string
}) {
  const x = cx - BOX_W / 2
  const y = cy - BOX_H / 2

  return (
    <motion.g
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
      <rect x={x} y={y} width={BOX_W} height={BOX_H} rx={8} fill={color} />
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
    </motion.g>
  )
}

function SkillBox({ x, y, label }: { x: number; y: number; label: string }) {
  const skillW = 100
  const skillH = 28
  const cx = x + skillW / 2
  const cy = y + skillH / 2

  return (
    <motion.g
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.5, delay: 0.3 }}
    >
      <rect
        x={x}
        y={y}
        width={skillW}
        height={skillH}
        rx={6}
        fill="#64748b"
        stroke="#94a3b8"
        strokeWidth={1}
        strokeDasharray="3 2"
      />
      <text
        x={cx}
        y={cy + 4}
        textAnchor="middle"
        fill="white"
        fontSize={10}
        fontWeight={500}
        fontFamily="monospace, sans-serif"
      >
        {label}
      </text>
    </motion.g>
  )
}

function ConfigFlowDiagram({ caption }: { caption: string }) {
  // Skill boxes positioned left of the "Skill concat" stage (index 2)
  const concatCY = STAGE_Y[2]
  const skillBoxes = [
    { x: 30, y: concatCY - 32, label: 'eu-horizon' },
    { x: 30, y: concatCY - 4, label: 'academic-writing' },
    { x: 30, y: concatCY + 24, label: 'project-mgmt' },
  ]

  return (
    <figure className="my-8 flex flex-col items-center">
      <svg
        viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`}
        role="img"
        aria-label={caption}
        className="w-full max-w-md h-auto"
      >
        {/* Main vertical arrows between stages */}
        <Arrow y1={STAGE_Y[0] + BOX_H / 2} y2={STAGE_Y[1] - BOX_H / 2} />
        <Arrow y1={STAGE_Y[1] + BOX_H / 2} y2={STAGE_Y[2] - BOX_H / 2} />
        <Arrow y1={STAGE_Y[2] + BOX_H / 2} y2={STAGE_Y[3] - BOX_H / 2} />
        <Arrow y1={STAGE_Y[3] + BOX_H / 2} y2={STAGE_Y[4] - BOX_H / 2} />

        {/* Horizontal arrows from skill boxes to Skill concat */}
        {skillBoxes.map((skill, i) => (
          <HorizontalArrow
            key={`sk-arrow-${i}`}
            x1={130}
            x2={COL_CENTER - BOX_W / 2}
            y={skill.y + 14}
          />
        ))}

        {/* Main pipeline stages */}
        {STAGE_Y.map((cy, i) => (
          <DiagramNode
            key={`stage-${i}`}
            cx={COL_CENTER}
            cy={cy}
            label={stageLabels[i]}
            color={stageColors[i]}
          />
        ))}

        {/* Skill boxes */}
        {skillBoxes.map((skill, i) => (
          <SkillBox key={`skill-${i}`} x={skill.x} y={skill.y} label={skill.label} />
        ))}
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
      if (block.diagramId === 'config-flow') {
        return <ConfigFlowDiagram caption={block.caption} />
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
    <div className="grid gap-4 sm:grid-cols-2">
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

export default function ConfigsPage() {
  const section = learningSections.find((s) => s.slug === 'configs')!

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
          <span className="font-medium text-foreground">Agent Configurations</span>
        </nav>

        {/* Page header */}
        <PageHeader
          title={section.title}
          description={section.description}
          actions={
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
                <Settings2 className="h-5 w-5 text-primary" />
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
            <Link to="/cult/configs">
              Manage Configurations
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

ConfigsPage.displayName = 'ConfigsPage'
