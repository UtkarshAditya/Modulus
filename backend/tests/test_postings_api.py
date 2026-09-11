import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.factories import EmployerFactory, ModeratorFactory
from apps.moderation.models import Decision
from apps.moderation.services import apply_decision, submit_for_moderation
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


CLEAN_DESCRIPTION = (
    "We are hiring a registered nurse for our medical-surgical unit. Active RN license "
    "required. You'll provide direct patient care on day shift. Full benefits included."
)


@pytest.fixture
def employer_client():
    user = EmployerFactory(username="employer1")
    client = APIClient(enforce_csrf_checks=False)
    client.force_authenticate(user=user)
    return client, user


def test_create_submits_immediately_and_returns_202(employer_client):
    client, user = employer_client
    payload = {
        "company_name": "Northwind Traders",
        "title": "Registered Nurse",
        "description": CLEAN_DESCRIPTION,
        "location": "Remote",
        "employment_type": "FULL_TIME",
        "salary_min": 70000,
        "salary_max": 90000,
        "currency": "USD",
        "salary_disclosed": True,
        "apply_url": "https://example.com/apply",
        "contact_email": "hr@example.com",
    }
    response = client.post(reverse("posting-list"), payload, format="json")

    assert response.status_code == 202
    assert response.data["status"] == "AUTO_APPROVED"
    assert response.data["submitter"] == user.username

    posting = JobPosting.objects.get(pk=response.data["id"])
    assert posting.moderation_runs.count() == 1


def test_list_only_returns_own_postings(employer_client):
    client, user = employer_client
    JobPostingFactory(submitter=user, title="Mine")
    JobPostingFactory(title="Someone else's")

    response = client.get(reverse("posting-list"))
    assert response.status_code == 200
    titles = (
        [p["title"] for p in response.data["results"]]
        if "results" in response.data
        else [p["title"] for p in response.data]
    )
    assert titles == ["Mine"]


def test_cannot_retrieve_another_users_posting(employer_client):
    client, _ = employer_client
    other_posting = JobPostingFactory()

    response = client.get(reverse("posting-detail", args=[other_posting.pk]))
    assert response.status_code == 404


def test_review_summary_present_on_rejected_posting(employer_client):
    client, user = employer_client
    payload = {
        "company_name": "QuickCash Global",
        "title": "Data Entry Clerk",
        "description": (
            "Earn money from home! Please pay a refundable deposit of $75 to secure your "
            "starter kit before you start."
        ),
        "location": "Remote",
        "employment_type": "PART_TIME",
        "salary_disclosed": False,
        "apply_url": "",
        "contact_email": "",
    }
    response = client.post(reverse("posting-list"), payload, format="json")

    assert response.data["status"] == "AUTO_REJECTED"
    assert response.data["review_summary"], "expected a non-empty review_summary"
    categories = [f["category"] for f in response.data["review_summary"]]
    assert "ADVANCE_FEE" in categories
    # submitter-facing summary must never leak internal scoring fields
    assert "confidence" not in response.data["review_summary"][0]
    assert "contributing_terms" not in response.data["review_summary"][0]


def test_patch_rejected_unless_changes_requested(employer_client):
    client, user = employer_client
    posting = JobPostingFactory(submitter=user, status=JobPosting.Status.AUTO_APPROVED)

    response = client.patch(
        reverse("posting-detail", args=[posting.pk]), {"title": "New title"}, format="json"
    )
    assert response.status_code == 400


def test_patch_when_changes_requested_resubmits_and_bumps_version(employer_client):
    client, user = employer_client
    # CHANGES_REQUESTED is only reachable in real usage via a genuine run
    # plus a moderator decision - build that state for real rather than
    # setting the status field directly, so the resubmission logic (which
    # keys off "has this posting ever actually been submitted before") is
    # exercised the way it would be in production.
    posting = JobPostingFactory(
        submitter=user,
        title="Old title",
        description=(
            "Be your own boss! Build your team and earn unlimited earning potential "
            "through our downline commission structure."
        ),
        status=JobPosting.Status.DRAFT,
    )
    submit_for_moderation(posting)
    posting.refresh_from_db()
    assert posting.status == JobPosting.Status.IN_REVIEW

    moderator = ModeratorFactory(username="moderator1")
    apply_decision(
        posting,
        moderator=moderator,
        action=Decision.Action.REQUEST_CHANGES,
        notes="Remove MLM language.",
    )
    posting.refresh_from_db()
    assert posting.status == JobPosting.Status.CHANGES_REQUESTED

    response = client.patch(
        reverse("posting-detail", args=[posting.pk]), {"title": "New title"}, format="json"
    )

    assert response.status_code == 200
    assert response.data["title"] == "New title"
    assert response.data["version"] == 2
    posting.refresh_from_db()
    assert posting.moderation_runs.count() == 2


def test_anonymous_cannot_access_postings_api():
    client = APIClient()
    response = client.get(reverse("posting-list"))
    assert response.status_code in (401, 403)
