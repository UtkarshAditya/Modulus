"""Phase 7 verification: moderator decisions turn into labelled training
examples with the conservative heuristic documented in
apps/moderation/exports.py — only APPROVED/REJECTED carry a clear enough
signal, false-positive-marked flags don't count as confirmed positives,
and the file is regenerated from scratch each time.
"""

import json

import pytest

from apps.moderation.exports import derive_labels, export_examples, write_export
from apps.moderation.factories import FlagFactory, ModerationRunFactory
from apps.moderation.models import ModerationRun
from apps.postings.factories import JobPostingFactory
from apps.postings.models import JobPosting

pytestmark = pytest.mark.django_db


def _posting_with_run(status, flag_kwargs_list):
    posting = JobPostingFactory(status=status)
    run = ModerationRunFactory(posting=posting, status=ModerationRun.Status.SUCCEEDED)
    for kwargs in flag_kwargs_list:
        FlagFactory(run=run, **kwargs)
    return posting


def test_approved_posting_yields_empty_labels():
    posting = _posting_with_run(
        JobPosting.Status.APPROVED, [{"category": "MLM_RECRUITMENT", "source": "MODEL"}]
    )
    assert derive_labels(posting) == []


def test_rejected_posting_yields_its_model_category_flags():
    posting = _posting_with_run(
        JobPosting.Status.REJECTED,
        [
            {"category": "MLM_RECRUITMENT", "source": "MODEL"},
            {"category": "GHOST_JOB", "source": "MODEL"},
            {"category": "ADVANCE_FEE", "source": "RULE"},  # not a model category, excluded
        ],
    )
    assert derive_labels(posting) == ["GHOST_JOB", "MLM_RECRUITMENT"]


def test_false_positive_flags_are_excluded_from_rejected_labels():
    posting = _posting_with_run(
        JobPosting.Status.REJECTED,
        [
            {"category": "MLM_RECRUITMENT", "source": "MODEL", "is_false_positive": True},
            {"category": "GHOST_JOB", "source": "MODEL"},
        ],
    )
    assert derive_labels(posting) == ["GHOST_JOB"]


@pytest.mark.parametrize(
    "status",
    [
        JobPosting.Status.CHANGES_REQUESTED,
        JobPosting.Status.IN_REVIEW,
        JobPosting.Status.PENDING,
        JobPosting.Status.DRAFT,
    ],
)
def test_non_terminal_statuses_have_no_signal(status):
    posting = JobPostingFactory(status=status)
    assert derive_labels(posting) is None


def test_write_export_regenerates_the_file_from_scratch(tmp_path):
    approved = _posting_with_run(JobPosting.Status.APPROVED, [])
    rejected = _posting_with_run(
        JobPosting.Status.REJECTED, [{"category": "ILLEGAL_WORK", "source": "RULE"}]
    )
    JobPostingFactory(status=JobPosting.Status.DRAFT)  # no signal, must be excluded

    path = tmp_path / "exported.jsonl"
    count = write_export(path)
    assert count == 2

    lines = [json.loads(line) for line in path.read_text().splitlines()]
    by_id = {line["source_posting_id"]: line for line in lines}
    assert by_id[approved.pk]["labels"] == []
    assert by_id[rejected.pk]["labels"] == ["ILLEGAL_WORK"]

    # Regenerating drops anything that no longer qualifies.
    approved.delete()
    count = write_export(path)
    assert count == 1


def test_export_examples_are_shaped_for_ml_train_loader():
    posting = _posting_with_run(JobPosting.Status.APPROVED, [])
    examples = export_examples()
    example = next(e for e in examples if e["source_posting_id"] == posting.pk)
    for field in ("title", "description", "labels"):
        assert field in example
