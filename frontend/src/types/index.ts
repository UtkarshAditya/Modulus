export type HealthStatus = 'ok' | 'unreachable'

export type Role = 'EMPLOYER' | 'MODERATOR' | 'ADMIN'

export interface User {
  authenticated: boolean
  id?: number
  username?: string
  email?: string
  role?: Role
}

export type PostingStatus =
  | 'DRAFT'
  | 'PENDING'
  | 'AUTO_APPROVED'
  | 'AUTO_REJECTED'
  | 'IN_REVIEW'
  | 'APPROVED'
  | 'REJECTED'
  | 'CHANGES_REQUESTED'

export type EmploymentType = 'FULL_TIME' | 'PART_TIME' | 'CONTRACT' | 'INTERNSHIP' | 'TEMPORARY'

export interface ReviewSummaryItem {
  category: string
  severity: string
  reason: string
  evidence: { start: number; end: number; text: string }[]
}

export interface LatestDecision {
  reason_code: string
  notes: string
}

export interface JobPosting {
  id: number
  submitter: string
  company_name: string
  title: string
  description: string
  location: string
  employment_type: EmploymentType
  salary_min: number | null
  salary_max: number | null
  currency: string
  salary_disclosed: boolean
  apply_url: string
  contact_email: string
  status: PostingStatus
  version: number
  submitted_at: string | null
  decided_at: string | null
  created_at: string
  updated_at: string
  review_summary: ReviewSummaryItem[] | null
  latest_decision: LatestDecision | null
}

export type JobPostingInput = Omit<
  JobPosting,
  | 'id'
  | 'submitter'
  | 'status'
  | 'version'
  | 'submitted_at'
  | 'decided_at'
  | 'created_at'
  | 'updated_at'
  | 'review_summary'
  | 'latest_decision'
>

export interface Flag {
  id: number
  category: string
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  source: 'RULE' | 'MODEL' | 'DEDUPE'
  confidence: number
  rule_id: string
  evidence: { start: number; end: number; text: string; note: string }[]
  reason: string
  contributing_terms: { term: string; weight: number }[]
  is_false_positive: boolean
  created_at: string
}

export interface ModerationRun {
  id: number
  posting_version: number
  policy_version: number | null
  model_version: string
  engine_version: string
  risk_score: number | null
  routing: string
  status: string
  error: string
  started_at: string | null
  finished_at: string | null
  duration_ms: number | null
  flags: Flag[]
}

export interface Decision {
  id: number
  run: number
  moderator: string
  action: 'APPROVE' | 'REJECT' | 'REQUEST_CHANGES' | 'ESCALATE'
  reason_code: string
  notes: string
  created_at: string
}

export interface QueueRow {
  id: number
  title: string
  company_name: string
  submitter: string
  status: PostingStatus
  submitted_at: string
  risk_score: number | null
  routing: string | null
  top_category: string | null
  flag_count: number
  claimed_by: number | null
}

export interface CasePosting {
  id: number
  submitter: string
  company_name: string
  title: string
  description: string
  location: string
  employment_type: EmploymentType
  salary_min: number | null
  salary_max: number | null
  currency: string
  salary_disclosed: boolean
  apply_url: string
  contact_email: string
  status: PostingStatus
  version: number
  submitted_at: string | null
  decided_at: string | null
  runs: ModerationRun[]
  claimed_by: number | null
}
