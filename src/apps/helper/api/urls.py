from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ActionViewSet,
    ApplicationViewSet,
    EcosystemViewSet,
    HelperHealthView,
    ServiceViewSet,
    SystemViewSet,
    WhoAmIView,
)

router = DefaultRouter()
router.register("ecosystems", EcosystemViewSet, basename="ecosystem")
router.register("systems", SystemViewSet, basename="system")
router.register("applications", ApplicationViewSet, basename="application")
router.register("services", ServiceViewSet, basename="service")
router.register("actions", ActionViewSet, basename="action")

urlpatterns = [
    path("health/", HelperHealthView.as_view(), name="helper-health"),
    path("me/", WhoAmIView.as_view(), name="helper-me"),
    path("", include(router.urls)),
]
