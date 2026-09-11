import type { PostingStatus } from '../types'

const STYLES: Record<PostingStatus, string> = {
  DRAFT: 'bg-slate-100 text-slate-600',
  PENDING: 'bg-slate-100 text-slate-600',
  AUTO_APPROVED: 'bg-emerald-100 text-emerald-800',
  APPROVED: 'bg-emerald-100 text-emerald-800',
  AUTO_REJECTED: 'bg-red-100 text-red-800',
  REJECTED: 'bg-red-100 text-red-800',
  IN_REVIEW: 'bg-amber-100 text-amber-800',
  CHANGES_REQUESTED: 'bg-amber-100 text-amber-800',
}

const LABELS: Record<PostingStatus, string> = {
  DRAFT: 'Draft',
  PENDING: 'Analyzing…',
  AUTO_APPROVED: 'Approved',
  APPROVED: 'Approved',
  AUTO_REJECTED: 'Rejected',
  REJECTED: 'Rejected',
  IN_REVIEW: 'In review',
  CHANGES_REQUESTED: 'Changes requested',
}

export function PostingStatusBadge({ status }: { status: PostingStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap ${STYLES[status]}`}
    >
      {LABELS[status]}
    </span>
  )
}

const SEVERITY_STYLES: Record<string, string> = {
  CRITICAL: 'bg-red-100 text-red-800 border border-red-300',
  HIGH: 'bg-orange-100 text-orange-800 border border-orange-300',
  MEDIUM: 'bg-amber-100 text-amber-800 border border-amber-300',
  LOW: 'bg-slate-100 text-slate-600 border border-slate-300',
}

export function SeverityBadge({ severity }: { severity: string }) {
  const style = SEVERITY_STYLES[severity] ?? SEVERITY_STYLES.LOW
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${style}`}>
      {severity}
    </span>
  )
}
