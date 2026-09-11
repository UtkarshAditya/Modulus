from rest_framework import serializers

from apps.moderation.claims import get_claim_holder
from apps.postings.models import JobPosting

from .models import Decision, Flag, ModerationRun

DECIDABLE_ACTIONS = [
    Decision.Action.APPROVE,
    Decision.Action.REJECT,
    Decision.Action.REQUEST_CHANGES,
    Decision.Action.ESCALATE,
]


class FlagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Flag
        fields = [
            "id",
            "category",
            "severity",
            "source",
            "confidence",
            "rule_id",
            "evidence",
            "reason",
            "contributing_terms",
            "is_false_positive",
            "created_at",
        ]
        read_only_fields = fields


class ModerationRunSerializer(serializers.ModelSerializer):
    flags = FlagSerializer(many=True, read_only=True)

    class Meta:
        model = ModerationRun
        fields = [
            "id",
            "posting_version",
            "policy_version",
            "model_version",
            "engine_version",
            "risk_score",
            "routing",
            "status",
            "error",
            "started_at",
            "finished_at",
            "duration_ms",
            "flags",
        ]
        read_only_fields = fields


class DecisionSerializer(serializers.ModelSerializer):
    moderator = serializers.CharField(source="moderator.username", read_only=True)

    class Meta:
        model = Decision
        fields = ["id", "run", "moderator", "action", "reason_code", "notes", "created_at"]
        read_only_fields = fields


class DecisionCreateSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=[a.value for a in DECIDABLE_ACTIONS])
    reason_code = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class QueuePostingSerializer(serializers.Serializer):
    """One row in the moderator queue — built from an annotated
    JobPosting queryset (see views.get_queue_queryset), not a plain
    ModelSerializer, since risk_score/routing come from an annotation.
    """

    id = serializers.IntegerField()
    title = serializers.CharField()
    company_name = serializers.CharField()
    submitter = serializers.CharField(source="submitter.username")
    status = serializers.CharField()
    submitted_at = serializers.DateTimeField()
    risk_score = serializers.FloatField(allow_null=True)
    routing = serializers.CharField(allow_null=True, allow_blank=True)
    top_category = serializers.SerializerMethodField()
    flag_count = serializers.SerializerMethodField()
    claimed_by = serializers.SerializerMethodField()

    def get_top_category(self, posting):
        flags = getattr(posting, "_prefetched_top_flags", None)
        if not flags:
            return None
        order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        return min(flags, key=lambda f: order.get(f.severity, 99)).category

    def get_flag_count(self, posting):
        flags = getattr(posting, "_prefetched_top_flags", None)
        return len(flags) if flags else 0

    def get_claimed_by(self, posting):
        return get_claim_holder(posting.id)


class CasePostingSerializer(serializers.ModelSerializer):
    """The full case file a moderator sees — unlike the submitter-facing
    serializer in apps.postings, this one has nothing to hide: risk
    scores, confidence, contributing terms, all of it.
    """

    submitter = serializers.CharField(source="submitter.username", read_only=True)
    runs = serializers.SerializerMethodField()
    claimed_by = serializers.SerializerMethodField()

    class Meta:
        model = JobPosting
        fields = [
            "id",
            "submitter",
            "company_name",
            "title",
            "description",
            "location",
            "employment_type",
            "salary_min",
            "salary_max",
            "currency",
            "salary_disclosed",
            "apply_url",
            "contact_email",
            "status",
            "version",
            "submitted_at",
            "decided_at",
            "runs",
            "claimed_by",
        ]
        read_only_fields = fields

    def get_runs(self, posting):
        runs = posting.moderation_runs.order_by("-started_at", "-id")
        return ModerationRunSerializer(runs, many=True).data

    def get_claimed_by(self, posting):
        return get_claim_holder(posting.id)
