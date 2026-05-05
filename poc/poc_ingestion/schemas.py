from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math
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


def _require_non_empty_string(*, name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _require_positive_int(*, name: str, value: int) -> None:
    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")


def _require_positive_number(*, name: str, value: float) -> None:
    if not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a positive finite number")


def _require_finite_number(*, name: str, value: float) -> None:
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")


def _require_iso_date(*, name: str, value: str) -> None:
    _require_non_empty_string(name=name, value=value)
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(f"{name} must use YYYY-MM-DD format") from exc


def validate_event_envelope(event: dict[str, Any]) -> None:
    required_keys = {
        "event_id",
        "source",
        "entity_key",
        "event_ts_ms",
        "ingest_ts_ms",
        "schema_version",
        "payload",
    }
    missing_keys = required_keys.difference(event)
    if missing_keys:
        missing_csv = ", ".join(sorted(missing_keys))
        raise ValueError(f"event is missing required keys: {missing_csv}")

    _require_non_empty_string(name="event_id", value=str(event["event_id"]))
    _require_non_empty_string(name="source", value=str(event["source"]))
    _require_non_empty_string(name="entity_key", value=str(event["entity_key"]))
    _require_positive_int(name="event_ts_ms", value=event["event_ts_ms"])
    _require_positive_int(name="ingest_ts_ms", value=event["ingest_ts_ms"])
    _require_non_empty_string(name="schema_version", value=str(event["schema_version"]))
    if not isinstance(event["payload"], dict):
        raise ValueError("payload must be an object")


def build_market_trade_event(
    *,
    source: str,
    symbol: str,
    price: float,
    size: int,
    event_ts_ms: int,
) -> dict[str, Any]:
    _require_non_empty_string(name="source", value=source)
    _require_non_empty_string(name="symbol", value=symbol)
    _require_positive_number(name="price", value=price)
    _require_positive_int(name="size", value=size)
    _require_positive_int(name="event_ts_ms", value=event_ts_ms)

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
    event = envelope.as_dict()
    validate_event_envelope(event)
    return event


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
    _require_non_empty_string(name="source", value=source)
    _require_non_empty_string(name="series_id", value=series_id)
    _require_iso_date(name="observation_date", value=observation_date)
    _require_finite_number(name="value", value=value)
    _require_positive_int(name="release_ts_ms", value=release_ts_ms)
    _require_iso_date(name="realtime_start", value=realtime_start)
    _require_iso_date(name="realtime_end", value=realtime_end)

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
    event = envelope.as_dict()
    validate_event_envelope(event)
    return event


def build_dlq_event(
    *,
    source: str,
    entity_key: str,
    original_topic: str,
    original_key: str,
    failure_stage: str,
    error_type: str,
    error_message: str,
    failed_payload: dict[str, Any],
) -> dict[str, Any]:
    _require_non_empty_string(name="source", value=source)
    _require_non_empty_string(name="entity_key", value=entity_key)
    _require_non_empty_string(name="original_topic", value=original_topic)
    _require_non_empty_string(name="original_key", value=original_key)
    _require_non_empty_string(name="failure_stage", value=failure_stage)
    _require_non_empty_string(name="error_type", value=error_type)
    _require_non_empty_string(name="error_message", value=error_message)

    event = EventEnvelope(
        event_id=str(uuid4()),
        source=source,
        entity_key=entity_key,
        event_ts_ms=utc_now_ms(),
        ingest_ts_ms=utc_now_ms(),
        schema_version="v1",
        payload={
            "original_topic": original_topic,
            "original_key": original_key,
            "failure_stage": failure_stage,
            "error_type": error_type,
            "error_message": error_message,
            "failed_payload": failed_payload,
        },
    ).as_dict()
    validate_event_envelope(event)
    return event
