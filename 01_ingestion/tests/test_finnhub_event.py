import pytest

from module_loader import load_package


build_market_event = load_package("ingestion_finnhub", "01_finnhub").build_market_event


def test_build_market_event_shape() -> None:
    event = build_market_event(
        source="finnhub_quote",
        symbol="AAPL",
        price=187.2159,
        size=1,
        event_ts_ms=1_717_171_717_000,
    )

    assert event["source"] == "finnhub_quote"
    assert event["entity_key"] == "AAPL"
    assert event["payload"] == {
        "symbol": "AAPL",
        "price": 187.2159,
        "size": 1,
    }


def test_build_market_event_rejects_invalid_price() -> None:
    with pytest.raises(ValueError, match="price"):
        build_market_event(
            source="finnhub_quote",
            symbol="AAPL",
            price=0.0,
            size=1,
            event_ts_ms=1_717_171_717_000,
        )
