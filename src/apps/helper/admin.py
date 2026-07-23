from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Action,
    ActionExecutionLog,
    Application,
    Ecosystem,
    EscalationTarget,
    HealthCheckLog,
    Incident,
    MaintenanceWindow,
    Service,
    SyncLog,
    System,
)
from .schedules import create_application_schedules, deactivate_application_schedules


# ---------------------------------------------------------------------------
# Mixins
# ---------------------------------------------------------------------------


class SoftDeleteAdmin(admin.ModelAdmin):
    """Admin base para entidades com soft delete.

    - Exibe ativos e inativos.
    - Provê ação de hard delete explícito.
    - Bloqueia hard delete via botão delete padrão do admin (redireciona para soft delete).
    """

    actions = ["hard_delete_selected", "soft_delete_selected", "restore_selected"]

    def get_queryset(self, request):
        return self.model.all_objects.all()

    @admin.action(description="⚠️ Hard delete — remover permanentemente")
    def hard_delete_selected(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"{count} registro(s) removido(s) permanentemente.")

    @admin.action(description="Inativar selecionados (soft delete)")
    def soft_delete_selected(self, request, queryset):
        count = 0
        for obj in queryset:
            if obj.deleted_at is None:
                obj.soft_delete()
                count += 1
        self.message_user(request, f"{count} registro(s) inativado(s).")

    @admin.action(description="Restaurar selecionados")
    def restore_selected(self, request, queryset):
        count = 0
        for obj in queryset:
            if obj.deleted_at is not None:
                obj.restore()
                count += 1
        self.message_user(request, f"{count} registro(s) restaurado(s).")

    def status_badge(self, obj):
        if obj.deleted_at:
            return format_html(
                '<span style="color:#c0392b;font-weight:bold;">Inativo</span>'
            )
        return format_html(
            '<span style="color:#27ae60;font-weight:bold;">Ativo</span>'
        )

    status_badge.short_description = "Status"


class ReadOnlyLogAdmin(admin.ModelAdmin):
    """Admin somente-leitura para modelos de log."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# ---------------------------------------------------------------------------
# Domínio
# ---------------------------------------------------------------------------


@admin.register(Ecosystem)
class EcosystemAdmin(SoftDeleteAdmin):
    list_display = ["name", "slug", "status_badge", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["created_at", "updated_at", "deleted_at"]


@admin.register(System)
class SystemAdmin(SoftDeleteAdmin):
    list_display = ["name", "slug", "status_badge", "created_at"]
    list_filter = ["is_active", "ecosystems"]
    search_fields = ["name", "slug"]
    filter_horizontal = ["ecosystems", "administrators"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["created_at", "updated_at", "deleted_at"]


@admin.register(Application)
class ApplicationAdmin(SoftDeleteAdmin):
    list_display = ["name", "slug", "environment", "system", "base_url", "status_badge", "created_at"]
    list_filter = ["is_active", "environment", "system"]
    search_fields = ["name", "slug", "base_url"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["created_at", "updated_at", "deleted_at"]
    actions = SoftDeleteAdmin.actions + [
        "create_schedules_action",
        "deactivate_schedules_action",
    ]

    @admin.action(description="Criar/reativar agendamentos de sync (Django-Q)")
    def create_schedules_action(self, request, queryset):
        count = 0
        for application in queryset:
            create_application_schedules(application)
            count += 1
        self.message_user(
            request,
            f"Agendamentos criados/atualizados para {count} aplicação(ões). "
            "Verifique em Scheduled Tasks no menu do Django-Q.",
        )

    @admin.action(description="Desativar agendamentos de sync (Django-Q)")
    def deactivate_schedules_action(self, request, queryset):
        count = 0
        for application in queryset:
            deactivate_application_schedules(application)
            count += 1
        self.message_user(request, f"Agendamentos desativados para {count} aplicação(ões).")


@admin.register(Service)
class ServiceAdmin(SoftDeleteAdmin):
    list_display = ["name", "application", "status", "last_checked_at", "status_badge"]
    list_filter = ["is_active", "status", "application__system"]
    search_fields = ["name", "application__name"]
    readonly_fields = ["last_checked_at", "last_status_change_at", "created_at", "updated_at", "deleted_at"]


@admin.register(Action)
class ActionAdmin(SoftDeleteAdmin):
    list_display = ["name", "slug", "application", "source_version", "status_badge", "created_at"]
    list_filter = ["is_active", "application__system", "application"]
    search_fields = ["name", "slug", "application__name"]
    filter_horizontal = ["services"]
    readonly_fields = ["source_version", "created_at", "updated_at", "deleted_at"]


# ---------------------------------------------------------------------------
# Operacional
# ---------------------------------------------------------------------------


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = [
        "service", "current_status", "previous_status",
        "opened_at", "recovered_at", "is_active",
        "notification_sent_at",
    ]
    list_filter = ["is_active", "current_status", "service__application__system"]
    search_fields = ["service__name", "service__application__name"]
    readonly_fields = [
        "service", "previous_status", "current_status",
        "opened_at", "recovered_at",
        "notification_sent_at", "recovery_notification_sent_at",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(HealthCheckLog)
class HealthCheckLogAdmin(ReadOnlyLogAdmin):
    list_display = ["application", "service_name", "status", "message", "checked_at"]
    list_filter = ["status", "application__system", "application"]
    search_fields = ["service_name", "application__name"]
    date_hierarchy = "checked_at"
    readonly_fields = ["application", "service_name", "status", "message", "checked_at", "raw_payload"]


@admin.register(ActionExecutionLog)
class ActionExecutionLogAdmin(ReadOnlyLogAdmin):
    list_display = ["action", "executed_by", "result_status", "started_at", "finished_at"]
    list_filter = ["result_status", "action__application__system", "action__application"]
    search_fields = ["action__name", "executed_by__email"]
    date_hierarchy = "started_at"
    readonly_fields = [
        "action", "executed_by", "input_payload", "mapped_kwargs",
        "result_status", "result_message", "result_details",
        "started_at", "finished_at", "raw_response",
    ]


@admin.register(SyncLog)
class SyncLogAdmin(ReadOnlyLogAdmin):
    list_display = ["application", "sync_type", "status", "attempt", "started_at", "finished_at"]
    list_filter = ["sync_type", "status", "application__system", "application"]
    search_fields = ["application__name"]
    date_hierarchy = "started_at"
    readonly_fields = [
        "application", "sync_type", "status",
        "started_at", "finished_at", "attempt", "message", "raw_payload",
    ]


# ---------------------------------------------------------------------------
# Configuração operacional
# ---------------------------------------------------------------------------


@admin.register(MaintenanceWindow)
class MaintenanceWindowAdmin(admin.ModelAdmin):
    list_display = ["name", "scope_type", "start_at", "end_at", "is_active"]
    list_filter = ["is_active", "scope_type"]
    search_fields = ["name", "reason"]


@admin.register(EscalationTarget)
class EscalationTargetAdmin(admin.ModelAdmin):
    list_display = ["name", "email", "system", "is_active"]
    list_filter = ["is_active", "system"]
    search_fields = ["name", "email"]
