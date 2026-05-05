# Stock + Macro Streaming/Batch PoC (Kafka-Centric)

이 문서는 이 프로젝트에서 데이터를 **어떻게 수집하고(Collect), 어떻게 저장하며(Store), 저장 데이터를 어떻게 읽어 실시간/분석으로 보여주는지(Serve/Query)**를 코드 기준으로 설명한다.

## 1) 아키텍처 요약 (실제 코드 기준)

데이터 경로는 아래 순서로 고정되어 있다.

1. `poc_ingestion/main.py`가 시장/매크로 이벤트를 생성해서 Kafka raw topic에 적재
2. Flink SQL(`flink/sql/01~05`)이 raw를 읽어
   - Kafka curated/state/analytics topic으로 실시간 가공 결과를 적재
   - MinIO(S3A) silver parquet로 materialization
3. Trino가 silver(Hive external)를 읽고 Iceberg 테이블(silver mirror + gold)을 생성
4. Druid가 Kafka curated topic(`curated.market.bar.1m.v1`)을 실시간 ingestion
5. Superset이 Trino/Iceberg 또는 Druid를 데이터소스로 조회

현재 저장소 기준으로 **로컬에서 바로 재현되는 범위**는 Kafka/MinIO와 Python ingestion 경로다. Flink/Trino/Druid/Superset 실행 자체는 여전히 외부 쿠버네티스/인프라 경로를 전제로 하지만, 이 저장소 안의 SQL/스크립트/검증 로직은 실제 실행 경로와 맞도록 정리되어 있다.

## 2) 사전 준비

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -q
```

`.env`에는 최소 `FINNHUB_API_KEY`, `FRED_API_KEY`를 설정한다.

## 3) 인프라 기동

로컬에서 수집/저장 계층만 빠르게 재현하려면 아래 compose를 먼저 올린다. 이 compose는 **Kafka + MinIO(bucket bootstrap 포함)** 까지만 책임지고, Flink/Trino/Druid/Superset은 기존 외부/쿠버네티스 경로를 그대로 사용한다.

```bash
docker compose up -d zookeeper kafka minio minio-init
```

```bash
bash scripts/bootstrap_kafka_topics.sh
```

Superset에서 실시간으로 계속 확인 가능한 전체 활성화(인프라 + Flink + Druid + 연속 producer)는 아래 한 번으로 실행할 수 있다.

```bash
bash scripts/activate_superset_monitoring.sh
```

위 스크립트는 로컬 수집 파이프라인과 Kafka/Druid bootstrap을 기동하고, 외부 Superset 가용성을 확인한다.

주요 URL:

- Kafka(local compose): `localhost:9092`
- MinIO(local compose): `http://localhost:9000`
- MinIO Console(local compose): `http://localhost:9001`
- Flink UI: (Kubernetes endpoint)
- MinIO: (Kubernetes/infra endpoint)
- Trino: (Kubernetes endpoint)

## 4) 수집(Collect): 어떤 데이터를 어떻게 넣는가

### 4.1 이벤트 포맷

`poc_ingestion/schemas.py`의 `EventEnvelope` 구조를 사용한다.

- 공통: `event_id`, `source`, `entity_key`, `event_ts_ms`, `ingest_ts_ms`, `schema_version`, `payload`
- Market payload: `symbol`, `price`, `size`
- Macro payload: `series_id`, `observation_date`, `value`, `release_ts_ms`, `realtime_start`, `realtime_end`

이벤트 생성 시 `build_market_trade_event`, `build_macro_release_event`가 필수 필드와 기본 타입/값을 검증한다. 검증 실패 또는 Kafka publish 실패가 발생하면 동일한 envelope 형식의 DLQ 이벤트를 `dlq.raw.*` topic으로 보낸다.

### 4.2 수집 실행

```bash
bash scripts/run_market_mock.sh
bash scripts/run_finnhub_poll.sh
bash scripts/run_fred_batch.sh
```

실제 수집 로직:

- 진입: `poc_ingestion/main.py`
- 외부 API: `poc_ingestion/sources.py`
  - Finnhub quote API
  - FRED observations API
- Kafka 전송: `poc_ingestion/kafka_client.py` (`acks=all`)
- 실패 처리: `poc_ingestion/main.py`가 validation/publish 예외를 잡아 `dlq.raw.market.finnhub.tick.v1`, `dlq.raw.macro.fred.release.v1`로 우회

### 4.3 수집 확인

```bash
docker run --rm confluentinc/cp-kafka:7.6.1 kafka-topics --bootstrap-server 172.30.1.4:9092 --list
docker run --rm confluentinc/cp-kafka:7.6.1 kafka-console-consumer --bootstrap-server 172.30.1.4:9092 --topic raw.market.finnhub.tick.v1 --from-beginning --max-messages 3
docker run --rm confluentinc/cp-kafka:7.6.1 kafka-console-consumer --bootstrap-server 172.30.1.4:9092 --topic raw.macro.fred.release.v1 --from-beginning --max-messages 3
```

## 5) 처리(Process): Flink가 실시간으로 무엇을 만드는가

### 5.1 테이블 정의 (`flink/sql/01_tables.sql`)

- Source: `raw_market_tick`, `raw_macro_release` (Kafka)
- 실시간 sink:
  - `curated_market_bar_1m` (Kafka)
  - `macro_latest_state` (upsert-kafka)
  - `analytics_market_macro_1m` (upsert-kafka)
- 파일 sink:
  - `silver_market_bar_1m` (MinIO S3A parquet)
  - `silver_macro_release` (MinIO S3A parquet)

### 5.2 변환 SQL

- `flink/sql/02_market_bar_1m.sql`: 1분 event-time TUMBLE window 기준으로 `symbol`별 OHLCV + `tick_count` 생성
  - `high_price`, `low_price`, `volume`, `tick_count`는 window aggregate로 계산
  - `open_price`, `close_price`는 같은 1분 window 안에서 `event_time` 기준 첫 tick / 마지막 tick을 `ROW_NUMBER()`로 선택
  - 동률 방지를 위해 `event_id`를 tie-breaker로 사용
- `flink/sql/03_macro_state.sql`: macro latest state upsert
- `flink/sql/04_enriched_analytics.sql`: 1분 바 + macro latest 조인, `macro_age_minutes` 계산
- `flink/sql/05_silver_materialization.sql`: checkpoint(`30s`) + MinIO silver 적재

### 5.3 제출/확인

```bash
export FLINK_K8S_NAMESPACE=default
export FLINK_SQL_CLIENT_POD=<flink-sql-client-pod>
bash scripts/submit_flink_sql.sh

# Flink SQL 적용 후 Kafka 산출물 확인
docker run --rm confluentinc/cp-kafka:7.6.1 kafka-console-consumer --bootstrap-server 172.30.1.4:9092 --topic curated.market.bar.1m.v1 --from-beginning --max-messages 3
```

## 6) 저장(Store) + 분석(Query): Hive external + Iceberg

### 6.1 현재 저장 계층

- Silver 원본: MinIO parquet (`s3a://smtrend-silver/*`) — Flink가 생성
- Trino/Hive external: silver parquet를 읽기용으로 매핑
- Trino/Iceberg: silver mirror + gold analytics를 Iceberg 테이블로 생성

### 6.2 Iceberg 카탈로그

`infra/trino/etc/catalog/iceberg.properties` 사용:

- `connector.name=iceberg`
- `iceberg.catalog.type=hive_metastore`
- `hive.metastore.uri=thrift://172.30.1.30:9083`

카탈로그 파일 적용 후 Trino(Kubernetes)에서 SQL 실행:

```bash
python scripts/run_trino_sql_http.py --sql-file trino/sql/03_correlation_queries.sql
```

### 6.3 SQL 실행 순서

```bash
# silver parquet(MinIO) 읽기용 external table
python scripts/run_trino_sql_http.py --sql-file trino/sql/01_create_external_tables.sql

# Iceberg schema/table bootstrap
python scripts/run_trino_sql_http.py --sql-file trino/sql/02_build_gold_tables.sql

# external table row count 검증
python scripts/run_trino_sql_http.py --sql-file trino/sql/04_validate_external_tables.sql --require-rows --expect-first-value-ge 1 --print-rows

# changed partition 기준 incremental refresh + optimize
python scripts/refresh_gold_incremental.py

# 최종 조회
python scripts/run_trino_sql_http.py --sql-file trino/sql/03_correlation_queries.sql
```

### 6.4 저장/조회 확인

```bash
python scripts/run_trino_sql_http.py --sql-file trino/sql/05_validate_gold_tables.sql --require-rows --expect-first-value-ge 1 --print-rows
python scripts/run_trino_sql_http.py --sql-file trino/sql/03_correlation_queries.sql
```

시간 컬럼 해석은 UTC 기준으로 맞춰 사용한다(`bucket_1m_utc`, `release_ts_utc`).

## 7) 실시간 서빙(Serve): Druid + Superset

Druid는 `druid/specs/market_bar_1m_kafka.json`으로 `curated.market.bar.1m.v1`를 실시간 ingest한다.

```bash
export DRUID_API_URL=http://<druid-k8s-endpoint>
bash scripts/request_druid_ingestion.sh
bash scripts/apply_druid_retention.sh
curl -sS ${DRUID_API_URL}/druid/indexer/v1/supervisor/market_bar_1m/status
curl -sS ${DRUID_API_URL}/druid/indexer/v1/tasks
```

데이터 보관 주기는 `.env`로 조정한다.

- Kafka topic 보관: `RAW_MARKET_RETENTION_DAYS`, `CURATED_MARKET_RETENTION_DAYS` 등 (적용: `bash scripts/bootstrap_kafka_topics.sh`)
- Druid datasource 보관: `DRUID_RETENTION_DAYS` (적용: `bash scripts/apply_druid_retention.sh`)

실시간 가시화는 아래 두 경로를 사용한다.

1. Druid (Kafka→Druid 실시간 ingestion 결과)
2. Superset (Druid 또는 Trino/Iceberg 쿼리 결과)

현재 Druid spec은 `rollup=false` 기준으로 1분 bar row를 그대로 유지하고, 집계 metric은 `volume_sum`, `tick_count_sum`만 정의한다. 가격은 합계 metric으로 다루지 않고 raw `close_price`를 유지한 뒤, 조회 시 `LATEST_BY(close_price, "__time")` 같은 latest-value query로 해석하는 것이 기준이다.

Superset bootstrap(`scripts/bootstrap_superset_content.py`)은 Trino의 `market_bar_1m` dataset을 기준으로 table chart에 `open/high/low/close/volume/tick_count`를 노출하고, time series chart는 minute bucket별 `close_price`를 그대로 시각화하도록 맞춘다.

URL:

- Druid API: (Kubernetes endpoint, `DRUID_API_URL`)
- Superset: `http://172.30.1.40:8088`
- Airflow: (Kubernetes endpoint)

Superset은 외부 인프라(172.30.1.40:8088)에서 운영한다.
