from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def utc_now_ms() -> int:
    return int(datetime.now(tz=timezone.utc).timestamp() * 1000)


@dataclass(frozen=True)
class EventEnvelope:
    event_id: str
    source: str
    entity_key: str
    event_ts_ms: int
    ingest_ts_ms: int
    schema_version: str
    payload: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "source": self.source,
            "entity_key": self.entity_key,
            "event_ts_ms": self.event_ts_ms,
            "ingest_ts_ms": self.ingest_ts_ms,
            "schema_version": self.schema_version,
            "payload": self.payload,
        }


def build_market_trade_event(
    *,
    source: str,
    symbol: str,
    price: float,
    size: int,
    event_ts_ms: int,
) -> dict[str, Any]:
    envelope = EventEnvelope(
        event_id=str(uuid4()),
        source=source,
        entity_key=symbol,
        event_ts_ms=event_ts_ms,
        ingest_ts_ms=utc_now_ms(),
        schema_version="v1",
        payload={
            "symbol": symbol,
            "price": round(price, 4),
            "size": size,
        },
    )
    return envelope.as_dict()


def build_macro_release_event(
    *,
    source: str,
    series_id: str,
    observation_date: str,
    value: float,
    release_ts_ms: int,
    realtime_start: str,
    realtime_end: str,
) -> dict[str, Any]:
    envelope = EventEnvelope(
        event_id=str(uuid4()),
        source=source,
        entity_key=series_id,
        event_ts_ms=release_ts_ms,
        ingest_ts_ms=utc_now_ms(),
        schema_version="v1",
        payload={
            "series_id": series_id,
            "observation_date": observation_date,
            "value": value,
            "release_ts_ms": release_ts_ms,
            "realtime_start": realtime_start,
            "realtime_end": realtime_end,
        },
    )
    return envelope.as_dict()
