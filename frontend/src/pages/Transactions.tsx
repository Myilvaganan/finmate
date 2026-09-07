import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { transactionService, type Transaction } from '@/services/transactionService'
import { LoadingState, EmptyState, ErrorState } from '@/components/ui/States'
import { InitialsAvatar } from '@/components/ui/Avatar'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { formatCurrency, formatDate } from '@/lib/format'

const PAGE_SIZE = 25

export function TransactionsPage() {
  const [params, setParams] = useSearchParams()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState(params.get('search') ?? '')
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const [bulkLoading, setBulkLoading] = useState(false)
  const queryClient = useQueryClient()

  const filters = { page, page_size: PAGE_SIZE, search: search || undefined }
  const { data, isLoading, isError } = useQuery({
    queryKey: ['transactions', filters],
    queryFn: () => transactionService.list(filters),
  })

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const bulkExclude = async (action: 'exclude' | 'include' | 'delete') => {
    if (selected.size === 0) return
    setBulkLoading(true)
    try {
      await transactionService.bulk(Array.from(selected), action)
      setSelected(new Set())
      setConfirmingDelete(false)
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['overview'] })
    } finally {
      setBulkLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h1 className="text-xl font-semibold">Transactions</h1>
        <div className="flex items-center gap-2">
          <input
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); setParams(e.target.value ? { search: e.target.value } : {}) }}
            placeholder="Search description…"
            className="rounded-lg border border-default bg-transparent px-3 py-1.5 text-sm outline-none w-56"
          />
        </div>
      </div>

      {selected.size > 0 && (
        <div className="surface rounded-lg p-2 flex items-center gap-3 text-sm">
          <span className="text-muted">{selected.size} selected</span>
          <button onClick={() => bulkExclude('exclude')} className="text-[color:var(--color-warning)]">Exclude</button>
          <button onClick={() => bulkExclude('include')} className="text-[color:var(--color-positive)]">Include</button>
          <button onClick={() => setConfirmingDelete(true)} className="text-[color:var(--color-negative)]">Delete</button>
        </div>
      )}

      <ConfirmDialog
        open={confirmingDelete}
        title={`Delete ${selected.size} transaction${selected.size === 1 ? '' : 's'}?`}
        description="This permanently removes the selected transactions and cannot be undone."
        confirmLabel="Delete"
        loading={bulkLoading}
        onConfirm={() => bulkExclude('delete')}
        onCancel={() => setConfirmingDelete(false)}
      />

      {isLoading && <LoadingState />}
      {isError && <ErrorState message="Could not load transactions." />}
      {data && data.data.length === 0 && <EmptyState title="No transactions found." description="Try adjusting your filters or upload a statement." />}

      {data && data.data.length > 0 && (
        <div className="surface rounded-xl overflow-x-auto">
          <table className="w-full text-sm min-w-[720px]">
            <thead className="text-muted text-xs uppercase border-b border-default">
              <tr>
                <th className="px-3 py-2"></th>
                <th className="text-left px-3 py-2 font-medium">Date</th>
                <th className="text-left px-3 py-2 font-medium">Description</th>
                <th className="text-left px-3 py-2 font-medium">Merchant</th>
                <th className="text-left px-3 py-2 font-medium">Category</th>
                <th className="text-right px-3 py-2 font-medium">Debit</th>
                <th className="text-right px-3 py-2 font-medium">Credit</th>
                <th className="text-right px-3 py-2 font-medium">Balance</th>
              </tr>
            </thead>
            <tbody>
              {data.data.map((t: Transaction) => (
                <tr key={t.id} className={`border-b border-default last:border-0 ${t.is_excluded ? 'opacity-50' : ''}`}>
                  <td className="px-3 py-2"><input type="checkbox" checked={selected.has(t.id)} onChange={() => toggle(t.id)} /></td>
                  <td className="px-3 py-2 whitespace-nowrap">{formatDate(t.transaction_date)}</td>
                  <td className="px-3 py-2 max-w-[240px] truncate" title={t.description}>{t.description}</td>
                  <td className="px-3 py-2">
                    <span className="flex items-center gap-2">
                      {t.merchant ? <InitialsAvatar name={t.merchant} size={22} /> : null}
                      {t.merchant || '—'}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <span className="text-xs px-2 py-0.5 rounded-full surface-2 border border-default">{t.category}</span>
                  </td>
                  <td className="px-3 py-2 text-right text-[color:var(--color-negative)]">{t.debit > 0 ? formatCurrency(t.debit) : ''}</td>
                  <td className="px-3 py-2 text-right text-[color:var(--color-positive)]">{t.credit > 0 ? formatCurrency(t.credit) : ''}</td>
                  <td className="px-3 py-2 text-right text-muted">{t.balance != null ? formatCurrency(t.balance) : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {data && data.meta.total_pages > 1 && (
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted">Page {data.meta.page} of {data.meta.total_pages} ({data.meta.total} transactions)</span>
          <div className="flex gap-2">
            <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)} className="px-3 py-1 rounded-lg border border-default disabled:opacity-40">Previous</button>
            <button disabled={page >= data.meta.total_pages} onClick={() => setPage((p) => p + 1)} className="px-3 py-1 rounded-lg border border-default disabled:opacity-40">Next</button>
          </div>
        </div>
      )}
    </div>
  )
}
