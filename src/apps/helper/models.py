import uuid

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class SoftDeleteManager(models.Manager):
    """Retorna apenas registros não deletados."""

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class AllObjectsManager(models.Manager):
    """Retorna todos os registros, incluindo os soft-deletados."""


class BaseModel(models.Model):
    """Model base com UUID, soft delete e timestamps."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="Deletado em")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.is_active = False
        self.save(update_fields=["deleted_at", "is_active", "updated_at"])

    def restore(self):
        self.deleted_at = None
        self.is_active = True
        self.save(update_fields=["deleted_at", "is_active", "updated_at"])


# ---------------------------------------------------------------------------
# Domínio principal
# ---------------------------------------------------------------------------


class Ecosystem(BaseModel):
    name = models.CharField(max_length=255, verbose_name="Nome")
    slug = models.SlugField(max_length=255, unique=True, verbose_name="Slug")

    class Meta:
        verbose_name = "Ecossistema"
        verbose_name_plural = "Ecossistemas"
        ordering = ["name"]

    def __str__(self):
        return self.name


class System(BaseModel):
    name = models.CharField(max_length=255, verbose_name="Nome")
    slug = models.SlugField(max_length=255, unique=True, verbose_name="Slug")
    description = models.TextField(blank=True, verbose_name="Descrição")
    ecosystems = models.ManyToManyField(
        Ecosystem,
        related_name="systems",
        blank=True,
        verbose_name="Ecossistemas",
    )
    administrators = models.ManyToManyField(
        User,
        related_name="administered_systems",
        blank=True,
        verbose_name="Administradores",
    )

    class Meta:
        verbose_name = "Sistema"
        verbose_name_plural = "Sistemas"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Application(BaseModel):
    ENVIRONMENT_STG = "STG"
    ENVIRONMENT_HML = "HML"
    ENVIRONMENT_PRD = "PRD"
    ENVIRONMENT_CHOICES = [
        (ENVIRONMENT_STG, "Staging"),
        (ENVIRONMENT_HML, "Homologação"),
        (ENVIRONMENT_PRD, "Produção"),
    ]

    AUTH_NONE = "NONE"
    AUTH_BEARER = "BEARER"
    AUTH_JWT = "JWT"
    AUTH_TYPE_CHOICES = [
        (AUTH_NONE, "Sem autenticação"),
        (AUTH_BEARER, "Bearer"),
        (AUTH_JWT, "JWT"),
    ]

    name = models.CharField(max_length=255, verbose_name="Nome")
    slug = models.SlugField(max_length=255, unique=True, verbose_name="Slug")
    base_url = models.URLField(max_length=500, verbose_name="URL Base")
    environment = models.CharField(
        max_length=3,
        choices=ENVIRONMENT_CHOICES,
        verbose_name="Ambiente",
    )
    auth_type = models.CharField(
        max_length=10,
        choices=AUTH_TYPE_CHOICES,
        default=AUTH_NONE,
        verbose_name="Tipo de autenticação",
        help_text="Prefixo usado no header Authorization ao chamar as APIs externas.",
    )
    system = models.ForeignKey(
        System,
        on_delete=models.PROTECT,
        related_name="applications",
        verbose_name="Sistema",
    )

    class Meta:
        verbose_name = "Aplicação"
        verbose_name_plural = "Aplicações"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.environment})"


class Service(BaseModel):
    STATUS_OK = "OK"
    STATUS_FAILED = "FAILED"
    STATUS_UNKNOWN = "UNKNOWN"
    STATUS_CHOICES = [
        (STATUS_OK, "OK"),
        (STATUS_FAILED, "Falha"),
        (STATUS_UNKNOWN, "Desconhecido"),
    ]

    name = models.CharField(max_length=255, verbose_name="Nome")
    description = models.TextField(blank=True, verbose_name="Descrição")
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_UNKNOWN,
        verbose_name="Status",
    )
    last_checked_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Última verificação"
    )
    last_status_change_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Última mudança de status"
    )
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="services",
        verbose_name="Aplicação",
    )

    class Meta:
        verbose_name = "Serviço"
        verbose_name_plural = "Serviços"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["application", "name"],
                condition=models.Q(deleted_at__isnull=True),
                name="unique_active_service_name_per_application",
            )
        ]

    def __str__(self):
        return f"{self.application.name} / {self.name}"


class Action(BaseModel):
    slug = models.SlugField(max_length=255, verbose_name="Slug")
    name = models.CharField(max_length=255, verbose_name="Nome")
    description = models.TextField(blank=True, verbose_name="Descrição")
    questions_schema = models.JSONField(
        default=list, blank=True, verbose_name="Schema de perguntas"
    )
    source_version = models.PositiveIntegerField(
        default=1, verbose_name="Versão da origem"
    )
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="actions",
        verbose_name="Aplicação",
    )
    services = models.ManyToManyField(
        Service,
        related_name="actions",
        blank=True,
        verbose_name="Serviços relacionados",
    )

    class Meta:
        verbose_name = "Ação"
        verbose_name_plural = "Ações"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["application", "slug"],
                condition=models.Q(deleted_at__isnull=True),
                name="unique_active_action_slug_per_application",
            )
        ]

    def __str__(self):
        return f"{self.application.name} / {self.name}"


# ---------------------------------------------------------------------------
# Operacional e logs
# ---------------------------------------------------------------------------


class Incident(models.Model):
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="incidents",
        verbose_name="Serviço",
    )
    previous_status = models.CharField(
        max_length=10, verbose_name="Status anterior"
    )
    current_status = models.CharField(max_length=10, verbose_name="Status atual")
    opened_at = models.DateTimeField(auto_now_add=True, verbose_name="Aberto em")
    recovered_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Recuperado em"
    )
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    notification_sent_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Notificação enviada em"
    )
    recovery_notification_sent_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Notif. recuperação enviada em"
    )

    class Meta:
        verbose_name = "Incidente"
        verbose_name_plural = "Incidentes"
        ordering = ["-opened_at"]

    def __str__(self):
        return f"{self.service} — {self.current_status} ({self.opened_at:%Y-%m-%d %H:%M})"


class HealthCheckLog(models.Model):
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="health_logs",
        verbose_name="Aplicação",
    )
    service_name = models.CharField(max_length=255, verbose_name="Serviço")
    status = models.CharField(max_length=10, verbose_name="Status")
    message = models.TextField(blank=True, verbose_name="Mensagem")
    checked_at = models.DateTimeField(auto_now_add=True, verbose_name="Verificado em")
    raw_payload = models.JSONField(
        default=dict, blank=True, verbose_name="Payload bruto"
    )

    class Meta:
        verbose_name = "Log de Health Check"
        verbose_name_plural = "Logs de Health Check"
        ordering = ["-checked_at"]
        indexes = [
            models.Index(fields=["application", "checked_at"]),
            models.Index(fields=["checked_at"]),
        ]

    def __str__(self):
        return (
            f"{self.application.name} / {self.service_name} — "
            f"{self.status} ({self.checked_at:%Y-%m-%d %H:%M})"
        )


class ActionExecutionLog(models.Model):
    RESULT_SUCCESS = "success"
    RESULT_ERROR = "error"
    RESULT_INFO = "info"
    RESULT_CHOICES = [
        (RESULT_SUCCESS, "Sucesso"),
        (RESULT_ERROR, "Erro"),
        (RESULT_INFO, "Informação"),
    ]

    action = models.ForeignKey(
        Action,
        on_delete=models.PROTECT,
        related_name="execution_logs",
        verbose_name="Ação",
    )
    executed_by = models.ForeignKey(
        User,
        null=True,
        on_delete=models.SET_NULL,
        related_name="action_executions",
        verbose_name="Executado por",
    )
    input_payload = models.JSONField(default=dict, verbose_name="Payload de entrada")
    mapped_kwargs = models.JSONField(default=dict, verbose_name="Kwargs mapeados")
    result_status = models.CharField(
        max_length=10, choices=RESULT_CHOICES, verbose_name="Status do resultado"
    )
    result_message = models.TextField(blank=True, verbose_name="Mensagem")
    result_details = models.TextField(
        blank=True, verbose_name="Detalhes técnicos (interno)"
    )
    started_at = models.DateTimeField(verbose_name="Iniciado em")
    finished_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Finalizado em"
    )
    raw_response = models.JSONField(
        default=dict, blank=True, verbose_name="Resposta bruta"
    )

    class Meta:
        verbose_name = "Log de Execução de Ação"
        verbose_name_plural = "Logs de Execução de Ações"
        ordering = ["-started_at"]

    def __str__(self):
        return (
            f"{self.action.name} — {self.result_status} "
            f"({self.started_at:%Y-%m-%d %H:%M})"
        )


class SyncLog(models.Model):
    SYNC_SERVICES = "services"
    SYNC_ACTIONS = "actions"
    SYNC_TYPE_CHOICES = [
        (SYNC_SERVICES, "Serviços"),
        (SYNC_ACTIONS, "Ações"),
    ]

    STATUS_SUCCESS = "success"
    STATUS_ERROR = "error"
    STATUS_PARTIAL = "partial"
    STATUS_CHOICES = [
        (STATUS_SUCCESS, "Sucesso"),
        (STATUS_ERROR, "Erro"),
        (STATUS_PARTIAL, "Parcial"),
    ]

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="sync_logs",
        verbose_name="Aplicação",
    )
    sync_type = models.CharField(
        max_length=10, choices=SYNC_TYPE_CHOICES, verbose_name="Tipo de sync"
    )
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, verbose_name="Status"
    )
    started_at = models.DateTimeField(verbose_name="Iniciado em")
    finished_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Finalizado em"
    )
    attempt = models.PositiveSmallIntegerField(
        default=1, verbose_name="Tentativa"
    )
    message = models.TextField(blank=True, verbose_name="Mensagem")
    raw_payload = models.JSONField(
        default=dict, blank=True, verbose_name="Payload bruto"
    )

    class Meta:
        verbose_name = "Log de Sincronização"
        verbose_name_plural = "Logs de Sincronização"
        ordering = ["-started_at"]

    def __str__(self):
        return (
            f"{self.application.name} / {self.sync_type} — "
            f"{self.status} ({self.started_at:%Y-%m-%d %H:%M})"
        )


class MaintenanceWindow(models.Model):
    SCOPE_GLOBAL = "global"
    SCOPE_SYSTEM = "system"
    SCOPE_APPLICATION = "application"
    SCOPE_CHOICES = [
        (SCOPE_GLOBAL, "Global"),
        (SCOPE_SYSTEM, "Sistema"),
        (SCOPE_APPLICATION, "Aplicação"),
    ]

    name = models.CharField(max_length=255, verbose_name="Nome")
    start_at = models.DateTimeField(verbose_name="Início")
    end_at = models.DateTimeField(verbose_name="Fim")
    scope_type = models.CharField(
        max_length=15,
        choices=SCOPE_CHOICES,
        default=SCOPE_GLOBAL,
        verbose_name="Escopo",
    )
    scope_id = models.UUIDField(
        null=True, blank=True, verbose_name="ID do escopo (Sistema ou Aplicação)"
    )
    reason = models.TextField(blank=True, verbose_name="Motivo")
    is_active = models.BooleanField(default=True, verbose_name="Ativo")

    class Meta:
        verbose_name = "Janela de Manutenção"
        verbose_name_plural = "Janelas de Manutenção"
        ordering = ["-start_at"]

    def __str__(self):
        return f"{self.name} ({self.start_at:%Y-%m-%d %H:%M} — {self.end_at:%Y-%m-%d %H:%M})"


class EscalationTarget(models.Model):
    name = models.CharField(max_length=255, verbose_name="Nome")
    email = models.EmailField(verbose_name="E-mail")
    system = models.ForeignKey(
        System,
        on_delete=models.CASCADE,
        related_name="escalation_targets",
        verbose_name="Sistema",
    )
    is_active = models.BooleanField(default=True, verbose_name="Ativo")

    class Meta:
        verbose_name = "Destino de Escalonamento"
        verbose_name_plural = "Destinos de Escalonamento"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} <{self.email}>"
