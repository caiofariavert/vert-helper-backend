"""
Gerenciamento de Schedules do Django-Q2 por Application e globais.

Schedules por Application (criados via Admin action):
  - helper:health:{slug}   → sync de saúde + serviços a cada 10 minutos
  - helper:actions:{slug}  → sync de ações 1 vez por dia

Schedules globais (criados via management command setup_helper_schedules):
  - helper:cleanup:health-check-logs → limpeza de HealthCheckLogs > 90 dias, 1 vez por dia

Política de retry (configurada no Q_CLUSTER):
  - timeout: 60s por task
  - retry: 65s de intervalo entre tentativas
  - attempts por schedule: 3 (health/actions) ou 1 (cleanup)
"""

import json
import logging

from django_q.models import Schedule

logger = logging.getLogger(__name__)

HEALTH_SCHEDULE_PREFIX = "helper:health:"
ACTIONS_SCHEDULE_PREFIX = "helper:actions:"
CLEANUP_SCHEDULE_NAME = "helper:cleanup:health-check-logs"

RETRY_ATTEMPTS = 3


def _health_schedule_name(application) -> str:
    return f"{HEALTH_SCHEDULE_PREFIX}{application.slug}"


def _actions_schedule_name(application) -> str:
    return f"{ACTIONS_SCHEDULE_PREFIX}{application.slug}"


def create_application_schedules(application) -> dict:
    """
    Cria ou reativa os dois schedules de uma Application.
    Retorna dict com as instâncias criadas/atualizadas.
    """
    application_id = str(application.id)
    kwargs_str = json.dumps({"application_id": application_id})

    health_schedule, health_created = Schedule.objects.update_or_create(
        name=_health_schedule_name(application),
        defaults={
            "func": "apps.helper.tasks.sync_application_health",
            "kwargs": kwargs_str,
            "schedule_type": Schedule.MINUTES,
            "minutes": 10,
            "repeats": -1,
        },
    )

    actions_schedule, actions_created = Schedule.objects.update_or_create(
        name=_actions_schedule_name(application),
        defaults={
            "func": "apps.helper.tasks.sync_application_actions",
            "kwargs": kwargs_str,
            "schedule_type": Schedule.DAILY,
            "repeats": -1,
        },
    )

    logger.info(
        "Schedules para %s: health=%s actions=%s",
        application.slug,
        "criado" if health_created else "atualizado",
        "criado" if actions_created else "atualizado",
    )

    return {"health": health_schedule, "actions": actions_schedule}


def deactivate_application_schedules(application):
    """
    Desativa os schedules de uma Application definindo repeats=0.
    Não deleta os registros para manter histórico no admin.
    """
    updated = Schedule.objects.filter(
        name__in=[
            _health_schedule_name(application),
            _actions_schedule_name(application),
        ]
    ).update(repeats=0)

    logger.info(
        "Schedules desativados para %s: %d schedule(s) afetado(s).",
        application.slug,
        updated,
    )


def create_global_schedules():
    """
    Cria ou reativa os schedules globais do Helper.
    Chamado pelo management command setup_helper_schedules.
    """
    schedule, created = Schedule.objects.update_or_create(
        name=CLEANUP_SCHEDULE_NAME,
        defaults={
            "func": "apps.helper.tasks.cleanup_health_check_logs",
            "schedule_type": Schedule.DAILY,
            "repeats": -1,
        },
    )

    logger.info(
        "Schedule global cleanup: %s",
        "criado" if created else "atualizado",
    )
    return schedule
