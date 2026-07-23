"""
Gerenciamento de Incidents por mudança de status de serviço.

Regras de deduplicação:
- Abre Incident e notifica SOMENTE na transição para FAILED.
- Não reabre nem renotifica enquanto o serviço permanecer FAILED.
- Fecha Incident e notifica recuperação quando voltar para OK.
- Status UNKNOWN não abre nem fecha Incident.

Notificação: stub para Fase 6 (implementação real de email).
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
# Notificações (stubs — implementação completa na Fase 6)
# ---------------------------------------------------------------------------


def _notify_failure(incident: Incident):
    """
    TODO Fase 6: enviar e-mail de falha para administradores do System
    e EscalationTargets se configurados.

    Regras:
    - Verificar MaintenanceWindow ativa antes de enviar.
    - Registrar notification_sent_at após envio.
    """
    logger.info(
        "[STUB] Notificação de falha pendente: service=%s incident=%s",
        incident.service.name, incident.pk,
    )


def _notify_recovery(incident: Incident):
    """
    TODO Fase 6: enviar e-mail de recuperação para administradores do System.

    Regras:
    - Verificar MaintenanceWindow ativa antes de enviar.
    - Registrar recovery_notification_sent_at após envio.
    """
    logger.info(
        "[STUB] Notificação de recuperação pendente: service=%s incident=%s",
        incident.service.name, incident.pk,
    )
