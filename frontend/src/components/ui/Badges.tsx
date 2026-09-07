import { Landmark } from 'lucide-react'
import { getBankColor, getCategoryColor, withAlpha } from '@/lib/colors'

export function CategoryBadge({ name }: { name: string }) {
  const color = getCategoryColor(name)
  return (
    <span
      className="text-xs px-2 py-0.5 rounded-full font-medium inline-flex items-center gap-1.5"
      style={{ background: withAlpha(color, 0.14), color }}
    >
      <span className="h-1.5 w-1.5 rounded-full shrink-0" style={{ background: color }} />
      {name}
    </span>
  )
}

export function BankTag({ name, masked }: { name: string; masked?: string }) {
  if (!name) return null
  const color = getBankColor(name)
  return (
    <span
      className="text-xs px-2 py-0.5 rounded-full font-medium inline-flex items-center gap-1 whitespace-nowrap"
      style={{ background: withAlpha(color, 0.14), color }}
      title={masked ? `${name} · ${masked}` : name}
    >
      <Landmark size={11} />
      {name}
    </span>
  )
}
