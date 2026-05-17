#!/usr/bin/env python3
"""polyDetector Extractor – Composition Root."""

import logging
import os
import sys

from adapters.rabbitmq_consumer import RabbitMqConsumer
from adapters.rabbitmq_publisher import RabbitMqPublisher
from domain.use_cases.process_markets import ProcessMarkets

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("extractor")


def main() -> None:
    rmq_host = os.getenv("RABBITMQ_HOST", "localhost")
    rmq_port = int(os.getenv("RABBITMQ_PORT", "5672"))
    rmq_user = os.getenv("RABBITMQ_USER", "guest")
    rmq_pass = os.getenv("RABBITMQ_PASS", "guest")
    input_queue = os.getenv("INPUT_QUEUE", "markets.raw")

    consumer = RabbitMqConsumer(host=rmq_host, port=rmq_port, user=rmq_user, password=rmq_pass)
    consumer.connect()

    publisher = RabbitMqPublisher(host=rmq_host, port=rmq_port, user=rmq_user, password=rmq_pass)
    publisher.connect()

    use_case = ProcessMarkets(consumer=consumer, publisher=publisher)

    logger.info("Extractor started – consuming from '%s'", input_queue)
    use_case.execute(input_queue)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Shutting down")
        sys.exit(0)
    except Exception as e:
        logger.critical("Fatal error: %s", e)
        sys.exit(1)
