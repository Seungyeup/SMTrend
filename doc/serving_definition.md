# Serving Definition

이 문서는 `05_serving` 레이어가 왜 필요한지, 그리고 이 프로젝트에서 Druid 가 어떤 조건에서 유용한지 정리한 문서다.

현재 범위는 아래 3가지다.

1. Druid realtime ingestion spec
2. Druid supervisor / retention 운영 스크립트
3. serving layer 와 query / visualization layer 의 경계 설명

---

## 1. 왜 `05_serving` 이 따로 필요한가

`03_storage` 와 `04_query` 는 아래 역할을 한다.

- `03_storage`: silver parquet, external table, Iceberg gold table 골격 생성
- `04_query`: Iceberg gold incremental refresh, validation, analytics query

이 경로는 **저장과 분석** 에는 적합하지만,
실시간 대시보드 serving 용으로는 별도 고려가 필요하다.

이유는 아래와 같다.

- Trino + Iceberg 는 object storage 위의 파일과 metadata 를 읽어 query planning / scan 을 수행한다.
- freshness 를 높이려고 write 주기를 촘촘히 가져가면 small files 가 많아질 수 있다.
- 따라서 realtime dashboard serving 에서는 low-latency serving datasource 가 따로 유리할 수 있다.

즉 `05_serving` 은 **저장된 데이터를 더 잘 분석하기 위한 단계** 가 아니라,
**사람이 계속 보는 화면이나 low-latency 소비처를 위해 serving datasource 를 유지하는 단계** 다.

---

## 2. 이 프로젝트에서 Druid 가 맡는 역할

현재 `05_serving` 은 Druid 를 아래 역할로 본다.

| 역할 | 설명 |
|---|---|
| Realtime ingest | `curated.market.bar.1m.v1` 를 Kafka 에서 직접 ingest |
| Serving datasource | `market_bar_1m` datasource 로 minute-bar 조회 제공 |
| Retention control | datasource 보관 주기를 별도로 운영 |

핵심은,
`05_serving` 의 Druid 는 **query layer 를 대체하는 것** 이 아니라,
**realtime serving path 를 추가로 제공하는 것** 이라는 점이다.

---

## 3. 언제 Druid 가 유리한가

이 프로젝트 기준으로 Druid 가 유리한 경우는 아래와 같다.

- Kafka 에 들어온 `curated.market.bar.1m.v1` 를 거의 바로 대시보드에 반영해야 할 때
- time-series 집계 / latest-value query 를 반복적으로 빠르게 보여줘야 할 때
- serving datasource 를 query path 와 분리해서 운영하고 싶을 때

즉 Druid 는 여기서 **realtime OLAP serving store** 로 이해하면 된다.

---

## 4. 언제 Druid 가 없어도 되는가

이 프로젝트는 Druid 가 없어도 아래 경로가 이미 가능하다.

`03_storage -> 04_query -> Trino/Iceberg -> 06_visualization(Superset)`

즉 아래 조건이면 Druid 는 필수가 아니다.

- Superset 이 Trino/Iceberg 를 몇 초 내로 조회하면 충분할 때
- dashboard 동시성이 아주 높지 않을 때
- realtime serving 전용 datastore 를 따로 운영하고 싶지 않을 때

그래서 현재 repo 기준으로 Druid 는 **optional serving path** 다.

---

## 5. 왜 Druid 이고, Trino/Iceberg 와 다른가

현재 repo 에서 Druid 는 아래처럼 가정된다.

- `05_serving`: Druid serving datasource 운영
- `06_visualization`: Superset dashboard / chart 구성

그리고 Superset 은 현재 기본적으로 Trino datasource 를 사용하도록 bootstrap 되어 있다.

즉 현재 구조는 아래 두 경로를 모두 허용한다.

1. `Trino/Iceberg -> Superset`
2. `Druid -> Superset`

차이는 목적이다.

- `Trino/Iceberg`: 저장/분석/query 유연성
- `Druid`: realtime serving latency

---

## 6. 현재 포함 자산

`05_serving` 에 현재 포함한 실자산은 아래와 같다.

| 경로 | 역할 |
|---|---|
| `05_serving/01_druid_specs/01_market_bar_1m_kafka.json.tmpl` | Druid realtime ingestion spec template |
| `05_serving/02_operations/request_druid_ingestion.sh` | supervisor 생성 요청 |
| `05_serving/02_operations/apply_druid_retention.sh` | retention rule 적용 |
| `05_serving/02_operations/check_druid_status.sh` | supervisor status 확인 |

---

## 7. 실행 명령

```bash
# Druid supervisor 생성
bash 00_infra/run_serving_ingestion.sh

# Druid retention rule 적용
bash 00_infra/run_serving_retention.sh

# Druid supervisor status 확인
bash 00_infra/run_serving_status.sh
```

중요한 점은,
현재 repo 의 기본 local compose 는 Druid full cluster 를 포함하지 않는다.
즉 이 명령들은 **외부 또는 별도 Druid endpoint** 를 대상으로 동작한다.

`DRUID_API_URL` 과 `DRUID_KAFKA_BOOTSTRAP_SERVERS` 를 환경변수로 조정해 사용한다.

---

## 8. local Druid overlay

이 repo 는 기본 compose 를 무겁게 만들지 않기 위해,
Druid 를 main `docker-compose.yaml` 에 상시 포함하지 않는다.

대신 아래 overlay 파일을 둔다.

- `00_infra/docker-compose.druid.yaml`

이 overlay 는 Apache Druid 공식 Docker guide 의 service set 을 따르는
**full local serving path** 다.

현재 포함 서비스는 아래와 같다.

- `druid-postgres`
- `druid-zookeeper`
- `druid-coordinator`
- `druid-broker`
- `druid-historical`
- `druid-middlemanager`
- `druid-router`

실행은 아래처럼 한다.

```bash
bash 00_infra/run_serving_local_up.sh
```

이후 serving command 는 아래 순서로 사용한다.

```bash
bash 00_infra/run_serving_ingestion.sh
bash 00_infra/run_serving_retention.sh
bash 00_infra/run_serving_status.sh
```

종료는 아래와 같다.

```bash
bash 00_infra/run_serving_local_down.sh
```

이 local overlay 는 production full cluster 와 동일하진 않지만,
공식 Docker guide 에 가까운 local dev cluster 이고,
**Superset 이 Druid datasource 경로를 실제로 테스트할 수 있게 하는 local serving path** 로 이해하면 된다.

메모리 여유가 있는 환경에서는 이 경로를 우선 사용하고,
필요 시 Druid query endpoint(`:8082`) 또는 router(`:8888`) 를 Superset datasource 로 연결하면 된다.
