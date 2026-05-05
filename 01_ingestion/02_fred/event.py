"""FRED macro 데이터를 Kafka 이벤트로 감싸는 모듈.

Finnhub와 마찬가지로 외부 응답을 그대로 Kafka에 넣지 않고,
공통 envelope 구조로 감싼다.
"""

import math

from module_loader import load_package


utc_now_ms = load_package("ingestion_finnhub", "01_finnhub").utc_now_ms


def build_macro_event(series_id, observation_date, value, release_ts_ms, realtime_start, realtime_end):
    """FRED 관측값을 공통 이벤트 형식으로 감싼다.

    예시 입력:
    - series_id = "CPIAUCSL"
    - observation_date = "2024-03-01"
    - value = 312.332

    예시 출력 payload:
    {
      "series_id": "CPIAUCSL",
      "observation_date": "2024-03-01",
      "value": 312.332,
      "release_ts_ms": 1709251200000,
      "realtime_start": "2024-04-10",
      "realtime_end": "2024-04-10"
    }
    """
    if not isinstance(series_id, str) or not series_id.strip():
        raise ValueError("series_id must be a non-empty string")

    if not isinstance(observation_date, str) or not observation_date.strip():
        raise ValueError("observation_date must be a non-empty string")

    if not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("value must be a finite number")

    if not isinstance(release_ts_ms, int) or release_ts_ms <= 0:
        raise ValueError("release_ts_ms must be a positive integer")

    if not isinstance(realtime_start, str) or not realtime_start.strip():
        raise ValueError("realtime_start must be a non-empty string")

    if not isinstance(realtime_end, str) or not realtime_end.strip():
        raise ValueError("realtime_end must be a non-empty string")

    return {
        "event_id": f"{series_id}-{observation_date}-{release_ts_ms}",
        "source": "fred_observation",
        "entity_key": series_id,
        "event_ts_ms": release_ts_ms,
        "ingest_ts_ms": utc_now_ms(),
        "schema_version": "v1",
        "payload": {
            "series_id": series_id,
            "observation_date": observation_date,
            "value": value,
            "release_ts_ms": release_ts_ms,
            "realtime_start": realtime_start,
            "realtime_end": realtime_end,
        },
    }
