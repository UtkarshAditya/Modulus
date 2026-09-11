"""Phase 1 verification: every new model is registered in the admin, and a
posting can actually be created through it end to end (not just via the ORM).
"""

import pytest
from django.contrib.admin.sites import site
from django.urls import reverse

from apps.accounts.factories import AdminFactory
from apps.audit.models import AuditEvent
from apps.moderation.models import Decision, Flag, ModerationRun, ReviewClaim
from apps.policies.models import Policy
from apps.postings.models import JobPosting


@pytest.mark.parametrize(
    "model", [JobPosting, ModerationRun, Flag, ReviewClaim, Decision, Policy, AuditEvent]
)
def test_model_registered_in_admin(model):
    assert site.is_registered(model)


@pytest.mark.django_db
def test_create_job_posting_through_admin_add_view(client):
    admin = AdminFactory()
    client.force_login(admin)

    response = client.get(reverse("admin:postings_jobposting_add"))
    assert response.status_code == 200

    response = client.post(
        reverse("admin:postings_jobposting_add"),
        data={
            "submitter": admin.pk,
            "company_name": "Test Co",
            "title": "QA Engineer",
            "description": "Come test our software.",
            "location": "Remote",
            "employment_type": JobPosting.EmploymentType.FULL_TIME,
            "currency": "USD",
            "status": JobPosting.Status.DRAFT,
            "version": 1,
            "apply_url": "",
            "contact_email": "",
            "salary_min": "",
            "salary_max": "",
        },
    )
    assert response.status_code == 302, (
        response.context["adminform"].form.errors if response.status_code == 200 else None
    )

    posting = JobPosting.objects.get(title="QA Engineer")
    assert posting.company_name == "Test Co"
    # the admin's save_model hook should have stamped the content hash
    assert posting.content_hash == posting.compute_content_hash()
