from django.conf import settings
from django.db import models


class AuditEvent(models.Model):
    """Append-only log of everything that changes moderation-relevant
    state. Deliberately not a ForeignKey to the objects it describes —
    `object_type` + `object_id` are plain strings so the log outlives the
    object (a deleted posting still has a history) and can point at any
    model without a union of nullable FKs.
    """

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
        help_text="Null for system-initiated events (e.g. the moderation pipeline itself).",
    )
    action = models.CharField(
        max_length=100, help_text="e.g. 'posting.submitted', 'decision.approve'"
    )
    object_type = models.CharField(max_length=100, help_text="e.g. 'postings.JobPosting'")
    object_id = models.CharField(max_length=64)

    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)

    ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["object_type", "object_id"]),
            models.Index(fields=["action"]),
        ]

    def __str__(self) -> str:
        return f"{self.action} on {self.object_type}#{self.object_id}"
