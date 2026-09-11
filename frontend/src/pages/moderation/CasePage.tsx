import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ApiError, moderation } from '../../api/client'
import { HighlightedText } from '../../components/HighlightedText'
import { SeverityBadge } from '../../components/PostingStatusBadge'
import type { CasePosting, Flag } from '../../types'

const CLAIM_RENEW_MS = 3 * 60 * 1000 // TTL is 10 minutes server-side; renew well before it lapses

const ACTIONS: { value: string; label: string; style: string }[] = [
  { value: 'APPROVE', label: 'Approve', style: 'bg-emerald-600 hover:bg-emerald-700' },
  { value: 'REJECT', label: 'Reject', style: 'bg-red-600 hover:bg-red-700' },
  { value: 'REQUEST_CHANGES', label: 'Request changes', style: 'bg-amber-600 hover:bg-amber-700' },
  { value: 'ESCALATE', label: 'Escalate', style: 'bg-slate-600 hover:bg-slate-700' },
]

export function CasePage() {
  const { id } = useParams<{ id: string }>()
  const postingId = Number(id)
  const navigate = useNavigate()

  const [posting, setPosting] = useState<CasePosting | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [claimError, setClaimError] = useState<string | null>(null)
  const [activeFlagId, setActiveFlagId] = useState<number | null>(null)
  const [action, setAction] = useState('APPROVE')
  const [reasonCode, setReasonCode] = useState('')
  const [notes, setNotes] = useState('')
  const [deciding, setDeciding] = useState(false)
  const claimedRef = useRef(false)

  function load() {
    moderation
      .caseDetail(postingId)
      .then(setPosting)
      .catch(() => setError('Could not load this case.'))
  }

  useEffect(() => {
    load()

    moderation
      .claim(postingId)
      .then(() => {
        claimedRef.current = true
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 409) {
          setClaimError('This case is already claimed by another moderator.')
        }
      })

    const renewInterval = setInterval(() => {
      moderation.claim(postingId).catch(() => {})
    }, CLAIM_RENEW_MS)

    return () => {
      clearInterval(renewInterval)
      if (claimedRef.current) moderation.release(postingId).catch(() => {})
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [postingId])

  async function handleDecide() {
    setDeciding(true)
    try {
      await moderation.decide(postingId, action, reasonCode, notes)
      navigate('/moderation')
    } catch {
      setError('Could not submit this decision. Please try again.')
    } finally {
      setDeciding(false)
    }
  }

  async function handleFalsePositive(flag: Flag) {
    await moderation.markFalsePositive(flag.id)
    load()
  }

  if (error) return <p className="text-sm text-red-600">{error}</p>
  if (!posting) return <p className="text-sm text-slate-500">Loading…</p>

  const latestRun = posting.runs[0]
  const combinedText = `${posting.title}\n${posting.description}`
  const evidenceSpans = (latestRun?.flags ?? []).flatMap((flag) =>
    flag.evidence
      .filter((e) => e.end > e.start)
      .map((e) => ({ start: e.start, end: e.end, severity: flag.severity, id: flag.id })),
  )

  return (
    <div>
      <button onClick={() => navigate('/moderation')} className="mb-4 text-sm text-slate-500 hover:text-slate-800">
        ← Back to queue
      </button>

      {claimError && (
        <div className="mb-4 rounded-md bg-amber-50 px-4 py-3 text-sm text-amber-900">{claimError}</div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Pane 1: the posting */}
        <div className="lg:col-span-1 lg:order-1">
          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <h1 className="text-lg font-semibold text-slate-900">{posting.title}</h1>
            <p className="mb-3 text-sm text-slate-500">
              {posting.company_name} · {posting.location || 'no location given'} · v{posting.version}
            </p>
            <dl className="mb-4 grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-slate-500">
              <dt>Submitter</dt>
              <dd className="text-slate-800">{posting.submitter}</dd>
              <dt>Salary</dt>
              <dd className="text-slate-800">
                {posting.salary_disclosed && posting.salary_min && posting.salary_max
                  ? `${posting.currency} ${posting.salary_min}–${posting.salary_max}`
                  : 'Not disclosed'}
              </dd>
              <dt>Apply URL</dt>
              <dd className="truncate text-slate-800">{posting.apply_url || '—'}</dd>
              <dt>Contact</dt>
              <dd className="truncate text-slate-800">{posting.contact_email || '—'}</dd>
            </dl>
            <HighlightedText text={combinedText} spans={evidenceSpans} activeId={activeFlagId} />
          </div>
        </div>

        {/* Pane 2: flags */}
        <div className="lg:col-span-1 lg:order-2">
          <h2 className="mb-2 text-sm font-semibold text-slate-900">
            Flags {latestRun && `(risk score ${latestRun.risk_score?.toFixed(2) ?? '—'})`}
          </h2>
          <div className="space-y-3">
            {latestRun?.flags.length === 0 && (
              <p className="text-sm text-slate-500">No flags on this run.</p>
            )}
            {latestRun?.flags.map((flag) => (
              <button
                key={flag.id}
                onClick={() => {
                  setActiveFlagId(flag.id)
                  document.getElementById(`evidence-${flag.id}`)?.scrollIntoView({ block: 'center' })
                }}
                className={`block w-full rounded-lg border p-3 text-left text-sm ${
                  activeFlagId === flag.id ? 'border-slate-400 bg-slate-50' : 'border-slate-200 bg-white'
                } ${flag.is_false_positive ? 'opacity-50' : ''}`}
              >
                <div className="mb-1 flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <SeverityBadge severity={flag.severity} />
                    <span className="text-xs font-medium text-slate-700">
                      {flag.category.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <span className="text-xs text-slate-400">{flag.source}</span>
                </div>
                <p className="text-slate-700">{flag.reason}</p>
                <p className="mt-1 text-xs text-slate-400">confidence {flag.confidence.toFixed(2)}</p>
                {flag.contributing_terms.length > 0 && (
                  <p className="mt-1 text-xs text-slate-400">
                    top terms: {flag.contributing_terms.map((t) => t.term).join(', ')}
                  </p>
                )}
                <span
                  role="button"
                  onClick={(e) => {
                    e.stopPropagation()
                    handleFalsePositive(flag)
                  }}
                  className="mt-2 inline-block text-xs text-slate-400 underline hover:text-slate-700"
                >
                  {flag.is_false_positive ? 'Marked false positive' : 'Mark false positive'}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Pane 3: decision */}
        <div className="lg:col-span-1 lg:order-3">
          <h2 className="mb-2 text-sm font-semibold text-slate-900">Decision</h2>
          <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-4">
            <div className="grid grid-cols-2 gap-2">
              {ACTIONS.map((a) => (
                <button
                  key={a.value}
                  onClick={() => setAction(a.value)}
                  className={`rounded-md px-3 py-2 text-sm font-medium text-white ${a.style} ${
                    action === a.value ? 'ring-2 ring-offset-2 ring-slate-400' : 'opacity-70'
                  }`}
                >
                  {a.label}
                </button>
              ))}
            </div>
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-slate-700">Reason code</span>
              <input className="input" value={reasonCode} onChange={(e) => setReasonCode(e.target.value)} />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-slate-700">Notes</span>
              <textarea
                rows={4}
                className="input"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Shown to the submitter if you request changes."
              />
            </label>
            <button
              onClick={handleDecide}
              disabled={deciding}
              className="w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
            >
              {deciding ? 'Submitting…' : `Submit: ${ACTIONS.find((a) => a.value === action)?.label}`}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
