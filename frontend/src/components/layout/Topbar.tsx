import { Menu, Search } from 'lucide-react'
import { useLocation } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { ThemeToggle } from '@/components/theme/ThemeToggle'
import { UserMenu } from './UserMenu'

interface TopbarProps {
  onMenuClick?: () => void
}

const pageTitles: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/assets': 'Assets',
  '/cult': 'Intelligence',
  '/workflows': 'Workflows',
  '/settings': 'Settings',
}

export function Topbar({ onMenuClick }: TopbarProps) {
  const location = useLocation()

  const pageTitle =
    Object.entries(pageTitles).find(
      ([path]) =>
        location.pathname === path ||
        location.pathname.startsWith(path + '/'),
    )?.[1] || 'ScholarFlow'

  return (
    <header className="sticky top-0 z-20 flex h-16 shrink-0 items-center justify-between border-b border-border/50 bg-background/60 backdrop-blur-xl px-4 lg:px-6">
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          className="lg:hidden text-muted-foreground"
          onClick={onMenuClick}
          aria-label="Open navigation menu"
        >
          <Menu aria-hidden="true" className="h-5 w-5" />
        </Button>

        <span
          aria-hidden="true"
          className="hidden sm:block text-sm font-medium text-foreground"
        >
          {pageTitle}
        </span>

        <button
          type="button"
          aria-label="Open search (Command+K)"
          className="hidden lg:inline-flex items-center gap-2 rounded-md border border-border/50 bg-muted/30 px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
        >
          <Search aria-hidden="true" className="h-4 w-4" />
          <span>Search...</span>
          <kbd className="ml-4 hidden xl:inline-flex h-5 items-center gap-1 rounded border border-border bg-background px-1.5 text-[10px] font-medium text-muted-foreground">
            <span className="text-xs" aria-hidden="true">⌘</span>K
          </kbd>
        </button>
      </div>

      <div className="flex items-center gap-2">
        <ThemeToggle />
        <UserMenu />
      </div>
    </header>
  )
}
