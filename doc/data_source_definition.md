# Data Source Definition

이 문서는 현재 `01_ingestion` 에서 실제로 수집하는 데이터 소스를 비즈니스 관점에서 정리한 문서다.
핵심 목표는 아래 두 가지다.

1. **왜 이 데이터를 수집하는가**를 비즈니스 언어로 설명한다.
2. **Kafka로 들어가는 실제 이벤트 스키마**를 한눈에 볼 수 있게 정리한다.

---

## 1. 현재 수집 중인 데이터 소스 요약

| 구분 | 소스 | 목적 | 수집 방식 | Kafka Topic |
|---|---|---|---|---|
| 시장 데이터 | Finnhub Quote API | 미국 주식 가격 움직임을 실시간에 가깝게 수집 | HTTP polling | `raw.market.finnhub.tick.v1` |
| 거시경제 데이터 | FRED Observations API | 금리/물가/고용 지표를 수집해 시장 데이터와 함께 해석 | Batch 조회 | `raw.macro.fred.release.v1` |

---

## 2. 공통 이벤트 구조

두 소스 모두 외부 API 응답을 그대로 Kafka에 넣지 않고, 아래 공통 envelope 구조로 감싼다.

| 필드명 | 타입 | 의미 |
|---|---|---|
| `event_id` | string | 이벤트 고유 식별자 |
| `source` | string | 이벤트 원천 시스템 식별자 |
| `entity_key` | string | 이벤트 대표 키 (주식은 심볼, 거시는 series_id) |
| `event_ts_ms` | int64 | 원본 데이터 기준 시각 (UTC epoch milliseconds) |
| `ingest_ts_ms` | int64 | 우리 시스템이 적재한 시각 (UTC epoch milliseconds) |
| `schema_version` | string | 이벤트 스키마 버전 |
| `payload` | object | 소스별 상세 데이터 |

### 공통 시간 처리 원칙

- Kafka에 저장되는 표준 시각은 **UTC epoch milliseconds** 다.
- 사람이 로그를 볼 때만 UTC / KST 문자열을 같이 보여준다.
- 즉 **저장 표준은 UTC**, **운영자 확인용 표시는 KST 병행** 이다.

---

## 3. 시장 데이터 소스: Finnhub

### 3.1 비즈니스 목적

Finnhub는 미국 주식의 현재 가격 변화를 빠르게 확인하기 위한 소스다.
이 데이터는 다음과 같은 질문에 답하기 위해 수집한다.

- 특정 종목 가격이 지금 어떻게 움직이고 있는가?
- 거시 지표 발표 이후 가격 반응이 있었는가?
- 이후 Flink에서 1분 bar, 집계, 조인 분석을 만들 수 있는 최소 시장 이벤트는 무엇인가?

현재 단계에서는 **학습과 파이프라인 연결 검증**이 목적이므로,
quote API에서 꼭 필요한 최소 필드만 가져온다.

### 3.2 수집 방식

| 항목 | 값 |
|---|---|
| API | Finnhub Quote API |
| Endpoint | `GET https://finnhub.io/api/v1/quote` |
| 인증 | query param `token=<FINNHUB_API_KEY>` |
| 수집 방식 | HTTP polling |
| 기본 대상 | `AAPL` |
| 기본 Topic | `raw.market.finnhub.tick.v1` |

### 3.3 외부 응답에서 실제 사용하는 필드

Finnhub 응답에는 여러 필드가 있지만 현재는 아래 두 개만 핵심적으로 사용한다.

| 원본 필드 | 의미 | 내부 변환 필드 |
|---|---|---|
| `c` | current price (현재가) | `price` |
| `t` | quote timestamp (seconds) | `event_ts_ms` |

중요한 점은 `t` 가 **polling 시각** 이 아니라 **quote 기준 시각** 이라는 점이다.
그래서 시장이 닫혀 있거나 quote 자체가 갱신되지 않으면,
여러 번 polling 해도 같은 `t` 값이 반복될 수 있다.

### 3.4 내부 정규화 결과

Finnhub 응답은 아래처럼 내부 표준 필드로 바뀐다.

| 필드명 | 타입 | 설명 |
|---|---|---|
| `symbol` | string | 종목 코드 |
| `price` | float | 현재가 |
| `event_ts_ms` | int64 | quote 시각을 ms 로 변환한 값 |
| `size` | int | 현재 구현에서는 quote 1건을 의미하는 고정값 `1` |

### 3.5 Kafka 이벤트 스키마

#### Top-level event

| 필드명 | 타입 | 값 예시 |
|---|---|---|
| `event_id` | string | `7bc0754e-d324-4aa4-8fe4-626d43988851` |
| `source` | string | `finnhub_quote` |
| `entity_key` | string | `AAPL` |
| `event_ts_ms` | int64 | `1777665600000` |
| `ingest_ts_ms` | int64 | `1777681764885` |
| `schema_version` | string | `v1` |
| `payload` | object | 아래 payload 참조 |

#### Payload

| 필드명 | 타입 | 값 예시 | 설명 |
|---|---|---|---|
| `symbol` | string | `AAPL` | 종목 코드 |
| `price` | float | `280.14` | 현재가 |
| `size` | int | `1` | 현재 단계에서는 quote 1건 의미 |

### 3.6 예시 이벤트

```json
{
  "event_id": "7bc0754e-d324-4aa4-8fe4-626d43988851",
  "source": "finnhub_quote",
  "entity_key": "AAPL",
  "event_ts_ms": 1777665600000,
  "ingest_ts_ms": 1777681764885,
  "schema_version": "v1",
  "payload": {
    "symbol": "AAPL",
    "price": 280.14,
    "size": 1
  }
}
```

### 3.7 비즈니스 해석 포인트

- 지금 단계에서 Finnhub 데이터는 **가격 반응을 보는 최소 시장 신호**다.
- 나중에 Flink에서 1분 바를 만들거나 macro와 조인할 때 시장 측 기준 데이터가 된다.
- 현재 quote API 기반이므로 체결량/호가 depth 수준의 정밀 시장 마이크로구조 분석은 아니다.
- `event_ts_ms` 는 quote 기준 시각이라 source가 stale 하면 반복될 수 있고,
  downstream processing 은 필요시 `ingest_ts_ms` 와 함께 event time 을 해석한다.

---

## 4. 거시경제 데이터 소스: FRED

### 4.1 비즈니스 목적

FRED는 시장 가격만 봐서는 알 수 없는 거시 배경을 제공한다.
현재는 시장과 함께 보기 좋은 최소 거시 축 3개만 수집한다.

| Series ID | 이름 | 비즈니스 의미 |
|---|---|---|
| `DFF` | Effective Federal Funds Rate | 연준 정책금리 방향 |
| `CPIAUCSL` | Consumer Price Index | 물가 / 인플레이션 흐름 |
| `UNRATE` | Unemployment Rate | 고용 / 실업 흐름 |

즉, 현재 FRED 데이터는 **금리 / 물가 / 고용**이라는 세 가지 거시 상태를 시장 가격과 함께 보기 위한 목적이다.

### 4.2 수집 방식

| 항목 | 값 |
|---|---|
| API | FRED Series Observations API |
| Endpoint | `GET https://api.stlouisfed.org/fred/series/observations` |
| 인증 | query param `api_key=<FRED_API_KEY>` |
| 수집 방식 | series 별 batch 조회 |
| 기본 series | `DFF,CPIAUCSL,UNRATE` |
| 기본 limit | `1` (series마다 최신 관측값 1개) |
| 기본 Topic | `raw.macro.fred.release.v1` |

### 4.3 외부 응답에서 실제 사용하는 필드

FRED observations 응답에서 현재 구현이 사용하는 필드는 아래와 같다.

| 원본 필드 | 의미 | 내부 변환 필드 |
|---|---|---|
| `date` | 관측 기준일 | `observation_date` |
| `value` | 관측값(문자열) | `value` (float 변환) |
| `realtime_start` | 해당 값의 revision 시작일 | `realtime_start` |
| `realtime_end` | 해당 값의 revision 종료일 | `realtime_end` |

### 4.4 내부 정규화 결과

| 필드명 | 타입 | 설명 |
|---|---|---|
| `series_id` | string | FRED 지표 ID |
| `observation_date` | string (`YYYY-MM-DD`) | 관측 기준일 |
| `value` | float | 실제 수치값 |
| `release_ts_ms` | int64 | 현재 구현에서는 `observation_date` UTC 자정 |
| `realtime_start` | string | revision 시작일 |
| `realtime_end` | string | revision 종료일 |

### 4.5 Kafka 이벤트 스키마

#### Top-level event

| 필드명 | 타입 | 값 예시 |
|---|---|---|
| `event_id` | string | `UNRATE-2024-04-01-1711929600000` |
| `source` | string | `fred_observation` |
| `entity_key` | string | `UNRATE` |
| `event_ts_ms` | int64 | `1711929600000` |
| `ingest_ts_ms` | int64 | `1777682401315` |
| `schema_version` | string | `v1` |
| `payload` | object | 아래 payload 참조 |

#### Payload

| 필드명 | 타입 | 값 예시 | 설명 |
|---|---|---|---|
| `series_id` | string | `UNRATE` | FRED 지표 ID |
| `observation_date` | string | `2024-04-01` | 관측 기준일 |
| `value` | float | `3.8` | 관측값 |
| `release_ts_ms` | int64 | `1711929600000` | 현재 구현의 대표 시각 |
| `realtime_start` | string | `2024-05-03` | revision 시작일 |
| `realtime_end` | string | `2024-05-03` | revision 종료일 |

### 4.6 예시 이벤트

```json
{
  "event_id": "UNRATE-2024-04-01-1711929600000",
  "source": "fred_observation",
  "entity_key": "UNRATE",
  "event_ts_ms": 1711929600000,
  "ingest_ts_ms": 1777682401315,
  "schema_version": "v1",
  "payload": {
    "series_id": "UNRATE",
    "observation_date": "2024-04-01",
    "value": 3.8,
    "release_ts_ms": 1711929600000,
    "realtime_start": "2024-05-03",
    "realtime_end": "2024-05-03"
  }
}
```

### 4.7 비즈니스 해석 포인트

- `DFF`는 시장 할인율/정책 기조를 해석할 때 중요하다.
- `CPIAUCSL`는 인플레이션 압력을 보여준다.
- `UNRATE`는 경기/고용 상태를 보여준다.
- 이 세 지표를 시장 가격과 함께 보면 **“가격이 왜 움직였는가”** 를 더 잘 설명할 수 있다.

---

## 5. 현재 수집 범위에서 제외한 항목

현재 문서는 **실제 외부 데이터 소스**만 다룬다.

- 포함: Finnhub, FRED
- 제외: 테스트용 mock source

즉, 지금 시점의 fresh ingestion 범위는
**시장 가격(Finnhub)** + **거시 상태(FRED)** 를 Kafka raw topic으로 옮기는 것까지다.

---

## 6. 코드 기준 참조 위치

| 용도 | 파일 |
|---|---|
| 전체 ingestion 진입점 / source 선택 / topic 기본값 | `01_ingestion/main.py` |
| Finnhub API 호출 및 응답 정규화 | `01_ingestion/01_finnhub/client.py` |
| Finnhub 이벤트 envelope 정의 | `01_ingestion/01_finnhub/event.py` |
| FRED API 호출 및 응답 정규화 | `01_ingestion/02_fred/client.py` |
| FRED 이벤트 envelope 정의 | `01_ingestion/02_fred/event.py` |
| 로컬 API key / Kafka bootstrap 설정 | `local_configs.cfg` |

이 문서의 스키마와 예시는 위 파일들의 현재 구현을 기준으로 작성되었다.
