"""
Envio de notificações por email para incidentes do Helper.

Destinatários:
- Administradores do System associado ao serviço.
- EscalationTargets ativos do mesmo System.

Regras:
- Verificar MaintenanceWindow ativa antes de enviar.
- Se houver janela ativa, suprimir envio e registrar log.
- Registrar notification_sent_at / recovery_notification_sent_at após envio.
"""

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import models
from django.template.loader import render_to_string
from django.utils import timezone

from apps.helper.models import EscalationTarget, Incident, MaintenanceWindow

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------


def notify_incident_opened(incident: Incident):
    """Envia email de falha se não houver janela de manutenção ativa."""
    service = incident.service
    application = service.application
    system = application.system

    if _is_in_maintenance(service):
        logger.info(
            "Notificação suprimida por MaintenanceWindow: service=%s incident=%s",
            service.name,
            incident.pk,
        )
        return

    recipients = _get_recipients(system)
    if not recipients:
        logger.warning("Nenhum destinatário encontrado para system=%s", system.slug)
        return

    subject = render_to_string(
        "helper/mail/incident_alert_subject.txt",
        {"service": service, "application": application, "system": system},
    ).strip()

    html_body = render_to_string(
        "helper/mail/incident_alert.html",
        {
            "service": service,
            "application": application,
            "system": system,
            "incident": incident,
        },
    )

    _send(subject, html_body, recipients)

    incident.notification_sent_at = timezone.now()
    incident.save(update_fields=["notification_sent_at"])

    logger.info(
        "Notificação de falha enviada: service=%s incident=%s recipients=%d",
        service.name,
        incident.pk,
        len(recipients),
    )


def notify_incident_recovered(incident: Incident):
    """Envia email de recuperação se não houver janela de manutenção ativa."""
    service = incident.service
    application = service.application
    system = application.system

    if _is_in_maintenance(service):
        logger.info(
            "Notificação de recuperação suprimida por MaintenanceWindow: service=%s incident=%s",
            service.name,
            incident.pk,
        )
        return

    recipients = _get_recipients(system)
    if not recipients:
        return

    subject = render_to_string(
        "helper/mail/incident_recovery_subject.txt",
        {"service": service, "application": application, "system": system},
    ).strip()

    html_body = render_to_string(
        "helper/mail/incident_recovery.html",
        {
            "service": service,
            "application": application,
            "system": system,
            "incident": incident,
        },
    )

    _send(subject, html_body, recipients)

    incident.recovery_notification_sent_at = timezone.now()
    incident.save(update_fields=["recovery_notification_sent_at"])

    logger.info(
        "Notificação de recuperação enviada: service=%s incident=%s recipients=%d",
        service.name,
        incident.pk,
        len(recipients),
    )


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------


def _is_in_maintenance(service) -> bool:
    """Retorna True se existe MaintenanceWindow ativa cobrindo o serviço."""
    now = timezone.now()
    application = service.application
    system = application.system

    return (
        MaintenanceWindow.objects.filter(
            is_active=True,
            start_at__lte=now,
            end_at__gte=now,
        )
        .filter(
            models.Q(scope_type=MaintenanceWindow.SCOPE_GLOBAL)
            | models.Q(scope_type=MaintenanceWindow.SCOPE_SYSTEM, scope_id=system.id)
            | models.Q(
                scope_type=MaintenanceWindow.SCOPE_APPLICATION, scope_id=application.id
            )
        )
        .exists()
    )


def _get_recipients(system) -> list[str]:
    """Retorna lista de emails dos administradores do System e EscalationTargets ativos."""
    admin_emails = list(
        system.administrators.filter(is_active=True, email__isnull=False).values_list(
            "email", flat=True
        )
    )

    escalation_emails = list(
        EscalationTarget.objects.filter(system=system, is_active=True).values_list(
            "email", flat=True
        )
    )

    return list(set(admin_emails + escalation_emails))


def _send(subject: str, html_body: str, recipients: list[str]):
    """Envia email com body HTML e fallback em texto plano."""
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@helper.local")

    msg = EmailMultiAlternatives(
        subject=subject,
        body=subject,  # fallback text simples
        from_email=from_email,
        to=recipients,
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send()
