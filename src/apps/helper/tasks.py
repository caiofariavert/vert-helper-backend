"""
Funções agendadas do Helper executadas pelo Django-Q2.

Cada função recebe application_id como kwarg para isolamento total por aplicação.
"""

import logging

logger = logging.getLogger(__name__)


def sync_application_health(application_id: str, force_refresh: bool = False):
    """
    Job: Health check + sync de serviços de uma Application.

    Agendamento: a cada 10 minutos por Application.
    Retry: 3 tentativas com 1 minuto de intervalo (configurado no Schedule).
    """
    from apps.helper.integrations.health_sync import sync_health_for_application
    from apps.helper.models import Application

    try:
        application = Application.objects.get(id=application_id)
    except Application.DoesNotExist:
        logger.error("sync_application_health: Application %s não encontrada.", application_id)
        return

    logger.info("sync_application_health: iniciando para %s", application.name)
    sync_health_for_application(application, force_refresh=force_refresh)
    logger.info("sync_application_health: concluído para %s", application.name)


def sync_application_actions(application_id: str):
    """
    Job: Sync de Actions de uma Application.

    Agendamento: 1 vez por dia por Application.
    Retry: 3 tentativas com 1 minuto de intervalo (configurado no Schedule).
    """
    from apps.helper.integrations.action_sync import sync_actions_for_application
    from apps.helper.models import Application

    try:
        application = Application.objects.get(id=application_id)
    except Application.DoesNotExist:
        logger.error("sync_application_actions: Application %s não encontrada.", application_id)
        return

    logger.info("sync_application_actions: iniciando para %s", application.name)
    sync_actions_for_application(application)
    logger.info("sync_application_actions: concluído para %s", application.name)


def cleanup_health_check_logs():
    """
    Job: Remove HealthCheckLogs com mais de 90 dias.

    Agendamento: 1 vez por dia (schedule único global).
    """
    from datetime import timedelta

    from django.utils import timezone

    from apps.helper.models import HealthCheckLog

    cutoff = timezone.now() - timedelta(days=90)
    deleted, _ = HealthCheckLog.objects.filter(checked_at__lt=cutoff).delete()
    logger.info("cleanup_health_check_logs: %d registros removidos.", deleted)
