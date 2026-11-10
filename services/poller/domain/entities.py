from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Market:
    condition_id: str
    question: str
    slug: str | None
    end_date: datetime | None
    closed: bool
    outcomes: tuple[str, ...]
    token_ids: tuple[str, ...]
    outcome_prices: tuple[float, ...]
    volume: float | None
    volume_24h: float | None
    liquidity: float | None
    tag_ids: tuple[int, ...]


@dataclass(frozen=True)
class Trade:
    time: datetime
    transaction_hash: str
    condition_id: str
    token_id: str
    proxy_wallet: str
    side: str
    size: float
    price: float
    outcome: str | None


@dataclass(frozen=True)
class Resolution:
    """Final outcome of a market. winning_token_id is None if no outcome won outright (e.g. a 50/50 refund)."""

    condition_id: str
    resolved_at: datetime
    winning_token_id: str | None
    winning_outcome: str | None
    final_prices: tuple[float, ...]
