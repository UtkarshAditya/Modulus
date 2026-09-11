"""Rule protocol and shared types for the moderation engine.

Deliberately framework-agnostic: nothing here imports Django. Rules take a
plain `Submission` (matched by shape, not inheritance) and a `NormalizedDoc`,
and return plain dataclasses. That's what keeps a rule unit-testable with a
one-line fake object instead of a database-backed model instance, and keeps
`apps.moderation.models` a consumer of this module rather than the reverse.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol

from apps.moderation.engine.normalize import NormalizedDoc


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Category(str, Enum):
    ADVANCE_FEE = "ADVANCE_FEE"
    PII_HARVEST = "PII_HARVEST"
    ILLEGAL_WORK = "ILLEGAL_WORK"
    MLM_RECRUITMENT = "MLM_RECRUITMENT"
    OFF_PLATFORM_REDIRECT = "OFF_PLATFORM_REDIRECT"
    DISCRIMINATORY = "DISCRIMINATORY"
    MISLEADING_COMP = "MISLEADING_COMP"
    NO_COMP_DISCLOSURE = "NO_COMP_DISCLOSURE"
    SPAM_DUPLICATE = "SPAM_DUPLICATE"
    GHOST_JOB = "GHOST_JOB"
    KEYWORD_STUFFING = "KEYWORD_STUFFING"


@dataclass(frozen=True)
class Evidence:
    """A span of evidence for a hit, in *original* submission coordinates.

    A zero-length span (start == end == 0) marks field-level evidence —
    e.g. a salary_min/salary_max contradiction — that doesn't correspond
    to a highlightable passage of text.
    """

    start: int
    end: int
    text: str
    note: str = ""

    def to_dict(self) -> dict:
        return {"start": self.start, "end": self.end, "text": self.text, "note": self.note}


@dataclass(frozen=True)
class RuleHit:
    """The one hit type shared by rules and the classifier (Phase 3), so
    Phase 4 fusion can concatenate both without a case split. `source` and
    `contributing_terms` exist for the classifier's benefit — mirrors
    `moderation.models.Flag.Source` — and stay at their defaults for a
    rule-sourced hit.
    """

    rule_id: str
    category: Category
    severity: Severity
    source: str = "RULE"
    confidence: float = 1.0
    evidence: list[Evidence] = field(default_factory=list)
    reason: str = ""
    contributing_terms: list[dict] = field(default_factory=list)


class Submission(Protocol):
    """The minimal shape a rule needs from a JobPosting."""

    title: str
    description: str
    company_name: str
    salary_min: int | None
    salary_max: int | None
    salary_disclosed: bool
    apply_url: str
    contact_email: str


@dataclass
class RuleConfig:
    """Per-rule config sourced from the active Policy. `weight` is carried
    through to score fusion (Phase 4); a disabled rule simply never runs.
    """

    enabled: bool = True
    weight: float = 1.0


class Rule(ABC):
    """A rule is pure and deterministic: same input, same output, no I/O.

    Concrete rules set `id`, `category`, and `default_severity` as class
    attributes and implement `evaluate`.
    """

    id: str
    category: Category
    default_severity: Severity

    @abstractmethod
    def evaluate(self, submission: Submission, doc: NormalizedDoc) -> list[RuleHit]:
        raise NotImplementedError

    def hit(self, evidence: list[Evidence], reason: str) -> RuleHit:
        return RuleHit(
            rule_id=self.id,
            category=self.category,
            severity=self.default_severity,
            evidence=evidence,
            reason=reason,
        )


def run_rules(
    rules: list[Rule],
    submission: Submission,
    doc: NormalizedDoc,
    rule_config: dict[str, RuleConfig] | None = None,
) -> list[RuleHit]:
    """Run every enabled rule and flatten the hits. Rule order doesn't
    matter — each rule only ever reads `submission`/`doc`, never the
    other rules' output.
    """
    rule_config = rule_config or {}
    hits: list[RuleHit] = []
    for rule in rules:
        config = rule_config.get(rule.id, RuleConfig())
        if not config.enabled:
            continue
        hits.extend(rule.evaluate(submission, doc))
    return hits
