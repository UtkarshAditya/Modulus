import factory
from django.utils import timezone

from apps.accounts.factories import ModeratorFactory
from apps.moderation.engine.rules.base import Category, Severity
from apps.postings.factories import JobPostingFactory

from .models import Decision, Flag, ModerationRun, ReviewClaim


class ModerationRunFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ModerationRun

    posting = factory.SubFactory(JobPostingFactory)
    posting_version = factory.LazyAttribute(lambda o: o.posting.version)
    policy_version = 1
    model_version = "none"
    engine_version = "0.1"
    risk_score = 0.1
    routing = ModerationRun.Routing.AUTO_APPROVE
    status = ModerationRun.Status.SUCCEEDED
    started_at = factory.LazyFunction(timezone.now)
    finished_at = factory.LazyFunction(timezone.now)
    duration_ms = 50


class FlagFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Flag

    run = factory.SubFactory(ModerationRunFactory)
    category = Category.ADVANCE_FEE.value
    severity = Severity.CRITICAL.value
    source = Flag.Source.RULE
    confidence = 1.0
    rule_id = "job.advance_fee"
    evidence = factory.LazyFunction(list)
    reason = "Asks the applicant to pay before being hired."


class ReviewClaimFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ReviewClaim

    moderator = factory.SubFactory(ModeratorFactory)
    posting = factory.SubFactory(JobPostingFactory)
    expires_at = factory.LazyFunction(lambda: timezone.now() + timezone.timedelta(minutes=10))


class DecisionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Decision

    moderator = factory.SubFactory(ModeratorFactory)
    run = factory.SubFactory(ModerationRunFactory)
    action = Decision.Action.APPROVE
    reason_code = ""
    notes = ""
