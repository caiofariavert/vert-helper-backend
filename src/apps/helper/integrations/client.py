"""
Cliente HTTP para APIs externas dos sistemas monitorados.

Cada Application possui sua própria URL base. O cliente monta os endpoints
conforme o contrato definido em docs/ESPECIFICACAO_TECNICA_URLS.md.

TODO: adicionar suporte a autenticação quando definido (token, OAuth2, etc.).
"""

import logging
from typing import Generator

import requests

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 15  # segundos
PAGE_SIZE = 100


class ExternalApiClient:
    """Cliente para os endpoints externos de uma Application monitorada."""

    def __init__(self, base_url: str, timeout: int = DEFAULT_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        # TODO: adicionar headers de autenticação quando definido
        self._session = requests.Session()

    # ------------------------------------------------------------------
    # App Health
    # ------------------------------------------------------------------

    def get_app_health(self) -> dict:
        """
        GET /api/helper/v1/app-health/
        Retorna {"status": "stable"} ou {"status": "failed", "message": "..."}.
        Lança requests.RequestException em caso de erro de comunicação.
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
        Lança requests.RequestException em caso de erro de comunicação.
        """
        url = f"{self.base_url}/api/helper/v1/healthcare/"
        params = {"force_refresh": "true"} if force_refresh else {}
        response = self._session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def get_actions(self) -> Generator[dict, None, None]:
        """
        GET /api/helper/v1/actions/ com suporte a paginação.
        Yield de cada action da listagem (sem questions_schema).
        """
        url = f"{self.base_url}/api/helper/v1/actions/"
        params = {"page_size": PAGE_SIZE}

        while url:
            response = self._session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            for action in data.get("results", []):
                yield action

            url = data.get("next")
            params = {}  # próximas páginas já vêm na URL completa

    def get_action_detail(self, slug: str) -> dict:
        """
        GET /api/helper/v1/actions/<slug>/
        Retorna o detalhe completo da action, incluindo questions_schema.
        """
        url = f"{self.base_url}/api/helper/v1/actions/{slug}/"
        response = self._session.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.json()
