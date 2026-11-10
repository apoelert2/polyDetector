from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from domain.entities import Market, Trade
from domain.use_cases.poll_markets import PollMarkets
from domain.use_cases.poll_trades import PollTrades
from domain.use_cases.ports import MarketApiPort, RepositoryPort, TradeApiPort

NOW = datetime(2026, 11, 10, 12, tzinfo=UTC)
MARKET = Market(
    "0xa", "Q?", None, NOW + timedelta(hours=2), False, ("Yes", "No"), ("1", "2"), (0.4, 0.6), None, None, None, (2,)
)


class FakeRepo(RepositoryPort):
    def __init__(self, ids: list[str] | None = None, latest: dict[str, datetime] | None = None):
        self.markets: list[Market] = []
        self.trades: list[Trade] = []
        self._ids = ids or []
        self._latest = latest or {}

    def save_markets(self, markets: list[Market], polled_at: datetime) -> None:
        self.markets = markets

    def closing_market_ids(self, end_min: datetime, end_max: datetime) -> list[str]:
        return self._ids

    def latest_trade_times(self, condition_ids: list[str]) -> dict[str, datetime]:
        return self._latest

    def save_trades(self, trades: list[Trade]) -> None:
        self.trades += trades


class FakeMarketApi(MarketApiPort):
    def fetch_closing_markets(self, tag_id: int, end_min: datetime, end_max: datetime) -> list[Market]:
        if tag_id == 99:
            raise ConnectionError("boom")
        return [replace(MARKET, tag_ids=(tag_id,))]


def trade(cid: str, minutes_ago: int) -> Trade:
    return Trade(
        NOW - timedelta(minutes=minutes_ago), f"0xtx{cid}{minutes_ago}", cid, "1", "0xw", "BUY", 10, 0.5, "Yes"
    )


class FakeTradeApi(TradeApiPort):
    def __init__(self, trades: list[Trade]):
        self._trades = sorted(trades, key=lambda t: t.time, reverse=True)
        self.consumed = 0

    def iter_trades(self, condition_ids: list[str]) -> Iterator[Trade]:
        for t in self._trades:
            if t.condition_id in condition_ids:
                self.consumed += 1
                yield t


def test_poll_markets_merges_tags_and_survives_failing_tag() -> None:
    repo = FakeRepo()
    count = PollMarkets(FakeMarketApi(), repo, timedelta(hours=24)).execute([2, 99, 126], NOW)
    assert count == 1
    assert repo.markets[0].tag_ids == (2, 126)


def test_poll_trades_respects_backfill_and_last_seen() -> None:
    repo = FakeRepo(ids=["0xa", "0xb"], latest={"0xa": NOW - timedelta(minutes=10)})
    api = FakeTradeApi([trade("0xa", 5), trade("0xa", 30), trade("0xb", 30), trade("0xb", 300)])
    use_case = PollTrades(api, repo, window=timedelta(hours=24), backfill=timedelta(hours=1))

    assert use_case.execute(NOW) == 2  # 0xa: only newer than last seen; 0xb: only within backfill
    assert {(t.condition_id, t.time) for t in repo.trades} == {
        ("0xa", NOW - timedelta(minutes=5)),
        ("0xb", NOW - timedelta(minutes=30)),
    }


def test_poll_trades_second_cycle_does_not_reread_backfill() -> None:
    repo = FakeRepo(ids=["0xa", "0xquiet"])
    api = FakeTradeApi([trade("0xa", m) for m in range(0, 600, 10)])
    use_case = PollTrades(api, repo, window=timedelta(hours=24), backfill=timedelta(hours=10))
    use_case.execute(NOW)
    api.consumed = 0
    use_case.execute(NOW + timedelta(minutes=1))
    assert api.consumed <= 3  # stops near the last check, even though 0xquiet never had a trade
