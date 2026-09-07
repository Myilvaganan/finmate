import type { ReactNode } from 'react'
import { useEffect, useRef, useState } from 'react'

const MIN_HEIGHT = 160
const MAX_HEIGHT = 900

export function ChartCard({
  title, subtitle, children, action, defaultHeight = 320,
}: {
  title: string; subtitle?: string; children: ReactNode; action?: ReactNode; defaultHeight?: number
}) {
  const storageKey = `chartcard-height:${title}`
  const bodyRef = useRef<HTMLDivElement>(null)
  const [height] = useState<number>(() => {
    try {
      const saved = Number(localStorage.getItem(storageKey))
      return saved >= MIN_HEIGHT && saved <= MAX_HEIGHT ? saved : defaultHeight
    } catch {
      return defaultHeight
    }
  })

  useEffect(() => {
    const el = bodyRef.current
    if (!el) return
    let first = true
    const observer = new ResizeObserver((entries) => {
      if (first) { first = false; return } // skip the initial observe-triggered callback
      const h = Math.round(entries[0].contentRect.height)
      if (h > 0) {
        try { localStorage.setItem(storageKey, String(h)) } catch { /* ignore */ }
      }
    })
    observer.observe(el)
    return () => observer.disconnect()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [storageKey])

  return (
    <div className="surface rounded-xl p-5 flex flex-col gap-4 min-w-0 animate-fade-in-up">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold">{title}</h3>
          {subtitle && <p className="text-xs text-muted mt-0.5">{subtitle}</p>}
        </div>
        {action}
      </div>
      <div
        ref={bodyRef}
        style={{ height, minHeight: MIN_HEIGHT, maxHeight: MAX_HEIGHT }}
        className="min-h-0 resize-y overflow-auto rounded-lg -mx-1 px-1 pb-1"
      >
        {children}
      </div>
    </div>
  )
}
