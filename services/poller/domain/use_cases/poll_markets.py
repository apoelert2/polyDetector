import logging
from dataclasses import replace
from datetime import datetime, timedelta

from domain.entities import Market
from domain.use_cases.ports import MarketApiPort, RepositoryPort

logger = logging.getLogger(__name__)


class PollMarkets:
    """Use case: load markets of interesting tags that close within the window (or closed less than
    `grace` ago, since trading often goes on until resolution) and store them."""

    def __init__(self, api: MarketApiPort, repo: RepositoryPort, window: timedelta, grace: timedelta):
        self._api = api
        self._repo = repo
        self._window = window
        self._grace = grace

    def execute(self, tag_ids: list[int], now: datetime) -> int:
        by_id: dict[str, Market] = {}
        for tid in tag_ids:
            try:
                markets = self._api.fetch_closing_markets(tid, now - self._grace, now + self._window)
            except Exception as e:
                logger.error("Failed to poll tag_id=%s: %s", tid, e)
                continue
            for m in markets:
                seen = by_id.get(m.condition_id)
                # A market can carry several interesting tags: store it once with all of them.
                by_id[m.condition_id] = m if seen is None else replace(seen, tag_ids=seen.tag_ids + m.tag_ids)
        self._repo.save_markets(list(by_id.values()), now)
        return len(by_id)
