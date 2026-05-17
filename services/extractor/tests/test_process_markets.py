#Unit tests for ProcessMarkets use case.

from unittest.mock import MagicMock

from domain.use_cases.process_markets import ProcessMarkets, _enrich_market


def test_enrich_market_valid_data() -> None:
    raw = {
        "condition_id": "0xabc123",
        "question": "Will BTC reach $100k in 2025?",
        "description": "A market about Bitcoin",
        "outcomes": [{"name": "Yes"}, {"name": "No"}],
        "volume": "1500000.50",
        "end_date": "2025-12-31T23:59:59Z",
        "volume24hr": "50000.00",
        "liquidity": "2000000",
        "spread": "0.05",
    }
    enriched = _enrich_market(raw)
    assert enriched is not None
    assert enriched.condition_id == "0xabc123"
    assert enriched.question == "Will BTC reach $100k in 2025?"
    assert enriched.volume == 1500000.50
    assert enriched.volume_24h == 50000.00
    assert enriched.liquidity == 2000000.0
    assert enriched.spread == 0.05
    assert enriched.end_date == "2025-12-31T23:59:59Z"
    assert enriched._source == "extractor"


def test_enrich_market_missing_condition_id() -> None:
    raw = {"question": "Some market"}
    enriched = _enrich_market(raw)
    assert enriched is None


def test_enrich_market_string_outcomes() -> None:
    raw = {
        "condition_id": "0xdef456",
        "question": "Test?",
        "outcomes": ["Yes", "No"],
    }
    enriched = _enrich_market(raw)
    assert enriched is not None
    assert enriched.outcomes == [{"name": "Yes"}, {"name": "No"}]


def test_enrich_market_invalid_volume() -> None:
    raw = {
        "condition_id": "0xghi789",
        "question": "Test?",
        "volume": "not-a-number",
    }
    enriched = _enrich_market(raw)
    assert enriched is not None
    assert enriched.volume is None


def test_process_markets_handle_message() -> None:
    consumer = MagicMock()
    publisher = MagicMock()
    use_case = ProcessMarkets(consumer=consumer, publisher=publisher)

    raw = {
        "condition_id": "0xabc",
        "question": "Test market",
        "volume": "1000",
    }
    use_case._handle_message(raw)

    publisher.publish.assert_called_once()
    call_args = publisher.publish.call_args
    assert call_args[0][0] == "markets.enriched"
    assert call_args[0][1]["condition_id"] == "0xabc"
    assert call_args[0][1]["_source"] == "extractor"


def test_process_markets_skip_invalid() -> None:
    consumer = MagicMock()
    publisher = MagicMock()
    use_case = ProcessMarkets(consumer=consumer, publisher=publisher)

    use_case._handle_message({"question": "No condition_id"})
    publisher.publish.assert_not_called()
