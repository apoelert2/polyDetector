import logging

from domain.entities import Market
from domain.use_cases.ports import MarketApiPort, MessagePublisherPort

logger = logging.getLogger(__name__)


class PollMarkets:
    """Use Case: Ruft Märkte für gegebene Tag-IDs ab und publisht sie."""

    def __init__(self, api: MarketApiPort, publisher: MessagePublisherPort):
        self._api = api
        self._publisher = publisher

    def execute(self, tag_ids: list[int]) -> int:
        count = 0
        for tid in tag_ids:
            try:
                raw_markets = self._api.fetch_markets(tid)
                for raw in raw_markets:
                    market = Market(condition_id=raw.get("condition_id", ""))
                    enriched = {
                        "condition_id": market.condition_id,
                        "question": raw.get("question"),
                        "outcomes": raw.get("outcomes"),
                        "volume": raw.get("volume"),
                        "end_date": raw.get("end_date"),
                        "_source": "poller",
                        "tag_id": tid,
                    }
                    self._publisher.publish("markets.raw", enriched)
                    count += 1
            except Exception as e:
                logger.error("Failed to poll tag_id=%s: %s", tid, e)
        return count
