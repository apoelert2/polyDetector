import json
import logging
from typing import Any

import pika
from domain.use_cases.ports import MessagePublisherPort

logger = logging.getLogger(__name__)


class RabbitMqPublisher(MessagePublisherPort):
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5672,
        user: str = "guest",
        password: str = "guest",
    ):
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._connection: pika.BlockingConnection | None = None
        self._channel: pika.adapters.blocking_connection.BlockingChannel | None = None

    def connect(self) -> None:
        credentials = pika.PlainCredentials(self._user, self._password)
        params = pika.ConnectionParameters(
            host=self._host,
            port=self._port,
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300,
        )
        self._connection = pika.BlockingConnection(params)
        self._channel = self._connection.channel()
        self._channel.exchange_declare(exchange="polymarket", exchange_type="topic", durable=True)
        self._channel.queue_declare(queue="markets.raw", durable=True)
        self._channel.queue_bind(exchange="polymarket", queue="markets.raw", routing_key="markets.raw")
        logger.info("Connected to RabbitMQ at %s:%s", self._host, self._port)

    def publish(self, routing_key: str, message: dict[str, Any]) -> None:
        if not self._channel or self._channel.is_closed:
            self.connect()
        assert self._channel is not None
        body = json.dumps(message, default=str)
        self._channel.basic_publish(
            exchange="polymarket",
            routing_key=routing_key,
            body=body,
            properties=pika.BasicProperties(
                delivery_mode=2,  # persistent
                content_type="application/json",
            ),
        )
        logger.debug("Published %s -> %s", routing_key, message.get("condition_id", "?"))

    def close(self) -> None:
        if self._connection and not self._connection.is_closed:
            self._connection.close()
            logger.info("RabbitMQ connection closed")
