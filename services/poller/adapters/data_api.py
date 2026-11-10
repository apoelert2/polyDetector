import logging
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import requests
from domain.entities import Trade
from domain.use_cases.ports import TradeApiPort

logger = logging.getLogger(__name__)

PAGE_SIZE = 1000


def parse_trade(raw: dict[str, Any]) -> Trade:
    return Trade(
        time=datetime.fromtimestamp(int(raw["timestamp"]), UTC),
        transaction_hash=raw["transaction_hash"],
        condition_id=raw["condition_id"],
        token_id=raw["token_id"],
        proxy_wallet=raw["proxy_wallet"],
        side=raw["side"],
        size=float(raw["size"]),
        price=float(raw["price"]),
        outcome=raw.get("outcome"),
    )


class DataApi(TradeApiPort):
    """Polymarket Data API v2. Trades come newest first, paged by cursor."""

    def __init__(self, base_url: str, timeout: int = 30):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"Accept": "application/json"})

    def iter_trades(self, condition_ids: list[str]) -> Iterator[Trade]:
        params: dict[str, str | int] = {"condition": ",".join(condition_ids), "limit": PAGE_SIZE}
        while True:
            resp = self._session.get(f"{self._base_url}/v2/trades", params=params, timeout=self._timeout)
            resp.raise_for_status()
            body = resp.json()
            for raw in body["data"]:
                yield parse_trade(raw)
            page = body.get("pagination") or {}
            if not page.get("has_more") or not page.get("next_cursor"):
                return
            params["cursor"] = page["next_cursor"]
