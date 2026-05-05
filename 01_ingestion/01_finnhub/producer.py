"""Kafka 전송 전용 래퍼.

지금은 로컬 개발과 학습이 목적이므로,
가능하면 Python Kafka client를 쓰고,
그게 없으면 로컬 Kafka 컨테이너 안의 CLI producer로 보낸다.
"""

import json
import subprocess


class KafkaJsonProducer:
    def __init__(self, bootstrap_servers, dry_run):
        """JSON 이벤트를 Kafka로 보내는 producer를 준비한다."""
        self.dry_run = dry_run
        self._producer = None
        self._mode = "dry-run"
        self._bootstrap_servers = bootstrap_servers

        if not dry_run:
            try:
                from confluent_kafka import Producer

                self._producer = Producer(
                    {
                        "bootstrap.servers": bootstrap_servers,
                        "acks": "all",
                    }
                )
                self._mode = "confluent-kafka"
            except ModuleNotFoundError:
                # Python 패키지가 없으면 로컬 Kafka 컨테이너의 CLI를 사용한다.
                self._mode = "docker-cli"

    def send(self, topic, key, value):
        """Kafka topic으로 이벤트를 전송한다."""
        if self.dry_run:
            return

        if self._mode == "confluent-kafka":
            if self._producer is None:
                raise RuntimeError("Kafka producer is not initialized")

            self._producer.produce(
                topic,
                key=key.encode("utf-8"),
                value=json.dumps(value).encode("utf-8"),
            )
            self._producer.poll(0)
            self._producer.flush(5)
            return

        if self._mode == "docker-cli":
            payload = f"{key}\t{json.dumps(value, ensure_ascii=False)}\n"
            result = subprocess.run(
                [
                    "docker",
                    "exec",
                    "-i",
                    "smtrend-kafka",
                    "/opt/kafka/bin/kafka-console-producer.sh",
                    "--bootstrap-server",
                    "localhost:9092",
                    "--topic",
                    topic,
                    "--property",
                    "parse.key=true",
                    "--property",
                    "key.separator=\t",
                ],
                input=payload,
                text=True,
                capture_output=True,
                check=False,
            )
            if result.returncode != 0:
                stderr = result.stderr.strip()
                raise RuntimeError(f"Kafka docker CLI produce failed: {stderr}")
            return

        if self._producer is None and self._mode != "docker-cli":
            raise RuntimeError("Kafka producer is not initialized")
        raise RuntimeError("Kafka producer backend is not configured")

    def close(self):
        """남아 있는 메시지를 마무리한다."""
        if self._mode == "confluent-kafka" and self._producer is not None:
            self._producer.flush(5)
