import { useCallback, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, FileText, Loader2, Lock, Trash2, UploadCloud, XCircle } from 'lucide-react'
import { statementService } from '@/services/statementService'
import { LoadingState, EmptyState } from '@/components/ui/States'
import { ProcessingStepper, jobStatusToStepIndex } from '@/components/ui/Stepper'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { BankTag } from '@/components/ui/Badges'
import { formatCurrency, formatDate } from '@/lib/format'
import type { ApiError } from '@/services/apiClient'

const SUPPORTED = ['PDF', 'CSV', 'XLS', 'XLSX', 'TXT', 'HTML', 'PNG', 'JPG']

type UploadState = 'idle' | 'uploading' | 'processing' | 'completed' | 'failed'

interface ActiveUpload {
  id: string
  file: File
  jobId?: string
  state: UploadState
  statementId?: string
  error?: string
  errorCode?: string | null
  jobStatus?: string
  passwordInput?: string
  passwordSubmitting?: boolean
}

const PASSWORD_CODES = ['PDF_PASSWORD_REQUIRED', 'PDF_PASSWORD_INCORRECT']

export function StatementsPage() {
  const queryClient = useQueryClient()
  const [uploads, setUploads] = useState<ActiveUpload[]>([])
  const [reviewingId, setReviewingId] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragOver, setDragOver] = useState(false)

  const { data: statements, isLoading } = useQuery({ queryKey: ['statements'], queryFn: statementService.list })
  const [pendingDelete, setPendingDelete] = useState<{ id: string; filename: string } | null>(null)

  const uploadMutation = useMutation<{ job_id: string; status: string }, ApiError, File>({
    mutationFn: (file: File) => statementService.upload(file),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => statementService.remove(id),
    onSuccess: () => {
      // Deleting a statement changes transactions, account balances, and every derived
      // analytics figure -- invalidate everything rather than trying to enumerate query keys.
      queryClient.invalidateQueries()
      setPendingDelete(null)
    },
  })

  const pollJob = useCallback((id: string, jobId: string) => {
    const interval = setInterval(async () => {
      try {
        const job = await statementService.getJob(jobId)
        if (job.status === 'FAILED') {
          clearInterval(interval)
          setUploads((prev) => prev.map((u) => (u.id === id ? {
            ...u, state: 'failed', error: job.error_message ?? undefined, errorCode: job.error_code, jobStatus: job.status, passwordSubmitting: false,
          } : u)))
        } else if (['NEEDS_REVIEW', 'COMPLETED', 'DUPLICATE', 'OVERLAP_DETECTED'].includes(job.status)) {
          clearInterval(interval)
          setUploads((prev) => prev.map((u) => (u.id === id ? { ...u, state: 'completed', statementId: job.statement_id ?? undefined, jobStatus: job.status } : u)))
          queryClient.invalidateQueries({ queryKey: ['statements'] })
        } else {
          setUploads((prev) => prev.map((u) => (u.id === id ? { ...u, jobStatus: job.status } : u)))
        }
      } catch {
        clearInterval(interval)
      }
    }, 1500)
  }, [queryClient])

  const submitPassword = async (id: string) => {
    const upload = uploads.find((u) => u.id === id)
    if (!upload?.jobId || !upload.passwordInput) return
    setUploads((prev) => prev.map((u) => (u.id === id ? { ...u, passwordSubmitting: true } : u)))
    try {
      await statementService.retryJobWithPassword(upload.jobId, upload.passwordInput)
      setUploads((prev) => prev.map((u) => (u.id === id ? { ...u, state: 'processing', error: undefined, errorCode: undefined } : u)))
      pollJob(id, upload.jobId)
    } catch (err) {
      setUploads((prev) => prev.map((u) => (u.id === id ? { ...u, passwordSubmitting: false, error: (err as ApiError).message } : u)))
    }
  }

  const handleFiles = (files: FileList | null) => {
    if (!files) return
    Array.from(files).forEach((file) => {
      const id = crypto.randomUUID()
      setUploads((prev) => [...prev, { id, file, state: 'uploading' }])
      uploadMutation.mutate(file, {
        onSuccess: (res) => {
          setUploads((prev) => prev.map((u) => (u.id === id ? { ...u, state: 'processing', jobId: res.job_id } : u)))
          pollJob(id, res.job_id)
        },
        onError: (err) => {
          setUploads((prev) => prev.map((u) => (u.id === id ? { ...u, state: 'failed', error: err.message } : u)))
        },
      })
    })
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Upload Bank Statement</h1>
        <p className="text-sm text-muted mt-0.5">Upload your statement in any supported format. We'll take care of the rest.</p>
      </div>

      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFiles(e.dataTransfer.files) }}
        onClick={() => inputRef.current?.click()}
        className={`surface rounded-2xl border-2 border-dashed p-10 flex flex-col items-center justify-center text-center cursor-pointer transition-colors ${
          dragOver ? 'border-[color:var(--color-accent)]' : 'border-default'
        }`}
      >
        <UploadCloud size={32} className="text-muted mb-3" />
        <p className="font-medium">Drag & drop your statement here, or click to browse</p>
        <p className="text-sm text-muted mt-1">Multiple files supported</p>
        <div className="flex flex-wrap gap-2 justify-center mt-4">
          {SUPPORTED.map((f) => (
            <span key={f} className="text-xs px-2 py-1 rounded-md surface-2 border border-default">{f}</span>
          ))}
        </div>
        <input
          ref={inputRef} type="file" multiple hidden
          accept=".pdf,.csv,.xls,.xlsx,.txt,.html,.png,.jpg,.jpeg"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      {uploads.length > 0 && (
        <div className="space-y-3">
          {uploads.map((u) => (
            <div key={u.id} className="surface rounded-xl p-4 flex flex-col gap-4">
              <div className="flex items-center gap-3">
                <FileText size={18} className="text-muted shrink-0" />
                <span className="text-sm flex-1 truncate">{u.file.name}</span>
                <UploadStatus state={u.state} error={u.error} errorCode={u.errorCode} />
                {u.state === 'completed' && u.statementId && (
                  <button
                    onClick={() => setReviewingId(u.statementId!)}
                    className="text-sm text-[color:var(--color-accent)] font-medium"
                  >
                    Review
                  </button>
                )}
              </div>
              {u.state !== 'failed' && (
                <ProcessingStepper activeIndex={jobStatusToStepIndex(u.jobStatus ?? 'QUEUED')} />
              )}
              {u.state === 'failed' && !PASSWORD_CODES.includes(u.errorCode ?? '') && (
                <ProcessingStepper activeIndex={jobStatusToStepIndex(u.jobStatus ?? 'QUEUED')} failed />
              )}
              {u.state === 'failed' && PASSWORD_CODES.includes(u.errorCode ?? '') && (
                <form
                  onSubmit={(e) => { e.preventDefault(); submitPassword(u.id) }}
                  className="flex items-center gap-2"
                >
                  <Lock size={14} className="text-muted shrink-0" />
                  <input
                    type="password"
                    autoFocus
                    placeholder="Enter PDF password"
                    value={u.passwordInput ?? ''}
                    onChange={(e) => setUploads((prev) => prev.map((row) => (row.id === u.id ? { ...row, passwordInput: e.target.value } : row)))}
                    className="flex-1 rounded-lg border border-default bg-transparent px-3 py-1.5 text-sm outline-none focus:border-[color:var(--color-accent)]"
                  />
                  <button
                    type="submit"
                    disabled={!u.passwordInput || u.passwordSubmitting}
                    className="rounded-lg bg-[color:var(--color-accent)] text-[color:var(--color-accent-fg)] px-3 py-1.5 text-sm font-medium disabled:opacity-50"
                  >
                    {u.passwordSubmitting ? 'Unlocking…' : 'Unlock'}
                  </button>
                </form>
              )}
              {u.state === 'failed' && u.errorCode === 'PDF_PASSWORD_INCORRECT' && (
                <p className="text-xs text-[color:var(--color-negative)] -mt-2">Incorrect password — please try again.</p>
              )}
            </div>
          ))}
        </div>
      )}

      <div>
        <h2 className="text-sm font-semibold mb-3">Upload History</h2>
        {isLoading && <LoadingState />}
        {statements && statements.length === 0 && <EmptyState title="No statements uploaded yet." />}
        {statements && statements.length > 0 && (
          <div className="md:hidden space-y-2">
            {statements.map((s: any) => (
              <div key={s.id} className="surface rounded-xl p-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-medium truncate">{s.original_filename}</div>
                    <div className="text-xs text-muted mt-1 flex items-center gap-1.5 flex-wrap">
                      <BankTag name={s.detected_bank} />
                      <span>{s.period_start} → {s.period_end}</span>
                    </div>
                  </div>
                  <button
                    onClick={() => setPendingDelete({ id: s.id, filename: s.original_filename })}
                    className="text-muted hover:text-[color:var(--color-negative)] shrink-0"
                    aria-label={`Delete ${s.original_filename}`}
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
                <div className="flex items-center justify-between mt-2.5 text-xs">
                  <div className="flex items-center gap-2">
                    <StatusBadge status={s.status} />
                    <span className="text-muted">{s.transaction_count} txns · {formatDate(s.created_at)}</span>
                  </div>
                  {(s.status === 'NEEDS_REVIEW' || s.status === 'DUPLICATE' || s.status === 'OVERLAP_DETECTED') && (
                    <button className="text-[color:var(--color-accent)] font-medium" onClick={() => setReviewingId(s.id)}>Review</button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
        {statements && statements.length > 0 && (
          <div className="hidden md:block surface rounded-xl overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-muted text-xs uppercase border-b border-default">
                <tr>
                  <th className="text-left px-4 py-2 font-medium">File</th>
                  <th className="text-left px-4 py-2 font-medium">Bank</th>
                  <th className="text-left px-4 py-2 font-medium">Period</th>
                  <th className="text-left px-4 py-2 font-medium">Transactions</th>
                  <th className="text-left px-4 py-2 font-medium">Status</th>
                  <th className="text-left px-4 py-2 font-medium">Uploaded</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {statements.map((s: any) => (
                  <tr key={s.id} className="border-b border-default last:border-0">
                    <td className="px-4 py-2 truncate max-w-[180px]">{s.original_filename}</td>
                    <td className="px-4 py-2"><BankTag name={s.detected_bank} /></td>
                    <td className="px-4 py-2 whitespace-nowrap">{s.period_start} → {s.period_end}</td>
                    <td className="px-4 py-2">{s.transaction_count}</td>
                    <td className="px-4 py-2"><StatusBadge status={s.status} /></td>
                    <td className="px-4 py-2 whitespace-nowrap">{formatDate(s.created_at)}</td>
                    <td className="px-4 py-2 text-right">
                      <div className="flex items-center justify-end gap-3">
                        {(s.status === 'NEEDS_REVIEW' || s.status === 'DUPLICATE' || s.status === 'OVERLAP_DETECTED') && (
                          <button className="text-[color:var(--color-accent)] font-medium" onClick={() => setReviewingId(s.id)}>Review</button>
                        )}
                        <button
                          onClick={() => setPendingDelete({ id: s.id, filename: s.original_filename })}
                          className="text-muted hover:text-[color:var(--color-negative)]"
                          aria-label={`Delete ${s.original_filename}`}
                        >
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {reviewingId && <StatementReviewModal statementId={reviewingId} onClose={() => setReviewingId(null)} />}

      <ConfirmDialog
        open={!!pendingDelete}
        title={`Delete ${pendingDelete?.filename}?`}
        description="This permanently deletes this statement and every transaction imported from it. Account balances and analytics will be recalculated. This cannot be undone."
        confirmLabel="Delete Statement"
        loading={deleteMutation.isPending}
        onConfirm={() => pendingDelete && deleteMutation.mutate(pendingDelete.id)}
        onCancel={() => setPendingDelete(null)}
      />
    </div>
  )
}

function UploadStatus({ state, error, errorCode }: { state: UploadState; error?: string; errorCode?: string | null }) {
  if (state === 'uploading' || state === 'processing') {
    return <span className="flex items-center gap-1 text-xs text-muted"><Loader2 size={14} className="animate-spin" /> {state === 'uploading' ? 'Uploading' : 'Processing'}</span>
  }
  if (state === 'completed') return <span className="flex items-center gap-1 text-xs text-[color:var(--color-positive)]"><CheckCircle2 size={14} /> Ready for review</span>
  if (state === 'failed' && PASSWORD_CODES.includes(errorCode ?? '')) {
    return <span className="flex items-center gap-1 text-xs text-[color:var(--color-warning)]"><Lock size={14} /> Password protected</span>
  }
  if (state === 'failed') return <span className="flex items-center gap-1 text-xs text-[color:var(--color-negative)]" title={error}><XCircle size={14} /> Failed</span>
  return null
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    PROCESSED: 'text-[color:var(--color-positive)]',
    NEEDS_REVIEW: 'text-[color:var(--color-warning)]',
    DUPLICATE: 'text-[color:var(--color-negative)]',
    OVERLAP_DETECTED: 'text-[color:var(--color-negative)]',
    FAILED: 'text-[color:var(--color-negative)]',
    PROCESSING: 'text-muted',
  }
  return <span className={`text-xs font-medium ${map[status] ?? 'text-muted'}`}>{status.replace('_', ' ')}</span>
}

function StatementReviewModal({ statementId, onClose }: { statementId: string; onClose: () => void }) {
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['statement', statementId], queryFn: () => statementService.get(statementId) })

  const confirmMutation = useMutation({
    mutationFn: () => statementService.confirm(statementId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['statements'] })
      queryClient.invalidateQueries({ queryKey: ['overview'] })
      onClose()
    },
  })
  const cancelMutation = useMutation({
    mutationFn: () => statementService.cancel(statementId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['statements'] })
      onClose()
    },
  })

  const isCriticalDuplicate = data?.status === 'DUPLICATE'

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="surface rounded-2xl max-w-lg w-full p-6 max-h-[85vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-lg font-semibold mb-4">Statement Review</h2>
        {isLoading && <LoadingState />}
        {data && (
          <div className="space-y-4">
            <dl className="grid grid-cols-2 gap-y-3 text-sm">
              <dt className="text-muted">Bank</dt><dd>{data.detected_bank}</dd>
              <dt className="text-muted">Period</dt><dd>{data.period_start} → {data.period_end}</dd>
              <dt className="text-muted">Transactions</dt><dd>{data.transaction_count}</dd>
              <dt className="text-muted">Income</dt><dd>{formatCurrency(data.total_income)}</dd>
              <dt className="text-muted">Expenses</dt><dd>{formatCurrency(data.total_expenses)}</dd>
              <dt className="text-muted">Potential Duplicates</dt><dd>{data.duplicate_count}</dd>
              <dt className="text-muted">Period Overlap</dt><dd className="capitalize">{data.overlap_type.replace('_', ' ')}</dd>
              <dt className="text-muted">Warnings</dt><dd>{data.warnings?.length ?? 0}</dd>
            </dl>

            {data.overlap_type !== 'none' && (
              <div className="rounded-lg bg-[color:var(--color-warning)]/10 border border-[color:var(--color-warning)]/30 p-3 text-sm">
                {isCriticalDuplicate
                  ? 'This is an exact duplicate of an existing statement and cannot be imported.'
                  : 'This statement overlaps with existing data. Exact-duplicate transactions will be skipped automatically; likely duplicates are imported but excluded from analytics until you confirm them.'}
              </div>
            )}

            {data.warnings?.length > 0 && (
              <ul className="text-xs text-muted list-disc pl-4 space-y-1 max-h-32 overflow-y-auto">
                {data.warnings.map((w: string, i: number) => <li key={i}>{w}</li>)}
              </ul>
            )}

            <div className="flex gap-2 justify-end pt-2">
              <button onClick={() => cancelMutation.mutate()} className="px-4 py-2 rounded-lg border border-default text-sm">Cancel Import</button>
              <button
                disabled={isCriticalDuplicate || data.status === 'PROCESSED' || confirmMutation.isPending}
                onClick={() => confirmMutation.mutate()}
                className="px-4 py-2 rounded-lg bg-[color:var(--color-accent)] text-[color:var(--color-accent-fg)] text-sm font-medium disabled:opacity-50"
              >
                {data.status === 'PROCESSED' ? 'Already Imported' : confirmMutation.isPending ? 'Importing…' : 'Import Data'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
