from rest_framework.routers import DefaultRouter

from .views import JobPostingViewSet

router = DefaultRouter()
router.register("postings", JobPostingViewSet, basename="posting")

urlpatterns = router.urls
