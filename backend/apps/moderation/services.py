"""The one entry point for putting a posting through moderation — called
by the submitter API (Phase 5) on initial submit and on resubmit after
`CHANGES_REQUESTED`, and by the admin for manual testing. Keeping this in
one place is what guarantees a `ModerationRun` always exists before the
Celery task that fills it in runs, and that an edit always bumps
`version` before re-triggering analysis, per the plan's posting model.
"""

from __future__ import annotations

from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.moderation.claims import release_claim
from apps.moderation.models import Decision, ModerationRun
from apps.postings.models import JobPosting

_DECISION_TO_STATUS = {
    Decision.Action.APPROVE: JobPosting.Status.APPROVED,
    Decision.Action.REJECT: JobPosting.Status.REJECTED,
    Decision.Action.REQUEST_CHANGES: JobPosting.Status.CHANGES_REQUESTED,
    # Escalate keeps the posting in the human queue for a second look —
    # it's a decision worth recording, not a terminal outcome.
    Decision.Action.ESCALATE: JobPosting.Status.IN_REVIEW,
}
_TERMINAL_STATUSES = {JobPosting.Status.APPROVED, JobPosting.Status.REJECTED}


def submit_for_moderation(posting: JobPosting, *, actor=None) -> ModerationRun:
    is_resubmission = posting.moderation_runs.exists()
    if is_resubmission:
        posting.version += 1

    posting.content_hash = posting.compute_content_hash()
    posting.status = JobPosting.Status.PENDING
    posting.submitted_at = timezone.now()
    posting.decided_at = None
    posting.save(update_fields=["version", "content_hash", "status", "submitted_at", "decided_at"])

    run = ModerationRun.objects.create(
        posting=posting,
        posting_version=posting.version,
        status=ModerationRun.Status.PENDING,
    )

    AuditEvent.objects.create(
        actor=actor if actor and actor.is_authenticated else None,
        action="posting.resubmitted" if is_resubmission else "posting.submitted",
        object_type="postings.JobPosting",
        object_id=str(posting.pk),
        after={"version": posting.version, "run_id": run.pk},
    )

    from apps.moderation.tasks import run_moderation_task

    run_moderation_task.delay(run.pk)
    return run


def apply_decision(
    posting: JobPosting, *, moderator, action: str, reason_code: str = "", notes: str = ""
) -> Decision:
    """A moderator's final call on a posting's most recent run. The one
    place `Decision` rows get created, so a decision and the posting
    status change it causes can never happen separately.
    """
    run = posting.moderation_runs.order_by("-started_at", "-id").first()
    if run is None:
        raise ValueError("This posting has no moderation run to decide on.")

    decision = Decision.objects.create(
        moderator=moderator, run=run, action=action, reason_code=reason_code, notes=notes
    )

    new_status = _DECISION_TO_STATUS[action]
    posting.status = new_status
    if new_status in _TERMINAL_STATUSES:
        posting.decided_at = timezone.now()
    posting.save(update_fields=["status", "decided_at"])

    release_claim(posting.pk, moderator)

    AuditEvent.objects.create(
        actor=moderator,
        action=f"decision.{action.lower()}",
        object_type="postings.JobPosting",
        object_id=str(posting.pk),
        after={"status": posting.status, "reason_code": reason_code, "decision_id": decision.pk},
    )
    return decision
