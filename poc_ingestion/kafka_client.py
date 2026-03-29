from __future__ import annotations

import json
from typing import Any

from kafka import KafkaProducer


class EventProducer:
    def __init__(self, *, bootstrap_servers: str, dry_run: bool) -> None:
        self.dry_run = dry_run
        self._producer: KafkaProducer | None = None
        if not dry_run:
            self._producer = KafkaProducer(
                bootstrap_servers=bootstrap_servers,
                value_serializer=lambda value: json.dumps(value).encode("utf-8"),
                key_serializer=lambda key: key.encode("utf-8"),
                acks="all",
            )

    def send(self, *, topic: str, key: str, value: dict[str, Any]) -> None:
        if self.dry_run:
            return
        if self._producer is None:
            raise RuntimeError("Kafka producer is not initialized")
        self._producer.send(topic, key=key, value=value)
        self._producer.flush(timeout=5)

    def close(self) -> None:
        if self._producer is not None:
            self._producer.close(timeout=5)
