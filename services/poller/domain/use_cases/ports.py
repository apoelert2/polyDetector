from abc import ABC, abstractmethod
from typing import Any


class MessagePublisherPort(ABC):
    @abstractmethod
    def publish(self, routing_key: str, message: dict[str, Any]) -> None: ...


class MarketApiPort(ABC):
    @abstractmethod
    def fetch_markets(self, tag_id: int) -> list[dict[str, Any]]: ...
