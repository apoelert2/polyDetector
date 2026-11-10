import json
import logging
from datetime import datetime
from typing import Any

import requests
from domain.entities import Market
from domain.use_cases.ports import MarketApiPort

logger = logging.getLogger(__name__)

PAGE_SIZE = 100  # Gamma returns at most 100 markets per request


def _float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _json_list(value: Any) -> list[Any]:
    # Gamma encodes outcomes, outcomePrices and clobTokenIds as JSON strings.
    if isinstance(value, str):
        value = json.loads(value)
    return value if isinstance(value, list) else []


def parse_market(raw: dict[str, Any], tag_id: int) -> Market | None:
    condition_id = raw.get("conditionId")
    if not condition_id:
        logger.warning("Skipping market without conditionId: id=%s", raw.get("id"))
        return None
    end = raw.get("endDate")
    return Market(
        condition_id=condition_id,
        question=raw.get("question") or "",
        slug=raw.get("slug"),
        end_date=datetime.fromisoformat(end) if end else None,
        closed=bool(raw.get("closed")),
        outcomes=tuple(str(o) for o in _json_list(raw.get("outcomes"))),
        token_ids=tuple(str(t) for t in _json_list(raw.get("clobTokenIds"))),
        outcome_prices=tuple(float(p) for p in _json_list(raw.get("outcomePrices"))),
        volume=_float(raw.get("volume")),
        volume_24h=_float(raw.get("volume24hr")),
        liquidity=_float(raw.get("liquidity")),
        tag_ids=(tag_id,),
    )


class GammaApi(MarketApiPort):
    def __init__(self, base_url: str, timeout: int = 30):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"Accept": "application/json"})

    def fetch_closing_markets(self, tag_id: int, end_min: datetime, end_max: datetime) -> list[Market]:
        markets: list[Market] = []
        offset = 0
        while True:
            params: dict[str, str | int] = {
                "tag_id": tag_id,
                "closed": "false",
                "end_date_min": end_min.isoformat(),
                "end_date_max": end_max.isoformat(),
                "limit": PAGE_SIZE,
                "offset": offset,
            }
            resp = self._session.get(f"{self._base_url}/markets", params=params, timeout=self._timeout)
            resp.raise_for_status()
            page: list[dict[str, Any]] = resp.json()
            markets.extend(m for raw in page if (m := parse_market(raw, tag_id)))
            if len(page) < PAGE_SIZE:
                return markets
            offset += PAGE_SIZE
