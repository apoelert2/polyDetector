import logging
from typing import Any

import requests
from domain.use_cases.ports import MarketApiPort

logger = logging.getLogger(__name__)


class GammaApi(MarketApiPort):
    def __init__(self, base_url: str = "https://gamma-api.polymarket.com", timeout: int = 30):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._session: requests.Session | None = None

    def _get_session(self) -> requests.Session:
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({"Accept": "application/json"})
        return self._session

    def fetch_markets(self, tag_id: int) -> list[dict[str, Any]]:
        url = f"{self._base_url}/markets"
        params = {"tag_id": tag_id, "limit": 100}
        try:
            resp = self._get_session().get(url, params=params, timeout=self._timeout)
            resp.raise_for_status()
            data: list[dict[str, Any]] = resp.json()
            logger.debug("Fetched %d markets for tag_id=%s", len(data), tag_id)
            return data
        except requests.RequestException as e:
            logger.error("Gamma API error for tag_id=%s: %s", tag_id, e)
            raise
