from poc_ingestion.schemas import build_macro_release_event, build_market_trade_event


def test_build_market_trade_event_shape() -> None:
    event = build_market_trade_event(
        source="finnhub_mock",
        symbol="GOOG",
        price=182.1234,
        size=100,
        event_ts_ms=1_700_000_000_000,
    )

    assert event["source"] == "finnhub_mock"
    assert event["entity_key"] == "GOOG"
    assert event["payload"]["symbol"] == "GOOG"
    assert event["payload"]["price"] == 182.1234
    assert event["payload"]["size"] == 100


def test_build_macro_release_event_shape() -> None:
    event = build_macro_release_event(
        source="fred_batch",
        series_id="DFF",
        observation_date="2026-03-25",
        value=4.5,
        release_ts_ms=1_700_000_000_000,
        realtime_start="2026-03-25",
        realtime_end="2026-03-25",
    )

    assert event["source"] == "fred_batch"
    assert event["entity_key"] == "DFF"
    assert event["payload"]["series_id"] == "DFF"
    assert event["payload"]["value"] == 4.5
