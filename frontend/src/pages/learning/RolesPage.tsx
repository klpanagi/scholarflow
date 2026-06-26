import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Users,
  Info,
  CheckCircle,
  AlertTriangle,
  ChevronRight,
  ArrowRight,
  Search,
  PenLine,
  ClipboardCheck,
  Microscope,
  Sparkles,
  RefreshCw,
  Swords,
  FileSignature,
  KanbanSquare,
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
  Search,
  PenLine,
  ClipboardCheck,
  Microscope,
  Sparkles,
  RefreshCw,
  Swords,
  FileSignature,
  KanbanSquare,
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
const GOLD_COLOR = '#d4a574'
const NAVY_COLOR = '#334155'

// ---------------------------------------------------------------------------
// Diagram component — hand-authored SVG of the role graph
// ---------------------------------------------------------------------------

const CX = 250
const CY = 250
const OUTER_RADIUS = 170
const NODE_R = 48

/** Compute polar coordinates */
function polar(cx: number, cy: number, r: number, angleDeg: number): [number, number] {
  const rad = (angleDeg * Math.PI) / 180
  return [cx + r * Math.cos(rad), cy + r * Math.sin(rad)]
}

interface RoleNodeDef {
  key: string
  label: string
  angle: number
  icon: string
}

const OUTER_NODES: RoleNodeDef[] = [
  { key: 'researcher', label: 'researcher', angle: -90, icon: 'Search' },
  { key: 'writer', label: 'writer', angle: -45, icon: 'PenLine' },
  { key: 'reviewer', label: 'reviewer', angle: 0, icon: 'ClipboardCheck' },
  { key: 'deep_reviewer', label: 'deep_reviewer', angle: 45, icon: 'Microscope' },
  { key: 'recommender', label: 'recommender', angle: 90, icon: 'Sparkles' },
  { key: 'revision', label: 'revision', angle: 135, icon: 'RefreshCw' },
  { key: 'debater', label: 'debater', angle: 180, icon: 'Swords' },
  { key: 'review_writer', label: 'review_writer', angle: 225, icon: 'FileSignature' },
]

/** Tiny SVG icon shapes for each role */
function TinyRoleIcon({ icon, cx, cy }: { icon: string; cx: number; cy: number }) {
  const color = ARROW_COLOR
  switch (icon) {
    case 'Search':
      return (
        <g>
          <circle cx={cx} cy={cy} r={5} fill="none" stroke={color} strokeWidth={1.5} />
          <line x1={cx + 3.5} y1={cy + 3.5} x2={cx + 8} y2={cy + 8} stroke={color} strokeWidth={1.5} strokeLinecap="round" />
        </g>
      )
    case 'PenLine':
      return (
        <line x1={cx - 5} y1={cy + 5} x2={cx + 5} y2={cy - 5} stroke={color} strokeWidth={1.5} strokeLinecap="round" />
      )
    case 'ClipboardCheck':
      return (
        <g>
          <rect x={cx - 5} y={cy - 6} width={10} height={12} rx={1.5} fill="none" stroke={color} strokeWidth={1.5} />
          <polyline points={`${cx - 2},${cy} ${cx + 1},${cy + 3} ${cx + 4},${cy - 2}`} fill="none" stroke={color} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" />
        </g>
      )
    case 'Microscope':
      return (
        <g>
          <circle cx={cx} cy={cy - 4} r={4} fill="none" stroke={color} strokeWidth={1.5} />
          <line x1={cx} y1={cy} x2={cx} y2={cy + 6} stroke={color} strokeWidth={1.5} />
          <line x1={cx - 5} y1={cy + 6} x2={cx + 5} y2={cy + 6} stroke={color} strokeWidth={1.5} />
        </g>
      )
    case 'Sparkles':
      return (
        <path
          d={`M ${cx} ${cy - 6} l 1.5 4.5 4.5 1.5 -4.5 1.5 -1.5 4.5 -1.5 -4.5 -4.5 -1.5 4.5 -1.5 z`}
          fill="none"
          stroke={color}
          strokeWidth={1.2}
          strokeLinejoin="round"
        />
      )
    case 'RefreshCw':
      return (
        <g>
          <path
            d={`M ${cx - 4} ${cy - 3} a 6 6 0 1 1 -1 7`}
            fill="none"
            stroke={color}
            strokeWidth={1.5}
            strokeLinecap="round"
          />
          <polyline points={`${cx - 4},${cy + 4} ${cx - 7},${cy + 4} ${cx - 7},${cy + 1}`} fill="none" stroke={color} strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" />
        </g>
      )
    case 'Swords':
      return (
        <g>
          <line x1={cx - 5} y1={cy + 5} x2={cx + 5} y2={cy - 5} stroke={color} strokeWidth={1.5} strokeLinecap="round" />
          <line x1={cx + 5} y1={cy + 5} x2={cx - 5} y2={cy - 5} stroke={color} strokeWidth={1.5} strokeLinecap="round" />
        </g>
      )
    case 'FileSignature':
      return (
        <path
          d={`M ${cx - 6} ${cy} Q ${cx - 3} ${cy - 4} ${cx} ${cy} T ${cx + 6} ${cy}`}
          fill="none"
          stroke={color}
          strokeWidth={1.5}
          strokeLinecap="round"
        />
      )
    default:
      return null
  }
}

function RoleGraphDiagram({ caption, prefersReduced }: { caption: string; prefersReduced: boolean }) {
  const lineProps = prefersReduced
    ? { initial: { pathLength: 1 }, animate: { pathLength: 1 } }
    : {
        initial: { pathLength: 0 },
        animate: { pathLength: 1 },
        transition: { duration: 1.5, ease: 'easeInOut' as const },
      }

  return (
    <figure className="my-8 flex flex-col items-center">
      <svg
        viewBox="0 0 500 500"
        role="img"
        aria-label={caption}
        className="w-full max-w-md h-auto"
      >
        {/* Connecting lines from each outer node to center */}
        {OUTER_NODES.map((node) => {
          const [nx, ny] = polar(CX, CY, OUTER_RADIUS, node.angle)
          return (
            <motion.path
              key={`line-${node.key}`}
              d={`M ${CX} ${CY} L ${nx} ${ny}`}
              stroke={ARROW_COLOR}
              strokeWidth={2}
              fill="none"
              strokeLinecap="round"
              strokeOpacity={0.4}
              {...lineProps}
            />
          )
        })}

        {/* Center — Manager node */}
        <motion.g
          initial={prefersReduced ? {} : { scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
        >
          <motion.circle
            cx={CX}
            cy={CY}
            r={60}
            fill={GOLD_COLOR}
            variants={prefersReduced ? {} : pulseVariants}
            animate="animate"
          />
          <text
            x={CX}
            y={CY - 4}
            textAnchor="middle"
            dominantBaseline="central"
            fill="white"
            fontSize={14}
            fontWeight={700}
            fontFamily="system-ui, sans-serif"
          >
            Manager
          </text>
          <TinyRoleIcon icon="KanbanSquare" cx={CX} cy={CY + 18} />
        </motion.g>

        {/* Outer nodes */}
        {OUTER_NODES.map((node, i) => {
          const [nx, ny] = polar(CX, CY, OUTER_RADIUS, node.angle)
          return (
            <motion.g
              key={`node-${node.key}`}
              initial={prefersReduced ? {} : { opacity: 0, scale: 0.6 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5, delay: 0.3 + i * 0.1 }}
            >
              <circle cx={nx} cy={ny} r={NODE_R} fill={NAVY_COLOR} />
              <TinyRoleIcon icon={node.icon} cx={nx} cy={ny - 8} />
              <text
                x={nx}
                y={ny + 12}
                textAnchor="middle"
                fill="white"
                fontSize={11}
                fontWeight={600}
                fontFamily="system-ui, sans-serif"
              >
                {node.label}
              </text>
            </motion.g>
          )
        })}
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

function ContentBlockRenderer({ block, prefersReduced }: { block: ContentBlock; prefersReduced: boolean }) {
  switch (block.type) {
    case 'text':
      return (
        <motion.p
          variants={withReducedMotion(fadeInUp, prefersReduced)}
          initial="initial"
          animate="animate"
          className="prose prose-slate dark:prose-invert max-w-none text-base leading-relaxed text-foreground/90"
        >
          {block.content}
        </motion.p>
      )

    case 'list':
      return <ListBlockRenderer block={block} prefersReduced={prefersReduced} />

    case 'diagram':
      if (block.diagramId === 'role-graph') {
        return <RoleGraphDiagram caption={block.caption} prefersReduced={prefersReduced} />
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
      className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
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

export default function RolesPage() {
  const section = learningSections.find((s) => s.slug === 'roles')!
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
          <span className="font-medium text-foreground">Agent Roles</span>
        </nav>

        {/* Page header */}
        <PageHeader
          title={section.title}
          description={section.description}
          actions={
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
                <Users className="h-5 w-5 text-primary" />
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
            <Link to="/cult/agents">
              Browse Agents
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

RolesPage.displayName = 'RolesPage'
