import { useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { pageVariants, useReducedMotion, withReducedMotion } from '@/lib/motion'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'
import { MobileSidebar } from './MobileSidebar'

export function AppShell() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const location = useLocation()
  const prefersReduced = useReducedMotion()
  const variants = withReducedMotion(pageVariants, prefersReduced)

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      <div className="hidden lg:flex lg:flex-col">
        <Sidebar />
      </div>

      <MobileSidebar
        open={mobileMenuOpen}
        onClose={() => setMobileMenuOpen(false)}
      />

      <div className="flex flex-1 flex-col overflow-hidden">
        <Topbar onMenuClick={() => setMobileMenuOpen(true)} />

        <main id="main-content" tabIndex={-1} className="flex flex-col flex-1 overflow-y-auto focus:outline-none">
          <div className="mx-auto flex w-full max-w-7xl min-h-0 flex-1 flex-col p-4 lg:p-6">
            <AnimatePresence mode="wait">
              <motion.div
                key={location.pathname}
                variants={variants}
                initial="initial"
                animate="animate"
                exit="exit"
                className="flex flex-1 flex-col min-h-0"
              >
                <Outlet />
              </motion.div>
            </AnimatePresence>
          </div>
        </main>
      </div>
    </div>
  )
}
