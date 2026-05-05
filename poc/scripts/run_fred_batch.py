from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from types import SimpleNamespace

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from poc_ingestion.main import run_fred_batch


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Run FRED batch ingestion with Python")
    parser.add_argument(
        "--bootstrap-servers",
        default=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "172.30.1.4:9092"),
        help="Kafka bootstrap servers",
    )
    parser.add_argument("--series", default="DFF,CPIAUCSL,UNRATE")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--topic", default="raw.macro.fred.release.v1")
    parser.add_argument("--fred-api-key", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    run_args = SimpleNamespace(
        bootstrap_servers=args.bootstrap_servers,
        series=args.series,
        limit=args.limit,
        topic=args.topic,
        fred_api_key=args.fred_api_key,
        dry_run=args.dry_run,
    )
    run_fred_batch(run_args)


if __name__ == "__main__":
    main()
