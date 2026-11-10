import logging
from datetime import datetime, timedelta

from domain.entities import Trade
from domain.use_cases.ports import RepositoryPort, TradeApiPort

logger = logging.getLogger(__name__)

BATCH_SIZE = 20  # Data API v2: "'condition' accepts at most 20 distinct values"
OVERLAP = timedelta(minutes=1)  # re-read a little; duplicates are dropped by the DB


class PollTrades:
    """Use case: fetch new trades (with wallet) for markets that close within the window."""

    def __init__(self, api: TradeApiPort, repo: RepositoryPort, window: timedelta, backfill: timedelta):
        self._api = api
        self._repo = repo
        self._window = window
        self._backfill = backfill
        # Up to when each market was fetched. Lost on restart; then the DB or the backfill decides.
        self._checked: dict[str, datetime] = {}

    def execute(self, now: datetime) -> int:
        ids = self._repo.closing_market_ids(now, now + self._window)
        total = 0
        for i in range(0, len(ids), BATCH_SIZE):
            batch = ids[i : i + BATCH_SIZE]
            try:
                total += self._poll_batch(batch, now)
            except Exception as e:
                logger.error("Failed to poll trades for %d markets: %s", len(batch), e)
        return total

    def _poll_batch(self, batch: list[str], now: datetime) -> int:
        latest = self._repo.latest_trade_times(batch)
        since = {cid: self._checked.get(cid) or latest.get(cid) or now - self._backfill for cid in batch}
        stop_at = min(since.values()) - OVERLAP
        trades: list[Trade] = []
        for t in self._api.iter_trades(batch):
            if t.time < stop_at:
                break
            if t.time >= since.get(t.condition_id, stop_at) - OVERLAP:
                trades.append(t)
        self._repo.save_trades(trades)
        for cid in batch:
            self._checked[cid] = now
        return len(trades)
