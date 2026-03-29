# Stock + Macro Streaming/Batch PoC (Kafka-Centric)

이 문서는 이 프로젝트에서 데이터를 **어떻게 수집하고(Collect), 어떻게 저장하며(Store), 저장 데이터를 어떻게 읽어 실시간/분석으로 보여주는지(Serve/Query)**를 코드 기준으로 설명한다.

## 1) 아키텍처 요약 (실제 코드 기준)

데이터 경로는 아래 순서로 고정되어 있다.

1. `poc_ingestion/main.py`가 시장/매크로 이벤트를 생성해서 Kafka raw topic에 적재
2. Flink SQL(`flink/sql/01~05`)이 raw를 읽어
   - Kafka curated/state/analytics topic으로 실시간 가공 결과를 적재
   - HDFS silver parquet로 materialization
3. Trino가 silver(Hive external)를 읽고 Iceberg 테이블(silver mirror + gold)을 생성
4. Druid가 Kafka curated topic(`curated.market.bar.1m.v1`)을 실시간 ingestion
5. Superset이 Trino/Iceberg 또는 Druid를 데이터소스로 조회

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

```bash
docker compose --profile core --profile storage --profile compute --profile query up -d
bash scripts/fetch_flink_connectors.sh
bash scripts/bootstrap_kafka_topics.sh
```

확인:

```bash
docker compose ps
```

주요 URL:

- Kafka UI: `http://localhost:8091`
- Flink UI: `http://localhost:8082`
- NameNode UI: `http://localhost:9870`
- Trino: `http://localhost:8081`

## 4) 수집(Collect): 어떤 데이터를 어떻게 넣는가

### 4.1 이벤트 포맷

`poc_ingestion/schemas.py`의 `EventEnvelope` 구조를 사용한다.

- 공통: `event_id`, `source`, `entity_key`, `event_ts_ms`, `ingest_ts_ms`, `schema_version`, `payload`
- Market payload: `symbol`, `price`, `size`
- Macro payload: `series_id`, `observation_date`, `value`, `release_ts_ms`, `realtime_start`, `realtime_end`

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

### 4.3 수집 확인

```bash
docker compose exec -T kafka kafka-topics --bootstrap-server kafka:9092 --list
docker compose exec -T kafka kafka-console-consumer --bootstrap-server kafka:9092 --topic raw.market.finnhub.tick.v1 --from-beginning --max-messages 3
docker compose exec -T kafka kafka-console-consumer --bootstrap-server kafka:9092 --topic raw.macro.fred.release.v1 --from-beginning --max-messages 3
```

## 5) 처리(Process): Flink가 실시간으로 무엇을 만드는가

### 5.1 테이블 정의 (`flink/sql/01_tables.sql`)

- Source: `raw_market_tick`, `raw_macro_release` (Kafka)
- 실시간 sink:
  - `curated_market_bar_1m` (Kafka)
  - `macro_latest_state` (upsert-kafka)
  - `analytics_market_macro_1m` (upsert-kafka)
- 파일 sink:
  - `hdfs_market_bar_1m` (filesystem/parquet)
  - `hdfs_macro_release` (filesystem/parquet)

### 5.2 변환 SQL

- `flink/sql/02_market_bar_1m.sql`: 1분 TUMBLE 윈도우 OHLCV + tick_count 생성
- `flink/sql/03_macro_state.sql`: macro latest state upsert
- `flink/sql/04_enriched_analytics.sql`: 1분 바 + macro latest 조인, `macro_age_minutes` 계산
- `flink/sql/05_hdfs_materialization.sql`: checkpoint(`30s`) + HDFS silver 적재

### 5.3 제출/확인

```bash
bash scripts/submit_flink_sql.sh
curl -sS http://localhost:8082/jobs/overview
docker compose exec -T kafka kafka-console-consumer --bootstrap-server kafka:9092 --topic curated.market.bar.1m.v1 --from-beginning --max-messages 3
docker compose exec -T namenode hdfs dfs -ls -R /data/silver
```

## 6) 저장(Store) + 분석(Query): Hive external + Iceberg

### 6.1 현재 저장 계층

- Silver 원본: HDFS parquet (`/data/silver/*`) — Flink가 생성
- Trino/Hive external: silver parquet를 읽기용으로 매핑
- Trino/Iceberg: silver mirror + gold analytics를 Iceberg 테이블로 생성

### 6.2 Iceberg 카탈로그

`infra/trino/etc/catalog/iceberg.properties` 사용:

- `connector.name=iceberg`
- `iceberg.catalog.type=hive_metastore`
- `hive.metastore.uri=thrift://hive-metastore:9083`

카탈로그 파일 추가 후 Trino 재시작:

```bash
docker compose restart trino
docker compose exec -T trino trino --execute "SHOW CATALOGS"
```

### 6.3 SQL 실행 순서

```bash
# silver parquet(HDFS) 읽기용 external table
docker compose exec -T trino trino --server http://localhost:8080 --file /opt/trino/sql/01_create_external_tables.sql

# Iceberg schema/silver mirror/gold 생성
docker compose exec -T namenode hdfs dfs -mkdir -p /data/iceberg/market_iceberg
docker compose exec -T namenode hdfs dfs -chmod -R 777 /data/iceberg
docker compose exec -T trino trino --server http://localhost:8080 --file /opt/trino/sql/02_build_gold_tables.sql

# 최종 조회
docker compose exec -T trino trino --server http://localhost:8080 --file /opt/trino/sql/03_correlation_queries.sql
```

### 6.4 저장/조회 확인

```bash
docker compose exec -T trino trino --execute "SELECT count(*) FROM hive.market.market_bar_1m; SELECT count(*) FROM hive.market.macro_release;"
docker compose exec -T trino trino --execute "SELECT count(*) FROM iceberg.market_iceberg.market_bar_1m; SELECT count(*) FROM iceberg.market_iceberg.macro_release;"
docker compose exec -T trino trino --execute "SELECT count(*) FROM iceberg.market_iceberg.market_macro_aligned_daily; SELECT count(*) FROM iceberg.market_iceberg.market_macro_correlation_daily;"
```

시간 컬럼 해석은 UTC 기준으로 맞춰 사용한다(`bucket_1m_utc`, `release_ts_utc`).

## 7) 실시간 서빙(Serve): Druid + Superset

Druid는 `druid/specs/market_bar_1m_kafka.json`으로 `curated.market.bar.1m.v1`를 실시간 ingest한다.

```bash
docker compose --profile serving --profile bi --profile orchestration up -d
bash scripts/request_druid_ingestion.sh
curl -sS http://localhost:8083/druid/indexer/v1/supervisor/market_bar_1m/status
curl -sS http://localhost:8083/druid/indexer/v1/tasks
```

실시간 가시화는 아래 두 경로를 사용한다.

1. Druid (Kafka→Druid 실시간 ingestion 결과)
2. Superset (Druid 또는 Trino/Iceberg 쿼리 결과)

URL:

- Druid API: `http://localhost:8083`
- Superset: `http://localhost:8088` (admin/admin)
- Airflow: `http://localhost:8090` (admin/admin)
