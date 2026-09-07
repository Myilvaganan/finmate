import { useState, useRef, useEffect } from 'react'
import { Send, Sparkles } from 'lucide-react'
import { chatService } from '@/services/chatService'
import { ChatDataCard } from '@/components/ui/ChatDataCard'

const SUGGESTED = [
  'How much did I spend this month?',
  'What are my top 5 expense categories?',
  'Compare this month with last month.',
  'Show my recurring payments.',
  'What were my biggest transactions?',
  'How much did I save this year?',
]

interface Message {
  role: 'user' | 'assistant'
  content: string
  factType?: string
  structuredData?: Record<string, unknown>
}

export function AIAssistantPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [sessionId, setSessionId] = useState<string | undefined>()
  const [loading, setLoading] = useState(false)
  const [aiAvailable, setAiAvailable] = useState(true)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, loading])

  const send = async (question: string) => {
    if (!question.trim() || loading) return
    setMessages((prev) => [...prev, { role: 'user', content: question }])
    setInput('')
    setLoading(true)
    try {
      const res = await chatService.ask(question, sessionId)
      setSessionId(res.session_id)
      setAiAvailable(res.ai_available)
      setMessages((prev) => [...prev, { role: 'assistant', content: res.answer, factType: res.fact_type, structuredData: res.structured_data }])
    } catch {
      setMessages((prev) => [...prev, { role: 'assistant', content: 'Something went wrong answering that. Please try again.' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] md:h-[calc(100vh-6rem)] max-w-3xl mx-auto w-full">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold flex items-center gap-2">
            <span className="h-8 w-8 rounded-lg bg-[color:var(--color-accent)]/10 text-[color:var(--color-accent)] flex items-center justify-center">
              <Sparkles size={17} />
            </span>
            AI Financial Assistant
          </h1>
          <p className="text-sm text-muted mt-0.5">Ask questions about your money.</p>
        </div>
        <span className={`text-[10px] uppercase tracking-wide px-2 py-1 rounded-full font-medium ${
          aiAvailable ? 'bg-[color:var(--color-positive)]/10 text-[color:var(--color-positive)]' : 'bg-[color:var(--color-warning)]/10 text-[color:var(--color-warning)]'
        }`}>
          {aiAvailable ? 'AI Connected' : 'Grounded mode'}
        </span>
      </div>

      <div className="flex-1 overflow-y-auto surface rounded-xl p-4 space-y-4">
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center gap-3 text-center text-muted">
            <Sparkles size={28} className="text-[color:var(--color-accent)]" />
            <p className="text-sm">Ask anything about your income, spending, or savings.</p>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm ${
              m.role === 'user' ? 'bg-[color:var(--color-accent)] text-[color:var(--color-accent-fg)]' : 'surface-2 border border-default'
            }`}>
              {m.factType && m.role === 'assistant' && (
                <div className="text-[10px] uppercase tracking-wide opacity-60 mb-1 font-semibold">{m.factType}</div>
              )}
              {m.content}
              {m.role === 'assistant' && m.structuredData && <ChatDataCard data={m.structuredData} />}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="surface-2 border border-default rounded-2xl px-4 py-2.5 text-sm text-muted flex gap-1 items-center">
              <span className="h-1.5 w-1.5 rounded-full bg-current animate-bounce [animation-delay:-0.3s]" />
              <span className="h-1.5 w-1.5 rounded-full bg-current animate-bounce [animation-delay:-0.15s]" />
              <span className="h-1.5 w-1.5 rounded-full bg-current animate-bounce" />
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {SUGGESTED.map((q) => (
          <button
            key={q} onClick={() => send(q)} disabled={loading}
            className="text-xs px-3 py-1.5 rounded-full border border-default hover:bg-[color:var(--color-surface-2)] disabled:opacity-50"
          >
            {q}
          </button>
        ))}
      </div>

      <form
        onSubmit={(e) => { e.preventDefault(); send(input) }}
        className="mt-3 flex items-center gap-2 surface rounded-xl p-2"
      >
        <input
          value={input} onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about your spending, income, or savings…"
          className="flex-1 bg-transparent outline-none text-sm px-2"
        />
        <button type="submit" disabled={loading} className="p-2 rounded-lg bg-[color:var(--color-accent)] text-[color:var(--color-accent-fg)] disabled:opacity-50">
          <Send size={16} />
        </button>
      </form>
      <p className="text-[11px] text-muted mt-2 text-center">
        FinMate provides insights based on your transaction data and is not a substitute for professional financial advice.
      </p>
    </div>
  )
}
