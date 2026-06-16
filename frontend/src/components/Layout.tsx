import { Outlet, Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth'
import { Button } from '@/components/ui/button'
import { BookOpen, GitBranch, LogOut, Bot, Settings } from 'lucide-react'

export function Layout() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  return (
    <div className="min-h-screen bg-background font-sans text-slate-900">
      <header className="sticky top-0 z-40 w-full border-b bg-white/80 backdrop-blur-md shadow-sm">
        <div className="container flex h-16 items-center justify-between px-4 md:px-8">
          <Link to="/" className="flex items-center gap-2 font-bold text-xl text-primary transition-colors hover:text-primary/80">
            <BookOpen className="h-6 w-6" />
            <span className="tracking-tight">ScholarFlow</span>
          </Link>

          <nav className="hidden md:flex items-center gap-1">
            {user ? (
              <>
                <Link to="/dashboard">
                  <Button variant="ghost" className="text-sm font-medium text-slate-600 hover:text-slate-900">Dashboard</Button>
                </Link>
                <Link to="/assets">
                  <Button variant="ghost" className="text-sm font-medium text-slate-600 hover:text-slate-900">Assets</Button>
                </Link>
                <Link to="/cult">
                  <Button variant="ghost" className="text-sm font-medium text-slate-600 hover:text-slate-900">
                    <Bot className="h-4 w-4 mr-2" /> Cult
                  </Button>
                </Link>
                <Link to="/workflows">
                  <Button variant="ghost" className="text-sm font-medium text-slate-600 hover:text-slate-900">
                    <GitBranch className="h-4 w-4 mr-2" /> Workflows
                  </Button>
                </Link>
                <div className="h-4 w-px bg-slate-200 mx-2" />
                <Link to="/settings">
                  <Button variant="ghost" size="icon" className="text-slate-500 hover:text-slate-900">
                    <Settings className="h-4 w-4" />
                  </Button>
                </Link>
                <div className="flex items-center gap-3 ml-2 pl-2 border-l border-slate-200">
                  <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary/10 text-primary font-semibold text-sm">
                    {user.name.charAt(0).toUpperCase()}
                  </div>
                  <span className="text-sm font-medium hidden lg:inline-block">{user.name}</span>
                  <Button variant="ghost" size="icon" onClick={handleLogout} className="text-slate-500 hover:text-destructive">
                    <LogOut className="h-4 w-4" />
                  </Button>
                </div>
              </>
            ) : (
              <div className="flex items-center gap-2">
                <Link to="/login">
                  <Button variant="ghost" className="font-medium">Log in</Button>
                </Link>
                <Link to="/register">
                  <Button className="font-medium shadow-sm">Get Started</Button>
                </Link>
              </div>
            )}
          </nav>
        </div>
      </header>

      <main className="container max-w-7xl mx-auto px-4 md:px-8 py-8 animate-in fade-in duration-500">
        <Outlet />
      </main>
    </div>
  )
}
