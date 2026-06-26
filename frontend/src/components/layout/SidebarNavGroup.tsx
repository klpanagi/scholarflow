import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface SidebarNavGroupProps {
  label: string
  gradient: string
  children: ReactNode
}

export function SidebarNavGroup({ label, gradient, children }: SidebarNavGroupProps) {
  return (
    <div className="mb-4">
      <div className={cn('mb-1.5 rounded-md px-3 py-1', gradient)}>
        <h2 className="text-[10px] font-semibold uppercase tracking-[0.15em] text-muted-foreground">
          {label}
        </h2>
      </div>
      <ul className="m-0 list-none space-y-0.5 p-0">
        {children}
      </ul>
    </div>
  )
}
