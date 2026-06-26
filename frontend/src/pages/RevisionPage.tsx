import { useState, useCallback, useMemo, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { CheckCircle2, Loader2, MessageSquare } from 'lucide-react'

import { api } from '@/lib/api'
import { cn } from '@/lib/utils'
import { useRevisionSession } from '@/hooks/useRevisionSession'
import type {
  WorkflowExecution,
  WorkflowExecutionStage,
  ManuscriptRating,
  StageUsage,
} from '@/constants/workflows'
import { getStageMetaByIndex } from '@/constants/workflows'

import { PageHeader } from '@/components/shared/PageHeader'
import { ScoreDisplay, type Scores } from '@/components/shared/ScoreDisplay'
import { WorkflowStageStatus, type WorkflowStatus } from '@/components/shared/WorkflowStageStatus'
import { MessageList, type ChatListMessage } from '@/components/chat/MessageList'
import { ChatInput } from '@/components/chat/ChatInput'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'

/* ────────────────────────────────────────────── */
/*  Helpers                                        */
/* ────────────────────────────────────────────── */

function formatTokens(n: number): string {
  return n.toLocaleString('en-US')
}

function formatCost(cost: number): string {
  return `$${cost.toFixed(4)}`
}

function formatDuration(seconds?: number): string {
  if (seconds == null) return '—'
  if (seconds < 60) return `${Math.round(seconds)}s`
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return `${m}m ${s}s`
}

function extractScores(rating?: ManuscriptRating | null): Scores | null {
  if (!rating?.criteria?.length) return null
  const find = (name: string) => {
    const match = rating.criteria.find((c) =>
      c.name.toLowerCase().includes(name),
    )
    return match ? match.score : 0
  }
  return {
    quality: find('quality'),
    novelty: find('novelty'),
    rigor: find('rigor'),
    clarity: find('clarity'),
  }
}

function extractUsage(meta?: Record<string, unknown>): StageUsage | null {
  return (meta?.usage as StageUsage | undefined) ?? null
}

function toWorkflowStatus(status: string): WorkflowStatus {
  const s = status.toLowerCase().replace(/_/g, '-')
  const statusMap: Record<string, WorkflowStatus> = {
    pending: 'pending',
    running: 'running',
    'in-progress': 'running',
    completed: 'completed',
    complete: 'completed',
    failed: 'failed',
    cancelled: 'cancelled',
    queued: 'queued',
    paused: 'paused',
  }
  return statusMap[s] ?? 'pending'
}

/* ────────────────────────────────────────────── */
/*  Stage Output Panel (right column)              */
/* ────────────────────────────────────────────── */

interface StageOutputPanelProps {
  stages: WorkflowExecutionStage[]
  activeIndex: number
  onStageChange: (index: number) => void
}

function StageOutputPanel({ stages, activeIndex, onStageChange }: StageOutputPanelProps) {
  const stage = stages[activeIndex]
  const scores = useMemo(() => extractScores(stage?.rating), [stage?.rating])
  const usage = useMemo(() => extractUsage(stage?.metadata), [stage?.metadata])

  return (
    <div className="flex flex-col h-full">
      {/* Stage selector tabs */}
      <div className="flex items-center gap-1 overflow-x-auto border-b border-border/50 px-3 py-2 shrink-0">
        {stages.map((s, idx) => (
          <button
            key={idx}
            onClick={() => onStageChange(idx)}
            className={cn(
              'flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap',
              idx === activeIndex
                ? 'bg-primary/10 text-primary'
                : 'text-muted-foreground hover:text-foreground hover:bg-accent/50',
            )}
          >
            <span
              className={cn(
                'h-1.5 w-1.5 rounded-full shrink-0',
                s.status === 'completed' && 'bg-emerald-500',
                s.status === 'running' && 'bg-primary animate-pulse',
                s.status === 'failed' && 'bg-red-500',
                s.status === 'pending' && 'bg-muted-foreground/30',
              )}
            />
            {s.agent_name ?? s.agent_role ?? `Stage ${idx + 1}`}
          </button>
        ))}
      </div>

      {/* Stage content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {scores && (
          <div className="bg-card/40 rounded-lg p-3">
            <p className="text-xs font-medium text-muted-foreground mb-2">Ratings</p>
            <ScoreDisplay scores={scores} size="sm" layout="grid" />
          </div>
        )}

        {stage?.output ? (
          <div className="whitespace-pre-wrap text-sm leading-relaxed text-foreground/80 font-mono">
            {stage.output}
          </div>
        ) : (
          <div className="flex items-center justify-center py-12 text-muted-foreground">
            {stage?.status === 'running' || stage?.status === 'in_progress' || stage?.status === 'in-progress' ? (
              <div className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="text-sm">Stage in progress...</span>
              </div>
            ) : (
              <span className="text-sm">No output yet</span>
            )}
          </div>
        )}
      </div>

      {/* Metadata footer */}
      {(usage || stage?.metadata?.duration_seconds != null) && (
        <div className="border-t border-border/50 px-4 py-2 flex items-center gap-4 text-xs text-muted-foreground shrink-0 flex-wrap">
          {usage && (
            <>
              <span title="Total tokens">
                Tokens: {formatTokens(usage.total_tokens ?? 0)}
              </span>
              <span title="Estimated cost">
                Cost: {formatCost(usage.cost_usd ?? 0)}
              </span>
              {usage.model && (
                <span title="Model">Model: {usage.model}</span>
              )}
            </>
          )}
          {stage?.metadata?.duration_seconds != null && (
            <span title="Duration">
              Duration: {formatDuration(Number(stage.metadata.duration_seconds))}
            </span>
          )}
        </div>
      )}
    </div>
  )
}

/* ────────────────────────────────────────────── */
/*  Chat panel shared between desktop & mobile     */
/* ────────────────────────────────────────────── */

interface ChatPanelProps {
  messages: ChatListMessage[]
  isLoading: boolean
  isStreaming: boolean
  onSend: (content: string, files?: File[]) => void
}

function ChatPanel({ messages, isLoading, isStreaming, onSend }: ChatPanelProps) {
  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="flex-1 overflow-hidden">
        <MessageList
          messages={messages}
          isLoading={isLoading && messages.length === 0}
          isStreaming={isStreaming}
          className="h-full"
          emptyState={
            <div className="flex flex-col items-center gap-3 py-16">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
                <MessageSquare className="h-6 w-6 text-primary" />
              </div>
              <p className="text-sm font-medium text-muted-foreground">
                Start a conversation about this review
              </p>
              <p className="text-xs text-muted-foreground/60">
                Ask questions, request clarifications, or discuss findings
              </p>
            </div>
          }
        />
      </div>
      <div className="border-t border-border/50 p-3 shrink-0">
        <ChatInput
          onSend={onSend}
          disabled={isStreaming}
          isStreaming={isStreaming}
          placeholder="Ask about this review..."
        />
      </div>
    </div>
  )
}

/* ────────────────────────────────────────────── */
/*  Main Page Component                            */
/* ────────────────────────────────────────────── */

export default function RevisionPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const {
    session,
    messages,
    isLoading,
    isStreaming,
    streamingContent,
    selectedStageIds,
    loadSession,
    sendMessage,
    toggleStage,
    setAvailableStageIds,
    uploadFile,
    attachFile,
  } = useRevisionSession()

  // Load session on mount
  useEffect(() => {
    if (sessionId) {
      loadSession(sessionId)
    }
  }, [sessionId, loadSession])

  // Fetch workflow execution
  const { data: execution } = useQuery<WorkflowExecution | null>({
    queryKey: ['revision-execution', session?.workflow_execution_id],
    queryFn: async () => {
      if (!session?.workflow_execution_id) return null
      const { data } = await api.get<WorkflowExecution>(
        `/workflows/executions/${session.workflow_execution_id}`,
      )
      return data
    },
    enabled: !!session?.workflow_execution_id,
  })

  // Propagate stage IDs when execution loads
  useEffect(() => {
    if (execution?.stages && execution.stages.length > 0) {
      setAvailableStageIds(execution.stages.map((_, i) => String(i)))
    }
  }, [execution, setAvailableStageIds])

  // Active stage for the output panel
  const [activeStageIndex, setActiveStageIndex] = useState(0)

  // Convert messages → ChatListMessage format (for MessageList)
  const chatListMessages: ChatListMessage[] = useMemo(() => {
    const all: ChatListMessage[] = messages.map((m) => ({
      id: m.id,
      role: m.role,
      content: m.content,
      timestamp: m.timestamp,
    }))
    if (isStreaming && streamingContent) {
      all.push({
        id: 'streaming',
        role: 'assistant',
        content: streamingContent,
        timestamp: new Date().toISOString(),
      })
    }
    return all
  }, [messages, isStreaming, streamingContent])

  // Handle message send
  const handleSend = useCallback(
    async (content: string, files?: File[]) => {
      let fileRefs: string[] | undefined
      if (files && files.length > 0) {
        fileRefs = []
        for (const file of files) {
          const uploaded = await uploadFile(file)
          attachFile(uploaded)
          fileRefs.push(uploaded.file_key)
        }
      }
      sendMessage(content, fileRefs)
    },
    [uploadFile, attachFile, sendMessage],
  )

  // Aggregate usage across all stages
  const totalUsage = useMemo(() => {
    if (!execution?.stages) return null
    let tokens = 0
    let cost = 0
    let duration = 0
    for (const s of execution.stages) {
      const u = extractUsage(s.metadata)
      if (u) {
        tokens += u.total_tokens ?? 0
        cost += u.cost_usd ?? 0
      }
      if (s.metadata?.duration_seconds != null) {
        duration += Number(s.metadata.duration_seconds)
      }
    }
    return { tokens, cost, duration }
  }, [execution])

  // Overall scores — use the last stage that has a rating
  const overallScores: Scores | null = useMemo(() => {
    if (!execution?.stages) return null
    const rated = execution.stages.filter((s) => s.rating)
    if (rated.length === 0) return null
    return extractScores(rated[rated.length - 1].rating)
  }, [execution])

  // ── Loading / empty states ──

  if (isLoading && !session) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Loading revision session...</p>
        </div>
      </div>
    )
  }

  if (!session) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <p className="text-muted-foreground">Revision session not found</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6 h-full min-h-0">
      {/* ── Hero ── */}
      <PageHeader
        title={session.title}
        description={
          execution
            ? `${execution.stages.length} stages · ${totalUsage ? formatTokens(totalUsage.tokens) : '0'} tokens · ${totalUsage ? formatCost(totalUsage.cost) : '$0.00'}`
            : 'Loading execution details...'
        }
        actions={
          <div className="flex items-center gap-3">
            {execution && (
              <>
                {/* Status badge */}
                <span
                  className={cn(
                    'inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium',
                    execution.status === 'completed' && 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20',
                    execution.status === 'running' && 'bg-primary/10 text-primary border border-primary/20',
                    execution.status === 'failed' && 'bg-red-500/10 text-red-500 border border-red-500/20',
                    execution.status !== 'completed' &&
                      execution.status !== 'running' &&
                      execution.status !== 'failed' &&
                      'bg-muted text-muted-foreground border border-border',
                  )}
                >
                  {execution.status === 'completed' && <CheckCircle2 className="h-3 w-3" />}
                  {execution.status === 'running' && <Loader2 className="h-3 w-3 animate-spin" />}
                  {execution.status}
                </span>

                {/* Overall scores (row layout for hero) */}
                {overallScores && (
                  <ScoreDisplay scores={overallScores} size="sm" layout="row" />
                )}
              </>
            )}
          </div>
        }
      />

      {/* ── Stage Pipeline — Horizontal Stepper ── */}
      {execution?.stages && execution.stages.length > 0 && (
        <div className="bg-card/60 backdrop-blur-xl border border-border/50 rounded-xl p-3">
          <div className="flex items-center overflow-x-auto pb-1">
            {execution.stages.map((stage, idx) => {
              const meta = getStageMetaByIndex(execution.workflow_id, idx)
              const isSelected = selectedStageIds.has(String(idx))
              const isActive = activeStageIndex === idx

              return (
                <div key={idx} className="flex items-center gap-0">
                  {/* Connector line before (except first) */}
                  {idx > 0 && (
                    <div
                      className={cn(
                        'h-0.5 w-5 shrink-0',
                        stage.status === 'completed' ? 'bg-emerald-500/50' : 'bg-border',
                      )}
                    />
                  )}

                  {/* Stage button */}
                  <button
                    onClick={() => setActiveStageIndex(idx)}
                    className={cn(
                      'relative flex flex-col items-center gap-1.5 p-2 rounded-lg transition-all min-w-[72px] group',
                      isActive && 'bg-primary/10 ring-1 ring-primary/30',
                    )}
                  >
                    <div className="relative">
                      <WorkflowStageStatus
                        status={toWorkflowStatus(stage.status)}
                        size="sm"
                      />
                      {/* Selection toggle dot */}
                      <div
                        onClick={(e) => {
                          e.stopPropagation()
                          toggleStage(String(idx))
                        }}
                        className={cn(
                          'absolute -top-0.5 -right-0.5 h-4 w-4 rounded-sm border cursor-pointer flex items-center justify-center transition-colors',
                          isSelected
                            ? 'bg-primary border-primary'
                            : 'bg-card border-border group-hover:border-primary/50',
                        )}
                      >
                        {isSelected && (
                          <CheckCircle2 className="h-3 w-3 text-white" />
                        )}
                      </div>
                    </div>
                    <span
                      className={cn(
                        'text-[10px] font-medium text-center leading-tight max-w-[72px] truncate',
                        isActive ? 'text-primary' : 'text-muted-foreground',
                      )}
                    >
                      {stage.agent_name ?? meta?.description ?? `Stage ${idx + 1}`}
                    </span>
                  </button>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* ── Main Content ── */}
      <div className="flex-1 min-h-0">
        {/* Desktop: side-by-side */}
        <div className="hidden md:grid md:grid-cols-[1fr_400px] gap-6 h-full">
          {/* Left: Chat */}
          <div className="bg-card/60 backdrop-blur-xl border border-border/50 rounded-xl overflow-hidden">
            <ChatPanel
              messages={chatListMessages}
              isLoading={isLoading}
              isStreaming={isStreaming}
              onSend={handleSend}
            />
          </div>

          {/* Right: Stage output */}
          {execution?.stages && execution.stages.length > 0 && (
            <div className="bg-card/60 backdrop-blur-xl border border-border/50 rounded-xl overflow-hidden">
              <StageOutputPanel
                stages={execution.stages}
                activeIndex={activeStageIndex}
                onStageChange={setActiveStageIndex}
              />
            </div>
          )}
        </div>

        {/* Mobile: tabs */}
        <div className="md:hidden h-full flex flex-col">
          <Tabs defaultValue="chat" className="flex flex-col flex-1 min-h-0">
            <TabsList variant="pills" className="self-center mb-3 shrink-0">
              <TabsTrigger value="chat" variant="pills">
                Chat
              </TabsTrigger>
              <TabsTrigger value="output" variant="pills">
                Output
              </TabsTrigger>
            </TabsList>

            <TabsContent value="chat" className="flex-1 min-h-0">
              <div className="bg-card/60 backdrop-blur-xl border border-border/50 rounded-xl overflow-hidden h-full">
                <ChatPanel
                  messages={chatListMessages}
                  isLoading={isLoading}
                  isStreaming={isStreaming}
                  onSend={handleSend}
                />
              </div>
            </TabsContent>

            <TabsContent value="output" className="flex-1 min-h-0">
              {execution?.stages && execution.stages.length > 0 && (
                <div className="bg-card/60 backdrop-blur-xl border border-border/50 rounded-xl overflow-hidden h-full">
                  <StageOutputPanel
                    stages={execution.stages}
                    activeIndex={activeStageIndex}
                    onStageChange={setActiveStageIndex}
                  />
                </div>
              )}
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  )
}
