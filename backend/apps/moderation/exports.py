"""Exports moderator decisions into labelled training examples for the
Phase 3 classifier. Retraining itself stays a deliberate manual
`python ml/train.py` command per docs/PLAN.md — this only grows the pool
of real labelled examples sitting alongside the synthetic seed corpus,
so a human still looks at the eval report before anything gets promoted.

Labeling heuristic, deliberately conservative — only two outcomes carry
a clear enough signal to use:

- REJECTED: the model-category flags still standing on the posting's
  latest run (excluding anything a moderator explicitly marked as a
  false positive) become confirmed positive labels.
- APPROVED: a human looked at this and approved it anyway, so every
  model-category flag on it is a negative example for that category —
  this is the actual point of the loop, teaching the classifier what it
  got wrong.
- Everything else (CHANGES_REQUESTED, ESCALATE, still pending/in review,
  or a run that never completed) has no clear terminal signal yet and
  is skipped.
"""

from __future__ import annotations

import json
from pathlib import Path

from apps.moderation.engine.classifier import MODEL_CATEGORIES
from apps.moderation.models import ModerationRun
from apps.postings.models import JobPosting

MODEL_CATEGORY_VALUES = {c.value for c in MODEL_CATEGORIES}

EXPORT_PATH = Path(__file__).resolve().parents[2] / "ml" / "data" / "exported_labels.jsonl"

# JobPosting.Status -> whether it's a REJECT-like or APPROVE-like outcome
# for labeling purposes.
_REJECT_LIKE = {JobPosting.Status.REJECTED}
_APPROVE_LIKE = {JobPosting.Status.APPROVED}


def derive_labels(posting: JobPosting) -> list[str] | None:
    """The model-category labels this posting should train with, or None
    if it has no usable terminal signal yet.
    """
    if posting.status in _APPROVE_LIKE:
        return []
    if posting.status not in _REJECT_LIKE:
        return None

    run = posting.moderation_runs.order_by("-started_at", "-id").first()
    if run is None or run.status != ModerationRun.Status.SUCCEEDED:
        return None

    flagged = run.flags.filter(
        category__in=MODEL_CATEGORY_VALUES, is_false_positive=False
    ).values_list("category", flat=True)
    return sorted(set(flagged))


def export_examples() -> list[dict]:
    postings = JobPosting.objects.filter(status__in=_REJECT_LIKE | _APPROVE_LIKE).prefetch_related(
        "moderation_runs__flags"
    )

    examples = []
    for posting in postings:
        labels = derive_labels(posting)
        if labels is None:
            continue
        examples.append(
            {
                "title": posting.title,
                "description": posting.description,
                "company_name": posting.company_name,
                "salary_min": posting.salary_min,
                "salary_max": posting.salary_max,
                "salary_disclosed": posting.salary_disclosed,
                "labels": labels,
                # Provenance only — ml/train.py's loader ignores unknown
                # fields, but this makes the export auditable.
                "source_posting_id": posting.pk,
                "source_posting_version": posting.version,
            }
        )
    return examples


def write_export(path: Path = EXPORT_PATH) -> int:
    """Regenerates the export from scratch (not an append) so a flag
    that gets marked false-positive after an earlier export doesn't
    leave a stale, now-wrong label sitting in the file.
    """
    examples = export_examples()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for example in examples:
            f.write(json.dumps(example) + "\n")
    return len(examples)
