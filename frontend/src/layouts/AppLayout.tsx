import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, ArrowLeftRight, FileUp, BarChart3, Tags, Landmark,
  FileText, Sparkles, Settings, Search, Bell, Moon, Sun, Monitor, LogOut,
} from 'lucide-react'
import { BRAND } from '@/config/brand'
import { useAuth } from '@/context/AuthContext'
import { useTheme } from '@/context/ThemeContext'
import { useState } from 'react'

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/transactions', label: 'Transactions', icon: ArrowLeftRight },
  { to: '/statements', label: 'Statements', icon: FileUp },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/categories', label: 'Categories', icon: Tags },
  { to: '/accounts', label: 'Accounts', icon: Landmark },
  { to: '/reports', label: 'Reports', icon: FileText },
  { to: '/assistant', label: 'AI Assistant', icon: Sparkles },
  { to: '/settings', label: 'Settings', icon: Settings },
]

const MOBILE_NAV = [
  { to: '/', label: 'Home', icon: LayoutDashboard, end: true },
  { to: '/transactions', label: 'Transactions', icon: ArrowLeftRight },
  { to: '/assistant', label: 'AI', icon: Sparkles },
  { to: '/statements', label: 'Statements', icon: FileUp },
  { to: '/settings', label: 'More', icon: Settings },
]

export function AppLayout() {
  const { user, logout } = useAuth()
  const { theme, setTheme } = useTheme()
  const navigate = useNavigate()
  const [search, setSearch] = useState('')

  return (
    <div className="min-h-screen flex" style={{ background: 'var(--color-bg)' }}>
      <aside
        className="hidden md:flex md:flex-col w-64 shrink-0 border-r border-default"
        style={{ background: 'var(--color-sidebar-bg)', color: 'var(--color-sidebar-fg)' }}
      >
        <div className="px-5 py-5 flex items-center gap-2">
          <div className="h-7 w-7 rounded-md bg-[color:var(--color-accent)] flex items-center justify-center text-white text-sm font-bold">F</div>
          <div>
            <div className="font-semibold text-white leading-tight">{BRAND.name}</div>
            <div className="text-[11px] text-white/40 leading-tight">{BRAND.tagline}</div>
          </div>
        </div>
        <nav className="flex-1 px-3 space-y-1 mt-2">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive ? 'bg-[color:var(--color-sidebar-active)] text-white' : 'text-white/60 hover:text-white hover:bg-white/5'
                }`
              }
            >
              <item.icon size={17} />
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="p-4 border-t border-white/10 flex items-center gap-3">
          <div className="h-9 w-9 rounded-full bg-white/10 flex items-center justify-center text-sm font-medium text-white">
            {user?.full_name?.[0]?.toUpperCase() ?? 'U'}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm text-white truncate">{user?.full_name || user?.email}</div>
            <div className="text-xs text-white/40">{user?.plan} plan</div>
          </div>
          <button onClick={logout} title="Log out" className="text-white/50 hover:text-white">
            <LogOut size={16} />
          </button>
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 border-b border-default flex items-center gap-4 px-4 md:px-6 surface">
          <div className="flex-1 flex items-center gap-2 max-w-md">
            <Search size={16} className="text-muted" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && search.trim()) {
                  navigate(`/transactions?search=${encodeURIComponent(search.trim())}`)
                }
              }}
              placeholder="Search transactions, merchants, or ask a question…"
              className="bg-transparent outline-none text-sm w-full placeholder:text-muted"
            />
          </div>
          <div className="flex items-center gap-3">
            <ThemeSwitcher theme={theme} setTheme={setTheme} />
            <button className="text-muted hover:text-current" aria-label="Notifications">
              <Bell size={18} />
            </button>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-4 md:p-6 pb-20 md:pb-6">
          <Outlet />
        </main>
      </div>

      <nav className="md:hidden fixed bottom-0 left-0 right-0 h-16 surface border-t border-default flex items-center justify-around z-10">
        {MOBILE_NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) => `flex flex-col items-center gap-0.5 text-[11px] ${isActive ? 'text-[color:var(--color-accent)]' : 'text-muted'}`}
          >
            <item.icon size={19} />
            {item.label}
          </NavLink>
        ))}
      </nav>
    </div>
  )
}

function ThemeSwitcher({ theme, setTheme }: { theme: string; setTheme: (t: 'light' | 'dark' | 'system') => void }) {
  const icons = { light: Sun, dark: Moon, system: Monitor } as const
  const order: ('light' | 'dark' | 'system')[] = ['light', 'dark', 'system']
  const Icon = icons[theme as keyof typeof icons] ?? Monitor
  return (
    <button
      className="text-muted hover:text-current"
      title={`Theme: ${theme}`}
      onClick={() => setTheme(order[(order.indexOf(theme as any) + 1) % order.length])}
    >
      <Icon size={18} />
    </button>
  )
}
