import { NavLink, useLocation } from 'react-router-dom'
import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface SidebarNavItemProps {
  to: string
  label: string
  icon: LucideIcon
  end?: boolean
}

export function SidebarNavItem({ to, label, icon: Icon, end }: SidebarNavItemProps) {
  const location = useLocation()
  const isActive = end
    ? location.pathname === to
    : location.pathname === to || location.pathname.startsWith(`${to}/`)

  return (
    <li>
      <NavLink
        to={to}
        end={end}
        aria-current={isActive ? 'page' : undefined}
        className={cn(
          'group flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-200 border-l-2',
          isActive
            ? 'bg-gold-500/10 text-gold-500 border-gold-500'
            : 'text-muted-foreground hover:bg-gold-500/5 hover:text-gold-400 border-transparent',
        )}
      >
        <Icon aria-hidden="true" className="h-4 w-4 shrink-0" />
        <span>{label}</span>
      </NavLink>
    </li>
  )
}
