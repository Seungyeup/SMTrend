# 04_query

이 레이어는 `03_storage` 가 만든 Hive external / Iceberg gold table 정의를 실제 조회 가능한 데이터 상태로 채우고 검증하는 역할을 한다.

현재 범위는 아래 3가지다.

1. `01_gold_refresh/`
   - silver external table 을 읽어 Iceberg gold table 을 incremental refresh
2. `02_analytics_queries/`
   - gold table 에 대해 최종 분석 query 실행
3. `03_validation/`
   - external / gold table row count 와 기본 조회 검증

## 현재 단계에서 하는 일

- `hive.market.market_bar_1m`, `hive.market.macro_release` 를 읽는다.
- `iceberg.market_iceberg.market_bar_1m`, `macro_release` mirror 를 채운다.
- `market_macro_aligned_daily`, `market_macro_correlation_daily` 를 갱신한다.
- Trino query 로 external / gold 상태를 검증한다.

즉 `04_query` 는 **저장된 데이터를 다시 읽어 gold 를 채우고, 실제 분석/검증 가능 상태로 만드는 단계** 다.

## 실행 순서

1. `01_gold_refresh/01_refresh_gold_incremental.py`
2. `03_validation/01_validate_external_tables.sql`
3. `03_validation/02_validate_gold_tables.sql`
4. `02_analytics_queries/01_market_macro_correlation.sql`

로컬 실행 명령은 아래 세 개다.

- gold refresh: `bash 00_infra/run_query_refresh.sh`
- validation: `bash 00_infra/run_query_validation_sql.sh`
- analytics query: `bash 00_infra/run_query_analytics_sql.sh`
