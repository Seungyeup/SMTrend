from module_loader import load_package


normalize_observations_response = load_package("ingestion_fred", "02_fred").normalize_observations_response


def test_normalize_observations_response_shape() -> None:
    rows = normalize_observations_response(
        series_id="UNRATE",
        payload={
            "observations": [
                {
                    "date": "2024-04-01",
                    "value": "3.8",
                    "realtime_start": "2024-05-03",
                    "realtime_end": "2024-05-03",
                }
            ]
        },
    )

    assert rows == [
        {
            "series_id": "UNRATE",
            "observation_date": "2024-04-01",
            "value": 3.8,
            "release_ts_ms": 1711929600000,
            "realtime_start": "2024-05-03",
            "realtime_end": "2024-05-03",
        }
    ]


def test_normalize_observations_response_skips_missing_value() -> None:
    rows = normalize_observations_response(
        series_id="UNRATE",
        payload={
            "observations": [
                {
                    "date": "2024-04-01",
                    "value": ".",
                    "realtime_start": "2024-05-03",
                    "realtime_end": "2024-05-03",
                }
            ]
        },
    )

    assert rows == []
