import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { reportService } from '@/services/reportService'
import { presetToRange } from '@/components/ui/DateRangePicker'
import { formatCurrency } from '@/lib/format'

export function ReportsPage() {
  const [reportType, setReportType] = useState('monthly')
  const [result, setResult] = useState<any>(null)

  const generateMutation = useMutation({
    mutationFn: () => {
      const range = presetToRange(reportType === 'annual' ? 'this_year' : 'this_month')
      return reportService.generate({ report_type: reportType, start_date: range.start, end_date: range.end, export_format: 'json' })
    },
    onSuccess: (data) => setResult(data.data),
  })

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Reports</h1>
      <div className="surface rounded-xl p-4 flex flex-wrap items-end gap-3">
        <div>
          <label className="text-xs text-muted block mb-1">Report Type</label>
          <select value={reportType} onChange={(e) => setReportType(e.target.value)} className="rounded-lg border border-default bg-transparent px-3 py-1.5 text-sm">
            <option value="monthly">Monthly Financial Report</option>
            <option value="annual">Annual Financial Report</option>
            <option value="expenses">Expense Analysis</option>
            <option value="income">Income Analysis</option>
          </select>
        </div>
        <button
          onClick={() => generateMutation.mutate()}
          disabled={generateMutation.isPending}
          className="rounded-lg bg-[color:var(--color-accent)] text-[color:var(--color-accent-fg)] px-4 py-1.5 text-sm disabled:opacity-50"
        >
          {generateMutation.isPending ? 'Generating…' : 'Generate Report'}
        </button>
      </div>

      {result && (
        <div className="surface rounded-xl p-5 space-y-4">
          <h2 className="font-semibold">Report: {result.period.start} → {result.period.end}</h2>
          <dl className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
            <div><dt className="text-muted">Income</dt><dd className="font-medium">{formatCurrency(result.overview.total_income)}</dd></div>
            <div><dt className="text-muted">Expenses</dt><dd className="font-medium">{formatCurrency(result.overview.total_expenses)}</dd></div>
            <div><dt className="text-muted">Net Cash Flow</dt><dd className="font-medium">{formatCurrency(result.overview.net_cash_flow)}</dd></div>
            <div><dt className="text-muted">Savings Rate</dt><dd className="font-medium">{result.overview.savings_rate}%</dd></div>
          </dl>
          <div>
            <h3 className="text-sm font-semibold mb-2">Top Categories</h3>
            <div className="space-y-1 text-sm">
              {result.top_categories.map((c: any) => (
                <div key={c.category} className="flex justify-between"><span>{c.category}</span><span>{formatCurrency(c.total)}</span></div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
