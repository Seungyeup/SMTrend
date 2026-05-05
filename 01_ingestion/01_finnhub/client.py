"""Finnhub 외부 API 호출 전용 모듈.

현재 구현은 Finnhub 문서의 Quote API만 사용한다.
- endpoint: GET https://finnhub.io/api/v1/quote
- auth: query parameter `token`
- 사용 필드:
  - c: current price (현재가)
  - t: unix timestamp seconds (호가/체결 시각이 아니라 quote 시각)

문서에는 d, dp, h, l, o, pc 같은 필드도 있지만,
지금 1차 ingestion에서는 downstream에 꼭 필요한 최소 필드만 남긴다.
"""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen


def normalize_quote_response(*, symbol: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Finnhub 응답을 우리 내부 표준 필드로 정규화한다.

    왜 이 단계가 필요하냐면, Finnhub 응답 키는 `c`, `t`처럼 짧고,
    그대로 downstream에 흘리면 이후 Flink/Trino 쪽에서 의미를 잊기 쉽기 때문이다.
    그래서 여기서 한 번 `price`, `event_ts_ms` 같은 명시적인 이름으로 바꾼다.

    Finnhub 문서상 quote 응답 필드는 optional일 수 있으므로,
    여기서는 우리가 실제로 사용하는 `c`(현재가), `t`(unix seconds timestamp)가
    없으면 명시적인 ValueError로 실패시킨다.
    """
    # `c`는 current price. 값이 없으면 우리가 필요한 최소 이벤트를 만들 수 없다.
    if payload.get("c") is None:
        raise ValueError("Finnhub quote response is missing field 'c' (current price)")
    # `t`는 quote timestamp(초 단위). 이것도 event-time 계산에 필요하다.
    if payload.get("t") is None:
        raise ValueError("Finnhub quote response is missing field 't' (timestamp)")

    # Finnhub 문서상 `t`는 seconds 이므로, 아래에서 ms 로 바꿔야 한다.
    price = float(payload["c"])
    event_ts_s = int(payload["t"])
    # 음수/0 가격은 downstream 시장 데이터로 보기 어렵기 때문에 막는다.
    if price <= 0:
        raise ValueError("Finnhub quote price must be positive")
    # timestamp 가 0 이하인 경우도 비정상 응답으로 본다.
    if event_ts_s <= 0:
        raise ValueError("Finnhub quote timestamp must be positive")

    # size 는 Finnhub quote API 에서 직접 주지 않으므로,
    # 현재 단계에서는 1로 고정해서 "단일 quote 이벤트"라고 표현한다.
    return {
        "symbol": symbol,
        "price": price,
        "event_ts_ms": event_ts_s * 1000,
        "size": 1,
    }


def fetch_quote(*, api_key: str, symbol: str, timeout_s: int = 10) -> dict[str, Any]:
    """Finnhub Quote API를 호출한다.

    문서상 인증은 `token` query parameter 또는 `X-Finnhub-Token` header를 쓸 수 있다.
    여기서는 curl/브라우저에서 바로 재현하기 쉬운 query parameter 방식을 사용한다.

    참고로 Finnhub 문서에는 constant polling 보다 websocket 사용을 권장한다.
    하지만 지금 단계는 local 학습용 ingestion 이므로 단순 polling 구현으로 시작한다.
    """
    # 표준 라이브러리만 쓰기 위해 query string을 직접 만든다.
    query_string = urlencode({"symbol": symbol, "token": api_key})
    url = f"https://finnhub.io/api/v1/quote?{query_string}"

    try:
        # 실제 HTTP GET 요청을 보내고 응답 본문을 JSON으로 읽는다.
        with urlopen(url, timeout=timeout_s) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"Finnhub request failed with HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"Finnhub request failed: {exc.reason}") from exc

    # 받은 JSON 응답을 우리 내부 표준 필드 구조로 정규화한다.
    return normalize_quote_response(symbol=symbol, payload=payload)
