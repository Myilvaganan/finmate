import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Landmark, Plus, Trash2 } from 'lucide-react'
import { accountService, type Account } from '@/services/accountService'
import { LoadingState, EmptyState } from '@/components/ui/States'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { formatCurrency } from '@/lib/format'

export function AccountsPage() {
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['accounts'], queryFn: accountService.list })
  const [showForm, setShowForm] = useState(false)
  const [bankName, setBankName] = useState('')
  const [accountType, setAccountType] = useState('bank')
  const [pendingDelete, setPendingDelete] = useState<Account | null>(null)

  const createMutation = useMutation({
    mutationFn: () => accountService.create({ bank_name: bankName, account_type: accountType }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['accounts'] }); setShowForm(false); setBankName('') },
  })
  const removeMutation = useMutation({
    mutationFn: (id: string) => accountService.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
      queryClient.invalidateQueries({ queryKey: ['overview'] })
      setPendingDelete(null)
    },
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Accounts</h1>
        <button onClick={() => setShowForm((v) => !v)} className="flex items-center gap-1 text-sm rounded-lg bg-[color:var(--color-accent)] text-[color:var(--color-accent-fg)] px-3 py-1.5">
          <Plus size={15} /> Add Account
        </button>
      </div>

      {showForm && (
        <form
          onSubmit={(e) => { e.preventDefault(); createMutation.mutate() }}
          className="surface rounded-xl p-4 flex flex-wrap items-end gap-3"
        >
          <div>
            <label className="text-xs text-muted block mb-1">Bank Name</label>
            <input required value={bankName} onChange={(e) => setBankName(e.target.value)} className="rounded-lg border border-default bg-transparent px-3 py-1.5 text-sm" />
          </div>
          <div>
            <label className="text-xs text-muted block mb-1">Type</label>
            <select value={accountType} onChange={(e) => setAccountType(e.target.value)} className="rounded-lg border border-default bg-transparent px-3 py-1.5 text-sm">
              <option value="bank">Bank Account</option>
              <option value="credit_card">Credit Card</option>
              <option value="cash">Cash</option>
              <option value="other">Other</option>
            </select>
          </div>
          <button type="submit" className="rounded-lg bg-[color:var(--color-accent)] text-[color:var(--color-accent-fg)] px-4 py-1.5 text-sm">Save</button>
        </form>
      )}

      {isLoading && <LoadingState />}
      {data && data.length === 0 && <EmptyState title="No accounts yet." description="Accounts are created automatically when you upload a statement, or you can add one manually." />}

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {data?.map((a) => (
          <div key={a.id} className="surface rounded-xl p-4 flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Landmark size={16} className="text-muted" />
                <span className="font-medium text-sm">{a.bank_name}</span>
              </div>
              <button onClick={() => setPendingDelete(a)} className="text-muted hover:text-[color:var(--color-negative)]" aria-label={`Delete ${a.bank_name}`}>
                <Trash2 size={15} />
              </button>
            </div>
            <div className="text-xs text-muted capitalize">{a.account_type.replace('_', ' ')} · {a.masked_account_number}</div>
            <div className="text-lg font-semibold mt-1">{formatCurrency(a.closing_balance, a.currency)}</div>
            {a.is_demo && <span className="text-[10px] uppercase tracking-wide text-[color:var(--color-warning)]">Demo Data</span>}
          </div>
        ))}
      </div>

      <ConfirmDialog
        open={!!pendingDelete}
        title={`Delete ${pendingDelete?.bank_name}?`}
        description="This permanently deletes this account and every transaction imported under it. This cannot be undone."
        confirmLabel="Delete Account"
        loading={removeMutation.isPending}
        onConfirm={() => pendingDelete && removeMutation.mutate(pendingDelete.id)}
        onCancel={() => setPendingDelete(null)}
      />
    </div>
  )
}
