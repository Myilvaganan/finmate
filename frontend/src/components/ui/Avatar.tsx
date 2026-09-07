const COLORS = [
  '#2563eb', '#16794e', '#b54708', '#7c3aed', '#0891b2', '#be185d', '#65a30d', '#c2410c', '#4f46e5',
]

function hashColor(seed: string): string {
  let hash = 0
  for (let i = 0; i < seed.length; i++) hash = seed.charCodeAt(i) + ((hash << 5) - hash)
  return COLORS[Math.abs(hash) % COLORS.length]
}

export function InitialsAvatar({ name, size = 32 }: { name: string; size?: number }) {
  const initial = name?.trim()?.[0]?.toUpperCase() || '?'
  const color = hashColor(name || '?')
  return (
    <div
      className="shrink-0 rounded-full flex items-center justify-center font-semibold text-white"
      style={{ width: size, height: size, background: color, fontSize: size * 0.42 }}
    >
      {initial}
    </div>
  )
}
