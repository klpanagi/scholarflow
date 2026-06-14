import { useQuery } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useAuthStore } from "@/stores/auth"
import { FileText, Search, BookOpen, MessageSquare, Upload } from "lucide-react"
import { HealthStatus } from "@/components/HealthStatus"

interface DashboardStats {
  papers: number
  conversations: number
  workspaces: number
}

export default function DashboardPage() {
  const { user } = useAuthStore()

  const { data: stats } = useQuery<DashboardStats>({
    queryKey: ["dashboard-stats"],
    queryFn: async () => {
          return { papers: 0, conversations: 0, workspaces: 0 }
    },
  })

  const quickActions = [
    {
      icon: Search,
      title: "Search Papers",
      description: "Find academic papers with AI-powered search",
      href: "/papers?tab=search",
      variant: "default" as const,
    },
    {
      icon: Upload,
      title: "Upload Paper",
      description: "Upload and analyze your research papers",
      href: "/papers?tab=upload",
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
            <CardTitle className="text-sm font-medium">Papers</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.papers || 0}</div>
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
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
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
    </div>
  )
}
