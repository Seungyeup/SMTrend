# 02_processing

이 레이어는 `01_ingestion` 이 Kafka raw topic으로 적재한 이벤트를 읽어서,
비즈니스가 바로 사용할 수 있는 가공 데이터로 바꾸는 역할을 한다.

현재 starter 범위는 아래 3가지 출력이다.

1. `market/`
   - Finnhub raw tick -> 1분 market bar
2. `macro/`
   - FRED raw observation -> 최신 macro state
3. `analytics/`
   - 시장 1분 bar + macro latest state 조인

## 실행 순서

아래 순서로 실행하는 것을 기준으로 파일을 나눴다.

1. `01_common/01_source_and_sink_tables.sql`
2. `02_market/02_market_bar_1m.sql`
3. `03_macro/03_macro_latest_state.sql`
4. `04_analytics/04_market_macro_enriched.sql`

공통 source/sink 테이블 정의는 `01_common/01_source_and_sink_tables.sql` 에 있다.

## 현재 가정

- Kafka bootstrap server: `kafka:9094` (docker compose 내부 통신 기준)
- 처리 엔진: Flink SQL
- 현재 analytics 조인은 starter 버전이라 `DFF` 하나만 붙인다.

즉, 지금 단계의 목적은 모든 것을 완성하는 것이 아니라,
`raw -> curated/state -> analytics` 흐름을 명확히 만드는 것이다.
