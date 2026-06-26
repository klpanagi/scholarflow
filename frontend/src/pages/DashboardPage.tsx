import { useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  Legend,
} from "recharts"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useAuthStore } from "@/stores/auth"
import { api } from "@/lib/api"
import { cn } from "@/lib/utils"
import {
  FileText,
  Workflow,
  MessageSquare,
  Library,
  Search,
  Upload,
  Sparkles,
  ArrowRight,
  Clock,
  Activity,
  TrendingUp,
  PieChartIcon,
  BarChart3,
} from "lucide-react"

// ========================================================================
// Types
// ========================================================================

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

// ========================================================================
// Constants
// ========================================================================

const CHART_COLORS = {
  gold: "#d4a574",
  goldLight: "#eec85e",
  goldDark: "#b8864a",
  amber: "#f59e0b",
  emerald: "#10b981",
  navy: "#475569",
  rose: "#f43f5e",
  navyLight: "#64748b",
}

const PIE_COLORS = [
  CHART_COLORS.gold,
  CHART_COLORS.emerald,
  CHART_COLORS.amber,
  CHART_COLORS.rose,
  CHART_COLORS.navy,
]

// ========================================================================
// Helpers
// ========================================================================

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

// ========================================================================
// Custom Chart Tooltips
// ========================================================================

function ChartTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ name?: string; value?: number; color?: string }>; label?: string | number }) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-lg border border-primary/20 bg-card/90 px-4 py-3 shadow-xl backdrop-blur-xl">
      <p className="mb-1 text-xs font-medium text-muted-foreground">{label}</p>
      {payload.map((entry, idx) => (
        <p key={idx} className="text-sm font-semibold" style={{ color: entry.color }}>
          {entry.name ?? "Value"}: {entry.value}
        </p>
      ))}
    </div>
  )
}

function PieTooltip({ active, payload }: { active?: boolean; payload?: Array<{ name?: string; value?: number; color?: string }> }) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-lg border border-primary/20 bg-card/90 px-4 py-3 shadow-xl backdrop-blur-xl">
      <p className="mb-1 text-xs font-medium text-muted-foreground">Papers</p>
      {payload.map((entry, idx) => (
        <p key={idx} className="text-sm font-semibold" style={{ color: entry.color }}>
          {entry.name ?? "Value"}: {entry.value}
        </p>
      ))}
    </div>
  )
}

// ========================================================================
// Main Component
// ========================================================================

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

  // ----- Derived chart data -----

  const activityData = useMemo(() => {
    return stats?.monthly_activity?.slice(-7) ?? []
  }, [stats])

  const statusDistribution = useMemo(() => {
    if (!stats?.recent_executions?.length) {
      return [
        { name: "Completed", value: 0 },
        { name: "Running", value: 0 },
        { name: "Failed", value: 0 },
        { name: "Pending", value: 0 },
      ]
    }
    const counts: Record<string, number> = {}
    stats.recent_executions.forEach((exec) => {
      const status = exec.status.toLowerCase()
      counts[status] = (counts[status] || 0) + 1
    })
    return Object.entries(counts).map(([name, value]) => ({
      name: name.charAt(0).toUpperCase() + name.slice(1),
      value,
    }))
  }, [stats])

  const workflowBarData = useMemo(() => {
    return stats?.monthly_activity?.slice(-8) ?? []
  }, [stats])

  // ----- Activity feed -----

  const activityItems: ActivityItem[] = useMemo(() => {
    const recentAssets = stats?.recent_assets ?? []
    const recentSessions = stats?.recent_sessions ?? []
    const recentConversations = stats?.recent_ws_conversations ?? []
    const recentExecutions = stats?.recent_executions ?? []

    const items: ActivityItem[] = [
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
    return items
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
      .slice(0, 8)
  }, [stats])

  // ----- Metrics -----

  const metrics = [
    {
      label: "Papers",
      value: stats?.assets_count ?? 0,
      icon: FileText,
      href: "/assets",
      suffix: "total papers",
    },
    {
      label: "Workflows",
      value: stats?.workflow_executions_count ?? 0,
      icon: Workflow,
      href: "/workflows",
      suffix: `active / ${stats?.agents_count ?? 0} total`,
    },
    {
      label: "Reviews",
      value: stats?.conversations_count ?? 0,
      icon: MessageSquare,
      href: "/workspaces",
      suffix: "completed reviews",
    },
    {
      label: "Citations",
      value: stats?.workspaces_count ?? 0,
      icon: Library,
      href: "/workspaces",
      suffix: "tracked citations",
    },
  ]

  // ----- Quick actions -----

  const quickActions = [
    {
      icon: Search,
      label: "New Search",
      description: "AI-powered literature search",
      href: "/assets?action=search",
      variant: "default" as const,
    },
    {
      icon: Workflow,
      label: "New Workflow",
      description: "Create analysis workflow",
      href: "/workflows?action=new",
      variant: "default" as const,
    },
    {
      icon: Upload,
      label: "Upload Paper",
      description: "Add paper to your library",
      href: "/assets?action=upload",
      variant: "secondary" as const,
    },
    {
      icon: Library,
      label: "View All",
      description: "Browse your research assets",
      href: "/assets",
      variant: "secondary" as const,
    },
  ]

  // ========================================================================
  // Loading State
  // ========================================================================

  if (statsLoading) {
    return (
      <div className="space-y-6 animate-in fade-in duration-500">
        <div className="rounded-xl border border-border bg-card p-8">
          <Skeleton className="mb-2 h-9 w-72" />
          <Skeleton className="mb-6 h-4 w-48" />
          <div className="mt-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="rounded-lg border border-border bg-card/80 p-5">
                <Skeleton className="mb-3 h-4 w-16" />
                <Skeleton className="mb-1 h-9 w-20" />
                <Skeleton className="h-3 w-24" />
              </div>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="rounded-lg border border-border bg-card p-6">
              <Skeleton className="mb-4 h-5 w-32" />
              <Skeleton className="mb-2 h-48 w-full rounded-lg" />
            </div>
          ))}
        </div>

        <div className="rounded-lg border border-border bg-card p-6">
          <Skeleton className="mb-4 h-5 w-36" />
          <div className="space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="flex items-center gap-3">
                <Skeleton className="h-8 w-8 shrink-0 rounded-full" />
                <div className="flex-1">
                  <Skeleton className="mb-1 h-4 w-48" />
                  <Skeleton className="h-3 w-32" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  // ========================================================================
  // Rendered Content
  // ========================================================================

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* ================================================================= */}
      {/* Hero Section — Greeting + Metric Cards                            */}
      {/* ================================================================= */}
      <section className="relative overflow-hidden rounded-xl border border-primary/10 bg-gradient-to-br from-background via-card to-background p-8">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -right-20 -top-20 h-64 w-64 rounded-full bg-primary/5 blur-3xl"
        />
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -bottom-20 -left-20 h-48 w-48 rounded-full bg-primary/5 blur-3xl"
        />

        <div className="relative">
          <div className="mb-8 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h1 className="font-display text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
                {getGreeting()}, {user?.name?.split(" ")[0] || "Researcher"}
                <span className="text-primary">.</span>
              </h1>
              <div className="mt-2 h-0.5 w-16 rounded-full bg-primary/60" />
              <p className="mt-3 text-sm text-muted-foreground">
                Here&apos;s your research overview &mdash; {todayFormatted()}
              </p>
            </div>
            <Button
              size="lg"
              className="gap-2 border-primary/30 bg-primary/10 text-primary shadow-sm backdrop-blur-sm hover:bg-primary/20 hover:text-primary"
              asChild
            >
              <Link to="/assets?action=search">
                <Sparkles className="h-5 w-5" />
                Start Research
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </div>

          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {metrics.map((metric) => {
              const MetricIcon = metric.icon
              return (
                <Link key={metric.label} to={metric.href} className="group">
                  <div className="rounded-lg border border-border bg-card/40 p-5 backdrop-blur-sm transition-all duration-300 group-hover:border-primary/30 group-hover:bg-card/60 group-hover:shadow-lg group-hover:shadow-primary/5">
                    <div className="mb-3 flex items-center justify-between">
                      <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                        {metric.label}
                      </span>
                      <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary/10 text-primary">
                        <MetricIcon className="h-4 w-4" />
                      </div>
                    </div>
                    <div className="font-display text-3xl font-semibold text-primary">
                      {metric.value}
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">{metric.suffix}</p>
                  </div>
                </Link>
              )
            })}
          </div>
        </div>
      </section>

      {/* ================================================================= */}
      {/* Quick Actions Row                                                */}
      {/* ================================================================= */}
      <section>
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {quickActions.map((action) => {
            const ActionIcon = action.icon
            return (
              <Link key={action.label} to={action.href}>
                <Button
                  variant={action.variant}
                  className={cn(
                    "h-auto w-full flex-col items-start gap-2 p-5 text-left",
                    action.variant === "default"
                      ? "border-primary/20 bg-primary/10 text-primary hover:bg-primary/20"
                      : "border-border bg-card/40 text-foreground hover:bg-muted",
                  )}
                >
                  <div className="flex w-full items-center justify-between">
                    <ActionIcon className="h-5 w-5 shrink-0" />
                    <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
                  </div>
                  <div>
                    <span className="block text-sm font-semibold">{action.label}</span>
                    <span className="mt-0.5 block text-xs font-normal text-muted-foreground">
                      {action.description}
                    </span>
                  </div>
                </Button>
              </Link>
            )
          })}
        </div>
      </section>

      {/* ================================================================= */}
      {/* Charts Section                                                   */}
      {/* ================================================================= */}
      <section>
        <div className="mb-4 flex items-center gap-2">
          <Activity className="h-5 w-5 text-primary" />
          <h2 className="font-display text-xl font-semibold text-foreground">Analytics</h2>
          <div className="ml-2 h-px flex-1 bg-gradient-to-r from-primary/20 to-transparent" />
        </div>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          <Card className="border-border bg-card/30 backdrop-blur-sm">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                <TrendingUp className="h-4 w-4 text-primary" />
                Activity Over Time
              </CardTitle>
            </CardHeader>
            <CardContent>
              {activityData.length > 0 ? (
                <div className="h-56">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={activityData} margin={{ top: 5, right: 5, bottom: 5, left: -10 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" strokeOpacity={0.5} />
                      <XAxis
                        dataKey="label"
                        tick={{ fill: "#94a3b8", fontSize: 11 }}
                        axisLine={{ stroke: "#334155" }}
                        tickLine={false}
                      />
                      <YAxis
                        tick={{ fill: "#94a3b8", fontSize: 11 }}
                        axisLine={false}
                        tickLine={false}
                        allowDecimals={false}
                      />
                      <Tooltip content={<ChartTooltip />} />
                      <Line
                        type="monotone"
                        dataKey="count"
                        stroke={CHART_COLORS.gold}
                        strokeWidth={2}
                        dot={{ fill: CHART_COLORS.gold, strokeWidth: 2, r: 3 }}
                        activeDot={{ fill: CHART_COLORS.goldLight, strokeWidth: 2, r: 5 }}
                        fillOpacity={0.15}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="flex h-56 flex-col items-center justify-center text-muted-foreground">
                  <TrendingUp className="mb-2 h-8 w-8" />
                  <p className="text-xs">No activity data yet</p>
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="border-border bg-card/30 backdrop-blur-sm">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                <PieChartIcon className="h-4 w-4 text-primary" />
                Workflow Status
              </CardTitle>
            </CardHeader>
            <CardContent>
              {statusDistribution.some((d) => d.value > 0) ? (
                <div className="h-56">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={statusDistribution}
                        cx="50%"
                        cy="50%"
                        innerRadius={45}
                        outerRadius={80}
                        paddingAngle={3}
                        dataKey="value"
                        stroke="none"
                      >
                        {statusDistribution.map((entry, idx) => (
                          <Cell
                            key={entry.name}
                            fill={PIE_COLORS[idx % PIE_COLORS.length]}
                          />
                        ))}
                      </Pie>
                      <Tooltip content={<PieTooltip />} />
                      <Legend
                        wrapperStyle={{ fontSize: 11, color: "#94a3b8" }}
                        iconType="circle"
                        iconSize={8}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="flex h-56 flex-col items-center justify-center text-muted-foreground">
                  <PieChartIcon className="mb-2 h-8 w-8" />
                  <p className="text-xs">No execution data yet</p>
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="border-border bg-card/30 backdrop-blur-sm">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                <BarChart3 className="h-4 w-4 text-primary" />
                Workflows per Period
              </CardTitle>
            </CardHeader>
            <CardContent>
              {workflowBarData.length > 0 ? (
                <div className="h-56">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={workflowBarData} margin={{ top: 5, right: 5, bottom: 5, left: -10 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" strokeOpacity={0.5} />
                      <XAxis
                        dataKey="label"
                        tick={{ fill: "#94a3b8", fontSize: 11 }}
                        axisLine={{ stroke: "#334155" }}
                        tickLine={false}
                      />
                      <YAxis
                        tick={{ fill: "#94a3b8", fontSize: 11 }}
                        axisLine={false}
                        tickLine={false}
                        allowDecimals={false}
                      />
                      <Tooltip content={<ChartTooltip />} />
                      <Bar
                        dataKey="count"
                        fill={CHART_COLORS.gold}
                        radius={[4, 4, 0, 0]}
                        maxBarSize={40}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="flex h-56 flex-col items-center justify-center text-muted-foreground">
                  <BarChart3 className="mb-2 h-8 w-8" />
                  <p className="text-xs">No workflow data yet</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </section>

      {/* ================================================================= */}
      {/* Recent Activity Timeline                                         */}
      {/* ================================================================= */}
      {activityItems.length > 0 && (
        <section>
          <div className="mb-4 flex items-center gap-2">
            <Activity className="h-5 w-5 text-primary" />
            <h2 className="font-display text-xl font-semibold text-foreground">Recent Activity</h2>
            <div className="ml-2 h-px flex-1 bg-gradient-to-r from-primary/20 to-transparent" />
          </div>

          <div className="rounded-xl border border-border bg-card/30 px-6 py-5 backdrop-blur-sm">
            <div className="relative">
              <div
                aria-hidden="true"
                className="absolute left-[17px] top-2 h-[calc(100%-16px)] w-px bg-gradient-to-b from-primary/30 via-accent/30 to-transparent"
              />

              <div className="space-y-0">
                {activityItems.map((item) => (
                  <div key={item.id} className="relative flex items-start gap-4 py-3">
                    <div
                      className={cn(
                        "relative z-10 flex h-9 w-9 shrink-0 items-center justify-center rounded-full border",
                        item.type === "asset"
                          ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                          : item.type === "execution"
                            ? "border-amber-500/30 bg-amber-500/10 text-amber-400"
                            : "border-primary/30 bg-primary/10 text-primary",
                      )}
                    >
                      {item.type === "asset" ? (
                        <FileText className="h-4 w-4" />
                      ) : item.type === "execution" ? (
                        <Workflow className="h-4 w-4" />
                      ) : (
                        <MessageSquare className="h-4 w-4" />
                      )}
                    </div>

                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-foreground">
                        {item.title}
                      </p>
                      <p className="mt-0.5 flex items-center gap-1.5 text-xs text-muted-foreground">
                        <Clock className="h-3 w-3 shrink-0" />
                        <span>{item.description ?? item.type}</span>
                        <span aria-hidden="true">&middot;</span>
                        <span>{formatRelativeTime(item.timestamp)}</span>
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>
      )}

      {activityItems.length === 0 && !statsLoading && (
        <section>
          <div className="mb-4 flex items-center gap-2">
            <Activity className="h-5 w-5 text-primary" />
            <h2 className="font-display text-xl font-semibold text-foreground">Recent Activity</h2>
            <div className="ml-2 h-px flex-1 bg-gradient-to-r from-primary/20 to-transparent" />
          </div>
          <div className="flex flex-col items-center justify-center rounded-xl border border-border bg-card/30 px-6 py-16 backdrop-blur-sm">
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-primary/10">
              <Activity className="h-6 w-6 text-primary" />
            </div>
            <h3 className="mb-1 text-base font-medium text-foreground">No activity yet</h3>
            <p className="max-w-xs text-center text-sm text-muted-foreground">
              Start by searching for papers or creating a workflow. Your recent activity will appear here.
            </p>
          </div>
        </section>
      )}
    </div>
  )
}
