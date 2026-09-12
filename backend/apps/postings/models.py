import hashlib

from django.conf import settings
from django.db import models


class JobPosting(models.Model):
    """A single job listing submitted by an employer.

    Edits after submission don't create a new row — they bump `version`
    and re-trigger moderation, so `ModerationRun` rows accumulate across a
    posting's history instead of a posting silently changing under an
    approval already granted.
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PENDING = "PENDING", "Pending analysis"
        AUTO_APPROVED = "AUTO_APPROVED", "Auto-approved"
        AUTO_REJECTED = "AUTO_REJECTED", "Auto-rejected"
        IN_REVIEW = "IN_REVIEW", "In human review"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        CHANGES_REQUESTED = "CHANGES_REQUESTED", "Changes requested"

    class EmploymentType(models.TextChoices):
        FULL_TIME = "FULL_TIME", "Full-time"
        PART_TIME = "PART_TIME", "Part-time"
        CONTRACT = "CONTRACT", "Contract"
        INTERNSHIP = "INTERNSHIP", "Internship"
        TEMPORARY = "TEMPORARY", "Temporary"

    submitter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="job_postings"
    )

    company_name = models.CharField(max_length=200)
    title = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=200, blank=True)
    employment_type = models.CharField(
        max_length=20, choices=EmploymentType.choices, default=EmploymentType.FULL_TIME
    )

    salary_min = models.PositiveIntegerField(null=True, blank=True)
    salary_max = models.PositiveIntegerField(null=True, blank=True)
    currency = models.CharField(max_length=3, default="USD")
    salary_disclosed = models.BooleanField(default=False)

    apply_url = models.URLField(blank=True)
    contact_email = models.EmailField(blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    content_hash = models.CharField(max_length=64, blank=True, editable=False)
    version = models.PositiveIntegerField(default=1)

    submitted_at = models.DateTimeField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["submitter", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} @ {self.company_name} (v{self.version}, {self.status})"

    def compute_content_hash(self) -> str:
        """Hash of the fields that matter for moderation. Used to detect
        whether an edit actually changed anything worth re-analysing, and
        as the input to duplicate-detection in Phase 4.
        """
        payload = "␟".join(
            [
                self.company_name,
                self.title,
                self.description,
                self.location,
                self.employment_type,
                str(self.salary_min or ""),
                str(self.salary_max or ""),
                self.apply_url,
                self.contact_email,
            ]
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
