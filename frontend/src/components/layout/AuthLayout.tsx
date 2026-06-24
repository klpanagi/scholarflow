import { Link, Outlet } from 'react-router-dom'
import { BookOpen } from 'lucide-react'

export default function AuthLayout() {
  return (
    <div className="relative min-h-screen flex items-center justify-center overflow-hidden bg-gradient-to-br from-navy-50 via-background to-navy-50 dark:from-navy-950 dark:via-navy-900 dark:to-navy-950">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -top-40 -right-40 h-[500px] w-[500px] rounded-full bg-gold-300/20 blur-3xl dark:bg-gold-500/10"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -bottom-40 -left-40 h-[400px] w-[400px] rounded-full bg-amber-300/20 blur-3xl dark:bg-amber-500/10"
      />

      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 opacity-[0.03] dark:opacity-[0.05]"
        style={{
          backgroundImage: 'radial-gradient(circle, currentColor 1px, transparent 1px)',
          backgroundSize: '40px 40px',
        }}
      />

      <div className="relative z-10 w-full max-w-md mx-4 flex flex-col items-center">
        <Link
          to="/"
          className="flex items-center gap-3 mb-8 group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 rounded-md"
        >
          <div
            aria-hidden="true"
            className="flex h-10 w-10 items-center justify-center rounded-xl bg-gold-500/10 ring-1 ring-gold-500/20 group-hover:bg-gold-500/20 transition-colors"
          >
            <BookOpen aria-hidden="true" className="h-5 w-5 text-gold-500" />
          </div>
          <span className="text-2xl font-bold tracking-tight text-foreground font-display">
            ScholarFlow
          </span>
        </Link>

        <main className="w-full bg-card/60 backdrop-blur-xl border border-border/50 rounded-2xl shadow-2xl p-8">
          <Outlet />
        </main>

        <p className="mt-6 text-xs text-muted-foreground/60">
          Multi-agent academic research assistant
        </p>
      </div>
    </div>
  )
}
