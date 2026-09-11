import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { postings } from '../../api/client'
import { HighlightedText } from '../../components/HighlightedText'
import { PostingForm } from '../../components/PostingForm'
import { PostingStatusBadge, SeverityBadge } from '../../components/PostingStatusBadge'
import type { JobPosting, JobPostingInput } from '../../types'

export function PostingDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [posting, setPosting] = useState<JobPosting | null>(null)
  const [error, setError] = useState<string | null>(null)

  function load() {
    if (!id) return
    postings
      .retrieve(Number(id))
      .then(setPosting)
      .catch(() => setError('Could not load this posting.'))
  }

  useEffect(load, [id])

  if (error) return <p className="text-sm text-red-600">{error}</p>
  if (!posting) return <p className="text-sm text-slate-500">Loading…</p>

  const combinedText = `${posting.title}\n${posting.description}`

  async function handleResubmit(values: JobPostingInput) {
    if (!id) return
    const updated = await postings.update(Number(id), values)
    setPosting(updated)
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <button onClick={() => navigate('/postings')} className="text-sm text-slate-500 hover:text-slate-800">
        ← Back to my postings
      </button>

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">{posting.title}</h1>
          <p className="text-sm text-slate-500">
            {posting.company_name} · v{posting.version}
          </p>
        </div>
        <PostingStatusBadge status={posting.status} />
      </div>

      {posting.status === 'PENDING' && (
        <div className="rounded-md bg-slate-100 px-4 py-3 text-sm text-slate-600">
          Your posting is being analyzed. This usually takes just a few seconds — refresh to
          check again.
        </div>
      )}

      {posting.latest_decision && (
        <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <p className="font-medium">A moderator requested changes.</p>
          {posting.latest_decision.notes && <p className="mt-1">{posting.latest_decision.notes}</p>}
        </div>
      )}

      {posting.review_summary && posting.review_summary.length > 0 && (
        <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold text-slate-900">Why this was flagged</h2>
          {posting.review_summary.map((item, i) => (
            <div key={i} className="border-t border-slate-100 pt-3 first:border-t-0 first:pt-0">
              <div className="mb-1 flex items-center gap-2">
                <SeverityBadge severity={item.severity} />
                <span className="text-xs font-medium text-slate-500">
                  {item.category.replace(/_/g, ' ')}
                </span>
              </div>
              <p className="text-sm text-slate-700">{item.reason}</p>
              {item.evidence.length > 0 && (
                <div className="mt-2 rounded bg-slate-50 p-2">
                  <HighlightedText text={combinedText} spans={item.evidence} />
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {posting.status === 'CHANGES_REQUESTED' ? (
        <div>
          <h2 className="mb-3 text-sm font-semibold text-slate-900">Edit and resubmit</h2>
          <PostingForm initialValues={posting} onSubmit={handleResubmit} submitLabel="Resubmit for review" />
        </div>
      ) : (
        <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-700">
          <p className="whitespace-pre-wrap">{posting.description}</p>
        </div>
      )}
    </div>
  )
}
