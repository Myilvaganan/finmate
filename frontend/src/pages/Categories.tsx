import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import { analyticsService } from '@/services/analyticsService'
import { categoryService } from '@/services/categoryService'
import type { ApiError } from '@/services/apiClient'
import { presetToRange } from '@/components/ui/DateRangePicker'
import { LoadingState, EmptyState } from '@/components/ui/States'
import { CategoryBadge } from '@/components/ui/Badges'
import { formatCurrency } from '@/lib/format'

function NewCategoryDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [name, setName] = useState('')
  const [groupName, setGroupName] = useState('')
  const [isEssential, setIsEssential] = useState(false)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const queryClient = useQueryClient()

  if (!open) return null

  const reset = () => { setName(''); setGroupName(''); setIsEssential(false); setError('') }
  const close = () => { reset(); onClose() }

  const submit = async () => {
    if (!name.trim()) { setError('Category name is required.'); return }
    setSaving(true)
    setError('')
    try {
      await categoryService.create({ name: name.trim(), group_name: groupName.trim() || undefined, is_essential: isEssential })
      queryClient.invalidateQueries({ queryKey: ['all-categories'] })
      queryClient.invalidateQueries({ queryKey: ['all-categories-for-filter'] })
      close()
    } catch (err) {
      setError((err as ApiError).message || 'Could not create category.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" onClick={close}>
      <div className="surface rounded-2xl max-w-sm w-full p-6" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-base font-semibold mb-4">New category</h2>
        <div className="space-y-3">
          <div>
            <label className="text-xs text-muted">Name</label>
            <input
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Rent 1"
              className="mt-1 w-full rounded-lg border border-default bg-transparent px-3 py-2 text-sm outline-none"
            />
          </div>
          <div>
            <label className="text-xs text-muted">Group (optional)</label>
            <input
              value={groupName}
              onChange={(e) => setGroupName(e.target.value)}
              placeholder="e.g. Housing"
              className="mt-1 w-full rounded-lg border border-default bg-transparent px-3 py-2 text-sm outline-none"
            />
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={isEssential} onChange={(e) => setIsEssential(e.target.checked)} />
            Essential expense
          </label>
          {error && <p className="text-sm text-[color:var(--color-negative)]">{error}</p>}
        </div>
        <div className="flex gap-2 justify-end mt-5">
          <button onClick={close} className="px-4 py-2 rounded-lg border border-default text-sm">Cancel</button>
          <button
            onClick={submit}
            disabled={saving}
            className="px-4 py-2 rounded-lg text-sm font-medium text-white bg-[color:var(--color-accent)] disabled:opacity-50"
          >
            {saving ? 'Creating…' : 'Create'}
          </button>
        </div>
      </div>
    </div>
  )
}

export function CategoriesPage() {
  const range = presetToRange('this_year')
  const [creating, setCreating] = useState(false)
  const { data, isLoading } = useQuery({
    queryKey: ['categories-page', range],
    queryFn: () => analyticsService.categories({ start_date: range.start, end_date: range.end }),
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-xl font-semibold">Categories</h1>
          <p className="text-sm text-muted mt-0.5">Spending breakdown by category, year to date.</p>
        </div>
        <button
          onClick={() => setCreating(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-white bg-[color:var(--color-accent)]"
        >
          <Plus size={16} /> New category
        </button>
      </div>
      {isLoading && <LoadingState />}
      {data && data.length === 0 && <EmptyState title="No categorized spending yet." />}
      {data && data.length > 0 && (
        <div className="surface rounded-xl divide-y divide-[color:var(--color-border)]">
          {data.map((c) => (
            <div key={c.category_id ?? c.category} className="flex items-center justify-between px-4 py-3 text-sm">
              <CategoryBadge name={c.category} />
              <span className="text-muted">{c.count} transactions</span>
              <span className="font-medium">{formatCurrency(c.total)}</span>
            </div>
          ))}
        </div>
      )}
      <NewCategoryDialog open={creating} onClose={() => setCreating(false)} />
    </div>
  )
}
