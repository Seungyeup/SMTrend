# Processing Definition

이 문서는 `02_processing` 레이어가 어떤 비즈니스 출력 데이터를 만드는지 정리한 문서다.

현재 starter 범위는 아래 3가지 출력이다.

1. `curated.market.bar.1m.v1`
2. `state.macro.latest.v1`
3. `analytics.market_macro.1m.v1`

---

## 1. Market Processing

### 입력

- Source topic: `raw.market.finnhub.tick.v1`

### 출력

- Sink topic: `curated.market.bar.1m.v1`

### 비즈니스 의미

개별 quote 이벤트를 그대로 쓰지 않고,
종목별 1분 구간의 시가/고가/저가/종가/volume/tick_count 로 묶는다.
즉 downstream 분석이 보기 쉬운 최소 시장 bar 데이터다.

`curated_market_bar_1m` 의 핵심 의미는
"아주 잘게 들어오는 tick 을 그대로 보지 않고,
**1분 단위의 시장 상태 요약본** 으로 본다" 는 데 있다.

이 테이블이 있으면 아래 질문에 답하기 쉬워진다.

- 그 1분 동안 가격이 어디서 시작해서 어디서 끝났는가?
- 중간에 얼마나 위아래로 흔들렸는가?
- 거래 강도는 어느 정도였는가? (`volume`, `tick_count`)

즉 `curated_market_bar_1m` 는 단순 중간 산출물이 아니라,
이후 macro 와 결합하거나 analytics 를 만들 때 쓰는 **시장 측 기준 단위** 다.

### 출력 스키마

| 필드명 | 타입 | 설명 |
|---|---|---|
| `symbol` | string | 종목 코드 |
| `window_start` | timestamp_ltz(3) | 1분 bar 시작 시각 |
| `window_end` | timestamp_ltz(3) | 1분 bar 종료 시각 |
| `open_price` | double | 첫 가격 |
| `high_price` | double | 최고가 |
| `low_price` | double | 최저가 |
| `close_price` | double | 마지막 가격 |
| `volume` | bigint | volume 합 |
| `tick_count` | bigint | quote 건수 |

---

## 2. Macro Processing

### 입력

- Source topic: `raw.macro.fred.release.v1`

### 출력

- Sink topic: `state.macro.latest.v1`

### 비즈니스 의미

각 거시 지표의 최신 상태를 key-value 형태로 유지한다.
즉 시장 데이터와 조인할 때 "지금 최신 macro 값이 무엇인가"를 바로 꺼내기 위한 상태 레이어다.

### 출력 스키마

| 필드명 | 타입 | 설명 |
|---|---|---|
| `series_id` | string | FRED 지표 ID |
| `macro_value` | double | 최신 관측값 |
| `release_ts_ms` | bigint | 해당 값의 대표 시각 |

---

## 3. Analytics Processing

### 입력

- Source topic: `curated.market.bar.1m.v1`
- Source topic: `state.macro.latest.v1`

### 출력

- Sink topic: `analytics.market_macro.1m.v1`

### 비즈니스 의미

시장 1분 bar 와 최신 거시 상태를 결합한 starter analytics 데이터다.
현재는 단순화를 위해 `DFF` 하나만 먼저 붙인다.
즉 "현재 금리 상태 하에서 이 1분 bar 가 어떻게 형성됐는가"를 보는 최소 결합 뷰다.

여기서 "결합" 이라는 말은 추상적인 의미가 아니라,
실제 SQL 에서 아래 로직으로 구현되어 있다.

1. `curated_market_bar_1m` 에서
   `symbol`, `window_start`, `close_price`, `volume`, `tick_count` 를 읽는다.
2. 각 row 에 고정값 `series_id = 'DFF'` 를 붙여
   `curated_market_bar_1m_with_proc` view 를 만든다.
3. 이 view 를 `state_macro_latest` 와 `series_id` 기준으로 조인한다.
4. 결과 row 에 `macro_value`, `release_ts_ms` 를 붙인다.
5. `window_start - release_ts_ms` 를 분 단위로 계산해서
   `macro_age_minutes` 로 저장한다.

즉 현재 starter 구현은
"모든 시장 1분 bar 에 대해, **가장 최신 DFF 상태** 를 붙인다" 는 구조다.

### 결합 로직의 경제적 의미

`DFF` 는 Effective Federal Funds Rate 로,
문서의 다른 곳에서도 설명했듯 **연준 정책금리 방향** 을 대표하는 가장 기본적인 거시 신호다.

그래서 이 결합은 단순히 시장 데이터 옆에 숫자 하나를 더 붙이는 게 아니라,
아래 같은 질문을 가능하게 만든다.

- 지금 시장 bar 가 형성될 때 기준 금리 상태는 무엇이었는가?
- 금리 수준이 높거나 낮은 국면에서 가격 움직임과 거래 강도가 어떻게 달랐는가?
- 현재 bar 가 참조한 macro 값은 얼마나 최근 값인가? (`macro_age_minutes`)

즉 `analytics_market_macro_1m` 의 경제적 의미는
**시장 1분 움직임을 거시 배경 없이 보지 않고,
현재 정책금리 상태라는 해석 축을 함께 붙여 본다** 는 데 있다.

다만 현재 구현은 starter 버전이므로,
"그 시점에 유효했던 모든 macro 상태를 정교하게 시계열 정합성 있게 붙인다" 수준은 아니다.
지금은 `DFF` 최신 상태 하나를 붙여서
시장 움직임을 macro 맥락에서 읽을 수 있게 하는 최소 버전이다.

### 출력 스키마

| 필드명 | 타입 | 설명 |
|---|---|---|
| `symbol` | string | 종목 코드 |
| `window_start` | timestamp_ltz(3) | 1분 bar 시작 시각 |
| `close_price` | double | 종가 |
| `volume` | bigint | volume |
| `tick_count` | bigint | tick 개수 |
| `series_id` | string | 현재는 `DFF` |
| `macro_value` | double | 최신 거시값 |
| `release_ts_ms` | bigint | macro 시각 |
| `macro_age_minutes` | bigint | 시장 bar 시각 대비 macro 값 age |

---

## 4. 실행 순서

`02_processing` 은 아래 순서로 실행하는 것을 기준으로 파일이 나뉘어 있다.

1. `01_common/01_source_and_sink_tables.sql`
2. `02_market/02_market_bar_1m.sql`
3. `03_macro/03_macro_latest_state.sql`
4. `04_analytics/04_market_macro_enriched.sql`

로컬 실행은 `bash 00_infra/run_processing_sql.sh` 로 처리한다.

---

## 5. Flink 테이블 기준 실제 흐름

현재 processing 레이어는 단순히 "raw topic 을 읽고 output topic 을 만든다" 수준이 아니라,
아래처럼 **명시적인 Flink source/sink table** 을 먼저 정의한 뒤 SQL 을 순서대로 태운다.

### 5.1 source / sink table 정의

`01_common/01_source_and_sink_tables.sql` 에서 아래 테이블을 만든다.

| 구분 | Flink 테이블명 | 연결 Kafka topic | 역할 |
|---|---|---|---|
| Source | `raw_market_tick` | `raw.market.finnhub.tick.v1` | Finnhub raw tick 읽기 |
| Source | `raw_macro_release` | `raw.macro.fred.release.v1` | FRED raw release 읽기 |
| Sink | `curated_market_bar_1m` | `curated.market.bar.1m.v1` | Finnhub raw tick 을 종목별 1분 OHLC/volume/tick_count bar 로 가공한 결과 쓰기 |
| Sink | `state_macro_latest` | `state.macro.latest.v1` | 각 `series_id` 의 최신 macro 값을 상태 형태로 유지한 결과 쓰기 |
| Sink | `analytics_market_macro_1m` | `analytics.market_macro.1m.v1` | 시장 1분 bar 에 최신 macro 상태를 붙인 분석 결과 쓰기 |

즉 Kafka topic 과 SQL 로직 사이에 실제로는 이 Flink 테이블 계층이 하나 더 있다.

특히 sink table 이름은 아래처럼 읽으면 된다.

- `curated_market_bar_1m`: raw tick 을 바로 쓰지 않고 **1분 단위로 정리된 시장 bar 결과**
- `state_macro_latest`: macro 원본 전체 이력이 아니라 **지금 시점 최신 상태**
- `analytics_market_macro_1m`: 시장 데이터와 macro 상태를 붙여 만든 **분석용 결합 결과**

### 5.2 SQL 단계별 연결

1. `02_market/02_market_bar_1m.sql`
   - `raw_market_tick` 을 읽는다.
   - 여기서 `event_time` 은 `GREATEST(event_ts_ms, ingest_ts_ms)` 기준이라,
     source quote timestamp 가 stale 해도 watermark 가 멈추지 않게 한다.
   - `market_tick_1m_windowed`, `market_tick_1m_agg`, `market_tick_1m_open`, `market_tick_1m_close`
     임시 view 를 만든다.
   - 최종 결과를 `curated_market_bar_1m` 으로 `INSERT` 한다.

2. `03_macro/03_macro_latest_state.sql`
   - `raw_macro_release` 를 읽는다.
   - 최신 macro 값을 `state_macro_latest` 로 `INSERT` 한다.

3. `04_analytics/04_market_macro_enriched.sql`
   - `curated_market_bar_1m` 을 읽어 `curated_market_bar_1m_with_proc` view 를 만든다.
   - 모든 row 에 `series_id = 'DFF'` 를 붙인다.
   - `state_macro_latest` 와 `series_id` 기준으로 조인한다.
   - `window_start - release_ts_ms` 를 분 단위로 계산해 `macro_age_minutes` 를 만든다.
   - 결과를 `analytics_market_macro_1m` 으로 `INSERT` 한다.

### 5.3 현재 구현 수준에 대한 판단

현재 기준으로 processing 레이어는 starter 범위에서 **알맞게 구현되어 있다**.
이유는 다음과 같다.

- raw topic 을 읽는 source table 이 실제로 정의되어 있다.
- curated / state / analytics output 을 쓰는 sink table 도 실제로 정의되어 있다.
- market 집계, macro latest state, analytics join 이 각각 별도 SQL 로 분리되어 있다.
- `run_processing_sql.sh` 가 이 순서를 그대로 실행한다.

즉 부족했던 건 processing SQL 자체보다,
이 **Flink table 계층과 실행 순서가 문서에 충분히 드러나지 않았던 점** 이다.

---

## 6. 03_storage 로 이어지는 데이터

`02_processing` 의 세 output 중,
현재 `03_storage` 가 직접 durable storage 로 내리는 대상은 아래 두 가지다.

- `curated.market.bar.1m.v1` -> `market_bar_1m` silver parquet
- `raw.macro.fred.release.v1` -> `macro_release` silver parquet

즉 `03_storage` 는 processing 결과를 다시 가공해서 새로운 Kafka topic 을 만드는 단계가 아니라,
**Kafka/Flink 출력 데이터를 MinIO(S3A) parquet 와 warehouse table 정의로 옮기는 단계** 다.

자세한 저장 정의는 `doc/storage_definition.md` 에서 다룬다.

그 다음 단계인 `04_query` 는 이 silver/external/gold table 정의를 실제 데이터 refresh 와 query 실행으로 이어간다.
