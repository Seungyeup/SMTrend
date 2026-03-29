from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

import requests


def generate_mock_trade(*, current_price: float) -> tuple[float, int]:
    delta = random.uniform(-0.35, 0.35)
    next_price = max(1.0, current_price + delta)
    size = random.randint(10, 500)
    return round(next_price, 4), size


def fetch_finnhub_quote(*, api_key: str, symbol: str, timeout_s: int = 10) -> dict[str, Any]:
    response = requests.get(
        "https://finnhub.io/api/v1/quote",
        params={"symbol": symbol, "token": api_key},
        timeout=timeout_s,
    )
    response.raise_for_status()
    data = response.json()
    return {
        "symbol": symbol,
        "price": float(data["c"]),
        "event_ts_ms": int(data["t"]) * 1000,
        "size": 1,
    }


def fetch_fred_observations(
    *,
    api_key: str,
    series_id: str,
    limit: int,
    timeout_s: int = 20,
) -> list[dict[str, Any]]:
    response = requests.get(
        "https://api.stlouisfed.org/fred/series/observations",
        params={
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": limit,
        },
        timeout=timeout_s,
    )
    response.raise_for_status()
    payload = response.json()
    observations: list[dict[str, Any]] = []
    for row in payload.get("observations", []):
        value_raw = row.get("value", ".")
        if value_raw == ".":
            continue

        release_date = row.get("realtime_start") or row["date"]
        release_dt = datetime.strptime(release_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        release_ts_ms = int(release_dt.timestamp() * 1000)

        observations.append(
            {
                "series_id": series_id,
                "observation_date": row["date"],
                "value": float(value_raw),
                "release_ts_ms": release_ts_ms,
                "realtime_start": row.get("realtime_start", row["date"]),
                "realtime_end": row.get("realtime_end", row["date"]),
            }
        )
    return observations
