from rest_framework import serializers

from .models import JobPosting

WRITABLE_FIELDS = [
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
]

# Only these statuses show the submitter *why* — everything else (still
# pending, or a moderator approved it outright) has nothing to explain.
_STATUSES_WITH_REVIEW_SUMMARY = {
    JobPosting.Status.AUTO_REJECTED,
    JobPosting.Status.REJECTED,
    JobPosting.Status.CHANGES_REQUESTED,
}


class JobPostingWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPosting
        fields = WRITABLE_FIELDS

    def validate(self, attrs):
        salary_min = attrs.get("salary_min", getattr(self.instance, "salary_min", None))
        salary_max = attrs.get("salary_max", getattr(self.instance, "salary_max", None))
        if salary_min is not None and salary_max is not None and salary_min > salary_max:
            raise serializers.ValidationError(
                {"salary_max": "salary_max must be greater than or equal to salary_min."}
            )
        return attrs


class JobPostingSerializer(serializers.ModelSerializer):
    """The submitter-facing read view. Deliberately excludes risk_score,
    confidence, contributing_terms, and rule internals — a submitter sees
    that something was flagged and why in plain language, never the raw
    model output, per the plan's frontend design.
    """

    submitter = serializers.CharField(source="submitter.username", read_only=True)
    review_summary = serializers.SerializerMethodField()
    latest_decision = serializers.SerializerMethodField()

    class Meta:
        model = JobPosting
        fields = [
            "id",
            "submitter",
            *WRITABLE_FIELDS,
            "status",
            "version",
            "submitted_at",
            "decided_at",
            "created_at",
            "updated_at",
            "review_summary",
            "latest_decision",
        ]
        read_only_fields = fields

    def _latest_run(self, posting):
        if not hasattr(posting, "_prefetched_latest_run"):
            posting._prefetched_latest_run = posting.moderation_runs.order_by(
                "-started_at", "-id"
            ).first()
        return posting._prefetched_latest_run

    def get_review_summary(self, posting):
        if posting.status not in _STATUSES_WITH_REVIEW_SUMMARY:
            return None
        run = self._latest_run(posting)
        if run is None:
            return None
        flags = run.flags.exclude(severity="LOW").order_by("-severity")
        return [
            {
                "category": flag.category,
                "severity": flag.severity,
                "reason": flag.reason,
                "evidence": [
                    {"start": e["start"], "end": e["end"], "text": e["text"]}
                    for e in flag.evidence
                    if e.get("text")
                ],
            }
            for flag in flags
        ]

    def get_latest_decision(self, posting):
        if posting.status != JobPosting.Status.CHANGES_REQUESTED:
            return None
        run = self._latest_run(posting)
        if run is None:
            return None
        decision = run.decisions.order_by("-created_at").first()
        if decision is None:
            return None
        return {"reason_code": decision.reason_code, "notes": decision.notes}
