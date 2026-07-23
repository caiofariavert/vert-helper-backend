"""
Serviço de execução de Action.

Fluxo:
1. Monta a URL de execução no sistema externo:
   {application.base_url}/api/helper/v1/actions/{action.slug}/execute/
2. Envia POST com os kwargs mapeados como body JSON.
3. Interpreta a resposta (success / error / info).
4. Registra o resultado em ActionExecutionLog independente do status.

O campo result_details (detalhes técnicos de erro) é armazenado no log
mas NÃO é retornado ao frontend.
"""

import logging
from datetime import datetime

import requests
from django.utils import timezone

from apps.helper.models import Action, ActionExecutionLog

logger = logging.getLogger(__name__)

# Timeout padrão para chamadas ao sistema externo (segundos)
EXECUTION_TIMEOUT = 30


def execute_action(action: Action, mapped_kwargs: dict, input_payload: dict, user) -> dict:
    """
    Executa uma Action no sistema externo e persiste o log.

    :param action: instância de Action.
    :param mapped_kwargs: kwargs já validados e mapeados por action_kwarg.
    :param input_payload: payload original enviado pelo frontend (para log).
    :param user: usuário que disparou a execução.
    :returns: dict de resposta para o frontend (sem details em caso de erro).
    """
    application = action.application
    url = _build_execution_url(application.base_url, action.slug)

    started_at: datetime = timezone.now()
    raw_response: dict = {}
    result_status = ActionExecutionLog.RESULT_ERROR
    result_message = ""
    result_details = ""

    try:
        response = requests.post(url, json=mapped_kwargs, timeout=EXECUTION_TIMEOUT)
        raw_response = _safe_json(response)
        result_status, result_message, result_details = _parse_response(response, raw_response)
    except requests.Timeout:
        result_message = "A execução excedeu o tempo limite."
        result_details = f"Timeout após {EXECUTION_TIMEOUT}s em {url}"
        logger.error("Action execution timeout: action=%s url=%s", action.slug, url)
    except requests.RequestException as exc:
        result_message = "Falha ao comunicar com o sistema externo."
        result_details = str(exc)
        logger.error("Action execution request error: action=%s error=%s", action.slug, exc)

    finished_at = timezone.now()

    _persist_log(
        action=action,
        user=user,
        input_payload=input_payload,
        mapped_kwargs=mapped_kwargs,
        result_status=result_status,
        result_message=result_message,
        result_details=result_details,
        started_at=started_at,
        finished_at=finished_at,
        raw_response=raw_response,
    )

    return _build_frontend_response(result_status, result_message, raw_response)


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------


def _build_execution_url(base_url: str, slug: str) -> str:
    base = base_url.rstrip("/")
    return f"{base}/api/helper/v1/actions/{slug}/execute/"


def _safe_json(response: requests.Response) -> dict:
    try:
        return response.json()
    except Exception:
        return {"raw": response.text}


def _parse_response(response: requests.Response, body: dict) -> tuple[str, str, str]:
    """Retorna (result_status, result_message, result_details)."""
    status_code = response.status_code
    status = body.get("status", "")

    if status_code < 400 and status == "success":
        return (
            ActionExecutionLog.RESULT_SUCCESS,
            body.get("message", "Executado com sucesso."),
            "",
        )

    if status_code < 400 and status == "info":
        return (
            ActionExecutionLog.RESULT_INFO,
            body.get("message", ""),
            "",
        )

    # Qualquer outro caso trata como erro
    return (
        ActionExecutionLog.RESULT_ERROR,
        body.get("message", "Falha na execução."),
        body.get("details", f"HTTP {status_code}"),
    )


def _persist_log(
    action, user, input_payload, mapped_kwargs,
    result_status, result_message, result_details,
    started_at, finished_at, raw_response,
):
    try:
        ActionExecutionLog.objects.create(
            action=action,
            executed_by=user if user and user.is_authenticated else None,
            input_payload=input_payload,
            mapped_kwargs=mapped_kwargs,
            result_status=result_status,
            result_message=result_message,
            result_details=result_details,
            started_at=started_at,
            finished_at=finished_at,
            raw_response=raw_response,
        )
    except Exception as exc:
        logger.error("Failed to persist ActionExecutionLog: action=%s error=%s", action.slug, exc)


def _build_frontend_response(result_status: str, result_message: str, raw_response: dict) -> dict:
    """Monta resposta para o frontend. Nunca expõe result_details."""
    if result_status == ActionExecutionLog.RESULT_SUCCESS:
        return {"status": "success", "message": result_message}

    if result_status == ActionExecutionLog.RESULT_INFO:
        response = {"status": "info", "message": result_message}
        steps = raw_response.get("steps")
        if steps:
            response["steps"] = steps
        return response

    # error — details são omitidos na resposta ao frontend
    return {"status": "error", "message": result_message}
