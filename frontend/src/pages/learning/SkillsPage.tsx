import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  ScrollText,
  Landmark,
  BookOpen,
  ListChecks,
  FileSearch,
  ClipboardList,
  ScanSearch,
  FileEdit,
  Library,
  Mail,
  Mails,
  ChevronRight,
  ArrowRight,
  Info,
} from 'lucide-react'

import { Button } from '@/components/ui/button'
import { PageMotion } from '@/components/shared/PageMotion'
import { PageHeader } from '@/components/shared/PageHeader'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { useReducedMotion } from '@/lib/motion'
import { learningSections } from '@/content/learning'
import type { ContentBlock, ListBlock, CalloutBlock } from '@/content/learning'

// ---------------------------------------------------------------------------
// Icon map — maps string icon names from the content data to Lucide components
// ---------------------------------------------------------------------------
const LIST_ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  Landmark,
  BookOpen,
  ListChecks,
  FileSearch,
  ClipboardList,
  ScanSearch,
  FileEdit,
  Library,
  Mail,
  Mails,
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
    icon: Info,
    iconColor: 'text-emerald-600 dark:text-emerald-400',
  },
  warning: {
    border: 'border-l-amber-500',
    bg: 'bg-amber-50/50 dark:bg-amber-950/10',
    icon: Info,
    iconColor: 'text-amber-600 dark:text-amber-400',
  },
} as const

// ---------------------------------------------------------------------------
// Diagram component — custom SVG of the skill-loading flow
// ---------------------------------------------------------------------------

const GOLD = '#D97706'
const NAVY = '#1E3A5F'
const EMERALD = '#059669'
const ARROW_COLOR = '#94A3B8'

const BOX_X = 25
const BOX_W = 160
const BOX_H = 50
const BOX_GAP = 30

const BOX1_Y = 35
const BOX2_Y = BOX1_Y + BOX_H + BOX_GAP
const BOX3_Y = BOX2_Y + BOX_H + BOX_GAP

const FUNNEL_X = 280
const FUNNEL_W = 180
const FUNNEL_H = 160
const FUNNEL_Y = 60

const PROMPT_X = 530
const PROMPT_W = 170
const PROMPT_H = 170
const PROMPT_Y = 55

const TOOL_X = 325
const TOOL_Y = 290
const TOOL_W = 130
const TOOL_H = 48

const BOX1_CY = BOX1_Y + BOX_H / 2
const BOX2_CY = BOX2_Y + BOX_H / 2
const BOX3_CY = BOX3_Y + BOX_H / 2
const FUNNEL_CY = FUNNEL_Y + FUNNEL_H / 2
const PROMPT_CY = PROMPT_Y + PROMPT_H / 2

const FUNNEL_LEFT_X = FUNNEL_X
const FUNNEL_RIGHT_X = FUNNEL_X + FUNNEL_W

function AnimatedArrow({
  d,
  delay = 0,
}: {
  d: string
  delay?: number
}) {
  const prefersReduced = useReducedMotion()

  if (prefersReduced) {
    return (
      <path
        d={d}
        stroke={ARROW_COLOR}
        strokeWidth={2.5}
        fill="none"
        strokeLinecap="round"
      />
    )
  }

  return (
    <motion.path
      d={d}
      stroke={ARROW_COLOR}
      strokeWidth={2.5}
      fill="none"
      strokeLinecap="round"
      initial={{ pathLength: 0 }}
      animate={{ pathLength: 1 }}
      transition={{ duration: 1, delay, ease: 'easeInOut' }}
    />
  )
}

function Arrowhead({
  cx,
  cy,
  delay = 0,
}: {
  cx: number
  cy: number
  delay?: number
}) {
  const prefersReduced = useReducedMotion()

  if (prefersReduced) {
    return (
      <path
        d={`M ${cx - 6} ${cy - 5} L ${cx} ${cy} L ${cx + 6} ${cy - 5}`}
        stroke={ARROW_COLOR}
        strokeWidth={2.5}
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    )
  }

  return (
    <motion.path
      d={`M ${cx - 6} ${cy - 5} L ${cx} ${cy} L ${cx + 6} ${cy - 5}`}
      stroke={ARROW_COLOR}
      strokeWidth={2.5}
      fill="none"
      strokeLinecap="round"
      strokeLinejoin="round"
      initial={{ pathLength: 0 }}
      animate={{ pathLength: 1 }}
      transition={{ duration: 1, delay, ease: 'easeInOut' }}
    />
  )
}

function SkillLoadingDiagram({ caption }: { caption: string }) {
  return (
    <figure className="my-8 flex flex-col items-center">
      <svg
        viewBox="0 0 700 370"
        role="img"
        aria-label={caption}
        className="w-full max-w-2xl h-auto"
      >
        {/* =============================================================== */}
        {/* Arrow paths                                                      */}
        {/* =============================================================== */}
        {/* Box 1 → funnel (angled down-right) */}
        <AnimatedArrow
          d={`M ${BOX_X + BOX_W} ${BOX1_CY} L ${FUNNEL_LEFT_X} ${BOX1_CY + 25}`}
          delay={0}
        />
        <Arrowhead
          cx={FUNNEL_LEFT_X}
          cy={BOX1_CY + 25}
          delay={0}
        />

        {/* Box 2 → funnel (straight) */}
        <AnimatedArrow
          d={`M ${BOX_X + BOX_W} ${BOX2_CY} L ${FUNNEL_LEFT_X} ${BOX2_CY}`}
          delay={0.3}
        />
        <Arrowhead
          cx={FUNNEL_LEFT_X}
          cy={BOX2_CY}
          delay={0.3}
        />

        {/* Box 3 → funnel (angled up-right) */}
        <AnimatedArrow
          d={`M ${BOX_X + BOX_W} ${BOX3_CY} L ${FUNNEL_LEFT_X} ${BOX3_CY - 25}`}
          delay={0.6}
        />
        <Arrowhead
          cx={FUNNEL_LEFT_X}
          cy={BOX3_CY - 25}
          delay={0.6}
        />

        {/* Funnel → system prompt (straight) */}
        <AnimatedArrow
          d={`M ${FUNNEL_RIGHT_X} ${FUNNEL_CY} L ${PROMPT_X} ${PROMPT_CY}`}
          delay={1}
        />
        <Arrowhead
          cx={PROMPT_X}
          cy={PROMPT_CY}
          delay={1}
        />

        {/* Tool bindings → funnel (straight up) */}
        <AnimatedArrow
          d={`M ${TOOL_X + TOOL_W / 2} ${TOOL_Y} L ${TOOL_X + TOOL_W / 2} ${FUNNEL_Y + FUNNEL_H}`}
          delay={1.2}
        />
        <Arrowhead
          cx={TOOL_X + TOOL_W / 2}
          cy={FUNNEL_Y + FUNNEL_H}
          delay={1.2}
        />

        {/* =============================================================== */}
        {/* Source boxes (gold)                                              */}
        {/* =============================================================== */}
        <g>
          <rect
            x={BOX_X}
            y={BOX1_Y}
            width={BOX_W}
            height={BOX_H}
            rx={8}
            ry={8}
            fill={GOLD}
          />
          <text
            x={BOX_X + BOX_W / 2}
            y={BOX1_CY + 4}
            textAnchor="middle"
            fill="white"
            fontSize={13}
            fontWeight={600}
            fontFamily="system-ui, sans-serif"
          >
            eu-horizon
          </text>
        </g>

        <g>
          <rect
            x={BOX_X}
            y={BOX2_Y}
            width={BOX_W}
            height={BOX_H}
            rx={8}
            ry={8}
            fill={GOLD}
          />
          <text
            x={BOX_X + BOX_W / 2}
            y={BOX2_CY + 4}
            textAnchor="middle"
            fill="white"
            fontSize={13}
            fontWeight={600}
            fontFamily="system-ui, sans-serif"
          >
            academic-writing
          </text>
        </g>

        <g>
          <rect
            x={BOX_X}
            y={BOX3_Y}
            width={BOX_W}
            height={BOX_H}
            rx={8}
            ry={8}
            fill={GOLD}
          />
          <text
            x={BOX_X + BOX_W / 2}
            y={BOX3_CY + 4}
            textAnchor="middle"
            fill="white"
            fontSize={13}
            fontWeight={600}
            fontFamily="system-ui, sans-serif"
          >
            project-management
          </text>
        </g>

        {/* =============================================================== */}
        {/* Funnel (navy) — trapezoid shape                                 */}
        {/* =============================================================== */}
        <g>
          <polygon
            points={`${FUNNEL_X},${FUNNEL_Y} ${FUNNEL_X + FUNNEL_W},${FUNNEL_Y} ${FUNNEL_X + FUNNEL_W - 25},${FUNNEL_Y + FUNNEL_H} ${FUNNEL_X + 25},${FUNNEL_Y + FUNNEL_H}`}
            fill={NAVY}
          />
          <text
            x={FUNNEL_X + FUNNEL_W / 2}
            y={FUNNEL_CY - 6}
            textAnchor="middle"
            fill="white"
            fontSize={14}
            fontWeight={700}
            fontFamily="system-ui, sans-serif"
          >
            Skill
          </text>
          <text
            x={FUNNEL_X + FUNNEL_W / 2}
            y={FUNNEL_CY + 14}
            textAnchor="middle"
            fill="white"
            fontSize={14}
            fontWeight={700}
            fontFamily="system-ui, sans-serif"
          >
            Loader
          </text>
        </g>

        {/* =============================================================== */}
        {/* System prompt (emerald)                                          */}
        {/* =============================================================== */}
        <g>
          <rect
            x={PROMPT_X}
            y={PROMPT_Y}
            width={PROMPT_W}
            height={PROMPT_H}
            rx={12}
            ry={12}
            fill={EMERALD}
          />
          <text
            x={PROMPT_X + PROMPT_W / 2}
            y={PROMPT_CY - 10}
            textAnchor="middle"
            fill="white"
            fontSize={14}
            fontWeight={700}
            fontFamily="system-ui, sans-serif"
          >
            System
          </text>
          <text
            x={PROMPT_X + PROMPT_W / 2}
            y={PROMPT_CY + 10}
            textAnchor="middle"
            fill="white"
            fontSize={14}
            fontWeight={700}
            fontFamily="system-ui, sans-serif"
          >
            Prompt
          </text>
        </g>

        {/* =============================================================== */}
        {/* Tool bindings (slate, below funnel)                              */}
        {/* =============================================================== */}
        <g>
          <rect
            x={TOOL_X}
            y={TOOL_Y}
            width={TOOL_W}
            height={TOOL_H}
            rx={8}
            ry={8}
            fill="none"
            stroke={ARROW_COLOR}
            strokeWidth={2}
            strokeDasharray="4 3"
          />
          <text
            x={TOOL_X + TOOL_W / 2}
            y={TOOL_Y + TOOL_H / 2 + 4}
            textAnchor="middle"
            fill={ARROW_COLOR}
            fontSize={12}
            fontWeight={600}
            fontFamily="system-ui, sans-serif"
          >
            Tool Bindings
          </text>
        </g>
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
      if (block.diagramId === 'skill-loading') {
        return <SkillLoadingDiagram caption={block.caption} />
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

export default function SkillsPage() {
  const section = learningSections.find((s) => s.slug === 'skills')!

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
          <span className="font-medium text-foreground">Default Skills</span>
        </nav>

        {/* Page header */}
        <PageHeader
          title={section.title}
          description={section.description}
          actions={
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
                <ScrollText className="h-5 w-5 text-primary" />
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
            <Link to="/cult/skills">
              Browse Skills
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

SkillsPage.displayName = 'SkillsPage'
