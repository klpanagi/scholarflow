import { useQuery } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useAuthStore } from "@/stores/auth"
import { HealthIndicator } from "@/components/HealthStatus"
import { api } from "@/lib/api"
import { cn } from "@/lib/utils"
import {
  FileText,
  Search,
  MessageSquare,
  Upload,
  Tag,
  Sparkles,
  ArrowRight,
  Calendar,
  Clock,
  Workflow,
  ChevronRight,
  Library,
  Activity,
} from "lucide-react"

// ----- Types -----

interface DashboardStats {
  assets_count: number
  conversations_count: number
  workspaces_count: number
  agents_count: number
  workflow_executions_count: number
  recent_assets: RecentAsset[]
  recent_sessions: ChatSessionItem[]
  recent_ws_conversations: WsConversationItem[]
  recent_executions: WorkflowExecutionItem[]
  tag_breakdown: TagBreakdown[]
  monthly_activity: MonthlyActivity[]
}

interface RecentAsset {
  id: string
  title: string
  authors: string[]
  doc_type: string
  year?: number
  venue?: string
  tags: string[]
  analysis?: {
    scientific_areas?: string[]
    field_of_study?: string
    subfield?: string
    keywords?: string[]
    summary?: string
  }
  created_at: string
}

interface ChatSessionItem {
  id: string
  title: string
  model?: string
  provider?: string
  updated_at: string
}

interface WsConversationItem {
  id: string
  title: string
  workspace_id: string
  updated_at: string
}

interface WorkflowExecutionItem {
  id: string
  workflow_id: string
  status: string
  created_at: string
}

interface TagBreakdown {
  tag: string
  count: number
}

interface MonthlyActivity {
  month: string
  label: string
  count: number
}

interface ActivityItem {
  id: string
  type: "asset" | "conversation" | "execution"
  title: string
  timestamp: string
  description?: string
}

// ----- Helpers -----

function getGreeting(): string {
  const hour = new Date().getHours()
  if (hour < 12) return "Good morning"
  if (hour < 18) return "Good afternoon"
  return "Good evening"
}

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

function todayFormatted(): string {
  return new Date().toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  })
}

// ----- Component -----

export default function DashboardPage() {
  const { user } = useAuthStore()

  const { data: stats, isLoading: statsLoading } = useQuery<DashboardStats>({
    queryKey: ["dashboard-stats"],
    queryFn: async () => {
      const { data } = await api.get("/dashboard/stats")
      return data
    },
    staleTime: 30000,
    retry: 1,
  })

  // Quick action definitions
  const quickActions = [
    {
      icon: Search,
      title: "Search Assets",
      description: "AI-powered asset discovery",
      href: "/assets?tab=search",
      color: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
    },
    {
      icon: Upload,
      title: "Upload Asset",
      description: "Upload & analyze research",
      href: "/assets?tab=upload",
      color: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
    },
    {
      icon: Sparkles,
      title: "AI Agents",
      description: "Run specialized agents",
      href: "/cult",
      color: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
    },
    {
      icon: MessageSquare,
      title: "New Conversation",
      description: "Start a research chat",
      href: "/workspaces/new",
      color: "bg-violet-500/10 text-violet-600 dark:text-violet-400",
    },
  ]

  // KPI card definitions
  const kpiCards = [
    {
      label: "Assets",
      key: "assets_count" as const,
      icon: FileText,
      color: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
      href: "/assets",
    },
    {
      label: "Conversations",
      key: "conversations_count" as const,
      icon: MessageSquare,
      color: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
      href: "/workspaces",
    },
    {
      label: "Workflows",
      key: "agents_count" as const,
      icon: Workflow,
      color: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
      href: "/workflows",
    },
    {
      label: "Workspaces",
      key: "workspaces_count" as const,
      icon: Library,
      color: "bg-violet-500/10 text-violet-600 dark:text-violet-400",
      href: "/workspaces",
    },
  ]

  // Build activity feed from all data sources
  const recentAssets = stats?.recent_assets ?? []
  const recentSessions = stats?.recent_sessions ?? []
  const recentConversations = stats?.recent_ws_conversations ?? []
  const recentExecutions = stats?.recent_executions ?? []

  const activityItems: ActivityItem[] = [
    ...recentAssets.map((a) => ({
      id: `asset-${a.id}`,
      type: "asset" as const,
      title: a.title,
      timestamp: a.created_at,
      description: a.doc_type,
    })),
    ...recentSessions.map((s) => ({
      id: `session-${s.id}`,
      type: "conversation" as const,
      title: s.title || "Untitled chat",
      timestamp: s.updated_at,
      description: "Chat session",
    })),
    ...recentConversations.map((c) => ({
      id: `conv-${c.id}`,
      type: "conversation" as const,
      title: c.title || "Untitled conversation",
      timestamp: c.updated_at,
      description: "Workspace conversation",
    })),
    ...recentExecutions.map((e) => ({
      id: `exec-${e.id}`,
      type: "execution" as const,
      title: `Workflow execution (${e.status})`,
      timestamp: e.created_at,
      description: `Status: ${e.status}`,
    })),
  ]
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
    .slice(0, 8)

  return (
    <div className="container mx-auto px-4 py-8 space-y-8">
      {/* ----- Hero Banner ----- */}
      <section className="relative overflow-hidden rounded-xl bg-gradient-to-br from-primary/10 via-background to-primary/5 border p-8">
        <div
          aria-hidden="true"
          className="absolute top-0 right-0 w-72 h-72 bg-primary/5 rounded-full -translate-y-1/2 translate-x-1/3 blur-3xl pointer-events-none"
        />
        <div
          aria-hidden="true"
          className="absolute bottom-0 left-0 w-56 h-56 bg-amber-500/5 rounded-full translate-y-1/2 -translate-x-1/3 blur-3xl pointer-events-none"
        />
        <div className="relative flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-2">
            <h1 className="text-3xl font-bold tracking-tight">
              {getGreeting()}, {user?.name?.split(" ")[0] || "Researcher"}
              <span className="text-muted-foreground">.</span>
            </h1>
            <p className="text-muted-foreground flex items-center gap-2 text-sm">
              <Calendar className="h-4 w-4" />
              {todayFormatted()}
            </p>
            <p className="text-sm text-muted-foreground/80">
              {stats
                ? `${stats.assets_count} assets across ${stats.workspaces_count} workspaces`
                : "Your academic research hub"}
            </p>
          </div>
          <Button size="lg" className="gap-2 shadow-sm shrink-0" asChild>
            <Link to="/assets?tab=search">
              <Sparkles className="h-5 w-5" />
              Start Research
              <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        </div>
      </section>

      {/* ----- KPI Stats Row ----- */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {statsLoading
          ? [1, 2, 3, 4].map((i) => (
              <Card key={i}>
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between mb-3">
                    <Skeleton className="h-4 w-16" />
                    <Skeleton className="h-8 w-8 rounded-lg" />
                  </div>
                  <Skeleton className="h-8 w-20 mb-1" />
                  <Skeleton className="h-3 w-24" />
                </CardContent>
              </Card>
            ))
          : kpiCards.map((card) => {
              const Icon = card.icon
              const value = stats?.[card.key] ?? 0
              return (
                <Link key={card.key} to={card.href} className="group">
                  <Card className="transition-all duration-200 group-hover:shadow-md group-hover:-translate-y-0.5">
                    <CardContent className="pt-6">
                      <div className="flex items-start justify-between mb-3">
                        <span className="text-sm font-medium text-muted-foreground">
                          {card.label}
                        </span>
                        <div className={cn("p-2 rounded-lg", card.color)}>
                          <Icon className="h-4 w-4" />
                        </div>
                      </div>
                      <div className="text-3xl font-bold tracking-tight">{value}</div>
                      <p className="text-xs text-muted-foreground mt-1">Total {card.label.toLowerCase()}</p>
                    </CardContent>
                  </Card>
                </Link>
              )
            })}
      </div>

      {/* ----- Two-Column Layout ----- */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Recent Assets */}
        <div className="lg:col-span-7 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <FileText className="h-5 w-5 text-muted-foreground" />
              Recent Assets
            </h2>
            <Button variant="ghost" size="sm" asChild>
              <Link to="/assets" className="gap-1">
                View all <ChevronRight className="h-4 w-4" />
              </Link>
            </Button>
          </div>

          {statsLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[1, 2, 3, 4].map((i) => (
                <Card key={i}>
                  <CardContent className="pt-4">
                    <Skeleton className="h-4 w-16 mb-2" />
                    <Skeleton className="h-5 w-full mb-2" />
                    <Skeleton className="h-4 w-3/4 mb-2" />
                    <div className="flex gap-2 mt-2">
                      <Skeleton className="h-5 w-16" />
                      <Skeleton className="h-5 w-20" />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : recentAssets.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12 text-center">
                <div className="p-4 rounded-full bg-primary/5 mb-4">
                  <FileText className="h-8 w-8 text-muted-foreground" />
                </div>
                <h3 className="font-medium mb-1">No assets yet</h3>
                <p className="text-sm text-muted-foreground mb-4 max-w-xs">
                  Upload your first research asset to get started with AI-powered analysis
                </p>
                <Button variant="outline" size="sm" asChild>
                  <Link to="/assets?tab=upload">
                    <Upload className="h-4 w-4 mr-2" />
                    Upload Asset
                  </Link>
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {recentAssets.map((asset) => (
                <Link key={asset.id} to="/assets" className="group">
                  <Card className="h-full transition-all duration-200 group-hover:shadow-md group-hover:-translate-y-0.5">
                    <CardContent className="pt-4 flex flex-col h-full">
                      <div className="flex items-center gap-2 mb-2">
                        <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                          {asset.doc_type}
                        </Badge>
                        {asset.year && (
                          <span className="text-[10px] text-muted-foreground">{asset.year}</span>
                        )}
                      </div>
                      <h3 className="font-medium text-sm leading-snug line-clamp-2 mb-1 flex-1">
                        {asset.title}
                      </h3>
                      {asset.authors && asset.authors.length > 0 && (
                        <p className="text-xs text-muted-foreground line-clamp-1 mb-2">
                          {asset.authors.join(", ")}
                        </p>
                      )}
                      {(asset.analysis?.field_of_study || asset.analysis?.subfield) && (
                        <div className="flex flex-wrap gap-1 mb-1.5">
                          {asset.analysis?.field_of_study && (
                            <Badge variant="default" className="text-[10px] px-1.5 py-0">
                              {asset.analysis.field_of_study}
                            </Badge>
                          )}
                          {asset.analysis?.subfield && (
                            <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                              {asset.analysis.subfield}
                            </Badge>
                          )}
                        </div>
                      )}
                      {asset.tags && asset.tags.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          {asset.tags.slice(0, 2).map((tag, i) => (
                            <Badge
                              key={i}
                              variant="outline"
                              className="text-[10px] px-1.5 py-0 flex items-center gap-0.5"
                            >
                              <Tag className="h-2.5 w-2.5" />
                              {tag}
                            </Badge>
                          ))}
                          {asset.tags.length > 2 && (
                            <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                              +{asset.tags.length - 2}
                            </Badge>
                          )}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Right: Health + Quick Actions */}
        <div className="lg:col-span-5 space-y-6">
          <HealthIndicator variant="compact" />

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-amber-500" />
                Quick Actions
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-1">
              {quickActions.map((action) => {
                const ActionIcon = action.icon
                return (
                  <Link
                    key={action.title}
                    to={action.href}
                    className="flex items-center gap-3 p-3 rounded-lg hover:bg-muted/50 transition-colors group"
                  >
                    <div className={cn("p-2 rounded-lg shrink-0", action.color)}>
                      <ActionIcon className="h-4 w-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium">{action.title}</p>
                      <p className="text-xs text-muted-foreground">{action.description}</p>
                    </div>
                    <ChevronRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                  </Link>
                )
              })}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* ----- Recent Activity ----- */}
      {activityItems.length > 0 && (
        <section className="space-y-4">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Activity className="h-5 w-5 text-muted-foreground" />
            Recent Activity
          </h2>
          <Card>
            <CardContent className="pt-4">
              {activityItems.map((item, idx) => (
                <div key={item.id}>
                  <div className="flex items-start gap-3 py-3">
                    <div
                      className={cn(
                        "p-1.5 rounded-full mt-0.5 shrink-0",
                        item.type === "asset"
                          ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                          : item.type === "execution"
                            ? "bg-amber-500/10 text-amber-600 dark:text-amber-400"
                            : "bg-blue-500/10 text-blue-600 dark:text-blue-400"
                      )}
                    >
                      {item.type === "asset" ? (
                        <FileText className="h-3.5 w-3.5" />
                      ) : item.type === "execution" ? (
                        <Workflow className="h-3.5 w-3.5" />
                      ) : (
                        <MessageSquare className="h-3.5 w-3.5" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{item.title}</p>
                      <p className="text-xs text-muted-foreground flex items-center gap-1 mt-0.5">
                        <Clock className="h-3 w-3 shrink-0" />
                        {item.description ?? item.type}
                        <span aria-hidden="true" className="mx-1">
                          &middot;
                        </span>
                        {formatRelativeTime(item.timestamp)}
                      </p>
                    </div>
                  </div>
                  {idx < activityItems.length - 1 && (
                    <div className="h-px bg-border ml-9" />
                  )}
                </div>
              ))}
            </CardContent>
          </Card>
        </section>
      )}
    </div>
  )
}
