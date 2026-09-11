"""The job-board rule pack — the categories a literal, deterministic
pattern can catch with high precision. `MLM_RECRUITMENT`, `ILLEGAL_WORK`,
and `DISCRIMINATORY` are "rule + model" in the taxonomy; only the rule
half exists until Phase 3 adds the classifier.

Each rule searches `doc.folded` (word-boundary regex, precise spans) or
`doc.collapsed` (substring search, survives an evader inserting separators
or leetspeak between letters) and maps every match back to the original
text before returning it as evidence.
"""

from __future__ import annotations

import re
from collections import Counter

from apps.moderation.engine.normalize import NormalizedDoc
from apps.moderation.engine.rules.base import Category as C
from apps.moderation.engine.rules.base import Evidence, Rule, RuleHit, Severity

_STOPWORDS = {
    "the", "and", "for", "with", "you", "your", "our", "are", "will", "have",
    "this", "that", "from", "work", "job", "team", "role", "must", "able",
    "who", "all", "can", "not", "but", "was", "has", "org", "com", "www",
}  # fmt: skip


def _folded_matches(doc: NormalizedDoc, pattern: re.Pattern) -> list[Evidence]:
    evidence = []
    for m in pattern.finditer(doc.folded):
        span = doc.folded_span_to_original(m.start(), m.end())
        evidence.append(Evidence(span.start, span.end, doc.original_text(span)))
    return evidence


def _collapsed_matches(doc: NormalizedDoc, needles: list[str]) -> list[Evidence]:
    evidence = []
    for needle in needles:
        start = 0
        while (idx := doc.collapsed.find(needle, start)) != -1:
            span = doc.collapsed_span_to_original(idx, idx + len(needle))
            evidence.append(Evidence(span.start, span.end, doc.original_text(span)))
            start = idx + len(needle)
    return evidence


def _field_evidence(note: str, text: str = "") -> list[Evidence]:
    """Zero-length span for a flag sourced from a structured field rather
    than a passage of text — nothing to highlight in the description.
    """
    return [Evidence(0, 0, text, note)]


class AdvanceFeeRule(Rule):
    id = "job.advance_fee"
    category = C.ADVANCE_FEE
    default_severity = Severity.CRITICAL

    _PATTERN = re.compile(
        r"\b("
        r"(registration|processing|training|application|starter kit|onboarding)\s+fee"
        r"|refundable deposit"
        r"|pay\b[^.]{0,40}\b(to (start|begin|get started)|before (you )?(start|begin))"
        r"|send (us )?(a\s)?(payment|money order|wire transfer)"
        r"|purchase (your own |a )?(starter kit|equipment) before"
        r")\b"
    )

    def evaluate(self, submission, doc: NormalizedDoc) -> list[RuleHit]:
        evidence = _folded_matches(doc, self._PATTERN)
        if not evidence:
            return []
        return [self.hit(evidence, "Asks the applicant to pay before being hired.")]


class PiiHarvestRule(Rule):
    id = "job.pii_harvest"
    category = C.PII_HARVEST
    default_severity = Severity.CRITICAL

    _PATTERN = re.compile(
        r"\b(send|provide|email|upload)\b[^.]{0,40}\b"
        r"(your\s+)?(social security( number)?|ssn|bank account(\s+number)?|"
        r"routing number|passport (copy|number)|driver'?s licen[sc]e (copy|number))\b"
    )

    def evaluate(self, submission, doc: NormalizedDoc) -> list[RuleHit]:
        evidence = _folded_matches(doc, self._PATTERN)
        if not evidence:
            return []
        return [self.hit(evidence, "Asks for sensitive personal documents upfront.")]


class IllegalWorkRule(Rule):
    id = "job.illegal_work"
    category = C.ILLEGAL_WORK
    default_severity = Severity.CRITICAL

    _PATTERN = re.compile(
        r"\b("
        r"under the table|off the books|cash in hand,?\s*no taxes|"
        r"no background check required|no questions asked|"
        r"money mule|reshipp?ing\s+packages"
        r")\b"
    )

    def evaluate(self, submission, doc: NormalizedDoc) -> list[RuleHit]:
        evidence = _folded_matches(doc, self._PATTERN)
        if not evidence:
            return []
        return [self.hit(evidence, "Describes work arranged to avoid legal or tax obligations.")]


class MlmRecruitmentRule(Rule):
    id = "job.mlm_recruitment"
    category = C.MLM_RECRUITMENT
    default_severity = Severity.HIGH

    _PATTERN = re.compile(
        r"\b("
        r"be your own boss|unlimited earning potential|"
        r"recruit (your|new) (team|downline|members)|downline|pyramid|"
        r"multi-?level marketing|mlm|"
        r"pay(ing)?\s+a\s+(startup|joining|membership)\s+fee"
        r")\b"
    )

    def evaluate(self, submission, doc: NormalizedDoc) -> list[RuleHit]:
        evidence = _folded_matches(doc, self._PATTERN)
        if not evidence:
            return []
        return [self.hit(evidence, "Uses recruitment-chain / MLM language.")]


class OffPlatformRedirectRule(Rule):
    id = "job.off_platform_redirect"
    category = C.OFF_PLATFORM_REDIRECT
    default_severity = Severity.HIGH

    _NEEDLES = ["whatsapp", "telegram", "wechat", "viber", "signalapp"]
    _CONTACT_PATTERN = re.compile(r"\btext (me|us)\s+(at|on)\b")

    def evaluate(self, submission, doc: NormalizedDoc) -> list[RuleHit]:
        evidence = _collapsed_matches(doc, self._NEEDLES)
        evidence += _folded_matches(doc, self._CONTACT_PATTERN)
        if not evidence:
            return []
        return [self.hit(evidence, "Redirects contact to an off-platform channel.")]


class DiscriminatoryRule(Rule):
    id = "job.discriminatory"
    category = C.DISCRIMINATORY
    default_severity = Severity.HIGH

    _PATTERN = re.compile(
        r"\b("
        r"(only|prefer(?:red)?)\s+(male|female|men|women)\s+(candidates|applicants)|"
        r"no (married|pregnant)\s+(women|applicants|candidates)|"
        r"must be (single|unmarried)|"
        r"must be (under|below)\s?\d{1,2}\s*(years?\s*old)?|"
        r"(christian|muslim|hindu|jewish)s?\s+only"
        r")\b"
    )

    def evaluate(self, submission, doc: NormalizedDoc) -> list[RuleHit]:
        evidence = _folded_matches(doc, self._PATTERN)
        if not evidence:
            return []
        return [self.hit(evidence, "Excludes applicants by a protected characteristic.")]


class MisleadingCompRule(Rule):
    id = "job.misleading_comp"
    category = C.MISLEADING_COMP
    default_severity = Severity.MEDIUM

    def evaluate(self, submission, doc: NormalizedDoc) -> list[RuleHit]:
        lo, hi = submission.salary_min, submission.salary_max
        if lo is None or hi is None:
            return []
        if lo > hi:
            return [
                self.hit(
                    _field_evidence("salary_min is greater than salary_max", f"{lo}–{hi}"),
                    "Salary range is internally contradictory.",
                )
            ]
        if lo > 0 and hi > lo * 20:
            return [
                self.hit(
                    _field_evidence("salary_max is more than 20x salary_min", f"{lo}–{hi}"),
                    "Salary range spread is implausibly wide.",
                )
            ]
        return []


class NoCompDisclosureRule(Rule):
    id = "job.no_comp_disclosure"
    category = C.NO_COMP_DISCLOSURE
    default_severity = Severity.LOW

    def evaluate(self, submission, doc: NormalizedDoc) -> list[RuleHit]:
        if submission.salary_disclosed or submission.salary_min or submission.salary_max:
            return []
        return [
            self.hit(
                _field_evidence("no salary_min, salary_max, or salary_disclosed"),
                "No compensation information was disclosed.",
            )
        ]


class KeywordStuffingRule(Rule):
    id = "job.keyword_stuffing"
    category = C.KEYWORD_STUFFING
    default_severity = Severity.LOW

    _TOKEN = re.compile(r"[a-z][a-z0-9']{3,}")
    _MIN_OCCURRENCES = 8
    _MIN_SHARE = 0.06

    def evaluate(self, submission, doc: NormalizedDoc) -> list[RuleHit]:
        matches = [m for m in self._TOKEN.finditer(doc.folded) if m.group() not in _STOPWORDS]
        total = len(matches)
        if total == 0:
            return []
        counts = Counter(m.group() for m in matches)
        word, count = counts.most_common(1)[0]
        if count < self._MIN_OCCURRENCES or count / total < self._MIN_SHARE:
            return []
        evidence = []
        for m in matches:
            if m.group() != word:
                continue
            span = doc.folded_span_to_original(m.start(), m.end())
            evidence.append(Evidence(span.start, span.end, doc.original_text(span)))
            if len(evidence) == 3:
                break
        return [
            self.hit(
                evidence,
                f"The word '{word}' appears {count} times ({count / total:.0%} of all words).",
            )
        ]


JOB_RULES: list[Rule] = [
    AdvanceFeeRule(),
    PiiHarvestRule(),
    IllegalWorkRule(),
    MlmRecruitmentRule(),
    OffPlatformRedirectRule(),
    DiscriminatoryRule(),
    MisleadingCompRule(),
    NoCompDisclosureRule(),
    KeywordStuffingRule(),
]
