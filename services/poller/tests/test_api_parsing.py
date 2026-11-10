# Parsing tests against real (trimmed) API responses saved in tests/fixtures.

import json
from datetime import UTC, datetime
from pathlib import Path

from adapters.data_api import parse_trade
from adapters.gamma_api import parse_market

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
