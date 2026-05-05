"""FRED 관련 기능을 묶어두는 패키지.

구조는 Finnhub와 동일하게 맞춘다.
- client.py: FRED API 호출
- event.py: 우리 시스템 내부 이벤트 포맷 변환

Kafka 전송은 이미 만든 공용 KafkaJsonProducer를 그대로 재사용한다.
"""

from module_loader import load_package

from .client import fetch_observations, normalize_observations_response
from .event import build_macro_event


KafkaJsonProducer = load_package("ingestion_finnhub", "01_finnhub").KafkaJsonProducer

__all__ = [
    "KafkaJsonProducer",
    "build_macro_event",
    "fetch_observations",
    "normalize_observations_response",
]
