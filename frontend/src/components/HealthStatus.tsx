import { useQuery } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Activity,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Circle,
  CircleDot,
  ChevronRight,
} from "lucide-react"
import { api } from "@/lib/api"
import { cn } from "@/lib/utils"

// ----- Types -----

interface ModelHealth {
  model: string
  status: string
  latency_ms?: number
  error?: string
  last_checked?: number
}

interface ProviderHealth {
  provider: string
  status: "healthy" | "degraded" | "unhealthy" | "unknown" | "idle" | "active"
  models: ModelHealth[]
  last_checked?: number
  api_reachable?: boolean
}

interface HealthStatusData {
  providers: Record<string, ProviderHealth>
  active_models_count?: number
}

interface HealthIndicatorProps {
  variant: "compact" | "detailed"
  className?: string
}

// ----- Helpers -----

const statusMeta = (status: string) => {
  switch (status) {
    case "healthy":
    case "active":
      return { icon: CheckCircle2, color: "text-emerald-500", bg: "bg-emerald-500/10", label: "Healthy" }
    case "degraded":
      return { icon: AlertTriangle, color: "text-amber-500", bg: "bg-amber-500/10", label: "Degraded" }
    case "idle":
      return { icon: Circle, color: "text-muted-foreground", bg: "bg-muted/50", label: "Idle" }
    case "unhealthy":
      return { icon: XCircle, color: "text-red-500", bg: "bg-red-500/10", label: "Unhealthy" }
    default:
      return { icon: CircleDot, color: "text-muted-foreground", bg: "bg-muted/50", label: "Unknown" }
  }
}

function computeActiveModels(providers: Record<string, ProviderHealth>): number {
  return Object.values(providers).reduce(
    (count, p) => count + p.models.filter((m) => m.status === "healthy" || m.status === "active").length,
    0
  )
}

function computeTotalModels(providers: Record<string, ProviderHealth>): number {
  return Object.values(providers).reduce((count, p) => count + p.models.length, 0)
}

// ----- HealthIndicator -----

export function HealthIndicator({ variant, className }: HealthIndicatorProps) {
  const navigate = useNavigate()

  const { data: health, isLoading, refetch } = useQuery<HealthStatusData>({
    queryKey: ["health-status"],
    queryFn: async () => {
      const res = await api.get("/settings/health")
      return res.data
    },
    refetchInterval: 30000,
    retry: 1,
  })

  const handleForceCheck = async () => {
    await api.post("/settings/health/check")
    refetch()
  }

  const providers = health ? Object.values(health.providers) : []
  const totalModels = health ? computeTotalModels(health.providers) : 0
  const activeModels = health?.active_models_count ?? (health ? computeActiveModels(health.providers) : 0)
  const activeProviderCount = providers.filter(
    (p) => p.status === "healthy" || p.status === "active"
  ).length
  const hasIssues = providers.some((p) => p.status === "unhealthy" || p.status === "degraded")

  // ----- Compact variant -----
  if (variant === "compact") {
    if (isLoading) {
      return (
        <Card className={cn("overflow-hidden", className)}>
          <CardContent className="py-3 px-4">
            <div className="flex items-center gap-2">
              <Skeleton className="h-4 w-4 rounded-full" />
              <Skeleton className="h-4 w-48" />
            </div>
          </CardContent>
        </Card>
      )
    }

    if (!health) {
      return (
        <Card className={cn("overflow-hidden", className)}>
          <CardContent className="py-3 px-4">
            <div className="flex items-center gap-2 text-muted-foreground">
              <AlertTriangle aria-hidden="true" className="h-4 w-4 text-amber-500" />
              <span className="text-sm">Health check unavailable</span>
            </div>
          </CardContent>
        </Card>
      )
    }

    const Icon = hasIssues ? AlertTriangle : CheckCircle2
    const iconColor = hasIssues ? "text-amber-500" : "text-emerald-500"

    return (
      <Card
        className={cn("overflow-hidden", className)}
      >
        <button
          type="button"
          onClick={() => navigate("/settings")}
          className="w-full text-left cursor-pointer hover:shadow-sm transition-shadow focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          aria-label={`View LLM provider health: ${activeProviderCount} active providers, ${activeModels} of ${totalModels} models healthy`}
        >
          <CardContent className="py-3 px-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 min-w-0">
                <div
                  aria-hidden="true"
                  className={cn(
                    "p-1 rounded-md shrink-0",
                    hasIssues ? "bg-amber-500/10" : "bg-emerald-500/10"
                  )}
                >
                  <Icon className={cn("h-4 w-4", iconColor)} />
                </div>
                <span className="text-sm truncate">
                  {activeProviderCount > 0
                    ? `${activeProviderCount} active provider${activeProviderCount !== 1 ? "s" : ""} \u00b7 ${activeModels}/${totalModels} models healthy`
                    : "No active providers"}
                </span>
              </div>
              <ChevronRight aria-hidden="true" className="h-4 w-4 text-muted-foreground shrink-0 ml-2" />
            </div>
          </CardContent>
        </button>
      </Card>
    )
  }

  // ----- Detailed variant -----
  if (isLoading) {
    return (
      <Card className={cn(className)}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity aria-hidden="true" className="h-5 w-5" />
            LLM Provider Health
          </CardTitle>
          <CardDescription>Loading health status...</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  if (!health) return null

  return (
    <Card className={cn(className)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Activity aria-hidden="true" className="h-5 w-5" />
              LLM Provider Health
            </CardTitle>
            <CardDescription>
              {activeProviderCount}/{providers.length} providers healthy
            </CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={handleForceCheck}>
            <RefreshCw aria-hidden="true" className="h-4 w-4 mr-2" />
            Check Now
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {providers.map((provider) => {
            const meta = statusMeta(provider.status)
            const MetaIcon = meta.icon
            const healthyInProvider = provider.models.filter(
              (m) => m.status === "healthy" || m.status === "active"
            ).length

            return (
              <div
                key={provider.provider}
                className="flex items-center justify-between p-3 border rounded-lg"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div
                    aria-hidden="true"
                    className={cn("p-1 rounded-md shrink-0", meta.bg)}
                  >
                    <MetaIcon className={cn("h-5 w-5", meta.color)} />
                  </div>
                  <div className="min-w-0">
                    <p className="font-medium capitalize truncate">{provider.provider}</p>
                    <p className="text-sm text-muted-foreground">
                      {healthyInProvider}/{provider.models.length} models available
                    </p>
                  </div>
                </div>
                <Badge
                  variant={
                    provider.status === "healthy" || provider.status === "active"
                      ? "default"
                      : provider.status === "idle"
                        ? "outline"
                        : "destructive"
                  }
                  className="shrink-0 ml-2"
                >
                  {meta.label}
                </Badge>
              </div>
            )
          })}
        </div>

        {hasIssues && (
          <div
            role="alert"
            className="mt-4 p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg flex items-start gap-2"
          >
            <AlertTriangle aria-hidden="true" className="h-5 w-5 text-amber-500 mt-0.5 shrink-0" />
            <div>
              <p className="font-medium text-amber-500">Some providers are unavailable</p>
              <p className="text-sm text-muted-foreground">
                AI features may be degraded. Check your API keys in Settings.
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
