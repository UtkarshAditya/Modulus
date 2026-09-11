import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.factories import EmployerFactory, ModeratorFactory
from apps.moderation.claims import get_claim_holder
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


MLM_DESCRIPTION = (
    "Be your own boss! Build your team and earn unlimited earning potential through our "
    "downline commission structure. Flexible hours, no experience necessary."
)


@pytest.fixture
def in_review_posting():
    employer = EmployerFactory(username="employer2")
    posting = JobPostingFactory(
        submitter=employer,
        title="Independent Sales Representative",
        description=MLM_DESCRIPTION,
        status=JobPosting.Status.DRAFT,
    )
    submit_for_moderation(posting)
    posting.refresh_from_db()
    assert posting.status == JobPosting.Status.IN_REVIEW
    return posting


@pytest.fixture
def moderator_client():
    moderator = ModeratorFactory(username="mod1")
    client = APIClient(enforce_csrf_checks=False)
    client.force_authenticate(user=moderator)
    return client, moderator


def _rows(response_data):
    return response_data["results"] if isinstance(response_data, dict) else response_data


def test_queue_lists_in_review_postings(moderator_client, in_review_posting):
    client, _ = moderator_client
    response = client.get(reverse("moderation-queue-list"))
    assert response.status_code == 200
    data = _rows(response.data)
    assert any(row["id"] == in_review_posting.pk for row in data)
    row = next(row for row in data if row["id"] == in_review_posting.pk)
    assert row["top_category"] == "MLM_RECRUITMENT"
    assert row["claimed_by"] is None


def test_queue_filters_by_category(moderator_client, in_review_posting):
    client, _ = moderator_client
    matching = client.get(reverse("moderation-queue-list"), {"category": "MLM_RECRUITMENT"})
    nonmatching = client.get(reverse("moderation-queue-list"), {"category": "ADVANCE_FEE"})

    matching_ids = [row["id"] for row in _rows(matching.data)]
    nonmatching_ids = [row["id"] for row in _rows(nonmatching.data)]
    assert in_review_posting.pk in matching_ids
    assert in_review_posting.pk not in nonmatching_ids


def test_non_moderator_cannot_access_queue(in_review_posting):
    employer = EmployerFactory(username="employer3")
    client = APIClient(enforce_csrf_checks=False)
    client.force_authenticate(user=employer)

    response = client.get(reverse("moderation-queue-list"))
    assert response.status_code == 403


def test_claim_then_second_moderator_is_blocked(in_review_posting):
    mod_a = ModeratorFactory(username="mod_a")
    mod_b = ModeratorFactory(username="mod_b")
    client_a = APIClient(enforce_csrf_checks=False)
    client_a.force_authenticate(user=mod_a)
    client_b = APIClient(enforce_csrf_checks=False)
    client_b.force_authenticate(user=mod_b)

    claim_url = reverse("moderation-queue-claim", args=[in_review_posting.pk])
    first = client_a.post(claim_url)
    assert first.status_code == 200
    assert get_claim_holder(in_review_posting.pk) == mod_a.pk

    second = client_b.post(claim_url)
    assert second.status_code == 409
    assert second.data["held_by"] == mod_a.pk


def test_reclaiming_your_own_claim_succeeds(moderator_client, in_review_posting):
    client, moderator = moderator_client
    claim_url = reverse("moderation-queue-claim", args=[in_review_posting.pk])

    assert client.post(claim_url).status_code == 200
    assert client.post(claim_url).status_code == 200  # renew, not a conflict


def test_release_by_non_holder_is_forbidden(in_review_posting):
    mod_a = ModeratorFactory(username="mod_c")
    mod_b = ModeratorFactory(username="mod_d")
    client_a = APIClient(enforce_csrf_checks=False)
    client_a.force_authenticate(user=mod_a)
    client_b = APIClient(enforce_csrf_checks=False)
    client_b.force_authenticate(user=mod_b)

    client_a.post(reverse("moderation-queue-claim", args=[in_review_posting.pk]))
    response = client_b.post(reverse("moderation-queue-release", args=[in_review_posting.pk]))
    assert response.status_code == 403


def test_case_detail_includes_full_internal_flag_data(moderator_client, in_review_posting):
    client, _ = moderator_client
    response = client.get(reverse("moderation-posting-detail", args=[in_review_posting.pk]))
    assert response.status_code == 200
    latest_run = response.data["runs"][0]
    assert latest_run["risk_score"] is not None
    flag = next(f for f in latest_run["flags"] if f["category"] == "MLM_RECRUITMENT")
    assert "confidence" in flag
    assert "evidence" in flag


def test_decide_approve_updates_status_and_releases_claim(moderator_client, in_review_posting):
    client, moderator = moderator_client
    claim_url = reverse("moderation-queue-claim", args=[in_review_posting.pk])
    client.post(claim_url)
    assert get_claim_holder(in_review_posting.pk) == moderator.pk

    decide_url = reverse("moderation-posting-decide", args=[in_review_posting.pk])
    response = client.post(
        decide_url, {"action": "APPROVE", "reason_code": "", "notes": "Looks fine."}, format="json"
    )

    assert response.status_code == 201
    in_review_posting.refresh_from_db()
    assert in_review_posting.status == JobPosting.Status.APPROVED
    assert in_review_posting.decided_at is not None
    assert get_claim_holder(in_review_posting.pk) is None


def test_decide_request_changes_sets_changes_requested(moderator_client, in_review_posting):
    client, _ = moderator_client
    decide_url = reverse("moderation-posting-decide", args=[in_review_posting.pk])
    response = client.post(
        decide_url,
        {
            "action": "REQUEST_CHANGES",
            "reason_code": "mlm_language",
            "notes": "Remove downline language.",
        },
        format="json",
    )
    assert response.status_code == 201
    in_review_posting.refresh_from_db()
    assert in_review_posting.status == JobPosting.Status.CHANGES_REQUESTED
    assert in_review_posting.decided_at is None  # not a terminal outcome


def test_mark_flag_false_positive(moderator_client, in_review_posting):
    client, _ = moderator_client
    run = in_review_posting.moderation_runs.get()
    flag = run.flags.filter(category="MLM_RECRUITMENT").first()

    url = reverse("moderation-flag-false-positive", args=[flag.pk])
    response = client.post(url)
    assert response.status_code == 200
    flag.refresh_from_db()
    assert flag.is_false_positive is True
