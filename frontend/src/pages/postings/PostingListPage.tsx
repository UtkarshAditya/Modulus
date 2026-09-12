import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { postings } from '../../api/client'
import { PostingStatusBadge } from '../../components/PostingStatusBadge'
import type { JobPosting } from '../../types'
import '../../styles/modulus.css'

export function PostingListPage() {
  const [items, setItems] = useState<JobPosting[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    postings
      .list()
      .then(setItems)
      .catch(() => setError('Could not load your postings.'))
  }, [])

  return (
    <div>
      <div className="m-page-header">
        <h1>My postings</h1>
        <Link to="/postings/new" className="m-btn m-btn-solid">
          Submit a posting
        </Link>
      </div>

      {error && <div className="m-error-banner">{error}</div>}
      {items === null && !error && <p className="m-loading">Loading…</p>}
      {items?.length === 0 && <p className="m-empty">You haven't submitted any postings yet.</p>}

      {items && items.length > 0 && (
        <div className="m-list">
          {items.map((posting) => (
            <Link key={posting.id} to={`/postings/${posting.id}`} className="m-list-row">
              <div style={{ minWidth: 0 }}>
                <p className="m-list-row-title">{posting.title}</p>
                <p className="m-list-row-meta">
                  {posting.company_name} · v{posting.version}
                </p>
              </div>
              <PostingStatusBadge status={posting.status} />
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
