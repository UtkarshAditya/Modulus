import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { postings } from '../../api/client'
import { HighlightedText } from '../../components/HighlightedText'
import { PostingForm } from '../../components/PostingForm'
import { PostingStatusBadge, SeverityBadge } from '../../components/PostingStatusBadge'
import type { JobPosting, JobPostingInput } from '../../types'
import '../../styles/modulus.css'

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

  if (error) return <div className="m-error-banner">{error}</div>
  if (!posting) return <p className="m-loading">Loading…</p>

  const combinedText = `${posting.title}\n${posting.description}`

  async function handleResubmit(values: JobPostingInput) {
    if (!id) return
    const updated = await postings.update(Number(id), values)
    setPosting(updated)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <button
        onClick={() => navigate('/postings')}
        style={{
          alignSelf: 'flex-start',
          background: 'none',
          border: 'none',
          padding: 0,
          font: 'inherit',
          fontSize: '.88rem',
          color: 'var(--m-text-muted)',
          cursor: 'pointer',
        }}
      >
        ← Back to my postings
      </button>

      <div className="m-page-header">
        <div>
          <h1>{posting.title}</h1>
          <p className="m-page-sub" style={{ marginTop: 4 }}>
            {posting.company_name} · v{posting.version}
          </p>
        </div>
        <PostingStatusBadge status={posting.status} />
      </div>

      {posting.status === 'PENDING' && (
        <div className="m-banner">
          Your posting is being analyzed. This usually takes just a few seconds — refresh to
          check again.
        </div>
      )}

      {posting.latest_decision && (
        <div className="m-banner" data-tone="signal">
          <p style={{ fontWeight: 600 }}>A moderator requested changes.</p>
          {posting.latest_decision.notes && <p>{posting.latest_decision.notes}</p>}
        </div>
      )}

      {posting.review_summary && posting.review_summary.length > 0 && (
        <div className="m-card" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <h2>Why this was flagged</h2>
          {posting.review_summary.map((item, i) => (
            <div
              key={i}
              style={{
                paddingTop: i === 0 ? 0 : 14,
                borderTop: i === 0 ? 'none' : '1px solid var(--m-border)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                <SeverityBadge severity={item.severity} />
                <span
                  style={{
                    fontFamily: 'var(--m-font-mono)',
                    fontSize: '.72rem',
                    color: 'var(--m-text-faint)',
                    textTransform: 'uppercase',
                    letterSpacing: '.06em',
                  }}
                >
                  {item.category.replace(/_/g, ' ')}
                </span>
              </div>
              <p style={{ fontSize: '.92rem' }}>{item.reason}</p>
              {item.evidence.length > 0 && (
                <div style={{ marginTop: 8, background: 'var(--m-panel-2)', borderRadius: 3, padding: 8 }}>
                  <HighlightedText text={combinedText} spans={item.evidence} />
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {posting.status === 'CHANGES_REQUESTED' ? (
        <div>
          <h2 style={{ fontSize: '.95rem', fontWeight: 700, marginBottom: 14 }}>Edit and resubmit</h2>
          <PostingForm initialValues={posting} onSubmit={handleResubmit} submitLabel="Resubmit for review" />
        </div>
      ) : (
        <div className="m-card">
          <p style={{ whiteSpace: 'pre-wrap', fontSize: '.92rem' }}>{posting.description}</p>
        </div>
      )}
    </div>
  )
}
