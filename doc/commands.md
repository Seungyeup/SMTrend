## 00_infra
```bash
# 로컬 인프라 실행
docker compose -f 00_infra/docker-compose.yaml up -d

# Kafka topic bootstrap
bash 00_infra/bootstrap_kafka_topics.sh

# storage bucket 포함 로컬 인프라 실행 확인
docker compose -f 00_infra/docker-compose.yaml config >/dev/null

# 접속 포트
# - Kafka UI: http://localhost:8085
# - Flink UI: http://localhost:8081
# - MinIO API: http://localhost:9000
# - MinIO Console: http://localhost:9001
# - Trino: http://localhost:8080
# - Hive Metastore thrift: localhost:9083

# web UI 기본 인증 정보
# - Kafka UI: 로그인 없음
# - Flink UI: 로그인 없음
# - MinIO Console: ID `minio` / PW `minio123`
```

## 01_ingestion
### 1. finnhub 실시간 티커 수집 
```bash
# TEST
PYTHONPATH=01_ingestion pytest -q 01_ingestion/tests

# KAFKA 토픽 생성
docker exec smtrend-kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --create \
  --if-not-exists \
  --topic raw.market.finnhub.tick.v1 \
  --partitions 1 \
  --replication-factor 1

# 실행
## DRY RUN
python3 01_ingestion/main.py --dry-run --symbol AAPL --count 1
## KAFKA 전송까지
python3 01_ingestion/main.py --symbol AAPL --count 1
## 계속 수집
python3 01_ingestion/main.py --symbol AAPL
```

### 2. fred 주기 데이터 수집 
```bash
# 실행
## DRY RUN
python3 01_ingestion/main.py --source fred --dry-run --series DFF,CPIAUCSL,UNRATE --limit 1
## KAFKA 전송까지
python3 01_ingestion/main.py --source fred --series DFF,CPIAUCSL,UNRATE --limit 1
## 과거 관측값까지 여러 개 조회
python3 01_ingestion/main.py --source fred --series DFF,CPIAUCSL,UNRATE --limit 3
```

## 02_processing
```bash
# Kafka topic bootstrap
bash 00_infra/bootstrap_kafka_topics.sh

# processing SQL 실행
bash 00_infra/run_processing_sql.sh
```

## 03_storage
```bash
# silver parquet materialization 실행
bash 00_infra/run_storage_materialization_sql.sh

# Trino + Hive Metastore 가 올라온 뒤 external / iceberg table DDL 실행
bash 00_infra/run_storage_catalog_sql.sh
```

## 04_query
```bash
# Iceberg gold incremental refresh
bash 00_infra/run_query_refresh.sh

# external / gold validation query 실행
bash 00_infra/run_query_validation_sql.sh

# 최종 correlation query 실행
bash 00_infra/run_query_analytics_sql.sh

# query-layer 로직 테스트
pytest -q 04_query/tests
```

## 05_serving
```bash
# local Druid overlay 실행
bash 00_infra/run_serving_local_up.sh

# Druid supervisor 생성
bash 00_infra/run_serving_ingestion.sh

# Druid retention rule 적용
bash 00_infra/run_serving_retention.sh

# Druid supervisor status 확인
bash 00_infra/run_serving_status.sh

# local Druid overlay 종료
bash 00_infra/run_serving_local_down.sh

# 주의: main compose 에 Druid 가 상시 포함되는 것은 아님
# 필요할 때만 overlay 로 켜는 구조
# local Druid router: http://localhost:8888
# local Druid broker SQL/query: http://localhost:8082
```

## 06_visualization
```bash
# local Superset 실행
bash 00_infra/run_visualization_local_up.sh

# Trino datasource dashboard bootstrap
# - prerequisite: hive.market.market_bar_1m 이 Trino 에서 queryable 해야 함
bash 00_infra/run_visualization_bootstrap_trino.sh

# Druid datasource dashboard bootstrap
# - prerequisite: Druid datasource market_bar_1m 이 queryable 해야 함
bash 00_infra/run_visualization_bootstrap_druid.sh

# local Superset 종료
bash 00_infra/run_visualization_local_down.sh

# Superset UI
# - URL: http://localhost:8088
# - ID/PW: admin / admin
```
