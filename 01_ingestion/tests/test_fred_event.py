from module_loader import load_package


build_macro_event = load_package("ingestion_fred", "02_fred").build_macro_event


def test_build_macro_event_shape() -> None:
    event = build_macro_event(
        series_id="CPIAUCSL",
        observation_date="2024-03-01",
        value=312.332,
        release_ts_ms=1709251200000,
        realtime_start="2024-04-10",
        realtime_end="2024-04-10",
    )

    assert event["source"] == "fred_observation"
    assert event["entity_key"] == "CPIAUCSL"
    assert event["payload"] == {
        "series_id": "CPIAUCSL",
        "observation_date": "2024-03-01",
        "value": 312.332,
        "release_ts_ms": 1709251200000,
        "realtime_start": "2024-04-10",
        "realtime_end": "2024-04-10",
    }
