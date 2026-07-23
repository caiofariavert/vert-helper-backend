from django.db import connections
from django.db.utils import OperationalError
from django.db.models import Exists, OuterRef
from rest_framework import mixins, status, viewsets
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend

from apps.helper.models import Action, Application, Ecosystem, Service, System

from .filters import (
    ActionFilter,
    ApplicationFilter,
    EcosystemFilter,
    SystemFilter,
)
from .permissions import IsSuperUser
from .serializers import (
    ActionDetailSerializer,
    ActionExecuteSerializer,
    ActionListSerializer,
    ApplicationSerializer,
    EcosystemSerializer,
    SystemSerializer,
)
from .services import execute_action


# ---------------------------------------------------------------------------
# Health endpoints
# ---------------------------------------------------------------------------


class HelperHealthView(APIView):
    """Saúde interna do próprio serviço Helper (sem autenticação)."""

    permission_classes = [AllowAny]

    def get(self, request):
        try:
            connections["default"].ensure_connection()
        except OperationalError as exc:
            return Response({"status": "failed", "message": str(exc)}, status=503)
        return Response({"status": "ok"})


# ---------------------------------------------------------------------------
# Base ViewSet
# ---------------------------------------------------------------------------


class SuperUserReadOnlyViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """ViewSet de leitura restrito a superusuários."""

    permission_classes = [IsSuperUser]
    filter_backends = [DjangoFilterBackend, OrderingFilter]


# ---------------------------------------------------------------------------
# Ecossistemas
# ---------------------------------------------------------------------------


class EcosystemViewSet(SuperUserReadOnlyViewSet):
    serializer_class = EcosystemSerializer
    filterset_class = EcosystemFilter
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]
    lookup_field = "slug"

    def get_queryset(self):
        return Ecosystem.objects.all()


# ---------------------------------------------------------------------------
# Sistemas
# ---------------------------------------------------------------------------


class SystemViewSet(SuperUserReadOnlyViewSet):
    serializer_class = SystemSerializer
    filterset_class = SystemFilter
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]
    lookup_field = "slug"

    def get_queryset(self):
        return System.objects.prefetch_related("ecosystems").all()


# ---------------------------------------------------------------------------
# Aplicações
# ---------------------------------------------------------------------------


class ApplicationViewSet(SuperUserReadOnlyViewSet):
    serializer_class = ApplicationSerializer
    filterset_class = ApplicationFilter
    ordering_fields = ["name", "environment", "created_at"]
    ordering = ["name"]
    lookup_field = "slug"

    def get_queryset(self):
        return Application.objects.select_related("system").all()


# ---------------------------------------------------------------------------
# Ações
# ---------------------------------------------------------------------------


class ActionViewSet(SuperUserReadOnlyViewSet):
    filterset_class = ActionFilter
    ordering_fields = ["name", "created_at", "is_recommended"]
    ordering = ["-is_recommended", "name"]
    lookup_field = "slug"

    def get_queryset(self):
        failed_service = Service.objects.filter(
            actions=OuterRef("pk"),
            status=Service.STATUS_FAILED,
            deleted_at__isnull=True,
        )
        return (
            Action.objects.select_related("application")
            .prefetch_related("services")
            .annotate(is_recommended=Exists(failed_service))
            .order_by("-is_recommended", "name")
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ActionDetailSerializer
        if self.action == "execute":
            return ActionExecuteSerializer
        return ActionListSerializer

    @action(detail=True, methods=["post"], url_path="execute")
    def execute(self, request, slug=None):
        action_obj = self.get_object()

        serializer = ActionExecuteSerializer(
            data=request.data,
            action_schema=action_obj.questions_schema,
        )
        serializer.is_valid(raise_exception=True)

        result = execute_action(
            action=action_obj,
            mapped_kwargs=serializer.validated_data["mapped_kwargs"],
            input_payload=request.data,
            user=request.user,
        )

        http_status = status.HTTP_200_OK
        if result.get("status") == "error":
            http_status = status.HTTP_422_UNPROCESSABLE_ENTITY

        return Response(result, status=http_status)
