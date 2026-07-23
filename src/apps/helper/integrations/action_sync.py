"""
Sync de Actions de uma Application.

Fluxo por execução:
1. Pagina GET /api/helper/v1/actions/ para obter slugs e dados básicos.
2. Para cada action, busca detalhe (incluindo questions_schema).
3. Upsert por slug dentro da Application:
   - Cria se não existir.
   - Atualiza se name, description ou questions_schema mudaram (incrementa source_version).
   - Reconcilia vínculo Action x Service pelos nomes retornados.
4. Inativa Actions locais ausentes na origem.
5. Registra SyncLog ao final.
"""

import json
import logging
from datetime import datetime

import requests
from django.utils import timezone

from apps.helper.models import Action, Application, Service, SyncLog

from .client import ExternalApiClient

logger = logging.getLogger(__name__)


def sync_actions_for_application(application: Application) -> dict:
    """
    Sincroniza Actions de uma Application com a origem externa.
    Retorna dict de resumo.
    """
    started_at: datetime = timezone.now()
    client = ExternalApiClient(application)
    summary = {"created": 0, "updated": 0, "inactivated": 0, "errors": []}

    try:
        remote_slugs = _fetch_and_upsert_actions(client, application, summary)
    except Exception as exc:
        _persist_sync_log(application, SyncLog.STATUS_ERROR, started_at, str(exc), {})
        raise

    _inactivate_missing_actions(application, remote_slugs, summary)
    _persist_sync_log(application, SyncLog.STATUS_SUCCESS, started_at, "", summary)

    logger.info(
        "sync_actions: app=%s criados=%d atualizados=%d inativados=%d",
        application.slug, summary["created"], summary["updated"], summary["inactivated"],
    )
    return summary


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------


def _fetch_and_upsert_actions(client: ExternalApiClient, application: Application, summary: dict) -> set:
    """Itera sobre todos os actions remotos e faz upsert. Retorna set de slugs vistos."""
    seen_slugs: set[str] = set()

    for action_data in client.get_actions():
        slug = action_data.get("slug")
        if not slug:
            continue

        seen_slugs.add(slug)

        try:
            detail = client.get_action_detail(slug)
        except requests.RequestException as exc:
            logger.warning("Falha ao buscar detalhe da action %s: %s", slug, exc)
            summary["errors"].append(f"detail/{slug}: {exc}")
            continue

        _upsert_action(application, detail, summary)

    return seen_slugs


def _upsert_action(application: Application, detail: dict, summary: dict):
    slug = detail.get("slug", "")
    name = detail.get("name", "")
    description = detail.get("description", "")
    questions_schema = detail.get("questions", [])
    service_names: list[str] = detail.get("services", [])

    action, created = Action.all_objects.get_or_create(
        application=application,
        slug=slug,
        defaults={
            "name": name,
            "description": description,
            "questions_schema": questions_schema,
            "source_version": 1,
            "is_active": True,
            "deleted_at": None,
        },
    )

    if created:
        summary["created"] += 1
    else:
        changed = _has_changed(action, name, description, questions_schema)
        action.is_active = True
        action.deleted_at = None

        if changed:
            action.name = name
            action.description = description
            action.questions_schema = questions_schema
            action.source_version += 1
            summary["updated"] += 1

        action.save(update_fields=[
            "name", "description", "questions_schema", "source_version",
            "is_active", "deleted_at", "updated_at",
        ])

    _reconcile_action_services(action, application, service_names)


def _has_changed(action: Action, name: str, description: str, questions_schema: list) -> bool:
    if action.name != name or action.description != description:
        return True
    return json.dumps(action.questions_schema, sort_keys=True) != json.dumps(questions_schema, sort_keys=True)


def _reconcile_action_services(action: Action, application: Application, service_names: list[str]):
    """Atualiza vínculo M2M Action x Service com base nos nomes vindos da origem."""
    services = Service.objects.filter(application=application, name__in=service_names)
    action.services.set(services)


def _inactivate_missing_actions(application: Application, seen_slugs: set, summary: dict):
    missing = Action.objects.filter(application=application).exclude(slug__in=seen_slugs)
    for action in missing:
        action.soft_delete()
        summary["inactivated"] += 1


def _persist_sync_log(application, status, started_at, message, raw_payload):
    SyncLog.objects.create(
        application=application,
        sync_type=SyncLog.SYNC_ACTIONS,
        status=status,
        started_at=started_at,
        finished_at=timezone.now(),
        message=message,
        raw_payload=raw_payload if isinstance(raw_payload, dict) else {},
    )
