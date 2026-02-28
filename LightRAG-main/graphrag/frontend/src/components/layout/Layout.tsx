import { useEffect } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import {
  FileText,
  GitGraph,
  Search,
  LayoutDashboard,
  LogOut,
  User,
} from 'lucide-react'

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/documents', label: 'Documents', icon: FileText },
  { path: '/graph', label: 'Knowledge Graph', icon: GitGraph },
  { path: '/retrieval', label: 'Retrieval', icon: Search },
]

export function Layout() {
  const { isAuthenticated, isGuestMode, username, logout } = useAuthStore()
  const navigate = useNavigate()

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login')
    }
  }, [isAuthenticated, navigate])

  if (!isAuthenticated) {
    return null
  }

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background">
      {/* Sidebar */}
      <aside className="flex w-64 flex-col border-r bg-card">
        <div className="p-4">
          <h2 className="text-xl font-bold text-primary">GraphRAG</h2>
        </div>

        <nav className="flex-1 space-y-1 p-2">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors',
                  isActive
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                )
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* User section */}
        <div className="border-t p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted">
              <User className="h-4 w-4" />
            </div>
            <div className="flex-1 overflow-hidden">
              <p className="truncate text-sm font-medium">
                {username || 'Guest'}
              </p>
              {isGuestMode && (
                <p className="text-xs text-muted-foreground">Guest Mode</p>
              )}
            </div>
            <Button variant="ghost" size="icon" onClick={logout}>
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-14 items-center border-b px-6">
          <h1 className="text-lg font-semibold">GraphRAG UI</h1>
        </header>
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
