from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ActionViewSet,
    ApplicationViewSet,
    EcosystemViewSet,
    HelperHealthView,
    SystemViewSet,
)

router = DefaultRouter()
router.register("ecosystems", EcosystemViewSet, basename="ecosystem")
router.register("systems", SystemViewSet, basename="system")
router.register("applications", ApplicationViewSet, basename="application")
router.register("actions", ActionViewSet, basename="action")

urlpatterns = [
    path("health/", HelperHealthView.as_view(), name="helper-health"),
    path("", include(router.urls)),
]
