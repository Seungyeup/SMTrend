# Storage Definition

이 문서는 `03_storage` 레이어가 어떤 데이터를 durable storage 로 저장하는지 정리한 문서다.

현재 범위는 아래 3가지다.

1. silver parquet materialization
2. Hive external table 정의
3. Iceberg gold table DDL 정의

---

## 1. silver 저장 대상

현재 실제로 MinIO(S3A) parquet 로 저장하는 데이터는 아래 두 가지다.

| 저장 데이터 | 출처 | 저장 위치 | 의미 |
|---|---|---|---|
| `market_bar_1m` | `curated.market.bar.1m.v1` | `s3a://smtrend-silver/market_bar_1m` | 1분 OHLC/volume/tick_count 시장 bar |
| `macro_release` | `raw.macro.fred.release.v1` | `s3a://smtrend-silver/macro_release` | FRED 관측값 원본 release 이력 |

즉 현재 `03_storage` 는 processing 의 모든 Kafka output 을 다 저장하는 것이 아니라,
**시장 bar 와 macro release 를 durable silver parquet 로 먼저 내리는 단계** 다.

---

## 2. Flink materialization 흐름

실행 순서는 아래와 같다.

1. `01_materialization/01_storage_source_and_sink_tables.sql`
2. `01_materialization/02_materialize_silver.sql`

여기서 정의되는 핵심 Flink table 은 아래와 같다.

| 구분 | Flink 테이블명 | 연결 데이터 | 역할 |
|---|---|---|---|
| Source | `curated_market_bar_1m` | `curated.market.bar.1m.v1` | processing 결과 시장 bar 읽기 |
| Source | `raw_macro_release` | `raw.macro.fred.release.v1` | macro release 원본 읽기 |
| Sink | `silver_market_bar_1m` | `s3a://smtrend-silver/market_bar_1m` | market bar parquet 저장 |
| Sink | `silver_macro_release` | `s3a://smtrend-silver/macro_release` | macro release parquet 저장 |

### 저장 스키마 요약

#### market_bar_1m

- `dt`
- `bucket_1m_utc`
- `symbol`
- `open_price`
- `high_price`
- `low_price`
- `close_price`
- `volume`
- `tick_count`

#### macro_release

- `dt`
- `series_id`
- `observation_date`
- `macro_value`
- `release_ts_utc`
- `realtime_start`
- `realtime_end`

---

## 3. external table 정의

`02_external_tables/01_create_external_tables.sql` 는 silver parquet 를 Trino/Hive 에서 읽기 위한 외부 테이블을 만든다.

| External table | 읽는 저장 위치 |
|---|---|
| `hive.market.market_bar_1m` | `s3a://smtrend-silver/market_bar_1m` |
| `hive.market.macro_release` | `s3a://smtrend-silver/macro_release` |

이 단계의 의미는 parquet 파일 자체를 직접 다루지 않고,
warehouse/query 엔진에서 **테이블처럼 읽을 수 있게 표면을 만든다** 는 데 있다.

---

## 4. gold table DDL 정의

`03_gold_tables/01_build_gold_tables.sql` 는 Iceberg gold table 골격을 만든다.

현재 정의되는 테이블은 아래 네 가지다.

| Iceberg gold table | 의미 |
|---|---|
| `iceberg.market_iceberg.market_bar_1m` | silver market bar 의 Iceberg mirror |
| `iceberg.market_iceberg.macro_release` | silver macro release 의 Iceberg mirror |
| `iceberg.market_iceberg.market_macro_aligned_daily` | daily 정렬된 시장+macro 결합 테이블 |
| `iceberg.market_iceberg.market_macro_correlation_daily` | rolling correlation 결과 저장 테이블 |

중요한 점은, 현재 `03_storage` 는 **gold table 을 정의하는 단계까지** 포함하고,
그 gold table 에 실제 데이터를 채우는 분석/refresh/validation 흐름은 `04_query` 에서 이어진다는 점이다.

---

## 5. runtime config 의미

`04_runtime_configs/` 아래에는 storage runtime 에 필요한 설정이 들어 있다.

- `hadoop/core-site.xml`
  - MinIO S3A endpoint / access key / secret key / path-style 설정
- `hive/hive-site.xml`
  - 로컬 Hive Metastore thrift 바인딩과 Postgres-backed metastore 설정
- `trino/etc/catalog/hive.properties`
  - silver parquet external table 용 Hive catalog 설정
- `trino/etc/catalog/iceberg.properties`
  - Iceberg catalog 설정

즉 `03_storage` 는 SQL 만 있는 폴더가 아니라,
**저장을 실제로 가능하게 하는 runtime config 까지 함께 소유하는 레이어** 다.

---

## 6. 로컬 실행 시 필요한 catalog 서비스

`run_storage_catalog_sql.sh` 가 로컬에서 바로 동작하려면,
아래 두 서비스가 `00_infra/docker-compose.yaml` 에 함께 떠 있어야 한다.

- `trino`
  - `http://localhost:8080/v1/statement` 로 SQL 실행
- `hive-metastore`
  - `thrift://hive-metastore:9083` 로 Hive / Iceberg catalog metadata 제공
- `hive-db`
  - 로컬 Hive Metastore 가 쓰는 Postgres metadata 저장소

즉 로컬 `03_storage` 실행은 아래 두 단계로 나뉜다.

1. Flink 가 silver parquet 생성
   - `bash 00_infra/run_storage_materialization_sql.sh`
2. Trino 가 external table / Iceberg gold DDL 실행
   - `bash 00_infra/run_storage_catalog_sql.sh`

Kafka UI 는 로컬 Trino 와 포트 충돌을 피하기 위해 `8085` 로 옮긴다.

현재 로컬 stack 에서 브라우저로 접속하는 web UI 기준 기본 인증 정보는 아래와 같다.

| 컴포넌트 | URL | 기본 ID/PW |
|---|---|---|
| Kafka UI | `http://localhost:8085` | 로그인 없음 |
| Flink UI | `http://localhost:8081` | 로그인 없음 |
| MinIO Console | `http://localhost:9001` | `minio` / `minio123` |

여기서 중요한 점은,
로컬 Hive Metastore 의 기본 warehouse dir 은 `file:/tmp/hive-warehouse` 같은 local path 를 쓰고,
실제 silver / Iceberg 데이터 경로는 Trino DDL 에서 `s3a://...` 로 따로 지정한다는 점이다.

또한 local metastore metadata 자체는 embedded Derby 가 아니라
`hive-db` Postgres 컨테이너에 저장되므로,
Trino catalog DDL 실행 시 Derby 동시성/응답 문제를 피할 수 있다.

---

## 7. 04_query 와의 연결

`03_storage` 의 역할은 여기서 끝난다.

1. silver parquet 생성
2. external table 정의
3. Iceberg gold table DDL 정의

그 다음 `04_query` 는 아래를 담당한다.

- external table 에서 date partition 목록 확인
- Iceberg mirror/gold incremental refresh
- gold validation query
- correlation analytics query

즉 `03_storage` 는 **저장 표면과 gold 골격을 만드는 단계**,
`04_query` 는 **그 골격에 실제 데이터를 채우고 조회하는 단계** 다.

그 이후 future 단계는 아래처럼 분리된다.

- `05_serving`: query 결과 또는 curated stream 을 serving datasource 로 노출
- `06_visualization`: 그 datasource 를 dashboard / chart 로 시각화

이 구조는 곧
`Trino/Iceberg -> Superset` direct path 와,
`Druid -> Superset` serving path 를 둘 다 허용한다는 뜻이다.

즉 `05_serving` 은 필수보다는,
realtime serving 요구가 있을 때 분리해서 두는 optional 레이어다.
