from abc import ABC, abstractmethod
from collections.abc import Iterator
from datetime import datetime

from domain.entities import Market, Resolution, Trade


class MarketApiPort(ABC):
    @abstractmethod
    def fetch_closing_markets(self, tag_id: int, end_min: datetime, end_max: datetime) -> list[Market]: ...


class ResolutionApiPort(ABC):
    @abstractmethod
    def fetch_resolutions(self, condition_ids: list[str]) -> list[Resolution]:
        """Resolutions of those markets that are resolved by now; unresolved ones are left out."""


class TradeApiPort(ABC):
    @abstractmethod
    def iter_trades(self, condition_ids: list[str]) -> Iterator[Trade]:
        """Yield trades for the given markets, newest first."""


class RepositoryPort(ABC):
    @abstractmethod
    def save_markets(self, markets: list[Market], polled_at: datetime) -> None: ...

    @abstractmethod
    def closing_market_ids(self, end_min: datetime, end_max: datetime) -> list[str]: ...

    @abstractmethod
    def latest_trade_times(self, condition_ids: list[str]) -> dict[str, datetime]: ...

    @abstractmethod
    def save_trades(self, trades: list[Trade]) -> None: ...

    @abstractmethod
    def unresolved_market_ids(self, ended_after: datetime, ended_before: datetime) -> list[str]: ...

    @abstractmethod
    def save_resolutions(self, resolutions: list[Resolution]) -> None: ...
