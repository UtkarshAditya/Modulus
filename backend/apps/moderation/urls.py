from rest_framework.routers import DefaultRouter

from .views import FlagViewSet, ModerationPostingViewSet, ModerationQueueViewSet

router = DefaultRouter()
router.register("moderation/queue", ModerationQueueViewSet, basename="moderation-queue")
router.register("moderation/postings", ModerationPostingViewSet, basename="moderation-posting")
router.register("moderation/flags", FlagViewSet, basename="moderation-flag")

urlpatterns = router.urls
