import { useAuth } from '@/context/AuthContext'
import { useTheme } from '@/context/ThemeContext'
import { BRAND } from '@/config/brand'

export function SettingsPage() {
  const { user } = useAuth()
  const { theme, setTheme } = useTheme()

  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-xl font-semibold">Settings</h1>

      <section className="surface rounded-xl p-5 space-y-3">
        <h2 className="text-sm font-semibold">Profile</h2>
        <div className="text-sm text-muted">Name</div>
        <div className="text-sm">{user?.full_name || '—'}</div>
        <div className="text-sm text-muted">Email</div>
        <div className="text-sm">{user?.email}</div>
        <div className="text-sm text-muted">Plan</div>
        <div className="text-sm">{user?.plan}</div>
      </section>

      <section className="surface rounded-xl p-5 space-y-3">
        <h2 className="text-sm font-semibold">Appearance</h2>
        <div className="flex gap-2">
          {(['light', 'dark', 'system'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTheme(t)}
              className={`px-3 py-1.5 rounded-lg text-sm border capitalize ${theme === t ? 'border-[color:var(--color-accent)] text-[color:var(--color-accent)]' : 'border-default'}`}
            >
              {t}
            </button>
          ))}
        </div>
      </section>

      <section className="surface rounded-xl p-5 space-y-2">
        <h2 className="text-sm font-semibold">About</h2>
        <p className="text-sm text-muted">{BRAND.name} — {BRAND.tagline}</p>
        <p className="text-xs text-muted">AI provider and other server-side settings are configured via backend environment variables and are never exposed to the browser.</p>
      </section>
    </div>
  )
}
