import json

from poc_ingestion.main import _print_or_send


class StubProducer:
    def __init__(self, *, fail_first_send: bool) -> None:
        self.fail_first_send = fail_first_send
        self.calls: list[tuple[str, str, dict[str, object]]] = []

    def send(self, *, topic: str, key: str, value: dict[str, object]) -> None:
        if self.fail_first_send:
            self.fail_first_send = False
            raise RuntimeError("primary send failed")
        self.calls.append((topic, key, value))


def test_print_or_send_routes_invalid_event_to_dlq_in_dry_run(capsys) -> None:
    producer = StubProducer(fail_first_send=False)
    was_sent = _print_or_send(
        producer=producer,
        topic="raw.market.finnhub.tick.v1",
        key="GOOG",
        event={"bad": "event"},
        dry_run=True,
    )

    assert not was_sent
    stdout_lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert len(stdout_lines) == 1
    dlq_message = json.loads(stdout_lines[0])
    assert dlq_message["topic"] == "dlq.raw.market.finnhub.tick.v1"
    assert dlq_message["event"]["payload"]["failure_stage"] == "produce_event"


def test_print_or_send_routes_send_failure_to_dlq_topic() -> None:
    producer = StubProducer(fail_first_send=True)
    was_sent = _print_or_send(
        producer=producer,
        topic="raw.market.finnhub.tick.v1",
        key="GOOG",
        event={
            "event_id": "evt-1",
            "source": "finnhub_mock",
            "entity_key": "GOOG",
            "event_ts_ms": 1_700_000_000_000,
            "ingest_ts_ms": 1_700_000_000_100,
            "schema_version": "v1",
            "payload": {"symbol": "GOOG", "price": 181.2, "size": 10},
        },
        dry_run=False,
    )

    assert not was_sent
    assert len(producer.calls) == 1
    topic, key, value = producer.calls[0]
    assert topic == "dlq.raw.market.finnhub.tick.v1"
    assert key == "GOOG"
    assert value["payload"]["error_type"] == "RuntimeError"
    assert value["payload"]["failure_stage"] == "produce_event"
