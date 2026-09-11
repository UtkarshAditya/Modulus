from django.conf import settings
from django.db import models, transaction

DEFAULT_THRESHOLDS = {
    "auto_approve_below": 0.2,
    "auto_reject_above": 0.85,
    "category_overrides": {},
}


class PolicyManager(models.Manager):
    def get_active(self) -> "Policy | None":
        return self.filter(is_active=True).order_by("-version").first()

    @transaction.atomic
    def create_version(
        self, *, thresholds=None, rule_config=None, notes="", created_by=None, activate=True
    ):
        """Create a new policy version. Policies are never edited in place —
        every change is a new row, so any ModerationRun's recorded
        policy_version always points at an immutable snapshot.
        """
        last_version = self.aggregate(models.Max("version"))["version__max"] or 0
        policy = self.create(
            version=last_version + 1,
            thresholds=thresholds if thresholds is not None else DEFAULT_THRESHOLDS,
            rule_config=rule_config if rule_config is not None else {},
            notes=notes,
            created_by=created_by,
            is_active=False,
        )
        if activate:
            self.activate(policy)
        return policy

    @transaction.atomic
    def activate(self, policy: "Policy") -> None:
        self.exclude(pk=policy.pk).filter(is_active=True).update(is_active=False)
        policy.is_active = True
        policy.save(update_fields=["is_active"])


class Policy(models.Model):
    """A versioned bundle of routing thresholds and rule enable/weight
    config. Editable by an admin without a deploy — see PolicyManager,
    which enforces "new version, never edit in place" and "exactly one
    active version" as the only ways to change one.
    """

    version = models.PositiveIntegerField(unique=True)
    is_active = models.BooleanField(default=False)

    # {"auto_approve_below": float, "auto_reject_above": float,
    #  "category_overrides": {category: {"auto_approve_below": float, ...}}}
    thresholds = models.JSONField(default=dict)

    # {rule_id: {"enabled": bool, "weight": float}}
    rule_config = models.JSONField(default=dict, blank=True)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    objects = PolicyManager()

    class Meta:
        ordering = ["-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["is_active"],
                condition=models.Q(is_active=True),
                name="policies_only_one_active_policy",
            )
        ]

    def __str__(self) -> str:
        return f"Policy v{self.version}{' (active)' if self.is_active else ''}"

    def rule_is_enabled(self, rule_id: str) -> bool:
        return self.rule_config.get(rule_id, {}).get("enabled", True)

    def rule_weight(self, rule_id: str) -> float:
        return self.rule_config.get(rule_id, {}).get("weight", 1.0)
