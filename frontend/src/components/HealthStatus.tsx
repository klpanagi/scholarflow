import { useQuery } from "@tanstack/react-query"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Activity, CheckCircle2, XCircle, AlertTriangle, RefreshCw } from "lucide-react"
import { api } from "@/lib/api"

interface ModelHealth {
  model: string
  status: string
  latency_ms: number
  error?: string
  last_checked: number
}

interface ProviderHealth {
  provider: string
  status: string
  models: ModelHealth[]
  last_checked: number
  api_reachable: boolean
}

interface HealthStatusData {
  providers: Record<string, ProviderHealth>
}

export function HealthStatus() {
  const { data: health, isLoading, refetch } = useQuery<HealthStatusData>({
    queryKey: ["health-status"],
    queryFn: async () => {
      const res = await api.get("/settings/health")
      return res.data
    },
    refetchInterval: 30000,
  })

  const handleForceCheck = async () => {
    await api.post("/settings/health/check")
    refetch()
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            LLM Provider Health
          </CardTitle>
          <CardDescription>Loading health status...</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  if (!health) return null

  const providers = Object.values(health.providers)
  const healthyCount = providers.filter(p => p.status === "healthy").length
  const totalCount = providers.length
  const hasUnhealthy = providers.some(p => p.status !== "healthy")

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              LLM Provider Health
            </CardTitle>
            <CardDescription>
              {healthyCount}/{totalCount} providers healthy
            </CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={handleForceCheck}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Check Now
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {providers.map((provider) => (
            <div key={provider.provider} className="flex items-center justify-between p-3 border rounded-lg">
              <div className="flex items-center gap-3">
                {provider.status === "healthy" ? (
                  <CheckCircle2 className="h-5 w-5 text-green-500" />
                ) : (
                  <XCircle className="h-5 w-5 text-red-500" />
                )}
                <div>
                  <p className="font-medium capitalize">{provider.provider}</p>
                  <p className="text-sm text-muted-foreground">
                    {provider.models.filter(m => m.status === "healthy").length}/{provider.models.length} models available
                  </p>
                </div>
              </div>
              <Badge variant={provider.status === "healthy" ? "default" : "destructive"}>
                {provider.status === "healthy" ? "Healthy" : provider.status === "degraded" ? "Degraded" : "Unhealthy"}
              </Badge>
            </div>
          ))}
        </div>

        {hasUnhealthy && (
          <div className="mt-4 p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg flex items-start gap-2">
            <AlertTriangle className="h-5 w-5 text-yellow-500 mt-0.5" />
            <div>
              <p className="font-medium text-yellow-500">Some providers are unavailable</p>
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
