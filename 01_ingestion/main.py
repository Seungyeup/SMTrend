"""01_ingestion의 진입점.

지금 단계에서는 복잡한 운영 기능보다
"Finnhub에서 데이터를 받아 Kafka로 보낸다"는 핵심 흐름만 남긴다.
"""

import argparse
import configparser
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from module_loader import load_package


FINNHUB_PACKAGE = load_package("ingestion_finnhub", "01_finnhub")
FRED_PACKAGE = load_package("ingestion_fred", "02_fred")

KafkaJsonProducer = FINNHUB_PACKAGE.KafkaJsonProducer
build_market_event = FINNHUB_PACKAGE.build_market_event
fetch_quote = FINNHUB_PACKAGE.fetch_quote
build_macro_event = FRED_PACKAGE.build_macro_event
fetch_observations = FRED_PACKAGE.fetch_observations

# 프로젝트 루트 기준으로 local config 파일 위치를 고정한다.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCAL_CONFIG_PATH = PROJECT_ROOT / "local_configs.cfg"
# 한국 표준시는 DST가 없어서 고정 UTC+9 offset으로 단순하게 표현해도 충분하다.
KST = timezone(timedelta(hours=9), name="KST")


def load_local_config():
    """local_configs.cfg를 읽는다."""
    config = configparser.ConfigParser()
    if LOCAL_CONFIG_PATH.exists():
        config.read(LOCAL_CONFIG_PATH, encoding="utf-8")
    return config


def get_config_value(config, name, default=""):
    """설정값을 단순한 규칙으로 읽는다.

    우선순위:
    1. local_configs.cfg 의 [01_ingestion]
    2. 환경변수
    3. 기본값
    """
    if config.has_option("01_ingestion", name):
        return config.get("01_ingestion", name)

    env_value = os.getenv(name, "")
    if env_value:
        return env_value

    return default


def format_timestamp_views(timestamp_ms):
    """하나의 기준 timestamp를 UTC/KST 두 가지 읽기용 문자열로 바꾼다.

    표준은 `timestamp_ms` 자체다.
    즉 저장/처리는 unix epoch milliseconds 하나로 통일하고,
    사람이 읽을 때만 UTC와 KST 문자열을 파생해서 보여준다.

    예:
    - 입력: 1717171717000
    - 출력:
      {
        "utc": "2024-05-31T16:08:37+00:00",
        "kst": "2024-06-01T01:08:37+09:00"
      }
    """
    utc_dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
    kst_dt = utc_dt.astimezone(KST)
    return {
        "utc": utc_dt.isoformat(),
        "kst": kst_dt.isoformat(),
    }


def build_console_message(topic, key, event):
    """사람이 읽기 쉬운 console 출력용 payload를 만든다.

    Kafka에 들어가는 실제 event 자체는 그대로 유지하고,
    console에서는 event_ts_ms / ingest_ts_ms를 UTC + KST 두 형태로 같이 보여준다.

    예:
    {
      "topic": "raw.market.finnhub.tick.v1",
      "key": "AAPL",
      "event": {...},
      "time_view": {
        "event_ts": {"utc": "...", "kst": "..."},
        "ingest_ts": {"utc": "...", "kst": "..."}
      }
    }
    """
    return {
        "topic": topic,
        "key": key,
        "event": event,
        "time_view": {
            "event_ts": format_timestamp_views(event["event_ts_ms"]),
            "ingest_ts": format_timestamp_views(event["ingest_ts_ms"]),
        },
    }


def build_produce_log_message(topic, key, event):
    """실제 Kafka 전송 성공 시 터미널에 남길 간단한 로그를 만든다.

    dry-run 출력은 디버깅용으로 자세히 보여주고,
    실제 produce 성공 로그는 반복 실행해도 읽기 쉽게 요약형으로 남긴다.
    """
    time_view = format_timestamp_views(event["event_ts_ms"])
    payload = event["payload"]

    if "symbol" in payload:
        return {
            "status": "produced",
            "topic": topic,
            "key": key,
            "symbol": payload["symbol"],
            "price": payload["price"],
            "event_ts_utc": time_view["utc"],
            "event_ts_kst": time_view["kst"],
        }

    return {
        "status": "produced",
        "topic": topic,
        "key": key,
        "series_id": payload["series_id"],
        "value": payload["value"],
        "observation_date": payload["observation_date"],
        "event_ts_utc": time_view["utc"],
        "event_ts_kst": time_view["kst"],
    }


def print_or_send(producer, topic, key, event, dry_run):
    """dry-run이면 출력하고, 아니면 Kafka로 전송한다.

    여기서의 출력은 "로그/확인용"이므로 KST를 같이 보여줘도 된다.
    하지만 Kafka event 본문은 항상 timezone-independent 한 기준값
    (`event_ts_ms`, `ingest_ts_ms`)만 유지한다.
    """
    if dry_run:
        print(json.dumps(build_console_message(topic, key, event), ensure_ascii=False))
        return

    producer.send(topic=topic, key=key, value=event)
    print(json.dumps(build_produce_log_message(topic, key, event), ensure_ascii=False))


def run_finnhub_poll(args):
    """Finnhub quote API를 polling 해서 Kafka raw topic으로 적재한다.

    사용 문서:
    - endpoint: GET /api/v1/quote
    - auth: query parameter `token`
    - 사용 필드: `c`(현재가), `t`(unix seconds timestamp)

    시간 표준:
    - 저장/전송 표준: unix epoch milliseconds (`event_ts_ms`, `ingest_ts_ms`)
    - 사람 확인용 출력: UTC + KST 둘 다 표시
    """
    if not args.finnhub_api_key:
        raise ValueError("FINNHUB_API_KEY is required")

    producer = KafkaJsonProducer(bootstrap_servers=args.bootstrap_servers, dry_run=args.dry_run)

    try:
        sent_count = 0

        # count <= 0 이면 무한 반복, 아니면 지정 횟수만 실행한다.
        while args.count <= 0 or sent_count < args.count:
            # 1. Finnhub 에서 quote 조회
            quote = fetch_quote(
                api_key=args.finnhub_api_key,
                symbol=args.symbol,
                timeout_s=args.timeout_s,
            )

            # 2. 외부 응답을 우리 이벤트 형식으로 변환
            event = build_market_event(
                source="finnhub_quote",
                symbol=quote["symbol"],
                price=quote["price"],
                size=quote["size"],
                event_ts_ms=quote["event_ts_ms"],
            )

            # 3. dry-run 출력 또는 Kafka 전송
            print_or_send(
                producer=producer,
                topic=args.topic,
                key=args.symbol,
                event=event,
                dry_run=args.dry_run,
            )

            sent_count += 1
            time.sleep(args.interval_s)
    finally:
        producer.close()


def iter_series(series_csv):
    """쉼표로 이어진 series 문자열을 하나씩 분리한다."""
    for raw in series_csv.split(","):
        series_id = raw.strip()
        if series_id:
            yield series_id


def run_fred_batch(args):
    """FRED에서 핵심 거시지표를 가져와 Kafka raw topic으로 적재한다.

    지금 수집하는 기본 지표 3개는 다음 의미를 가진다.
    - DFF: 연준 정책금리 방향
    - CPIAUCSL: 물가/인플레이션 흐름
    - UNRATE: 고용/실업 흐름

    즉, 시장 가격과 함께 보기 좋은 최소 거시 축 3개만 먼저 가져온다.

    기본 동작은 "series마다 최신 관측값 1개"만 가져오는 것이다.
    과거 값까지 여러 개 보고 싶을 때만 `--limit`를 명시적으로 늘린다.
    """
    if not args.fred_api_key:
        raise ValueError("FRED_API_KEY is required")

    producer = KafkaJsonProducer(bootstrap_servers=args.bootstrap_servers, dry_run=args.dry_run)

    try:
        for series_id in iter_series(args.series):
            rows = fetch_observations(
                api_key=args.fred_api_key,
                series_id=series_id,
                limit=args.limit,
                timeout_s=args.timeout_s,
            )

            for row in rows:
                event = build_macro_event(
                    series_id=row["series_id"],
                    observation_date=row["observation_date"],
                    value=row["value"],
                    release_ts_ms=row["release_ts_ms"],
                    realtime_start=row["realtime_start"],
                    realtime_end=row["realtime_end"],
                )

                print_or_send(
                    producer=producer,
                    topic=args.topic,
                    key=series_id,
                    event=event,
                    dry_run=args.dry_run,
                )
    finally:
        producer.close()


def main():
    """CLI 인자를 읽고 Finnhub 또는 FRED ingestion 실행을 시작한다."""
    parser = argparse.ArgumentParser(description="Finnhub / FRED ingestion")

    # 공통 실행 옵션
    parser.add_argument("--source", choices=["finnhub", "fred"], default="finnhub")
    parser.add_argument("--bootstrap-servers", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--topic", default="")
    parser.add_argument("--timeout-s", type=int, default=10)

    # Finnhub polling 옵션
    parser.add_argument("--symbol", default="AAPL")
    parser.add_argument("--count", type=int, default=0)
    parser.add_argument("--interval-s", type=float, default=2.0)
    parser.add_argument("--finnhub-api-key", default="")

    # FRED batch 옵션
    parser.add_argument("--series", default="DFF,CPIAUCSL,UNRATE")
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--fred-api-key", default="")

    args = parser.parse_args()

    # local config 파일은 "로컬 개발용 기본값"을 넣는 용도다.
    config = load_local_config()

    # CLI 인자를 직접 주지 않았을 때만 config/env 값을 사용한다.
    if not args.bootstrap_servers:
        args.bootstrap_servers = get_config_value(config, "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

    if not args.finnhub_api_key:
        args.finnhub_api_key = get_config_value(config, "FINNHUB_API_KEY", "")

    if not args.fred_api_key:
        args.fred_api_key = get_config_value(config, "FRED_API_KEY", "")

    if not args.topic:
        if args.source == "finnhub":
            args.topic = "raw.market.finnhub.tick.v1"
        else:
            args.topic = "raw.macro.fred.release.v1"

    if args.source == "finnhub":
        run_finnhub_poll(args)
    else:
        run_fred_batch(args)


if __name__ == "__main__":
    main()
