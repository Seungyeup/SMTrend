# 03_storage

이 레이어는 `02_processing` 이 만든 Kafka output 과 raw macro topic 을 durable storage 로 내리는 역할을 한다.

현재 범위는 아래 3가지다.

1. `01_materialization/`
   - Flink SQL 로 MinIO(S3A) silver parquet 적재
2. `02_external_tables/`
   - silver parquet 를 읽는 Hive external table 정의
3. `03_gold_tables/`
   - Iceberg gold table DDL 정의

## 현재 저장 대상

- `market_bar_1m`
  - 출처: `curated.market.bar.1m.v1`
  - 저장 형태: `s3a://smtrend-silver/market_bar_1m` parquet
- `macro_release`
  - 출처: `raw.macro.fred.release.v1`
  - 저장 형태: `s3a://smtrend-silver/macro_release` parquet

## 현재 단계에서 하는 일과 하지 않는 일

- 하는 일
  - silver parquet sink 정의
  - silver parquet materialization
  - Hive external table 정의
  - Iceberg gold table DDL 정의

- 아직 하지 않는 일
  - gold analytics query 실행
  - gold validation query 실행
  - dashboard / serving 구성

즉 `03_storage` 는 **저장 가능한 형태로 내리고, warehouse 에서 읽을 테이블 골격을 만드는 단계** 까지를 담당한다.

## 실행 순서

1. `01_materialization/01_storage_source_and_sink_tables.sql`
2. `01_materialization/02_materialize_silver.sql`
3. `02_external_tables/01_create_external_tables.sql`
4. `03_gold_tables/01_build_gold_tables.sql`

로컬 실행 명령은 아래 두 개로 나뉜다.

- Flink silver materialization: `bash 00_infra/run_storage_materialization_sql.sh`
- Trino external/gold DDL: `bash 00_infra/run_storage_catalog_sql.sh`

로컬에서 catalog 단계까지 실제로 실행하려면 `00_infra/docker-compose.yaml` 이 아래 서비스까지 함께 올려야 한다.

- `minio`
- `hive-db`
- `hive-metastore`
- `trino`

즉 local `03_storage` 는
**MinIO 에 silver parquet 를 만든 뒤,
로컬 Trino + Postgres-backed Hive Metastore 가 그 parquet 위에 external / Iceberg table 을 세우는 구조** 다.

브라우저로 보는 web UI 인증 정보는 아래와 같다.

- Kafka UI: `http://localhost:8085` / 로그인 없음
- Flink UI: `http://localhost:8081` / 로그인 없음
- MinIO Console: `http://localhost:9001` / `minio` / `minio123`
