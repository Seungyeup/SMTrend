# 05_serving

이 레이어는 `04_query` 이후의 데이터를 **서비스 가능한 상태** 로 노출하는 역할을 한다.

현재 기준으로 이 레이어에 속하는 책임은 아래와 같다.

1. realtime serving datasource 구성
2. serving-side ingestion / retention 운영
3. query 결과를 사용자-facing serving store 로 연결

## 왜 `05_serving` 이 필요한가

현재 repo 는 이미 아래 경로를 갖고 있다.

- `03_storage`: MinIO silver parquet + external / Iceberg gold table 정의
- `04_query`: Iceberg gold incremental refresh + validation + analytics query
- `06_visualization`: Superset dataset / chart / dashboard 구성

즉 Superset 이 Trino/Iceberg 를 직접 조회하는 경로는 이미 가능하다.

그런데 realtime serving 관점에서는 별도 serving datasource 가 유리할 수 있다.
이 프로젝트에서 그 역할을 맡는 것이 Druid 다.

즉 `05_serving` 은 **Trino/Iceberg query path 를 대체하는 단계** 가 아니라,
**low-latency serving path 를 추가하는 단계** 다.

## 언제 Druid 가 좋은가

이 프로젝트에서 Druid 는 아래 상황에 유리하다.

- `curated.market.bar.1m.v1` 를 거의 바로 UI 에 반영해야 할 때
- minute-bar time series / latest-value query 를 반복적으로 빠르게 보여줘야 할 때
- serving datasource 와 batch/query path 를 분리하고 싶을 때

반대로,
Superset 이 Trino/Iceberg 를 몇 초 내로 조회하면 충분하고,
serving latency SLA 가 빡빡하지 않다면 Druid 는 필수가 아니다.

즉 현재 repo 기준에서 Druid 는 **optional serving path** 다.

## 현재 포함 자산

### 1. Druid ingestion spec

- `01_druid_specs/01_market_bar_1m_kafka.json.tmpl`

현재 spec 은 아래 가정을 가진다.

- source topic: `curated.market.bar.1m.v1`
- datasource: `market_bar_1m`
- timestamp column: `window_start`
- `queryGranularity = MINUTE`
- `segmentGranularity = HOUR`
- `rollup = false`

즉 1분 bar row 를 serving datasource 에 그대로 유지하는 방향이다.

### 2. 운영 스크립트

- `02_operations/request_druid_ingestion.sh`
  - Druid supervisor 생성 요청
- `02_operations/apply_druid_retention.sh`
  - datasource retention rule 적용
- `02_operations/check_druid_status.sh`
  - supervisor status 확인

### 3. 00_infra wrapper

- `00_infra/run_serving_ingestion.sh`
- `00_infra/run_serving_retention.sh`
- `00_infra/run_serving_status.sh`

즉 `05_serving` 은 이제 README placeholder 가 아니라,
**Druid spec + operation script + infra wrapper** 까지 갖춘 실제 레이어다.

## 로컬 실행 범위와 한계

현재 repo 의 기본 `00_infra/docker-compose.yaml` 은
Kafka / Flink / MinIO / Hive / Trino 까지만 포함한다.

즉 Druid full cluster 는 기본 local compose 에 들어 있지 않다.

이건 의도적이다.

- Druid 는 ZooKeeper + Broker + Historical + MiddleManager + Coordinator + Router 등
  runtime surface 가 커서 기본 dev stack 을 너무 무겁게 만든다.
- 따라서 현재 repo 는 **serving asset / script / doc 은 먼저 완성** 하고,
  Druid runtime 자체는 외부 endpoint 에 붙는 방식으로 둔다.

다만 local 확인이 필요할 때를 위해,
이제는 **별도 overlay compose** 로 공식 Docker 가이드에 가까운 full local Druid 경로를 올릴 수 있다.

- base stack: `00_infra/docker-compose.yaml`
- Druid overlay: `00_infra/docker-compose.druid.yaml`
- Druid env: `00_infra/druid.environment`

이 overlay 는 Apache Druid 공식 Docker 가이드의 service set 을 따른다.

- `druid-postgres`
- `druid-zookeeper`
- `druid-coordinator`
- `druid-broker`
- `druid-historical`
- `druid-middlemanager`
- `druid-router`

즉 기본 stack 위에 **full local Druid serving cluster** 를 opt-in 으로 붙이는 방식이다.

즉 기본 compose 를 무겁게 만들지 않으면서,
필요할 때만 Druid local path 를 켤 수 있게 한 구조다.

그래서 아래 환경변수를 통해 외부 또는 별도 Druid 환경을 대상으로 사용한다.

- `DRUID_API_URL`
- `DRUID_KAFKA_BOOTSTRAP_SERVERS`
- `DRUID_DATASOURCE`
- `DRUID_RETENTION_DAYS`

로컬 overlay 를 올렸을 때 기본값은 아래처럼 쓰면 된다.

- `DRUID_API_URL=http://localhost:8888`
- `DRUID_KAFKA_BOOTSTRAP_SERVERS=kafka:9094` (overlay container 기준)

## local overlay 실행

```bash
# base infra + druid overlay 실행
bash 00_infra/run_serving_local_up.sh

# Druid supervisor 생성
bash 00_infra/run_serving_ingestion.sh

# retention rule 적용
bash 00_infra/run_serving_retention.sh

# supervisor status 확인
bash 00_infra/run_serving_status.sh

# overlay 종료
bash 00_infra/run_serving_local_down.sh
```

이 local overlay 는 공식 Docker guide 쪽 구조를 따르는 local serving 경로다.

- Druid metadata store: local postgres (`druid-postgres`)
- Druid coordination: local zookeeper (`druid-zookeeper`)
- Druid broker/router API: `http://localhost:8082`, `http://localhost:8888`
- 기본 Trino/Iceberg path 를 대체하지 않음
- Superset 이 Druid 를 직접 조회해보는 serving 확인용에 적합

### 현재 확인된 local runtime 주의사항

이제 local overlay 는 공식 Docker guide 스타일 multi-service cluster 로 전환했다.
즉 이전 nano quickstart blocker 에 의존하지 않는다.

다만 전체 서비스 수가 늘어나므로,
실행 시 메모리/기동 시간이 base stack 보다 더 무겁다는 점은 감안해야 한다.

## 아직 이 레이어에 포함하지 않는 것

- Superset dashboard bootstrap
- chart / dataset / dashboard 시각화 구성

그 부분은 다음 단계인 `06_visualization` 이 담당한다.
