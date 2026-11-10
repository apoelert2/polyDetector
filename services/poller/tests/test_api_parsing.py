# Parsing tests against real (trimmed) API responses saved in tests/fixtures.

import json
from datetime import UTC, datetime
from pathlib import Path

from adapters.data_api import parse_trade
from adapters.gamma_api import GammaApi, parse_market, parse_resolution

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_market_maps_gamma_fields() -> None:
    raw = json.loads((FIXTURES / "gamma_markets.json").read_text())[0]
    m = parse_market(raw, tag_id=2)
    assert m is not None
    assert m.condition_id == raw["conditionId"]
    assert m.outcomes == ("Yes", "No")
    assert m.outcome_prices == (0.9865, 0.0135)
    assert len(m.token_ids) == 2
    assert m.end_date == datetime(2026, 11, 10, 17, tzinfo=UTC)
    assert m.volume is not None and m.volume_24h is not None  # one is a string, one a number in the API
    assert m.tag_ids == (2,)


def test_parse_market_without_condition_id_is_skipped() -> None:
    assert parse_market({"id": "1", "question": "x"}, tag_id=2) is None


def test_parse_trade_maps_data_api_fields() -> None:
    raw = json.loads((FIXTURES / "data_api_trades.json").read_text())["data"][0]
    t = parse_trade(raw)
    assert t.proxy_wallet.startswith("0x")
    assert t.transaction_hash == raw["transaction_hash"]
    assert t.time == datetime.fromtimestamp(raw["timestamp"], UTC)
    assert t.side in ("BUY", "SELL")


def test_parse_resolution_finds_winner_from_real_response() -> None:
    raw = json.loads((FIXTURES / "gamma_resolved_market.json").read_text())[0]
    r = parse_resolution(raw)
    assert r is not None
    assert r.winning_outcome == "No"  # outcomePrices ["0", "1"]
    assert r.winning_token_id == json.loads(raw["clobTokenIds"])[1]
    assert r.resolved_at == datetime(2026, 8, 8, 20, 27, 18, tzinfo=UTC)


def test_parse_resolution_unresolved_and_refund() -> None:
    raw = json.loads((FIXTURES / "gamma_resolved_market.json").read_text())[0]
    assert parse_resolution({**raw, "umaResolutionStatus": "proposed"}) is None
    assert parse_resolution({**raw, "closed": False}) is None
    refund = parse_resolution({**raw, "outcomePrices": '["0.5", "0.5"]'})
    assert refund is not None
    assert refund.winning_token_id is None
    assert refund.final_prices == (0.5, 0.5)


def test_fetch_resolutions_skips_unreadable_record_and_keeps_the_rest() -> None:
    good = json.loads((FIXTURES / "gamma_resolved_market.json").read_text())[0]
    bad = {**good, "conditionId": "0xbad", "outcomePrices": '["x", "1"]'}

    class FakeSession:
        def get(self, *args: object, **kwargs: object) -> "FakeSession":
            return self

        def raise_for_status(self) -> None: ...

        def json(self) -> list[dict[str, object]]:
            return [bad, good]

    api = GammaApi("http://gamma.test")
    api._session = FakeSession()  # type: ignore[assignment]
    assert [r.condition_id for r in api.fetch_resolutions(["0xbad", good["conditionId"]])] == [good["conditionId"]]
