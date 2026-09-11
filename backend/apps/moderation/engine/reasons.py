"""Renders a RuleHit into the sentence stored on Flag.reason and shown to
a moderator.

Every rule and the classifier already set `hit.reason` at the point they
find something — this module exists as the one place that's actually
persisted, so a rule that forgets to set a reason still produces a
sensible fallback instead of a blank field a moderator has to guess at.
"""

from __future__ import annotations

from apps.moderation.engine.rules.base import RuleHit

_FALLBACK_TEMPLATE = "Flagged for {category} ({source_label})."

_SOURCE_LABELS = {
    "RULE": "rule match",
    "MODEL": "model prediction",
    "DEDUPE": "duplicate detection",
}


def render_reason(hit: RuleHit) -> str:
    if hit.reason.strip():
        return hit.reason
    category_label = hit.category.value.replace("_", " ").title()
    source_label = _SOURCE_LABELS.get(hit.source, hit.source.lower())
    return _FALLBACK_TEMPLATE.format(category=category_label, source_label=source_label)
