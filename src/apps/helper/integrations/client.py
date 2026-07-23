"""
Cliente HTTP para APIs externas dos sistemas monitorados.

Cada Application possui sua própria URL base e configuração de autenticação.
O cliente obtém o token JWT via POST /api/helper/v1/auth/ usando credenciais
globais definidas em settings (HELPER_API_AUTH_EMAIL / HELPER_API_AUTH_PASSWORD).

O token é cacheado por application no Django cache para evitar autenticações
repetidas. Em caso de 401, o cache é invalidado e uma nova autenticação é feita.

A única rota que não exige autenticação é /api/helper/v1/app-health/.
"""

import logging
from typing import Generator

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 15
PAGE_SIZE = 100
TOKEN_CACHE_TTL = 50 * 60  # 50 minutos (margem de segurança)
AUTH_ENDPOINT = "/api/helper/v1/auth/"
CACHE_KEY_PREFIX = "helper:auth:token:"


class ExternalApiClient:
    """
    Cliente para os endpoints externos de uma Application monitorada.

    Autenticação:
    - Se application.auth_type == NONE: sem header de autenticação.
    - Caso contrário: POST /api/helper/v1/auth/ → obtém access_token.
    - Header enviado: Authorization: {auth_type} {access_token}
    - Em 401: invalida cache e reautentica uma vez.
    - /api/helper/v1/app-health/ nunca recebe header de autenticação.
    """

    def __init__(self, application, timeout: int = DEFAULT_TIMEOUT):
        from apps.helper.models import Application

        self.application = application
        self.base_url = application.base_url.rstrip("/")
        self.auth_type = application.auth_type
        self.timeout = timeout
        self._needs_auth = application.auth_type != Application.AUTH_NONE
        self._session = requests.Session()

    # ------------------------------------------------------------------
    # App Health (sem autenticação)
    # ------------------------------------------------------------------

    def get_app_health(self) -> dict:
        """
        GET /api/helper/v1/app-health/  — sem autenticação.
        Retorna {"status": "stable"} ou {"status": "failed", "message": "..."}.
        """
        url = f"{self.base_url}/api/helper/v1/app-health/"
        response = self._session.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------
    # Healthcare (serviços)
    # ------------------------------------------------------------------

    def get_healthcare(self, force_refresh: bool = False) -> dict:
        """
        GET /api/helper/v1/healthcare/
        Retorna dict com nome do serviço → {status, message, last_updated}.
        """
        url = f"{self.base_url}/api/helper/v1/healthcare/"
        params = {"force_refresh": "true"} if force_refresh else {}
        response = self._request("get", url, params=params)
        return response.json()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def get_actions(self) -> Generator[dict, None, None]:
        """
        GET /api/helper/v1/actions/ com suporte a paginação.
        Yield de cada action da listagem.
        """
        url = f"{self.base_url}/api/helper/v1/actions/"
        params = {"page_size": PAGE_SIZE}

        while url:
            response = self._request("get", url, params=params)
            data = response.json()
            for action in data.get("results", []):
                yield action
            url = data.get("next")
            params = {}

    def get_action_detail(self, slug: str) -> dict:
        """
        GET /api/helper/v1/actions/<slug>/
        Retorna o detalhe completo incluindo questions_schema.
        """
        url = f"{self.base_url}/api/helper/v1/actions/{slug}/"
        response = self._request("get", url)
        return response.json()

    # ------------------------------------------------------------------
    # Autenticação interna
    # ------------------------------------------------------------------

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Executa requisição autenticada. Em 401 reautentica e tenta uma vez.
        """
        if self._needs_auth:
            self._ensure_auth_header()
        response = getattr(self._session, method)(url, timeout=self.timeout, **kwargs)

        if response.status_code == 401 and self._needs_auth:
            logger.warning("401 recebido para %s — reautenticando.", url)
            self._invalidate_token_cache()
            self._ensure_auth_header(force=True)
            response = getattr(self._session, method)(url, timeout=self.timeout, **kwargs)

        response.raise_for_status()
        return response

    def _ensure_auth_header(self, force: bool = False):
        """Define o header Authorization na sessão com o token vigente."""
        token = self._get_token(force=force)
        if token:
            # self._session.headers["Authorization"] = f"{self.auth_type} {token}"
            self._session.headers.update({"Authorization": f"{self.auth_type} {token}"})

    def _get_token(self, force: bool = False) -> str | None:
        """Retorna token do cache ou autentica se necessário."""
        cache_key = f"{CACHE_KEY_PREFIX}{self.application.id}"
        if not force:
            token = cache.get(cache_key)
            if token:
                return token
        return self._authenticate(cache_key)

    def _authenticate(self, cache_key: str) -> str | None:
        """POST /api/helper/v1/auth/ com credenciais do settings."""
        url = f"{self.base_url}{AUTH_ENDPOINT}"
        payload = {
            "email": settings.HELPER_API_AUTH_EMAIL,
            "password": settings.HELPER_API_AUTH_PASSWORD,
        }

        try:
            response = self._session.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            response_data = response.json()
            token = response_data.get("access_token", response_data.get("access", None))
            if token:
                cache.set(cache_key, token, TOKEN_CACHE_TTL)
                logger.info("Token obtido para application %s", self.application.slug)
            return token
        except requests.RequestException as exc:
            logger.error(
                "Falha ao autenticar na application %s: %s",
                self.application.slug, exc,
            )
            raise

    def _invalidate_token_cache(self):
        cache.delete(f"{CACHE_KEY_PREFIX}{self.application.id}")
