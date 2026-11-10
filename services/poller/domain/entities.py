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
