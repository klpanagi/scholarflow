import { useMemo } from 'react'
import { cn } from '@/lib/utils'
import type { AgentProgressEvent } from '@/hooks/useChat'

const NODE_LABELS: Record<string, string> = {
  search_papers: 'Searching papers',
  review_paper: 'Reviewing paper',
  write_response: 'Writing response',
  pass_through: 'Processing',
  analyze: 'Analyzing',
  synthesize: 'Synthesizing results',
}

const TOOL_LABELS: Record<string, string> = {
  semantic_scholar_search: 'Semantic Scholar',
  arxiv_search: 'arXiv',
  crossref_search: 'CrossRef',
  openalex_search: 'OpenAlex',
}

function formatNodeName(name: string): string {
  return NODE_LABELS[name] || name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function formatToolName(name: string): string {
  return TOOL_LABELS[name] || name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function formatPhase(phase: string): string {
  return phase.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

interface AgentProgressIndicatorProps {
  events: AgentProgressEvent[]
  className?: string
}

export function AgentProgressIndicator({ events, className }: AgentProgressIndicatorProps) {
  const status = useMemo(() => {
    if (events.length === 0) return null

    const last = events[events.length - 1]

    switch (last.event_type) {
      case 'node.started': {
        const name = (last.data.node_name as string) || 'Processing'
        return { icon: '🔄', text: formatNodeName(name), sub: null }
      }
      case 'node.completed': {
        const name = (last.data.node_name as string) || 'Step'
        const duration = last.data.duration_ms
          ? `${((last.data.duration_ms as number) / 1000).toFixed(1)}s`
          : null
        return { icon: '✅', text: `${formatNodeName(name)} done`, sub: duration }
      }
      case 'tool.call': {
        const tool = (last.data.tool_name as string) || 'Tool'
        return { icon: '🔍', text: `Searching ${formatToolName(tool)}`, sub: null }
      }
      case 'tool.complete': {
        const tool = (last.data.tool_name as string) || 'Tool'
        return { icon: '✅', text: `${formatToolName(tool)} complete`, sub: null }
      }
      case 'strategy.iteration': {
        const phase = (last.data.phase as string) || 'Processing'
        const iteration = last.data.iteration as number | undefined
        const maxIter = last.data.max_iterations as number | undefined
        const sub = (iteration && maxIter) ? `(${iteration}/${maxIter})` : null
        return { icon: '📝', text: formatPhase(phase), sub }
      }
      case 'execution.started':
        return { icon: '🚀', text: 'Agent started', sub: null }
      case 'execution.completed':
        return { icon: '✅', text: 'Complete', sub: null }
      case 'execution.failed':
        return { icon: '❌', text: 'Failed', sub: null }
      default:
        return { icon: '⏳', text: 'Processing', sub: null }
    }
  }, [events])

  if (!status) return null

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <span className="text-sm" aria-hidden="true">{status.icon}</span>
      <span className="text-xs font-medium text-muted-foreground">{status.text}</span>
      {status.sub && (
        <span className="text-[10px] text-muted-foreground/50">{status.sub}</span>
      )}
    </div>
  )
}

AgentProgressIndicator.displayName = 'AgentProgressIndicator'
