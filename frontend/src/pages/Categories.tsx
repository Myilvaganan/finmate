import { useQuery } from '@tanstack/react-query'
import { analyticsService } from '@/services/analyticsService'
import { presetToRange } from '@/components/ui/DateRangePicker'
import { LoadingState, EmptyState } from '@/components/ui/States'
import { formatCurrency } from '@/lib/format'

export function CategoriesPage() {
  const range = presetToRange('this_year')
  const { data, isLoading } = useQuery({
    queryKey: ['categories-page', range],
    queryFn: () => analyticsService.categories({ start_date: range.start, end_date: range.end }),
  })

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Categories</h1>
        <p className="text-sm text-muted mt-0.5">Spending breakdown by category, year to date.</p>
      </div>
      {isLoading && <LoadingState />}
      {data && data.length === 0 && <EmptyState title="No categorized spending yet." />}
      {data && data.length > 0 && (
        <div className="surface rounded-xl divide-y divide-[color:var(--color-border)]">
          {data.map((c) => (
            <div key={c.category_id ?? c.category} className="flex items-center justify-between px-4 py-3 text-sm">
              <span>{c.category}</span>
              <span className="text-muted">{c.count} transactions</span>
              <span className="font-medium">{formatCurrency(c.total)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
