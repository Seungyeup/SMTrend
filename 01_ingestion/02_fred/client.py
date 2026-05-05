"""FRED 외부 API 호출 전용 모듈.

현재 구현은 FRED observations API만 사용한다.
- endpoint: GET https://api.stlouisfed.org/fred/series/observations
- auth: query parameter `api_key`
- 사용 필드:
  - date: 관측 기준일
  - value: 관측값(문자열)
  - realtime_start / realtime_end: 이 값이 유효했던 revision 구간

지금 1차 ingestion에서는 시장 데이터와 조합하기 좋은 기본 거시 지표 3개를 쓴다.
- DFF: Effective Federal Funds Rate (정책금리 방향)
- CPIAUCSL: CPI (인플레이션)
- UNRATE: 실업률 (고용)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen


def _date_to_utc_ms(date_str: str) -> int:
    """YYYY-MM-DD 날짜를 UTC 자정 기준 ms 로 바꾼다."""
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def normalize_observations_response(*, series_id: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    """FRED observations 응답을 우리 내부 표준 필드로 정규화한다.

    예시 FRED observation:
    {
      "date": "2024-04-01",
      "value": "3.5",
      "realtime_start": "2024-04-10",
      "realtime_end": "2024-04-10"
    }

    예시 변환 결과:
    {
      "series_id": "UNRATE",
      "observation_date": "2024-04-01",
      "value": 3.5,
      "release_ts_ms": 1711929600000,
      "realtime_start": "2024-04-10",
      "realtime_end": "2024-04-10"
    }
    """
    observations = payload.get("observations")
    if not isinstance(observations, list):
        raise ValueError("FRED response is missing observations list")

    rows: list[dict[str, Any]] = []
    for item in observations:
        observation_date = item.get("date")
        value = item.get("value")
        realtime_start = item.get("realtime_start")
        realtime_end = item.get("realtime_end")

        if not observation_date or value is None or not realtime_start or not realtime_end:
            continue

        # FRED 는 결측치를 "." 로 줄 수 있다. 지금 단계에서는 Kafka로 보내지 않고 건너뛴다.
        if value == ".":
            continue

        numeric_value = float(value)
        release_ts_ms = _date_to_utc_ms(observation_date)

        rows.append(
            {
                "series_id": series_id,
                "observation_date": observation_date,
                "value": numeric_value,
                # FRED observations API 는 intraday release timestamp를 직접 주지 않으므로,
                # 학습용 1차 구현에서는 observation_date 의 UTC 자정을 대표 시각으로 사용한다.
                "release_ts_ms": release_ts_ms,
                "realtime_start": realtime_start,
                "realtime_end": realtime_end,
            }
        )

    return rows


def fetch_observations(*, api_key: str, series_id: str, limit: int = 10, timeout_s: int = 10) -> list[dict[str, Any]]:
    """FRED observations API를 호출한다.

    구현 목표는 복잡한 vintage/history 전체가 아니라,
    지정한 series의 최근 관측값 몇 개를 가져와 Kafka 이벤트로 바꾸는 것이다.
    """
    query_string = urlencode(
        {
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": limit,
        }
    )
    url = f"https://api.stlouisfed.org/fred/series/observations?{query_string}"

    try:
        with urlopen(url, timeout=timeout_s) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"FRED request failed with HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"FRED request failed: {exc.reason}") from exc

    return normalize_observations_response(series_id=series_id, payload=payload)
