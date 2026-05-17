#!/usr/bin/env python3
#polyDetector Poller – Composition Root.

import json
import logging
import os
import sys
import time

from adapters.gamma_api import GammaApi
from adapters.rabbitmq_publisher import RabbitMqPublisher
from domain.use_cases.poll_markets import PollMarkets
from utils import load_tag_ids

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("poller")


# def load_tag_ids(path: str) -> list[int]:
#     with open(path) as f:
#         data = json.load(f)
#     if not isinstance(data, list):
#         data = [data]
#     # Handle objects with 'id' field vs raw integers
#     if data and isinstance(data[0], dict):
#         return [int(item['id']) for item in data]
#     return [int(i) for i in data]


def main() -> None:
    # Config
    rmq_host = os.getenv("RABBITMQ_HOST", "localhost")
    rmq_port = int(os.getenv("RABBITMQ_PORT", "5672"))
    rmq_user = os.getenv("RABBITMQ_USER", "guest")
    rmq_pass = os.getenv("RABBITMQ_PASS", "guest")
    gamma_url = os.getenv("GAMMA_API_URL", "https://gamma-api.polymarket.com")
    tag_ids_path = os.getenv("TAG_IDS_PATH", "/data/tag_ids.json")
    poll_interval = int(os.getenv("POLL_INTERVAL_SECONDS", "60"))

    # Adapters
    publisher = RabbitMqPublisher(host=rmq_host, port=rmq_port, user=rmq_user, password=rmq_pass)
    publisher.connect()

    api = GammaApi(base_url=gamma_url)

    # Use Case
    use_case = PollMarkets(api=api, publisher=publisher)

    # Load tag IDs
    try:
        tag_ids = load_tag_ids(tag_ids_path)
    except FileNotFoundError:
        logger.warning("tag_ids.json not found at %s – running with empty list", tag_ids_path)
        tag_ids = []

    logger.info("Poller started. %d tag IDs, interval=%ds", len(tag_ids), poll_interval)

    # Main loop
    while True:
        try:
            count = use_case.execute(tag_ids)
            logger.info("Polled %d markets", count)
        except Exception as e:
            logger.error("Poll cycle failed: %s", e)
        time.sleep(poll_interval)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Shutting down")
        sys.exit(0)
    except Exception as e:
        logger.critical("Fatal error: %s", e)
        sys.exit(1)
