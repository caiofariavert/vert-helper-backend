"""
Gerenciamento de Incidents por mudança de status de serviço.

Regras de deduplicação:
- Abre Incident e notifica SOMENTE na transição para FAILED.
- Não reabre nem renotifica enquanto o serviço permanecer FAILED.
- Fecha Incident e notifica recuperação quando voltar para OK.
- Status UNKNOWN não abre nem fecha Incident.
"""

import logging

from django.utils import timezone

from apps.helper.models import Incident, Service

logger = logging.getLogger(__name__)


def handle_service_status_change(service: Service, previous_status: str, new_status: str):
    """
    Avalia a transição de status e gerencia o Incident correspondente.
    Chamado após qualquer mudança de status no Service.
    """
    if previous_status == new_status:
        return

    logger.info(
        "Status change: service=%s %s → %s",
        service.name, previous_status, new_status,
    )

    if new_status == Service.STATUS_FAILED:
        _open_incident(service, previous_status)

    elif new_status == Service.STATUS_OK and previous_status == Service.STATUS_FAILED:
        _close_incident(service)


# ---------------------------------------------------------------------------
# Incident lifecycle
# ---------------------------------------------------------------------------


def _open_incident(service: Service, previous_status: str):
    """Abre Incident se ainda não houver um ativo para este serviço."""
    active = Incident.objects.filter(service=service, is_active=True).first()
    if active:
        logger.debug("Incident já ativo para %s — nenhuma notificação enviada.", service.name)
        return

    incident = Incident.objects.create(
        service=service,
        previous_status=previous_status,
        current_status=Service.STATUS_FAILED,
        is_active=True,
    )

    logger.warning("Incident aberto: service=%s incident_id=%s", service.name, incident.pk)
    _notify_failure(incident)


def _close_incident(service: Service):
    """Fecha todos os Incidents ativos para este serviço e notifica recuperação."""
    active_incidents = Incident.objects.filter(service=service, is_active=True)
    now = timezone.now()

    for incident in active_incidents:
        incident.is_active = False
        incident.recovered_at = now
        incident.current_status = Service.STATUS_OK
        incident.save(update_fields=["is_active", "recovered_at", "current_status"])

        logger.info("Incident fechado: service=%s incident_id=%s", service.name, incident.pk)
        _notify_recovery(incident)


# ---------------------------------------------------------------------------
# Notificações
# ---------------------------------------------------------------------------


def _notify_failure(incident: Incident):
    from apps.helper.notifications import notify_incident_opened

    try:
        notify_incident_opened(incident)
    except Exception as exc:
        logger.error(
            "Falha ao enviar notificação de incidente: service=%s error=%s",
            incident.service.name, exc,
        )


def _notify_recovery(incident: Incident):
    from apps.helper.notifications import notify_incident_recovered

    try:
        notify_incident_recovered(incident)
    except Exception as exc:
        logger.error(
            "Falha ao enviar notificação de recuperação: service=%s error=%s",
            incident.service.name, exc,
        )
