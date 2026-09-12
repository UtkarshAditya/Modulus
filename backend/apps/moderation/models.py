from django.conf import settings
from django.db import models

from apps.moderation.engine.rules.base import Category, Severity

_CATEGORY_CHOICES = [(c.value, c.value.replace("_", " ").title()) for c in Category]
_SEVERITY_CHOICES = [(s.value, s.value.title()) for s in Severity]


class ModerationRun(models.Model):
    """One pipeline execution over one version of a JobPosting. Recording
    policy/model/engine version on every row is what makes a past decision
    reproducible even after the policy or classifier has since changed.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        RUNNING = "RUNNING", "Running"
        SUCCEEDED = "SUCCEEDED", "Succeeded"
        FAILED = "FAILED", "Failed"

    class Routing(models.TextChoices):
        AUTO_APPROVE = "AUTO_APPROVE", "Auto-approve"
        AUTO_REJECT = "AUTO_REJECT", "Auto-reject"
        HUMAN_REVIEW = "HUMAN_REVIEW", "Human review"

    posting = models.ForeignKey(
        "postings.JobPosting", on_delete=models.CASCADE, related_name="moderation_runs"
    )
    posting_version = models.PositiveIntegerField()

    policy_version = models.PositiveIntegerField(null=True, blank=True)
    model_version = models.CharField(max_length=64, blank=True)
    engine_version = models.CharField(max_length=64, blank=True)

    risk_score = models.FloatField(null=True, blank=True)
    routing = models.CharField(max_length=20, choices=Routing.choices, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    error = models.TextField(blank=True)

    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at", "-id"]
        indexes = [models.Index(fields=["posting", "posting_version"])]

    def __str__(self) -> str:
        return (
            f"Run #{self.pk} for posting #{self.posting_id} v{self.posting_version} ({self.status})"
        )


class Flag(models.Model):
    """One triggered category from one ModerationRun."""

    class Source(models.TextChoices):
        RULE = "RULE", "Rule"
        MODEL = "MODEL", "Model"
        DEDUPE = "DEDUPE", "Dedupe"

    run = models.ForeignKey(ModerationRun, on_delete=models.CASCADE, related_name="flags")

    category = models.CharField(max_length=32, choices=_CATEGORY_CHOICES)
    severity = models.CharField(max_length=16, choices=_SEVERITY_CHOICES)
    source = models.CharField(max_length=16, choices=Source.choices)
    confidence = models.FloatField(default=1.0)

    rule_id = models.CharField(max_length=64, blank=True)
    # list[{"start": int, "end": int, "text": str, "note": str}]
    evidence = models.JSONField(default=list, blank=True)
    reason = models.TextField(blank=True)
    # list of {"term": str, "weight": float} for model-sourced flags
    contributing_terms = models.JSONField(default=list, blank=True)

    is_false_positive = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-severity", "-confidence"]
        indexes = [models.Index(fields=["run", "category"])]

    def __str__(self) -> str:
        return f"{self.category} ({self.severity}) on run #{self.run_id}"


class ReviewClaim(models.Model):
    """A moderator's claim on a posting's queue entry. The Redis lock
    (Phase 6) is what actually prevents two moderators opening the same
    case concurrently — this row is the durable record of who claimed
    what and when, for the queue UI and the audit trail.
    """

    moderator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="review_claims"
    )
    posting = models.ForeignKey(
        "postings.JobPosting", on_delete=models.CASCADE, related_name="review_claims"
    )
    claimed_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    released_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-claimed_at"]
        indexes = [models.Index(fields=["posting", "expires_at"])]

    def __str__(self) -> str:
        return f"{self.moderator} claimed posting #{self.posting_id}"


class Decision(models.Model):
    """A moderator's final call on a ModerationRun."""

    class Action(models.TextChoices):
        APPROVE = "APPROVE", "Approve"
        REJECT = "REJECT", "Reject"
        REQUEST_CHANGES = "REQUEST_CHANGES", "Request changes"
        ESCALATE = "ESCALATE", "Escalate"

    moderator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="decisions"
    )
    run = models.ForeignKey(ModerationRun, on_delete=models.CASCADE, related_name="decisions")

    action = models.CharField(max_length=20, choices=Action.choices)
    reason_code = models.CharField(max_length=64, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.action} on run #{self.run_id} by {self.moderator}"
