import { useQuery } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useAuthStore } from "@/stores/auth"
import { FileText, Search, BookOpen, MessageSquare, Upload, Tag, MapPin } from "lucide-react"
import { HealthStatus } from "@/components/HealthStatus"
import { api } from "@/lib/api"

interface DashboardStats {
  assets: number
  conversations: number
  workspaces: number
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

export default function DashboardPage() {
  const { user } = useAuthStore()

  const { data: stats } = useQuery<DashboardStats>({
    queryKey: ["dashboard-stats"],
    queryFn: async () => {
      return { assets: 0, conversations: 0, workspaces: 0 }
    },
  })

  const { data: recentAssets = [] } = useQuery<RecentAsset[]>({
    queryKey: ["recent-assets"],
    queryFn: async () => {
      const { data } = await api.get("/assets?size=5")
      return data.items || []
    },
  })

  const quickActions = [
    {
      icon: Search,
      title: "Search Assets",
      description: "Find academic assets with AI-powered search",
      href: "/assets?tab=search",
      variant: "default" as const,
    },
    {
      icon: Upload,
      title: "Upload Asset",
      description: "Upload and analyze your research assets",
      href: "/assets?tab=upload",
      variant: "outline" as const,
    },
    {
      icon: BookOpen,
      title: "AI Agents",
      description: "Configure and run specialized AI agents",
      href: "/cult",
      variant: "outline" as const,
    },
    {
      icon: MessageSquare,
      title: "New Conversation",
      description: "Start a new research conversation",
      href: "/workspaces/new",
      variant: "outline" as const,
    },
  ]

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">
          Welcome back, {user?.name || "Researcher"}
        </h1>
        <p className="text-muted-foreground mt-2">
          Your academic research dashboard
        </p>
      </div>

      <div className="mb-8">
        <HealthStatus />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Assets</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.assets || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Conversations</CardTitle>
            <MessageSquare className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.conversations || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Workspaces</CardTitle>
            <BookOpen className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.workspaces || 0}</div>
          </CardContent>
        </Card>
      </div>

      <h2 className="text-xl font-semibold mb-4">Quick Actions</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {quickActions.map((action) => (
          <Link key={action.title} to={action.href}>
            <Card className="h-full hover:shadow-md transition-shadow cursor-pointer">
              <CardHeader>
                <action.icon className="h-8 w-8 text-primary mb-2" />
                <CardTitle className="text-lg">{action.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <CardDescription>{action.description}</CardDescription>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      {recentAssets.length > 0 && (
        <>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">Recent Assets</h2>
            <Link to="/assets" className="text-sm text-primary hover:underline">View all</Link>
          </div>
          <div className="grid gap-4">
            {recentAssets.map((asset) => (
              <Link key={asset.id} to="/assets">
                <Card className="hover:shadow-md transition-shadow cursor-pointer">
                  <CardContent className="pt-4">
                    <div className="flex justify-between items-start gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <h3 className="font-medium">{asset.title}</h3>
                          <Badge variant="secondary" className="text-xs">{asset.doc_type}</Badge>
                          {asset.year && <span className="text-xs text-muted-foreground">{asset.year}</span>}
                        </div>
                        {asset.authors && asset.authors.length > 0 && (
                          <p className="text-sm text-muted-foreground mt-1">{asset.authors.join(", ")}</p>
                        )}
                        {asset.venue && (
                          <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                            <MapPin className="h-3 w-3" /> {asset.venue}
                          </p>
                        )}
                        <div className="flex flex-wrap gap-1 mt-2">
                          {asset.analysis?.field_of_study && (
                            <Badge key="fos" variant="default" className="text-xs">{asset.analysis.field_of_study}</Badge>
                          )}
                          {asset.analysis?.subfield && (
                            <Badge key="sub" variant="secondary" className="text-xs">{asset.analysis.subfield}</Badge>
                          )}
                          {asset.analysis?.scientific_areas?.slice(0, 3).map((area, i) => (
                            <Badge key={i} variant="outline" className="text-xs">{area}</Badge>
                          ))}
                        </div>
                        <div className="flex flex-wrap gap-1 mt-1.5">
                          {asset.tags?.slice(0, 4).map((tag, i) => (
                            <Badge key={i} variant="outline" className="text-xs flex items-center gap-1">
                              <Tag className="h-2.5 w-2.5" /> {tag}
                            </Badge>
                          ))}
                          {asset.tags && asset.tags.length > 4 && (
                            <Badge variant="outline" className="text-xs">+{asset.tags.length - 4}</Badge>
                          )}
                        </div>
                        {asset.analysis?.keywords && asset.analysis.keywords.length > 0 && (
                          <p className="text-xs text-muted-foreground mt-1.5">
                            Keywords: {asset.analysis.keywords.slice(0, 5).join(", ")}
                          </p>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
