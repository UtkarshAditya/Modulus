"""The moderation pipeline: normalize -> rules -> classifier -> dedupe ->
fuse -> persist -> route.

Implemented as one Celery task that runs each stage internally, not a
literal `celery.chain()` of separate tasks — `RuleHit`'s enum-typed fields
aren't trivially JSON-serializable for passing between chained tasks'
results, and there's no present need to run stages on separate queues or
workers. Each stage below is still a plain, independently-tested function
(`normalize`, `run_rules`, `classifier.evaluate`, `dedupe.check_and_record`,
`fuse`) and its own timing is recorded on the run, so splitting into a
real multi-task chain later is a refactor, not a redesign.

Failure policy: any exception marks the run FAILED and routes the posting
to IN_REVIEW — an engine failure must never silently auto-approve.
"""

from __future__ import annotations

import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.moderation.engine import ENGINE_VERSION
from apps.moderation.engine.classifier import get_classifier
from apps.moderation.engine.dedupe import check_and_record
from apps.moderation.engine.fusion import fuse
from apps.moderation.engine.normalize import NormalizedDoc
from apps.moderation.engine.reasons import render_reason
from apps.moderation.engine.rules.base import run_rules
from apps.moderation.engine.rules.packs.jobs import JOB_RULES
from apps.moderation.models import Flag, ModerationRun
from apps.policies.services import get_active_policy, get_rule_config
from apps.postings.models import JobPosting

logger = logging.getLogger(__name__)

_ROUTING_TO_STATUS = {
    "AUTO_APPROVE": JobPosting.Status.AUTO_APPROVED,
    "AUTO_REJECT": JobPosting.Status.AUTO_REJECTED,
    "HUMAN_REVIEW": JobPosting.Status.IN_REVIEW,
}


@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def run_moderation_task(self, run_id: int) -> None:
    # run_id is the correlation id threaded through every log line for
    # this run's lifecycle — the thing to grep for when tracing one
    # posting's path through an async pipeline across process boundaries.
    run = ModerationRun.objects.select_related("posting").get(pk=run_id)
    logger.info("run %s: starting for posting #%s", run_id, run.posting_id)
    run.status = ModerationRun.Status.RUNNING
    run.started_at = timezone.now()
    run.save(update_fields=["status", "started_at"])

    try:
        _execute(run)
    except (
        Exception
    ) as exc:  # noqa: BLE001 - deliberately broad: any failure routes to human review
        logger.exception("run %s: failed", run_id)
        _mark_failed(run, exc)
        raise


def _execute(run: ModerationRun) -> None:
    posting = run.posting
    policy = get_active_policy()

    doc = NormalizedDoc.combine(posting.title, posting.description)

    rule_config = get_rule_config(policy, [rule.id for rule in JOB_RULES])
    rule_hits = run_rules(JOB_RULES, posting, doc, rule_config)

    classifier = get_classifier()
    model_hits = classifier.evaluate(posting, doc) if classifier is not None else []

    dedupe_hits = check_and_record(doc.folded, posting.pk, posting.submitter_id)

    all_hits = rule_hits + model_hits + dedupe_hits
    fusion_result = fuse(all_hits, policy)

    with transaction.atomic():
        for hit in all_hits:
            Flag.objects.create(
                run=run,
                category=hit.category.value,
                severity=hit.severity.value,
                source=hit.source,
                confidence=hit.confidence,
                rule_id=hit.rule_id,
                evidence=[e.to_dict() for e in hit.evidence],
                reason=render_reason(hit),
                contributing_terms=hit.contributing_terms,
            )

        finished_at = timezone.now()
        run.risk_score = fusion_result.risk_score
        run.routing = fusion_result.routing
        run.status = ModerationRun.Status.SUCCEEDED
        run.finished_at = finished_at
        run.duration_ms = int((finished_at - run.started_at).total_seconds() * 1000)
        run.policy_version = policy.version
        run.model_version = str(classifier.bundle.version) if classifier is not None else ""
        run.engine_version = ENGINE_VERSION
        run.save()

        new_status = _ROUTING_TO_STATUS[fusion_result.routing]
        posting.status = new_status
        if new_status in (JobPosting.Status.AUTO_APPROVED, JobPosting.Status.AUTO_REJECTED):
            posting.decided_at = finished_at
        posting.save(update_fields=["status", "decided_at"])

        AuditEvent.objects.create(
            actor=None,
            action="moderation.run_completed",
            object_type="postings.JobPosting",
            object_id=str(posting.pk),
            after={
                "run_id": run.pk,
                "status": posting.status,
                "risk_score": fusion_result.risk_score,
                "routing": fusion_result.routing,
                "flag_count": len(all_hits),
            },
        )

    logger.info(
        "run %s: routed %s (risk_score=%s, %d flags, %dms)",
        run.pk,
        fusion_result.routing,
        fusion_result.risk_score,
        len(all_hits),
        run.duration_ms,
    )


def _mark_failed(run: ModerationRun, exc: Exception) -> None:
    finished_at = timezone.now()
    run.status = ModerationRun.Status.FAILED
    run.error = str(exc)
    run.finished_at = finished_at
    if run.started_at:
        run.duration_ms = int((finished_at - run.started_at).total_seconds() * 1000)
    run.engine_version = ENGINE_VERSION
    run.save(update_fields=["status", "error", "finished_at", "duration_ms", "engine_version"])

    posting = run.posting
    posting.status = JobPosting.Status.IN_REVIEW
    posting.save(update_fields=["status"])

    AuditEvent.objects.create(
        actor=None,
        action="moderation.run_failed",
        object_type="postings.JobPosting",
        object_id=str(posting.pk),
        after={"run_id": run.pk, "error": str(exc)},
    )


@shared_task
def export_training_labels_task() -> int:
    """Nightly (see CELERY_BEAT_SCHEDULE): regenerates
    ml/data/exported_labels.jsonl from moderator decisions made so far.
    Growing the labelled pool only — retraining on it stays the manual
    `python ml/train.py` command per docs/PLAN.md.
    """
    from apps.moderation.exports import write_export

    count = write_export()
    logger.info("export_training_labels_task: wrote %d labelled examples", count)
    return count
