from django.db.models import Exists, F, OuterRef, Subquery
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.moderation.services import apply_decision
from apps.postings.models import JobPosting

from .claims import acquire_claim, release_claim
from .models import Decision, Flag, ModerationRun
from .permissions import IsModeratorOrAdmin
from .serializers import (
    CasePostingSerializer,
    DecisionCreateSerializer,
    DecisionSerializer,
    FlagSerializer,
    QueuePostingSerializer,
)


def get_queue_queryset(params):
    """The IN_REVIEW queue, annotated with the *latest* run's risk_score
    and routing so filtering/ordering happens at the DB level rather than
    pulling every posting's full run history into Python.
    """
    latest_run_qs = ModerationRun.objects.filter(posting=OuterRef("pk")).order_by(
        "-started_at", "-id"
    )
    escalated_qs = Decision.objects.filter(
        run__posting=OuterRef("pk"), action=Decision.Action.ESCALATE
    )
    queryset = (
        JobPosting.objects.filter(status=JobPosting.Status.IN_REVIEW)
        .select_related("submitter")
        .annotate(
            latest_run_id=Subquery(latest_run_qs.values("id")[:1]),
            risk_score=Subquery(latest_run_qs.values("risk_score")[:1]),
            routing=Subquery(latest_run_qs.values("routing")[:1]),
            # A posting an earlier moderator escalated stays IN_REVIEW —
            # this is the only thing that distinguishes "someone already
            # looked at this and wanted a second opinion" from a fresh case.
            is_escalated=Exists(escalated_qs),
        )
    )

    category = params.get("category")
    severity = params.get("severity")
    if category or severity:
        # One filter() call so both conditions apply to the same joined
        # flag row, and that row belongs to the posting's *latest* run —
        # chaining separate .filter() calls here could each match a
        # different (possibly older) run's flags instead.
        same_run_filter = {"moderation_runs__id": F("latest_run_id")}
        if category:
            same_run_filter["moderation_runs__flags__category"] = category
        if severity:
            same_run_filter["moderation_runs__flags__severity"] = severity
        queryset = queryset.filter(**same_run_filter)

    min_score = params.get("min_score")
    if min_score is not None:
        queryset = queryset.filter(risk_score__gte=float(min_score))
    max_score = params.get("max_score")
    if max_score is not None:
        queryset = queryset.filter(risk_score__lte=float(max_score))

    ordering = params.get("ordering") or "submitted_at"  # oldest first = highest SLA risk
    if not params.get("ordering"):
        # Escalated cases jump the queue by default — a second-opinion
        # request from another moderator outranks a fresh case's age.
        return queryset.order_by("-is_escalated", ordering, "id").distinct()
    return queryset.order_by(ordering, "id").distinct()


class ModerationQueueViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = QueuePostingSerializer
    permission_classes = [IsModeratorOrAdmin]

    def get_queryset(self):
        return get_queue_queryset(self.request.query_params)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        postings = page if page is not None else list(queryset)

        # Batch-load the latest run's flags for every posting on this page
        # in one query instead of one query per row.
        latest_run_ids = [p.latest_run_id for p in postings if p.latest_run_id]
        flags_by_run: dict[int, list[Flag]] = {}
        for flag in Flag.objects.filter(run_id__in=latest_run_ids):
            flags_by_run.setdefault(flag.run_id, []).append(flag)
        for posting in postings:
            posting._prefetched_top_flags = flags_by_run.get(posting.latest_run_id, [])

        serializer = self.get_serializer(postings, many=True)
        data = serializer.data
        if page is not None:
            return self.get_paginated_response(data)
        return Response(data)

    @action(detail=True, methods=["post"])
    def claim(self, request, pk=None):
        posting = get_object_or_404(JobPosting, pk=pk, status=JobPosting.Status.IN_REVIEW)
        result = acquire_claim(posting.pk, request.user)
        if not result.success:
            return Response(
                {"detail": "This posting is already claimed.", "held_by": result.held_by},
                status=status.HTTP_409_CONFLICT,
            )
        return Response({"expires_at": result.expires_at})

    @action(detail=True, methods=["post"])
    def release(self, request, pk=None):
        posting = get_object_or_404(JobPosting, pk=pk)
        released = release_claim(posting.pk, request.user)
        if not released:
            return Response(
                {"detail": "You don't hold this claim."}, status=status.HTTP_403_FORBIDDEN
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class ModerationPostingViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = JobPosting.objects.select_related("submitter").prefetch_related(
        "moderation_runs__flags", "moderation_runs__decisions"
    )
    serializer_class = CasePostingSerializer
    permission_classes = [IsModeratorOrAdmin]

    @action(detail=True, methods=["post"])
    def decide(self, request, pk=None):
        posting = self.get_object()
        serializer = DecisionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            decision = apply_decision(posting, moderator=request.user, **serializer.validated_data)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(DecisionSerializer(decision).data, status=status.HTTP_201_CREATED)


class FlagViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Flag.objects.all()
    serializer_class = FlagSerializer
    permission_classes = [IsModeratorOrAdmin]

    @action(detail=True, methods=["post"], url_path="false-positive")
    def false_positive(self, request, pk=None):
        flag = self.get_object()
        flag.is_false_positive = True
        flag.save(update_fields=["is_false_positive"])
        return Response(FlagSerializer(flag).data)
