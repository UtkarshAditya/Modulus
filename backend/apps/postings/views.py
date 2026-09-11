from rest_framework import mixins, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.moderation.services import submit_for_moderation

from .models import JobPosting
from .permissions import IsOwner
from .serializers import JobPostingSerializer, JobPostingWriteSerializer


class JobPostingViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated, IsOwner]

    def get_queryset(self):
        return (
            JobPosting.objects.filter(submitter=self.request.user)
            .select_related("submitter")
            .prefetch_related("moderation_runs__flags", "moderation_runs__decisions")
        )

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return JobPostingWriteSerializer
        return JobPostingSerializer

    def get_throttles(self):
        if self.action in ("create", "update", "partial_update"):
            self.throttle_scope = "postings-submit"
            return [ScopedRateThrottle()]
        return []

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        posting = serializer.save(submitter=request.user)
        submit_for_moderation(posting, actor=request.user)
        posting.refresh_from_db()
        return Response(JobPostingSerializer(posting).data, status=status.HTTP_202_ACCEPTED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status != JobPosting.Status.CHANGES_REQUESTED:
            return Response(
                {"detail": "This posting can only be edited while changes have been requested."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        posting = serializer.save()
        submit_for_moderation(posting, actor=request.user)
        posting.refresh_from_db()
        return Response(JobPostingSerializer(posting).data)

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)
