// Shared frontend types. Grows per-domain (JobPosting, ModerationRun, Flag,
// ...) starting in Phase 5; kept to cross-cutting types until then.

export type HealthStatus = 'ok' | 'unreachable'
