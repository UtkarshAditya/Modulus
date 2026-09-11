"""Score fusion and routing (Phase 4): combines rule, classifier, and
dedupe hits into one risk score and a routing decision, using the active
Policy's thresholds.

The routing rule from docs/PLAN.md, applied in order:
  1. A CRITICAL rule hit with a literal text match (not a field-level or
     model hit) short-circuits straight to AUTO_REJECT.
  2. A score above `auto_reject_above` routes to HUMAN_REVIEW, not
     auto-reject — deliberately conservative; the pipeline never
     auto-rejects on model confidence alone.
  3. A score below `auto_approve_below` with no MEDIUM+ hit at all routes
     to AUTO_APPROVE.
  4. Everything else routes to HUMAN_REVIEW.
"""

from __future__ import annotations

from dataclasses import dataclass

from apps.moderation.engine.rules.base import RuleHit, Severity
from apps.policies.models import Policy

SEVERITY_WEIGHT: dict[Severity, float] = {
    Severity.LOW: 0.15,
    Severity.MEDIUM: 0.35,
    Severity.HIGH: 0.65,
    Severity.CRITICAL: 1.0,
}

_MEDIUM_WEIGHT = SEVERITY_WEIGHT[Severity.MEDIUM]


@dataclass(frozen=True)
class FusionResult:
    risk_score: float
    routing: str  # a ModerationRun.Routing value
    has_literal_critical_hit: bool


def _hit_contribution(hit: RuleHit, policy: Policy) -> float:
    base = SEVERITY_WEIGHT[hit.severity]
    weight = policy.rule_weight(hit.rule_id) if hit.source == "RULE" else 1.0
    # A model hit's own confidence further scales its contribution — a
    # classifier hit that barely cleared its threshold shouldn't weigh as
    # much as one the model is very sure about. Rule hits are already
    # deterministic (confidence 1.0), so this is a no-op for them.
    return min(1.0, base * weight * hit.confidence)


def _combine(contributions: list[float]) -> float:
    """Noisy-OR: each hit is treated as an independent piece of evidence
    that the posting is bad, so the combined score is the probability
    that *at least one* of them is right — several MEDIUM hits compound
    into something more serious, rather than the score just tracking
    whichever single hit is worst.
    """
    if not contributions:
        return 0.0
    survives_all = 1.0
    for c in contributions:
        survives_all *= 1.0 - c
    return round(1.0 - survives_all, 4)


def fuse(hits: list[RuleHit], policy: Policy) -> FusionResult:
    risk_score = _combine([_hit_contribution(h, policy) for h in hits])

    has_literal_critical_hit = any(
        h.severity == Severity.CRITICAL
        and h.source == "RULE"
        and any(e.start != e.end for e in h.evidence)
        for h in hits
    )
    has_medium_plus_hit = any(SEVERITY_WEIGHT[h.severity] >= _MEDIUM_WEIGHT for h in hits)

    thresholds = policy.thresholds or {}
    auto_approve_below = thresholds.get("auto_approve_below", 0.2)
    auto_reject_above = thresholds.get("auto_reject_above", 0.85)

    if has_literal_critical_hit:
        routing = "AUTO_REJECT"
    elif risk_score > auto_reject_above:
        routing = "HUMAN_REVIEW"
    elif risk_score < auto_approve_below and not has_medium_plus_hit:
        routing = "AUTO_APPROVE"
    else:
        routing = "HUMAN_REVIEW"

    return FusionResult(
        risk_score=risk_score, routing=routing, has_literal_critical_hit=has_literal_critical_hit
    )
