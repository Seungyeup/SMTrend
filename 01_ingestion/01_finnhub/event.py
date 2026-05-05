"""우리 시스템 내부 이벤트 포맷 정의.

지금은 Finnhub 시장 이벤트 하나만 만들기 때문에,
검증 로직도 최대한 단순하게 유지한다.
"""

import math
from datetime import datetime, timezone
from uuid import uuid4


def utc_now_ms():
    """현재 UTC 시각을 millisecond 단위로 반환한다."""
    return int(datetime.now(tz=timezone.utc).timestamp() * 1000)


def build_market_event(source, symbol, price, size, event_ts_ms):
    """시장 데이터를 Kafka에 넣기 위한 공통 이벤트 형식으로 감싼다."""
    if not isinstance(source, str) or not source.strip():
        raise ValueError("source must be a non-empty string")

    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("symbol must be a non-empty string")

    if not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0:
        raise ValueError("price must be a positive finite number")

    if not isinstance(size, int) or size <= 0:
        raise ValueError("size must be a positive integer")

    if not isinstance(event_ts_ms, int) or event_ts_ms <= 0:
        raise ValueError("event_ts_ms must be a positive integer")

    # 외부 응답을 그대로 Kafka에 넣지 않고, 항상 같은 envelope 구조로 감싼다.
    return {
        "event_id": str(uuid4()),
        "source": source,
        "entity_key": symbol,
        "event_ts_ms": event_ts_ms,
        "ingest_ts_ms": utc_now_ms(),
        "schema_version": "v1",
        "payload": {
            "symbol": symbol,
            "price": round(price, 4),
            "size": size,
        },
    }
