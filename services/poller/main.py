#!/usr/bin/env python3
# polyDetector Poller – Composition Root.

import logging
import os
import sys
import time
from datetime import UTC, datetime, timedelta

from adapters.data_api import DataApi
from adapters.gamma_api import GammaApi
from adapters.postgres_repository import PostgresRepository
from domain.use_cases.poll_markets import PollMarkets
from domain.use_cases.poll_trades import PollTrades
from settings import DbSettings
from utils import load_tag_ids

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("poller")


def main() -> None:
    tag_ids = load_tag_ids(os.getenv("TAG_IDS_PATH", "/data/tag_ids.json"))
    poll_interval = int(os.getenv("POLL_INTERVAL_SECONDS", "60"))
    window = timedelta(hours=float(os.getenv("CLOSING_WINDOW_HOURS", "24")))
    grace = timedelta(hours=float(os.getenv("CLOSING_GRACE_HOURS", "6")))
    backfill = timedelta(hours=float(os.getenv("TRADE_BACKFILL_HOURS", "24")))

    repo = PostgresRepository(DbSettings.from_env())
    poll_markets = PollMarkets(
        GammaApi(os.getenv("GAMMA_API_URL", "https://gamma-api.polymarket.com")), repo, window, grace
    )
    poll_trades = PollTrades(
        DataApi(os.getenv("DATA_API_URL", "https://data-api.polymarket.com")), repo, window, grace, backfill
    )

    logger.info(
        "Poller started. %d tag IDs, window=%s, grace=%s, interval=%ds", len(tag_ids), window, grace, poll_interval
    )
    while True:
        started = time.monotonic()
        now = datetime.now(UTC)
        try:
            markets = poll_markets.execute(tag_ids, now)
            trades = poll_trades.execute(now)
            logger.info("Cycle done: %d markets, %d trades", markets, trades)
        except Exception as e:
            logger.error("Poll cycle failed: %s", e)
        time.sleep(max(0.0, poll_interval - (time.monotonic() - started)))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Shutting down")
        sys.exit(0)
    except Exception as e:
        logger.critical("Fatal error: %s", e)
        sys.exit(1)
