import pytest

from apps.moderation.factories import (
    DecisionFactory,
    FlagFactory,
    ModerationRunFactory,
    ReviewClaimFactory,
)
from apps.policies.factories import PolicyFactory
from apps.policies.models import Policy
from apps.postings.factories import JobPostingFactory

pytestmark = pytest.mark.django_db


def test_job_posting_factory_produces_a_valid_posting():
    posting = JobPostingFactory()
    assert posting.pk is not None
    assert posting.content_hash == posting.compute_content_hash()


def test_job_posting_content_hash_changes_with_content():
    posting = JobPostingFactory(title="Original title")
    original_hash = posting.content_hash
    posting.title = "Changed title"
    assert posting.compute_content_hash() != original_hash


def test_moderation_run_flag_decision_review_claim_factories():
    run = ModerationRunFactory()
    flag = FlagFactory(run=run)
    decision = DecisionFactory(run=run)
    claim = ReviewClaimFactory(posting=run.posting)

    assert flag.run_id == run.pk
    assert decision.run_id == run.pk
    assert claim.posting_id == run.posting_id
    assert run.flags.count() == 1
    assert run.decisions.count() == 1


def test_policy_create_version_activates_and_deactivates_previous():
    first = PolicyFactory(version=1, is_active=False)
    Policy.objects.activate(first)
    assert Policy.objects.get_active() == first

    second = Policy.objects.create_version(notes="v2")
    first.refresh_from_db()

    assert Policy.objects.get_active() == second
    assert first.is_active is False


def test_policy_rule_config_helpers():
    policy = PolicyFactory(rule_config={"job.advance_fee": {"enabled": False, "weight": 2.0}})
    assert policy.rule_is_enabled("job.advance_fee") is False
    assert policy.rule_weight("job.advance_fee") == 2.0
    # rules absent from rule_config default to enabled, weight 1.0
    assert policy.rule_is_enabled("job.pii_harvest") is True
    assert policy.rule_weight("job.pii_harvest") == 1.0
