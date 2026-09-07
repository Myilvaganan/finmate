import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { transactionService, TRANSACTION_TYPES, PAYMENT_METHODS, type Transaction } from '@/services/transactionService'
import { accountService } from '@/services/accountService'
import { categoryService } from '@/services/categoryService'
import { LoadingState, EmptyState, ErrorState } from '@/components/ui/States'
import { InitialsAvatar } from '@/components/ui/Avatar'
import { BankTag } from '@/components/ui/Badges'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { formatCurrency, formatDate } from '@/lib/format'

const PAGE_SIZE = 25
const PAYMENT_METHOD_LABELS: Record<string, string> = {
  upi: 'UPI', card: 'Card', netbanking: 'Net Banking', cash: 'Cash', cheque: 'Cheque', neft_rtgs: 'NEFT/RTGS', other: 'Other',
}
const TXN_TYPE_LABELS: Record<string, string> = {
  income: 'Income', expense: 'Expense', transfer: 'Transfer', investment: 'Investment',
  cash_withdrawal: 'Cash Withdrawal', card_payment: 'Card Payment',
}

const selectClass = 'rounded-lg border border-default bg-transparent px-3 py-1.5 text-sm outline-none'

export function TransactionsPage() {
  const [params, setParams] = useSearchParams()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState(params.get('search') ?? '')
  const [accountId, setAccountId] = useState(params.get('account_id') ?? '')

  // Drill-down filters land here via URL (e.g. from an analytics chart click:
  // /transactions?category_id=...&start_date=...&end_date=...) -- read once on mount so a
  // "Clear filters" action can drop them without re-reading params on every render.
  const [categoryId, setCategoryId] = useState(params.get('category_id') ?? '')
  const [merchantId, setMerchantId] = useState(params.get('merchant_id') ?? '')
  const [startDate, setStartDate] = useState(params.get('start_date') ?? '')
  const [endDate, setEndDate] = useState(params.get('end_date') ?? '')
  const [paymentMethod, setPaymentMethod] = useState(params.get('payment_method') ?? '')
  const [txnType, setTxnType] = useState(params.get('txn_type') ?? '')
  const [isEssential, setIsEssential] = useState(params.get('is_essential') ?? '')
  const [weekday, setWeekday] = useState(params.get('weekday') ?? '')
  const [categoryLabel] = useState(params.get('category_label') ?? '')
  const [merchantLabel] = useState(params.get('merchant_label') ?? '')

  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const [bulkLoading, setBulkLoading] = useState(false)
  const queryClient = useQueryClient()

  const { data: accounts } = useQuery({ queryKey: ['accounts'], queryFn: accountService.list })
  const { data: allCategories } = useQuery({ queryKey: ['all-categories'], queryFn: categoryService.list })

  const hasDrilldown = Boolean(
    categoryId || merchantId || startDate || endDate || paymentMethod || txnType || isEssential || weekday,
  )
  const clearDrilldown = () => {
    setCategoryId(''); setMerchantId(''); setStartDate(''); setEndDate('')
    setPaymentMethod(''); setTxnType(''); setIsEssential(''); setWeekday('')
    setParams({})
  }

  const filters = {
    page, page_size: PAGE_SIZE, search: search || undefined, account_id: accountId || undefined,
    category_id: categoryId || undefined, merchant_id: merchantId || undefined,
    start_date: startDate || undefined, end_date: endDate || undefined,
    payment_method: paymentMethod || undefined, txn_type: txnType || undefined,
    is_essential: isEssential ? isEssential === 'true' : undefined,
    weekday: (weekday || undefined) as 'weekday' | 'weekend' | undefined,
  }
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

  const [savingCategoryId, setSavingCategoryId] = useState<string | null>(null)
  const changeCategory = async (transactionId: string, newCategoryId: string) => {
    setSavingCategoryId(transactionId)
    try {
      await transactionService.update(transactionId, { category_id: newCategoryId })
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['overview'] })
    } finally {
      setSavingCategoryId(null)
    }
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
        <input
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); setParams(e.target.value ? { search: e.target.value } : {}) }}
          placeholder="Search description…"
          className="rounded-lg border border-default bg-transparent px-3 py-1.5 text-sm outline-none w-56"
        />
      </div>

      <div className="surface rounded-xl p-3 flex flex-wrap items-center gap-2">
        <select value={accountId} onChange={(e) => { setAccountId(e.target.value); setPage(1) }} className={selectClass}>
          <option value="">All banks</option>
          {accounts?.map((a) => (
            <option key={a.id} value={a.id}>{a.bank_name} · {a.masked_account_number}</option>
          ))}
        </select>
        <select value={categoryId} onChange={(e) => { setCategoryId(e.target.value); setPage(1) }} className={selectClass}>
          <option value="">All categories</option>
          {allCategories?.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
        <select value={txnType} onChange={(e) => { setTxnType(e.target.value); setPage(1) }} className={selectClass}>
          <option value="">All types</option>
          {TRANSACTION_TYPES.map((t) => <option key={t} value={t}>{TXN_TYPE_LABELS[t]}</option>)}
        </select>
        <select value={paymentMethod} onChange={(e) => { setPaymentMethod(e.target.value); setPage(1) }} className={selectClass}>
          <option value="">All payment methods</option>
          {PAYMENT_METHODS.map((p) => <option key={p} value={p}>{PAYMENT_METHOD_LABELS[p]}</option>)}
        </select>
        <input type="date" value={startDate} onChange={(e) => { setStartDate(e.target.value); setPage(1) }} className={selectClass} />
        <span className="text-muted text-sm">to</span>
        <input type="date" value={endDate} onChange={(e) => { setEndDate(e.target.value); setPage(1) }} className={selectClass} />
        {hasDrilldown && <button onClick={clearDrilldown} className="ml-auto text-sm text-[color:var(--color-negative)]">Clear filters</button>}
      </div>

      {(categoryLabel || merchantLabel || isEssential || weekday) && (
        <div className="surface rounded-lg p-2 flex items-center gap-2 text-sm flex-wrap">
          <span className="text-muted">Filtered by:</span>
          {categoryId && categoryLabel && <span className="rounded-full bg-[color:var(--color-surface-2)] px-2.5 py-1">{categoryLabel}</span>}
          {merchantId && merchantLabel && <span className="rounded-full bg-[color:var(--color-surface-2)] px-2.5 py-1">{merchantLabel}</span>}
          {isEssential && <span className="rounded-full bg-[color:var(--color-surface-2)] px-2.5 py-1">{isEssential === 'true' ? 'Essential' : 'Discretionary'}</span>}
          {weekday && <span className="rounded-full bg-[color:var(--color-surface-2)] px-2.5 py-1 capitalize">{weekday}</span>}
        </div>
      )}

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
        <div className="md:hidden space-y-2">
          {data.data.map((t: Transaction) => (
            <div key={t.id} className={`surface rounded-xl p-3 ${t.is_excluded ? 'opacity-50' : ''}`}>
              <div className="flex items-center gap-3">
                <input type="checkbox" checked={selected.has(t.id)} onChange={() => toggle(t.id)} className="shrink-0" />
                <InitialsAvatar name={t.merchant || t.description} size={32} />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-medium">{t.merchant || t.description}</div>
                  <div className="text-xs text-muted flex items-center gap-1.5 flex-wrap mt-0.5">
                    <span className="whitespace-nowrap">{formatDate(t.transaction_date)}</span>
                    <BankTag name={t.bank_name} masked={t.account_masked} />
                  </div>
                </div>
                <div className="text-right shrink-0">
                  {t.debit > 0 && <div className="text-sm font-medium text-[color:var(--color-negative)]">-{formatCurrency(t.debit)}</div>}
                  {t.credit > 0 && <div className="text-sm font-medium text-[color:var(--color-positive)]">+{formatCurrency(t.credit)}</div>}
                  {t.balance != null && <div className="text-[11px] text-muted">Bal {formatCurrency(t.balance)}</div>}
                </div>
              </div>
              <select
                value={t.category_id ?? ''}
                disabled={savingCategoryId === t.id}
                onChange={(e) => changeCategory(t.id, e.target.value)}
                className="mt-2 w-full bg-transparent text-xs outline-none disabled:opacity-50 rounded-lg border border-default px-2 py-1.5"
                title="Change category"
              >
                {!t.category_id && <option value="">{t.category}</option>}
                {allCategories?.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
          ))}
        </div>
      )}

      {data && data.data.length > 0 && (
        <div className="hidden md:block surface rounded-xl overflow-x-auto">
          <table className="w-full text-sm min-w-[720px]">
            <thead className="text-muted text-xs uppercase border-b border-default">
              <tr>
                <th className="px-3 py-2"></th>
                <th className="text-left px-3 py-2 font-medium">Date</th>
                <th className="text-left px-3 py-2 font-medium">Description</th>
                <th className="text-left px-3 py-2 font-medium">Merchant</th>
                <th className="text-left px-3 py-2 font-medium">Category</th>
                <th className="text-left px-3 py-2 font-medium">Bank</th>
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
                    <select
                      value={t.category_id ?? ''}
                      disabled={savingCategoryId === t.id}
                      onChange={(e) => changeCategory(t.id, e.target.value)}
                      className="bg-transparent text-sm outline-none disabled:opacity-50 rounded border border-transparent hover:border-default focus:border-default px-1 py-0.5 -mx-1"
                      title="Change category"
                    >
                      {!t.category_id && <option value="">{t.category}</option>}
                      {allCategories?.map((c) => (
                        <option key={c.id} value={c.id}>{c.name}</option>
                      ))}
                    </select>
                  </td>
                  <td className="px-3 py-2">
                    <BankTag name={t.bank_name} masked={t.account_masked} />
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
