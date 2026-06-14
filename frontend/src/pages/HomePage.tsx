import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useAuthStore } from "@/stores/auth"
import { BookOpen, Search, FileText, Users, ArrowRight } from "lucide-react"

const features = [
  {
    icon: Search,
    title: "Scholar Search",
    description: "AI-powered academic paper discovery across multiple sources",
  },
  {
    icon: FileText,
    title: "Paper Writing",
    description: "AI-assisted academic writing with citation management",
  },
  {
    icon: BookOpen,
    title: "Paper Review",
    description: "Automated peer review with detailed feedback",
  },
  {
    icon: Users,
    title: "Recommendations",
    description: "Personalized paper recommendations based on your research",
  },
]

export default function HomePage() {
  const { isAuthenticated } = useAuthStore()

  return (
    <div className="flex flex-col min-h-[calc(100vh-4rem)]">
      {/* Hero Section */}
      <section className="flex-1 flex items-center justify-center px-4 py-16">
        <div className="max-w-4xl mx-auto text-center space-y-8">
          <h1 className="text-5xl font-bold tracking-tight sm:text-6xl">
            Your AI-Powered
            <span className="text-primary"> Academic Assistant</span>
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Streamline your research workflow with multi-agent AI. Search, write, review, and discover academic papers with intelligent assistance.
          </p>
          <div className="flex gap-4 justify-center">
            {isAuthenticated ? (
              <Button size="lg" asChild>
                <Link to="/dashboard">
                  Go to Dashboard
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Link>
              </Button>
            ) : (
              <>
                <Button size="lg" asChild>
                  <Link to="/register">
                    Get Started
                    <ArrowRight className="ml-2 h-5 w-5" />
                  </Link>
                </Button>
                <Button size="lg" variant="outline" asChild>
                  <Link to="/login">Sign In</Link>
                </Button>
              </>
            )}
          </div>
        </div>
      </section>

      <section className="px-4 py-16 bg-muted/50">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-12">
            Powerful Research Tools
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((feature) => (
              <Card key={feature.title}>
                <CardHeader>
                  <feature.icon className="h-10 w-10 text-primary mb-2" />
                  <CardTitle className="text-lg">{feature.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription>{feature.description}</CardDescription>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}
