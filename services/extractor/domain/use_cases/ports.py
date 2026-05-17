from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

MessageHandler = Callable[[dict[str, Any]], None]


class MessageConsumerPort(ABC):
    @abstractmethod
    def consume(self, queue: str, callback: MessageHandler) -> None: ...


class MessagePublisherPort(ABC):
    @abstractmethod
    def publish(self, routing_key: str, message: dict[str, Any]) -> None: ...
