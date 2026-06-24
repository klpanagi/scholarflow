import { useCallback, useMemo } from "react"
import { useParams, useNavigate, Link } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import {
  MessageSquare,
  BookOpen,
  Clock,
  Plus,
  Sparkles,
  FolderOpen,
  Calendar,
  Activity,
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api"
import { cn } from "@/lib/utils"
import { StatusBadge } from "@/components/shared/StatusBadge"
import { PaperCard } from "@/components/shared/PaperCard"
import type { StoredPaper } from "@/components/shared/PaperCard"
import { EmptyState } from "@/components/shared/EmptyState"

// ========================================================================
// Types
// ========================================================================

interface WorkspaceData {
  id: string
  name: string
  description?: string
  papers: string[]
  created_at: string
  updated_at: string
}

interface ConversationItem {
  id: string
  title?: string
  agent_config_id?: string | null
  created_at: string
  updated_at: string
}

interface AssetItem {
  id: string
  title: string
  authors: string[]
  abstract?: string
  year?: number
  venue?: string
  tags: string[]
  doc_type: string
  analysis?: Record<string, unknown>
  created_at: string
  updated_at: string
}

interface AssetListResponse {
  items: AssetItem[]
  total: number
  page: number
  size: number
}

// ========================================================================
// Helpers
// ========================================================================

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)

  if (diffMins < 1) return "just now"
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`
  if (diffMins < 10080) return `${Math.floor(diffMins / 1440)}d ago`
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" })
}

function formatFullDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  })
}

// ========================================================================
// Sub-components
// ========================================================================

function StatCard({
  icon: Icon,
  label,
  value,
  suffix,
  href,
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: number | string
  suffix?: string
  href?: string
}) {
  const Wrapper = href ? Link : "div"
  return (
    <Wrapper
      to={href ?? "#"}
      className={cn(
        "group rounded-lg border border-navy-700/50 bg-navy-800/40 p-5 backdrop-blur-sm transition-all duration-300",
        href && "hover:border-gold-500/30 hover:bg-navy-800/60 hover:shadow-lg hover:shadow-gold-500/5",
      )}
    >
      <div className="mb-3 flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wider text-navy-300">
          {label}
        </span>
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-gold-500/10 text-gold-400">
          <Icon className="h-4 w-4" />
        </div>
      </div>
      <div className="font-display text-3xl font-semibold text-gold-300">
        {value}
      </div>
      {suffix && (
        <p className="mt-1 text-xs text-navy-400">{suffix}</p>
      )}
    </Wrapper>
  )
}

function ConversationCard({
  conversation,
  workspaceId,
}: {
  conversation: ConversationItem
  workspaceId: string
}) {
  const title = conversation.title || "Untitled conversation"
  return (
    <Link
      to={`/workspaces/${workspaceId}`}
      className="group relative overflow-hidden rounded-xl border border-border/40 bg-card/60 p-5 backdrop-blur-xl transition-all duration-200 hover:border-gold-500/50 hover:shadow-lg hover:shadow-gold-500/5"
    >
      {/* Gold accent line */}
      <div className="absolute inset-x-0 top-0 h-0.5 scale-x-0 bg-gradient-to-r from-transparent via-gold-500/60 to-transparent transition-transform duration-300 group-hover:scale-x-100" />

      <div className="flex flex-col gap-3">
        <div className="flex items-start justify-between gap-3">
          <h3 className="line-clamp-2 text-sm font-semibold text-foreground leading-snug">
            {title}
          </h3>
          <MessageSquare className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground/40" />
        </div>
        <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1">
            <Calendar className="h-3 w-3" />
            {formatFullDate(conversation.created_at)}
          </span>
          <span className="inline-flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {formatRelativeTime(conversation.updated_at)}
          </span>
        </div>
      </div>
    </Link>
  )
}

function SkeletonGrid({ count = 4 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {Array.from({ length: count }, (_, i) => (
        <div
          key={i}
          className="rounded-xl border border-border/40 bg-card/60 p-5"
        >
          <Skeleton className="mb-3 h-4 w-3/4" />
          <Skeleton className="mb-2 h-3 w-1/2" />
          <Skeleton className="h-3 w-1/3" />
        </div>
      ))}
    </div>
  )
}

// ========================================================================
// Main Component
// ========================================================================

export default function WorkspacePage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  // ----- Fetch all workspaces (no single-workspace endpoint) -----
  const {
    data: workspaces,
    isLoading: wsLoading,
    error: wsError,
  } = useQuery<WorkspaceData[]>({
    queryKey: ["workspaces"],
    queryFn: async () => {
      const { data } = await api.get("/workspaces/")
      return data
    },
    staleTime: 10000,
    retry: 1,
  })

  // ----- Find the current workspace by ID -----
  const workspace = useMemo(() => {
    if (!workspaces || !id || id === "new") return null
    return workspaces.find((w) => w.id === id) ?? null
  }, [workspaces, id])

  // ----- Fetch conversations in this workspace -----
  const {
    data: conversations,
    isLoading: convLoading,
  } = useQuery<ConversationItem[]>({
    queryKey: ["workspace-conversations", workspace?.id],
    queryFn: async () => {
      const { data } = await api.get(`/workspaces/${workspace!.id}/conversations`)
      return data
    },
    enabled: !!workspace?.id,
    staleTime: 10000,
    retry: 1,
  })

  // ----- Fetch all assets to find papers in this workspace -----
  const { data: assetsData } = useQuery<AssetListResponse>({
    queryKey: ["assets"],
    queryFn: async () => {
      const { data } = await api.get("/assets/", { params: { size: 100 } })
      return data
    },
    enabled: !!workspace && workspace.papers.length > 0,
    staleTime: 30000,
    retry: 1,
  })

  // ----- Derive workspace papers as PaperCard-compatible items -----
  const workspacePapers: StoredPaper[] = useMemo(() => {
    if (!workspace || !assetsData?.items) return []
    const paperIds = new Set(workspace.papers)
    return assetsData.items
      .filter((asset) => paperIds.has(asset.id))
      .map((asset) => ({
        id: asset.id,
        title: asset.title,
        abstract: asset.abstract,
        year: asset.year,
        authors: asset.authors,
        tags: asset.tags,
        field:
          (asset.analysis as Record<string, unknown>)?.field_of_study as string | undefined ??
          ((asset.analysis as Record<string, unknown>)?.scientific_areas as string[] | undefined)?.[0],
        is_analyzed: !!asset.analysis,
      }))
  }, [workspace, assetsData])

  // ----- Derived stats -----
  const lastActivity = useMemo(() => {
    if (!workspace) return null
    if (!conversations || conversations.length === 0) return workspace.updated_at
    return conversations.reduce((latest, c) => {
      return c.updated_at > latest ? c.updated_at : latest
    }, workspace.updated_at)
  }, [workspace, conversations])

  const handlePaperClick = useCallback((paper: StoredPaper) => {
    navigate(`/assets/${paper.id}`)
  }, [navigate])

  // ----- Loading state -----
  if (wsLoading) {
    return (
      <div className="space-y-6 animate-in fade-in duration-500">
        {/* Skeleton hero */}
        <div className="rounded-xl border border-navy-700/50 bg-navy-800/50 p-8">
          <Skeleton className="mb-2 h-9 w-72" />
          <Skeleton className="mb-6 h-4 w-48" />
          <div className="mt-8 grid grid-cols-2 gap-4 lg:grid-cols-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="rounded-lg border border-navy-700/50 bg-navy-800/80 p-5">
                <Skeleton className="mb-3 h-4 w-16" />
                <Skeleton className="mb-1 h-9 w-20" />
                <Skeleton className="h-3 w-24" />
              </div>
            ))}
          </div>
        </div>
        <SkeletonGrid count={4} />
      </div>
    )
  }

  // ----- Error / Not found -----
  if (wsError || (!workspace && id !== "new")) {
    return (
      <div className="animate-in fade-in duration-500">
        <EmptyState
          icon={FolderOpen}
          title="Workspace not found"
          description={
            wsError
              ? "Failed to load workspace. Please try again."
              : "This workspace doesn't exist or has been removed."
          }
          action={{
            label: "Back to workspaces",
            onClick: () => navigate("/"),
          }}
        />
      </div>
    )
  }

  // ----- New workspace (empty placeholder) -----
  if (id === "new" || !workspace) {
    return (
      <div className="animate-in fade-in duration-500">
        <EmptyState
          icon={Sparkles}
          title="New Workspace"
          description="Create a new workspace to organize your research papers and conversations."
          action={{
            label: "Create workspace",
            onClick: () => navigate("/workspaces/new"),
          }}
        />
      </div>
    )
  }

  const conversationList = conversations ?? []
  const hasPapers = workspacePapers.length > 0

  // ========================================================================
  // Render
  // ========================================================================

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* ================================================================= */}
      {/* Hero Section                                                     */}
      {/* ================================================================= */}
      <section className="relative overflow-hidden rounded-xl border border-gold-500/10 bg-gradient-to-br from-navy-900 via-navy-950 to-navy-900 p-8">
        {/* Decorative blur blobs */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -right-20 -top-20 h-64 w-64 rounded-full bg-gold-500/5 blur-3xl"
        />
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -bottom-20 -left-20 h-48 w-48 rounded-full bg-gold-500/5 blur-3xl"
        />

        <div className="relative">
          <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-3">
                <h1 className="font-display text-3xl font-semibold tracking-tight text-white sm:text-4xl">
                  {workspace.name}
                </h1>
                <StatusBadge status="success" label="Active" />
              </div>
              <div className="h-0.5 w-16 rounded-full bg-gold-500/60" />
              {workspace.description && (
                <p className="max-w-2xl text-sm text-navy-200">
                  {workspace.description}
                </p>
              )}
              <div className="flex flex-wrap items-center gap-4 text-xs text-navy-300">
                <span className="inline-flex items-center gap-1.5">
                  <Calendar className="h-3.5 w-3.5" />
                  Created {formatFullDate(workspace.created_at)}
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <Activity className="h-3.5 w-3.5" />
                  Updated {formatRelativeTime(workspace.updated_at)}
                </span>
              </div>
            </div>

            <div className="flex shrink-0 items-center gap-3">
              <Button
                size="lg"
                className="gap-2 border-gold-500/30 bg-gold-500/10 text-gold-300 shadow-sm backdrop-blur-sm hover:bg-gold-500/20 hover:text-gold-200"
                onClick={() => navigate(`/workspaces/${workspace.id}`)}
              >
                <Plus className="h-5 w-5" />
                New Conversation
              </Button>
            </div>
          </div>

          {/* Stats row */}
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
            <StatCard
              icon={MessageSquare}
              label="Conversations"
              value={conversationList.length}
              suffix="total conversations"
            />
            <StatCard
              icon={BookOpen}
              label="Papers"
              value={workspace.papers.length}
              suffix={hasPapers ? `${workspacePapers.length} loaded` : "associated papers"}
            />
            <StatCard
              icon={Clock}
              label="Last Activity"
              value={lastActivity ? formatRelativeTime(lastActivity) : "—"}
              suffix={lastActivity ? formatFullDate(lastActivity) : "no activity yet"}
            />
          </div>
        </div>
      </section>

      {/* ================================================================= */}
      {/* Papers Section (if any)                                          */}
      {/* ================================================================= */}
      {hasPapers && (
        <section>
          <div className="mb-4 flex items-center gap-2">
            <BookOpen className="h-5 w-5 text-gold-400" />
            <h2 className="font-display text-xl font-semibold text-foreground">
              Papers
            </h2>
            <div className="ml-2 h-px flex-1 bg-gradient-to-r from-gold-500/20 to-transparent" />
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {workspacePapers.map((paper) => (
              <PaperCard
                key={paper.id}
                variant="stored"
                paper={paper}
                onClick={handlePaperClick}
              />
            ))}
          </div>
        </section>
      )}

      {/* ================================================================= */}
      {/* Conversations Section                                            */}
      {/* ================================================================= */}
      <section>
        <div className="mb-4 flex items-center gap-2">
          <MessageSquare className="h-5 w-5 text-gold-400" />
          <h2 className="font-display text-xl font-semibold text-foreground">
            Conversations
          </h2>
          <div className="ml-2 h-px flex-1 bg-gradient-to-r from-gold-500/20 to-transparent" />
        </div>

        {convLoading ? (
          <SkeletonGrid count={4} />
        ) : conversationList.length === 0 ? (
          <EmptyState
            icon={MessageSquare}
            title="No conversations yet"
            description="Start a conversation to begin exploring research topics."
            action={{
              label: "Start conversation",
              onClick: () => navigate(`/workspaces/${workspace.id}`),
            }}
          />
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {conversationList.map((conversation) => (
              <ConversationCard
                key={conversation.id}
                conversation={conversation}
                workspaceId={workspace.id}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
