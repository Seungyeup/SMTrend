# Query Definition

이 문서는 `04_query` 레이어가 `03_storage` 에서 정의된 external / gold table 을 실제 조회 가능한 분석 상태로 어떻게 채우고 검증하는지 정리한 문서다.

현재 범위는 아래 3가지다.

1. Iceberg gold incremental refresh
2. correlation analytics query
3. external / gold validation query

---

## 1. 입력과 출력

`04_query` 의 입력은 `03_storage` 가 만든 아래 테이블들이다.

| 구분 | 테이블 | 의미 |
|---|---|---|
| External | `hive.market.market_bar_1m` | MinIO silver market bar 읽기 표면 |
| External | `hive.market.macro_release` | MinIO silver macro release 읽기 표면 |
| Gold | `iceberg.market_iceberg.*` | Iceberg gold 대상 테이블 |

즉 `04_query` 는 새로운 raw source 를 읽지 않고,
**이미 저장된 silver/external 데이터를 읽어 gold 를 채우고 분석하는 단계** 다.

---

## 2. gold refresh 로직

`04_query/01_gold_refresh/01_refresh_gold_incremental.py` 는 아래 순서로 동작한다.

1. external table 에서 현재 존재하는 `dt` 목록을 읽는다.
2. 해당 `dt` 파티션만 Iceberg mirror table 에서 `DELETE` 한다.
3. external table 내용을 Iceberg mirror (`market_bar_1m`, `macro_release`) 로 다시 `INSERT` 한다.
4. 바뀐 최소 `dt` 기준으로 `market_macro_aligned_daily` tail 을 다시 만든다.
5. 같은 tail 기준으로 `market_macro_correlation_daily` 를 다시 만든다.
6. 각 단계 뒤 `ALTER TABLE ... EXECUTE optimize` 를 수행한다.

즉 전체 full rebuild 가 아니라,
**바뀐 날짜 파티션과 그 이후 tail 만 다시 계산하는 incremental refresh** 다.

---

## 3. analytics 의미

현재 최종 query 대상은 `market_macro_correlation_daily` 다.

이 테이블은 아래 의미를 가진다.

| 테이블 | 의미 |
|---|---|
| `market_macro_aligned_daily` | 일 단위로 정렬된 시장 close/volume/tick_count + macro value 결합 |
| `market_macro_correlation_daily` | 종목별 30일 rolling correlation 결과 |

즉 `04_query` 의 현재 목적은
**시장 일별 종가 흐름과 DFF macro 값이 최근 30일 구간에서 얼마나 같이 움직였는가** 를 보는 최소 분석 레이어다.

---

## 4. validation query 의미

현재 validation 은 두 단계다.

1. `03_validation/01_validate_external_tables.sql`
   - external table row count 확인
2. `03_validation/02_validate_gold_tables.sql`
   - gold table row count 확인

즉 local 실행에서 가장 먼저 보는 것은
"external 이 실제로 읽히는가" 와
"gold refresh 결과가 실제 row 로 쌓였는가" 다.

---

## 5. 실행 명령

```bash
# gold refresh
bash 00_infra/run_query_refresh.sh

# external / gold validation
bash 00_infra/run_query_validation_sql.sh

# correlation query 실행
bash 00_infra/run_query_analytics_sql.sh
```

---

## 6. 현재 레이어 경계

`04_query` 는 아래까지만 담당한다.

- Iceberg gold refresh
- Trino query 실행
- validation query 실행

아직 포함하지 않는 범위는 아래다.

- Druid realtime serving
- Druid datasource retention / serving 운영
- Superset dashboard / BI 시각화
- Superset bootstrap

즉 `04_query` 는 **저장 이후의 분석/검증 레이어** 이고,
그 다음은 두 개의 별도 단계로 이어진다.

- `05_serving`: Druid 같은 serving datasource 운영
- `06_visualization`: Superset 같은 dashboard / visualization 구성

여기서 중요한 점은,
`05_serving` 의 Druid 는 **필수 query engine 대체재** 가 아니라,
Trino/Iceberg path 와 별도로 둘 수 있는 **optional realtime serving path** 라는 점이다.
