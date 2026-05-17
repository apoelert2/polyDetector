import json
import logging
from collections.abc import Callable
from typing import Any

import pika
from domain.use_cases.ports import MessageConsumerPort

logger = logging.getLogger(__name__)


class RabbitMqConsumer(MessageConsumerPort):
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
        logger.info("Connected to RabbitMQ at %s:%s", self._host, self._port)

    def consume(self, queue: str, callback: Callable[[dict[str, Any]], None]) -> None:
        if not self._channel or self._channel.is_closed:
            self.connect()
        assert self._channel is not None

        self._channel.queue_declare(queue=queue, durable=True)
        self._channel.queue_bind(exchange="polymarket", queue=queue, routing_key=queue)

        def _on_message(
            ch: pika.adapters.blocking_connection.BlockingChannel,
            method: pika.spec.Basic.Deliver,
            properties: pika.spec.BasicProperties,
            body: bytes,
        ) -> None:
            try:
                message = json.loads(body)
                callback(message)
            except json.JSONDecodeError as e:
                logger.error("Failed to decode message: %s", e)
            finally:
                ch.basic_ack(delivery_tag=method.delivery_tag)

        self._channel.basic_qos(prefetch_count=1)
        self._channel.basic_consume(queue=queue, on_message_callback=_on_message)
        logger.info("Consuming from queue '%s'", queue)
        self._channel.start_consuming()

    def close(self) -> None:
        if self._connection and not self._connection.is_closed:
            self._connection.close()
            logger.info("RabbitMQ connection closed")
