import { Check } from 'lucide-react'

const STEPS = ['Upload', 'Extract', 'Validate', 'Categorize', 'Complete']

export function ProcessingStepper({ activeIndex, failed }: { activeIndex: number; failed?: boolean }) {
  return (
    <div className="flex items-center">
      {STEPS.map((step, i) => {
        const done = i < activeIndex
        const active = i === activeIndex
        return (
          <div key={step} className="flex items-center flex-1 last:flex-none">
            <div className="flex flex-col items-center gap-1">
              <div
                className={`h-6 w-6 rounded-full flex items-center justify-center text-[10px] font-semibold border-2 shrink-0 ${
                  failed && active
                    ? 'border-[color:var(--color-negative)] text-[color:var(--color-negative)]'
                    : done
                    ? 'bg-[color:var(--color-positive)] border-[color:var(--color-positive)] text-white'
                    : active
                    ? 'border-[color:var(--color-accent)] text-[color:var(--color-accent)]'
                    : 'border-default text-muted'
                }`}
              >
                {done ? <Check size={13} /> : i + 1}
              </div>
              <span className={`text-[10px] ${active || done ? '' : 'text-muted'}`}>{step}</span>
            </div>
            {i < STEPS.length - 1 && (
              <div className={`h-0.5 flex-1 mx-1 mb-4 ${done ? 'bg-[color:var(--color-positive)]' : 'bg-[color:var(--color-border)]'}`} />
            )}
          </div>
        )
      })}
    </div>
  )
}

export function jobStatusToStepIndex(status: string): number {
  const map: Record<string, number> = {
    QUEUED: 0, UPLOADING: 0,
    EXTRACTING: 1, NORMALIZING: 1,
    VALIDATING: 2, CHECKING_DUPLICATES: 2,
    CATEGORIZING: 3, SAVING: 3,
    NEEDS_REVIEW: 4, COMPLETED: 4, DUPLICATE: 4, OVERLAP_DETECTED: 4,
  }
  return map[status] ?? 0
}
