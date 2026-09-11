"""The one place the rules engine touches Django: turning the active
Policy row into the plain `RuleConfig` mapping `run_rules` expects. Keeps
`apps.moderation.engine` itself free of ORM imports.
"""

from __future__ import annotations

from apps.moderation.engine.rules.base import RuleConfig
from apps.policies.models import Policy


def get_active_policy() -> Policy:
    """Return the active policy, creating a default v1 if none exists yet
    (a fresh install, or a test that didn't seed one).
    """
    policy = Policy.objects.get_active()
    if policy is not None:
        return policy
    return Policy.objects.create_version(notes="Default policy, auto-created.")


def get_rule_config(policy: Policy, rule_ids: list[str]) -> dict[str, RuleConfig]:
    return {
        rule_id: RuleConfig(
            enabled=policy.rule_is_enabled(rule_id),
            weight=policy.rule_weight(rule_id),
        )
        for rule_id in rule_ids
    }
