import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { moderation } from '../../api/client'
import { useAuth } from '../../hooks/useAuth'
import type { QueueFilters } from '../../api/client'
import type { QueueRow } from '../../types'

const CATEGORIES = [
  'ADVANCE_FEE', 'PII_HARVEST', 'ILLEGAL_WORK', 'MLM_RECRUITMENT', 'OFF_PLATFORM_REDIRECT',
  'DISCRIMINATORY', 'MISLEADING_COMP', 'NO_COMP_DISCLOSURE', 'SPAM_DUPLICATE', 'GHOST_JOB',
  'KEYWORD_STUFFING',
]  // fmt: skip

const SEVERITIES = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']

function timeAgo(iso: string): string {
  const minutes = Math.round((Date.now() - new Date(iso).getTime()) / 60000)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.round(hours / 24)}d ago`
}

export function QueuePage() {
  const { user } = useAuth()
  const [rows, setRows] = useState<QueueRow[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [filters, setFilters] = useState<QueueFilters>({})

  function load() {
    moderation
      .queue(filters)
      .then(setRows)
      .catch(() => setError('Could not load the queue.'))
  }

  useEffect(load, [filters])

  return (
    <div>
      <h1 className="mb-4 text-xl font-semibold text-slate-900">Moderation queue</h1>

      <div className="mb-4 flex flex-wrap items-center gap-3 text-sm">
        <select
          className="input w-auto"
          value={filters.category ?? ''}
          onChange={(e) => setFilters((f) => ({ ...f, category: e.target.value || undefined }))}
        >
          <option value="">All categories</option>
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {c.replace(/_/g, ' ')}
            </option>
          ))}
        </select>
        <select
          className="input w-auto"
          value={filters.severity ?? ''}
          onChange={(e) => setFilters((f) => ({ ...f, severity: e.target.value || undefined }))}
        >
          <option value="">All severities</option>
          {SEVERITIES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <button onClick={load} className="text-slate-500 hover:text-slate-800">
          Refresh
        </button>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}
      {rows === null && !error && <p className="text-sm text-slate-500">Loading…</p>}
      {rows?.length === 0 && <p className="text-sm text-slate-500">The queue is empty. Nice.</p>}

      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2 font-medium">Posting</th>
              <th className="px-4 py-2 font-medium">Top category</th>
              <th className="px-4 py-2 font-medium">Risk score</th>
              <th className="px-4 py-2 font-medium">Submitted</th>
              <th className="px-4 py-2 font-medium">Claim</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows?.map((row) => (
              <tr key={row.id} className="hover:bg-slate-50">
                <td className="px-4 py-2">
                  <div className="flex items-center gap-2">
                    <Link to={`/moderation/${row.id}`} className="font-medium text-slate-900 hover:underline">
                      {row.title}
                    </Link>
                    {row.is_escalated && (
                      <span className="rounded-full bg-purple-100 px-2 py-0.5 text-xs font-medium text-purple-800">
                        Escalated
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-500">
                    {row.company_name} · {row.submitter}
                  </p>
                </td>
                <td className="px-4 py-2 text-slate-700">
                  {row.top_category?.replace(/_/g, ' ') ?? '—'}
                  {row.flag_count > 1 && (
                    <span className="ml-1 text-xs text-slate-400">+{row.flag_count - 1} more</span>
                  )}
                </td>
                <td className="px-4 py-2 text-slate-700">
                  {row.risk_score !== null ? row.risk_score.toFixed(2) : '—'}
                </td>
                <td className="px-4 py-2 text-slate-500">{timeAgo(row.submitted_at)}</td>
                <td className="px-4 py-2">
                  {row.claimed_by === null ? (
                    <span className="text-xs text-slate-400">Unclaimed</span>
                  ) : row.claimed_by === user?.id ? (
                    <span className="text-xs font-medium text-emerald-700">Claimed by you</span>
                  ) : (
                    <span className="text-xs font-medium text-amber-700">Claimed</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
