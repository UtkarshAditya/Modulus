import type { PostingStatus } from '../types'
import '../styles/modulus.css'

const TONES: Record<PostingStatus, 'neutral' | 'clear' | 'critical' | 'signal'> = {
  DRAFT: 'neutral',
  PENDING: 'neutral',
  AUTO_APPROVED: 'clear',
  APPROVED: 'clear',
  AUTO_REJECTED: 'critical',
  REJECTED: 'critical',
  IN_REVIEW: 'signal',
  CHANGES_REQUESTED: 'signal',
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
    <span className="m-status-badge" data-tone={TONES[status]}>
      {LABELS[status]}
    </span>
  )
}

export function SeverityBadge({ severity }: { severity: string }) {
  return (
    <span className="m-chip" data-sev={severity}>
      {severity}
    </span>
  )
}
