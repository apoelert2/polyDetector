import logging
from datetime import datetime, timedelta

from domain.use_cases.ports import RepositoryPort, ResolutionApiPort

logger = logging.getLogger(__name__)


class ResolveMarkets:
    """Use case: record who won for markets that ended. PollMarkets only sees open markets, so the result
    has to be fetched separately. Markets are checked every cycle until resolved, for at most `lookback`
    after their end date (disputed resolutions take days; shortcut: older ones are given up on)."""

    def __init__(self, api: ResolutionApiPort, repo: RepositoryPort, lookback: timedelta):
        self._api = api
        self._repo = repo
        self._lookback = lookback

    def execute(self, now: datetime) -> int:
        ids = self._repo.unresolved_market_ids(now - self._lookback, now)
        if not ids:
            return 0
        resolutions = self._api.fetch_resolutions(ids)
        self._repo.save_resolutions(resolutions)
        return len(resolutions)
