import { Outlet, Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth'
import { Button } from '@/components/ui/button'
import {
  BookOpen,
  GitBranch,
  LogOut,
  Bot,
  Settings,
  Menu,
  X,
  LayoutDashboard,
  HardDrive,
} from 'lucide-react'
import * as Dialog from '@radix-ui/react-dialog'
import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
import { cn } from '@/lib/utils'

const navLinks = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/assets', label: 'Assets', icon: HardDrive },
  { to: '/cult', label: 'Cult', icon: Bot },
  { to: '/workflows', label: 'Workflows', icon: GitBranch },
]

function MobileNav({ user, handleLogout }: { user: any; handleLogout: () => void }) {
  return (
    <Dialog.Root>
      <Dialog.Trigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="md:hidden text-slate-600"
          aria-label="Open navigation menu"
        >
          <Menu aria-hidden="true" className="h-5 w-5" />
        </Button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/40 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
        <Dialog.Content
          className="fixed left-0 top-0 h-full w-72 bg-white shadow-xl data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:slide-out-to-left data-[state=open]:slide-in-from-left z-50"
          aria-describedby={undefined}
        >
          <Dialog.Title className="sr-only">Navigation menu</Dialog.Title>
          <div className="flex items-center justify-between p-4 border-b">
            <Link
              to="/"
              className="flex items-center gap-2 font-bold text-xl text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
            >
              <BookOpen aria-hidden="true" className="h-6 w-6" />
              <span>ScholarFlow</span>
            </Link>
            <Dialog.Close asChild>
              <Button variant="ghost" size="icon" aria-label="Close navigation menu">
                <X aria-hidden="true" className="h-5 w-5" />
              </Button>
            </Dialog.Close>
          </div>
          <nav aria-label="Mobile primary" className="flex flex-col p-4 gap-1">
            {user ? (
              <>
                {navLinks.map((link) => (
                  <Dialog.Close key={link.to} asChild>
                    <Link
                      to={link.to}
                      className="flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-accent transition-colors"
                    >
                      <link.icon aria-hidden="true" className="h-4 w-4" />
                      {link.label}
                    </Link>
                  </Dialog.Close>
                ))}
                <div className="h-px bg-slate-200 my-2" />
                <Dialog.Close asChild>
                  <Link
                    to="/settings"
                    className="flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-accent transition-colors"
                  >
                    <Settings aria-hidden="true" className="h-4 w-4" />
                    Settings
                  </Link>
                </Dialog.Close>
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium text-red-600 hover:bg-red-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded transition-colors"
                >
                  <LogOut aria-hidden="true" className="h-4 w-4" />
                  Log out
                </button>
              </>
            ) : (
              <>
                <Dialog.Close asChild>
                  <Link
                    to="/login"
                    className="flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-accent transition-colors"
                  >
                    Log in
                  </Link>
                </Dialog.Close>
                <Dialog.Close asChild>
                  <Link
                    to="/register"
                    className="flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium text-primary bg-primary/5 hover:bg-primary/10 transition-colors"
                  >
                    Get Started
                  </Link>
                </Dialog.Close>
              </>
            )}
          </nav>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}

export function Layout() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  return (
    <div className="min-h-screen bg-background font-sans text-slate-900">
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      <header className="sticky top-0 z-40 w-full border-b bg-white/80 backdrop-blur-md shadow-sm">
        <div className="container flex h-16 items-center justify-between px-4 md:px-8">
          <div className="flex items-center gap-3">
            <MobileNav user={user} handleLogout={handleLogout} />
            <Link
              to="/"
              className="flex items-center gap-2 font-bold text-xl text-primary transition-colors hover:text-primary/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
            >
              <BookOpen aria-hidden="true" className="h-6 w-6" />
              <span className="tracking-tight">ScholarFlow</span>
            </Link>
          </div>

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
                    <Bot aria-hidden="true" className="h-4 w-4 mr-2" /> Cult
                  </Button>
                </Link>
                <Link to="/workflows">
                  <Button variant="ghost" className="text-sm font-medium text-slate-600 hover:text-slate-900">
                    <GitBranch aria-hidden="true" className="h-4 w-4 mr-2" /> Workflows
                  </Button>
                </Link>
                <div className="h-4 w-px bg-slate-200 mx-2" />

                <DropdownMenu.Root>
                  <DropdownMenu.Trigger asChild>
                    <button
                      className="flex items-center gap-2.5 ml-2 pl-2 border-l border-slate-200 outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
                      aria-label={`User menu for ${user.name}`}
                    >
                      <div
                        aria-hidden="true"
                        className="flex items-center justify-center w-8 h-8 rounded-full bg-primary/10 text-primary font-semibold text-sm"
                      >
                        {user.name.charAt(0).toUpperCase()}
                      </div>
                      <span className="text-sm font-medium hidden lg:inline-block">{user.name}</span>
                    </button>
                  </DropdownMenu.Trigger>
                  <DropdownMenu.Portal>
                    <DropdownMenu.Content
                      align="end"
                      sideOffset={8}
                      className={cn(
                        "z-50 min-w-[10rem] overflow-hidden rounded-md border bg-white p-1 shadow-md",
                        "data-[state=open]:animate-in data-[state=closed]:animate-out",
                        "data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0",
                        "data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95"
                      )}
                    >
                      <div className="px-2 py-1.5 text-sm text-muted-foreground border-b mb-1">
                        {user.email}
                      </div>
                      <DropdownMenu.Item asChild>
                        <Link
                          to="/settings"
                          className="flex items-center gap-2 px-2 py-1.5 text-sm rounded hover:bg-accent cursor-pointer outline-none"
                        >
                          <Settings aria-hidden="true" className="h-4 w-4" />
                          Settings
                        </Link>
                      </DropdownMenu.Item>
                      <DropdownMenu.Item asChild>
                        <button
                          onClick={handleLogout}
                          className="flex items-center gap-2 px-2 py-1.5 text-sm rounded hover:bg-red-50 text-red-600 cursor-pointer outline-none w-full"
                        >
                          <LogOut aria-hidden="true" className="h-4 w-4" />
                          Log out
                        </button>
                      </DropdownMenu.Item>
                    </DropdownMenu.Content>
                  </DropdownMenu.Portal>
                </DropdownMenu.Root>
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

      <main id="main-content" tabIndex={-1} className="container max-w-7xl mx-auto px-4 md:px-8 py-8 animate-in fade-in duration-500 focus:outline-none">
        <Outlet />
      </main>
    </div>
  )
}
