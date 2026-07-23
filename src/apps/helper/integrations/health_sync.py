"""
Sync de saúde e serviços de uma Application.

Fluxo por execução:
1. Consulta app-health → se falhou, marca todos os serviços como FAILED.
2. Consulta healthcare → atualiza status de cada serviço individualmente.
3. Concilia serviços: cria os novos, inativa os ausentes.
4. Para cada mudança de status aciona o incident_manager.
5. Registra HealthCheckLog por serviço e SyncLog ao final.
"""

import logging
from datetime import datetime

import requests
from django.utils import timezone

from apps.helper.models import Application, HealthCheckLog, Service, SyncLog

from .client import ExternalApiClient
from .incident_manager import handle_service_status_change

logger = logging.getLogger(__name__)


def sync_health_for_application(application: Application, force_refresh: bool = False) -> dict:
    """
    Executa health check + sync de serviços para uma Application.

    Retorna dict de resumo para uso no SyncLog e logging.
    """
    started_at: datetime = timezone.now()
    client = ExternalApiClient(application)
    summary = {"created": 0, "updated": 0, "inactivated": 0, "errors": []}

    try:
        healthcare_data = _fetch_healthcare(client, application, force_refresh, summary)
    except Exception as exc:
        _persist_sync_log(application, SyncLog.SYNC_SERVICES, SyncLog.STATUS_ERROR, started_at, str(exc), {})
        raise

    _reconcile_services(application, healthcare_data, summary)
    _persist_sync_log(
        application, SyncLog.SYNC_SERVICES, SyncLog.STATUS_SUCCESS, started_at, "", summary
    )

    logger.info(
        "sync_health: app=%s criados=%d atualizados=%d inativados=%d",
        application.slug, summary["created"], summary["updated"], summary["inactivated"],
    )
    return summary


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------


def _fetch_healthcare(client: ExternalApiClient, application: Application, force_refresh: bool, summary: dict) -> dict:
    """
    Consulta app-health e healthcare.
    Se app-health retornar failed ou falhar, trata todos como FAILED.
    Retorna dict {service_name: {status, message, last_updated}}.
    """
    # 1. Verificar app-health primeiro
    try:
        app_health = client.get_app_health()
        if app_health.get("status") == "failed":
            logger.warning("app-health FAILED para %s: %s", application.slug, app_health.get("message"))
            return _mark_all_as_failed(application, app_health.get("message", "App health failed"))
    except requests.RequestException as exc:
        logger.error("app-health indisponível para %s: %s", application.slug, exc)
        return _mark_all_as_failed(application, str(exc))

    # 2. Consultar healthcare
    try:
        return client.get_healthcare(force_refresh=force_refresh)
    except requests.RequestException as exc:
        logger.error("healthcare indisponível para %s: %s", application.slug, exc)
        return _mark_all_as_failed(application, str(exc))


def _mark_all_as_failed(application: Application, message: str) -> dict:
    """Monta dict de healthcare com FAILED para todos os serviços ativos."""
    names = application.services.values_list("name", flat=True)
    return {
        name: {"status": Service.STATUS_FAILED, "message": message, "last_updated": None}
        for name in names
    }


def _reconcile_services(application: Application, healthcare_data: dict, summary: dict):
    """
    Para cada serviço no payload externo:
      - Cria se não existir.
      - Atualiza status e detecta mudança.
      - Inativa serviços que não aparecem mais na origem.
    """
    now = timezone.now()
    seen_names: set[str] = set()

    for service_name, service_data in healthcare_data.items():
        seen_names.add(service_name)
        new_status = service_data.get("status", Service.STATUS_UNKNOWN)
        message = service_data.get("message", "")

        service, created = Service.all_objects.get_or_create(
            application=application,
            name=service_name,
            defaults={"status": new_status, "last_checked_at": now, "last_status_change_at": now},
        )

        if created:
            summary["created"] += 1
        else:
            previous_status = service.status
            changed = previous_status != new_status

            service.status = new_status
            service.last_checked_at = now
            service.is_active = True
            service.deleted_at = None

            if changed:
                service.last_status_change_at = now
                summary["updated"] += 1
                handle_service_status_change(service, previous_status, new_status)

            service.save(update_fields=[
                "status", "last_checked_at", "last_status_change_at",
                "is_active", "deleted_at", "updated_at",
            ])

        HealthCheckLog.objects.create(
            application=application,
            service_name=service_name,
            status=new_status,
            message=message,
            raw_payload=service_data,
        )

    # Inativar serviços que não apareceram no payload
    missing = (
        Service.objects
        .filter(application=application)
        .exclude(name__in=seen_names)
    )
    for service in missing:
        previous_status = service.status
        service.soft_delete()
        handle_service_status_change(service, previous_status, Service.STATUS_UNKNOWN)
        summary["inactivated"] += 1


def _persist_sync_log(application, sync_type, status, started_at, message, raw_payload):
    SyncLog.objects.create(
        application=application,
        sync_type=sync_type,
        status=status,
        started_at=started_at,
        finished_at=timezone.now(),
        message=message,
        raw_payload=raw_payload if isinstance(raw_payload, dict) else {},
    )
