"""Phase 4 verification: the full pipeline, run for real (Celery eager
mode, real Postgres, real Redis) end to end for all three routing
outcomes plus the engine-failure path, asserting on the actual
ModerationRun/Flag rows it produces — not just the pure fusion function.
"""

import pytest

from apps.moderation.models import Flag, ModerationRun
from apps.moderation.services import submit_for_moderation
from apps.policies.factories import PolicyFactory
from apps.policies.models import Policy
from apps.postings.factories import JobPostingFactory
from apps.postings.models import JobPosting

pytestmark = pytest.mark.django_db

# _eager_celery and _clean_redis are autouse fixtures from tests/conftest.py.


@pytest.fixture(autouse=True)
def _active_policy():
    if Policy.objects.get_active() is None:
        PolicyFactory(version=1, is_active=True)


def test_clean_posting_is_auto_approved():
    posting = JobPostingFactory(
        title="Registered Nurse",
        description=(
            "We are hiring a registered nurse for our medical-surgical unit. Active RN "
            "license required. You'll provide direct patient care on day shift. Full "
            "benefits including health insurance and paid time off."
        ),
        status=JobPosting.Status.DRAFT,
    )

    run = submit_for_moderation(posting)
    run.refresh_from_db()
    posting.refresh_from_db()

    assert run.status == ModerationRun.Status.SUCCEEDED
    assert run.routing == "AUTO_APPROVE"
    assert posting.status == JobPosting.Status.AUTO_APPROVED
    assert posting.decided_at is not None
    assert not Flag.objects.filter(run=run, severity="CRITICAL").exists()


def test_advance_fee_scam_is_auto_rejected():
    posting = JobPostingFactory(
        title="Data Entry Clerk",
        description=(
            "Earn money from home! Please pay a refundable deposit of $75 to secure your "
            "starter kit before you start. Limited spots available, apply today."
        ),
        status=JobPosting.Status.DRAFT,
    )

    run = submit_for_moderation(posting)
    run.refresh_from_db()
    posting.refresh_from_db()

    assert run.status == ModerationRun.Status.SUCCEEDED
    assert run.routing == "AUTO_REJECT"
    assert posting.status == JobPosting.Status.AUTO_REJECTED
    assert posting.decided_at is not None
    assert Flag.objects.filter(run=run, category="ADVANCE_FEE", severity="CRITICAL").exists()


def test_borderline_mlm_posting_goes_to_human_review():
    posting = JobPostingFactory(
        title="Independent Sales Representative",
        description=(
            "Be your own boss! Build your team and earn unlimited earning potential "
            "through our downline commission structure. Flexible hours, no experience "
            "necessary, great community of driven people."
        ),
        status=JobPosting.Status.DRAFT,
    )

    run = submit_for_moderation(posting)
    run.refresh_from_db()
    posting.refresh_from_db()

    assert run.status == ModerationRun.Status.SUCCEEDED
    assert run.routing == "HUMAN_REVIEW"
    assert posting.status == JobPosting.Status.IN_REVIEW
    assert posting.decided_at is None
    assert Flag.objects.filter(run=run, category="MLM_RECRUITMENT").exists()


def test_resubmission_increments_version_and_creates_a_second_run():
    posting = JobPostingFactory(
        title="Registered Nurse",
        description="A clean, boring posting with nothing wrong with it at all, truly.",
        status=JobPosting.Status.DRAFT,
    )
    assert posting.version == 1

    first_run = submit_for_moderation(posting)
    posting.refresh_from_db()
    assert first_run.posting_version == 1

    posting.description += " Updated with more detail about the role."
    posting.save()
    second_run = submit_for_moderation(posting)
    posting.refresh_from_db()

    assert posting.version == 2
    assert second_run.posting_version == 2
    assert posting.moderation_runs.count() == 2


def test_engine_failure_routes_to_human_review_and_never_silently_approves(monkeypatch):
    def _boom(*args, **kwargs):
        raise RuntimeError("simulated engine failure")

    monkeypatch.setattr("apps.moderation.tasks.run_rules", _boom)

    posting = JobPostingFactory(
        title="Registered Nurse",
        description="A clean, boring posting that would otherwise auto-approve cleanly.",
        status=JobPosting.Status.DRAFT,
    )

    with pytest.raises(RuntimeError, match="simulated engine failure"):
        submit_for_moderation(posting)

    posting.refresh_from_db()
    run = posting.moderation_runs.get()

    assert run.status == ModerationRun.Status.FAILED
    assert "simulated engine failure" in run.error
    assert posting.status == JobPosting.Status.IN_REVIEW
    assert posting.decided_at is None


def test_resubmitting_with_unchanged_content_is_a_noop():
    """Phase 7 idempotency: a PATCH that doesn't actually change anything
    moderation-relevant shouldn't burn a new run, bump version, or flip
    the posting back to PENDING.
    """
    posting = JobPostingFactory(
        title="Registered Nurse",
        description="A clean, boring posting with nothing wrong with it at all, truly.",
        status=JobPosting.Status.DRAFT,
    )
    first_run = submit_for_moderation(posting)
    posting.refresh_from_db()
    assert posting.version == 1
    assert posting.status == JobPosting.Status.AUTO_APPROVED

    # Force it back to CHANGES_REQUESTED as if a moderator asked for an
    # edit, then "resubmit" without actually changing anything.
    posting.status = JobPosting.Status.CHANGES_REQUESTED
    posting.save(update_fields=["status"])

    second_run = submit_for_moderation(posting)
    posting.refresh_from_db()

    assert second_run.pk == first_run.pk
    assert posting.version == 1
    assert posting.moderation_runs.count() == 1
    # Left exactly where it was — nothing was actually resubmitted.
    assert posting.status == JobPosting.Status.CHANGES_REQUESTED
