import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { postings } from '../../api/client'
import { PostingStatusBadge } from '../../components/PostingStatusBadge'
import type { JobPosting } from '../../types'

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
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-900">My postings</h1>
        <Link
          to="/postings/new"
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
        >
          Submit a posting
        </Link>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}
      {items === null && !error && <p className="text-sm text-slate-500">Loading…</p>}
      {items?.length === 0 && (
        <p className="text-sm text-slate-500">You haven't submitted any postings yet.</p>
      )}

      <div className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
        {items?.map((posting) => (
          <Link
            key={posting.id}
            to={`/postings/${posting.id}`}
            className="flex items-center justify-between gap-4 px-4 py-3 hover:bg-slate-50"
          >
            <div className="min-w-0">
              <p className="truncate font-medium text-slate-900">{posting.title}</p>
              <p className="truncate text-sm text-slate-500">
                {posting.company_name} · v{posting.version}
              </p>
            </div>
            <PostingStatusBadge status={posting.status} />
          </Link>
        ))}
      </div>
    </div>
  )
}
