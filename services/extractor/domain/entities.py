from dataclasses import dataclass, field
from typing import Any


@dataclass
class RawMarket:
    """Raw market data as received from the poller via markets.raw queue."""

    condition_id: str
    question: str | None = None
    description: str | None = None
    outcomes: list[dict[str, Any]] | None = None
    volume: float | None = None
    end_date: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class EnrichedMarket:
    """Enriched market data published to markets.enriched queue."""

    condition_id: str
    question: str
    description: str | None = None
    outcomes: list[dict[str, Any]] | None = None
    volume: float | None = None
    end_date: str | None = None
    volume_24h: float | None = None
    liquidity: float | None = None
    spread: float | None = None
    tag_ids: list[int] | None = None
    _source: str = "extractor"
