import logging
from typing import Any

from domain.entities import EnrichedMarket
from domain.use_cases.ports import MessageConsumerPort, MessagePublisherPort

logger = logging.getLogger(__name__)


def _extract_float(data: dict[str, Any], key: str) -> float | None:
    """Safely extract a float value from a dict, returning None if missing/invalid."""
    val = data.get(key)
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _enrich_market(raw: dict[str, Any]) -> EnrichedMarket | None:
    """Transform a raw market dict into an EnrichedMarket."""
    condition_id = raw.get("condition_id")
    if not condition_id:
        logger.warning("Skipping market without condition_id: %s", raw.get("id", "?"))
        return None

    outcomes = raw.get("outcomes")
    if isinstance(outcomes, list):
        parsed_outcomes = []
        for o in outcomes:
            if isinstance(o, dict):
                parsed_outcomes.append(o)
            else:
                parsed_outcomes.append({"name": str(o)})
        outcomes = parsed_outcomes

    return EnrichedMarket(
        condition_id=str(condition_id),
        question=str(raw.get("question", "")),
        description=raw.get("description"),
        outcomes=outcomes,
        volume=_extract_float(raw, "volume"),
        end_date=raw.get("end_date"),
        volume_24h=_extract_float(raw, "volume24hr"),
        liquidity=_extract_float(raw, "liquidity"),
        spread=_extract_float(raw, "spread"),
        tag_ids=raw.get("tag_ids"),
    )


class ProcessMarkets:
    """Use case: consume raw markets, enrich them, publish to next queue."""

    def __init__(self, consumer: MessageConsumerPort, publisher: MessagePublisherPort) -> None:
        self._consumer = consumer
        self._publisher = publisher

    def _handle_message(self, raw: dict[str, Any]) -> None:
        enriched = _enrich_market(raw)
        if enriched is None:
            return

        message = {
            "condition_id": enriched.condition_id,
            "question": enriched.question,
            "description": enriched.description,
            "outcomes": enriched.outcomes,
            "volume": enriched.volume,
            "end_date": enriched.end_date,
            "volume_24h": enriched.volume_24h,
            "liquidity": enriched.liquidity,
            "spread": enriched.spread,
            "tag_ids": enriched.tag_ids,
            "_source": enriched._source,
        }
        self._publisher.publish("markets.enriched", message)
        logger.info("Enriched and published market %s", enriched.condition_id)

    def execute(self, input_queue: str) -> None:
        """Start consuming from input_queue and publishing enriched data."""
        logger.info("Starting extractor – consuming from '%s'", input_queue)
        self._consumer.consume(input_queue, self._handle_message)
