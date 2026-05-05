"""Finnhub 관련 기능을 묶어두는 패키지.

초기 학습 단계에서는 파일을 역할별로 잘게 나누는 편이 이해하기 쉽다.
- client.py: 외부 API 호출
- event.py: 우리 시스템 내부 이벤트 포맷
- producer.py: Kafka 전송

main.py 는 이 세 가지를 조합만 한다.
"""

# 외부 API 호출 관련 함수.
from .client import fetch_quote, normalize_quote_response
# 우리 시스템 내부 이벤트 포맷 관련 함수.
from .event import build_market_event, utc_now_ms
# Kafka 전송 래퍼.
from .producer import KafkaJsonProducer

# main.py 에서 module_loader를 통해 안전한 별칭으로 가져갈 수 있게
# 공개 API 표면만 __all__ 에 명시한다.
__all__ = [
    "KafkaJsonProducer",
    "build_market_event",
    "fetch_quote",
    "normalize_quote_response",
    "utc_now_ms",
]
