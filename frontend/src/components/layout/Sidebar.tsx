import {
  BookOpen,
  Bot,
  GitBranch,
  HardDrive,
  LayoutDashboard,
  MessageSquare,
  ScrollText,
  Settings as SettingsIcon,
} from 'lucide-react'
import { SidebarNavItem } from './SidebarNavItem'
import { SidebarNavGroup } from './SidebarNavGroup'
import { ThemeToggle } from '@/components/theme/ThemeToggle'
import { ScrollArea } from '@/components/ui/scroll-area'
import { UserMenu } from './UserMenu'

export function Sidebar() {
  return (
    <aside
      aria-label="Primary"
      className="flex h-screen w-[15.25rem] flex-col border-r border-border/50 bg-card/60 backdrop-blur-xl"
    >
      <div className="flex h-16 shrink-0 items-center gap-3 border-b border-border/30 px-5">
        <div
          aria-hidden="true"
          className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-gold-400 to-gold-600 shadow-sm"
        >
          <BookOpen aria-hidden="true" className="h-4 w-4 text-white" />
        </div>
        <span className="text-lg font-display font-bold tracking-tight text-foreground">
          ScholarFlow
        </span>
      </div>

      <nav aria-label="Main" className="flex-1 min-h-0">
        <ScrollArea className="h-full px-3 py-4">
        <SidebarNavGroup
          label="Overview"
          gradient="bg-gradient-to-r from-[hsl(var(--color-accent-primary)_/_10%)] to-transparent"
        >
          <SidebarNavItem to="/dashboard" label="Dashboard" icon={LayoutDashboard} end />
        </SidebarNavGroup>

        <SidebarNavGroup
          label="Research"
          gradient="bg-gradient-to-r from-[hsl(var(--color-info)_/_10%)] to-transparent"
        >
          <SidebarNavItem to="/assets" label="Assets" icon={HardDrive} end />
        </SidebarNavGroup>

        <SidebarNavGroup
          label="Intelligence"
          gradient="bg-gradient-to-r from-[hsl(var(--color-warning)_/_10%)] to-transparent"
        >
          <SidebarNavItem to="/cult/agents" label="Agents" icon={Bot} end />
          <SidebarNavItem to="/cult/skills" label="Skills" icon={ScrollText} end />
          <SidebarNavItem to="/cult/chat" label="Chat" icon={MessageSquare} end />
        </SidebarNavGroup>

        <SidebarNavGroup
          label="Productivity"
          gradient="bg-gradient-to-r from-[hsl(var(--color-success)_/_10%)] to-transparent"
        >
          <SidebarNavItem to="/workflows" label="Workflows" icon={GitBranch} end />
        </SidebarNavGroup>

        <SidebarNavGroup
          label="Settings"
          gradient="bg-gradient-to-r from-muted/10 to-transparent"
        >
          <SidebarNavItem to="/settings" label="Settings" icon={SettingsIcon} end />
        </SidebarNavGroup>
        </ScrollArea>
      </nav>

      <div className="shrink-0 border-t border-border/30 px-2 py-2">
        <div className="flex items-center justify-between gap-1 rounded-lg px-1">
          <ThemeToggle />
          <UserMenu align="start" side="top" />
        </div>
      </div>
    </aside>
  )
}
