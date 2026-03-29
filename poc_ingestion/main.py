from __future__ import annotations

import argparse
import json
import os
import time
from typing import Iterable

from dotenv import load_dotenv

from poc_ingestion.kafka_client import EventProducer
from poc_ingestion.schemas import build_macro_release_event, build_market_trade_event, utc_now_ms
from poc_ingestion.sources import fetch_finnhub_quote, fetch_fred_observations, generate_mock_trade


def _print_or_send(
    *,
    producer: EventProducer,
    topic: str,
    key: str,
    event: dict[str, object],
    dry_run: bool,
) -> None:
    if dry_run:
        print(json.dumps({"topic": topic, "key": key, "event": event}, ensure_ascii=False))
    else:
        producer.send(topic=topic, key=key, value=event)


def run_market_mock(args: argparse.Namespace) -> None:
    producer = EventProducer(bootstrap_servers=args.bootstrap_servers, dry_run=args.dry_run)
    price = args.start_price
    try:
        for _ in range(args.count):
            price, size = generate_mock_trade(current_price=price)
            event = build_market_trade_event(
                source="finnhub_mock",
                symbol=args.symbol,
                price=price,
                size=size,
                event_ts_ms=utc_now_ms(),
            )
            _print_or_send(
                producer=producer,
                topic=args.topic,
                key=args.symbol,
                event=event,
                dry_run=args.dry_run,
            )
            time.sleep(args.interval_s)
    finally:
        producer.close()


def run_market_finnhub_poll(args: argparse.Namespace) -> None:
    api_key = args.finnhub_api_key or os.getenv("FINNHUB_API_KEY")
    if not api_key:
        raise ValueError("FINNHUB_API_KEY is required for market-finnhub-poll mode")

    producer = EventProducer(bootstrap_servers=args.bootstrap_servers, dry_run=args.dry_run)
    try:
        for _ in range(args.count):
            quote = fetch_finnhub_quote(api_key=api_key, symbol=args.symbol)
            event = build_market_trade_event(
                source="finnhub_quote",
                symbol=quote["symbol"],
                price=quote["price"],
                size=quote["size"],
                event_ts_ms=quote["event_ts_ms"],
            )
            _print_or_send(
                producer=producer,
                topic=args.topic,
                key=args.symbol,
                event=event,
                dry_run=args.dry_run,
            )
            time.sleep(args.interval_s)
    finally:
        producer.close()


def _series_iter(series_csv: str) -> Iterable[str]:
    for raw in series_csv.split(","):
        series = raw.strip()
        if series:
            yield series


def run_fred_batch(args: argparse.Namespace) -> None:
    api_key = args.fred_api_key or os.getenv("FRED_API_KEY")
    if not api_key:
        raise ValueError("FRED_API_KEY is required for fred-batch mode")

    producer = EventProducer(bootstrap_servers=args.bootstrap_servers, dry_run=args.dry_run)
    try:
        for series_id in _series_iter(args.series):
            rows = fetch_fred_observations(api_key=api_key, series_id=series_id, limit=args.limit)
            for row in rows:
                event = build_macro_release_event(
                    source="fred_batch",
                    series_id=row["series_id"],
                    observation_date=row["observation_date"],
                    value=row["value"],
                    release_ts_ms=row["release_ts_ms"],
                    realtime_start=row["realtime_start"],
                    realtime_end=row["realtime_end"],
                )
                _print_or_send(
                    producer=producer,
                    topic=args.topic,
                    key=series_id,
                    event=event,
                    dry_run=args.dry_run,
                )
    finally:
        producer.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Stock + macro ingestion PoC")
    parser.add_argument(
        "--bootstrap-servers",
        default=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:19092"),
        help="Kafka bootstrap servers",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    market_mock = sub.add_parser("market-mock", help="Generate mock market ticks")
    market_mock.add_argument("--symbol", default="GOOG")
    market_mock.add_argument("--topic", default="raw.market.finnhub.tick.v1")
    market_mock.add_argument("--count", type=int, default=20)
    market_mock.add_argument("--interval-s", type=float, default=1.0)
    market_mock.add_argument("--start-price", type=float, default=180.0)
    market_mock.add_argument("--dry-run", action="store_true")
    market_mock.set_defaults(func=run_market_mock)

    market_finnhub = sub.add_parser("market-finnhub-poll", help="Poll Finnhub quote endpoint")
    market_finnhub.add_argument("--symbol", default="GOOG")
    market_finnhub.add_argument("--topic", default="raw.market.finnhub.tick.v1")
    market_finnhub.add_argument("--count", type=int, default=20)
    market_finnhub.add_argument("--interval-s", type=float, default=2.0)
    market_finnhub.add_argument("--finnhub-api-key", default="")
    market_finnhub.add_argument("--dry-run", action="store_true")
    market_finnhub.set_defaults(func=run_market_finnhub_poll)

    fred_batch = sub.add_parser("fred-batch", help="Fetch FRED observations in batch")
    fred_batch.add_argument("--series", default="DFF,CPIAUCSL,UNRATE")
    fred_batch.add_argument("--limit", type=int, default=20)
    fred_batch.add_argument("--topic", default="raw.macro.fred.release.v1")
    fred_batch.add_argument("--fred-api-key", default="")
    fred_batch.add_argument("--dry-run", action="store_true")
    fred_batch.set_defaults(func=run_fred_batch)

    return parser


def main() -> None:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
