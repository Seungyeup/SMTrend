# Visualization Definition

이 문서는 `06_visualization` 레이어가 어떤 방식으로 Superset dashboard / dataset / chart 를 구성하는지 정리한 문서다.

현재 범위는 아래 3가지다.

1. local Superset runtime
2. Trino datasource bootstrap
3. Druid datasource bootstrap

---

## 1. 왜 `06_visualization` 이 따로 필요한가

`05_serving` 까지는 datasource 를 운영하는 단계다.

- `04_query` -> Trino/Iceberg query path
- `05_serving` -> Druid serving datasource path

하지만 이 둘을 사람이 보는 dashboard / chart / dataset 으로 만드는 일은 별도 단계가 필요하다.

즉 `06_visualization` 은 **데이터를 만든다/서빙한다** 가 아니라,
**그 datasource 를 사람이 보는 분석 화면으로 구성하는 단계** 다.

---

## 2. 현재 local Superset 경로

현재 local visualization runtime 은 아래 파일로 제공된다.

| 경로 | 역할 |
|---|---|
| `06_visualization/superset/docker-compose.yaml` | standalone local Superset runtime |
| `06_visualization/superset/superset.env` | Superset admin / secret 설정 |
| `06_visualization/superset/requirements-local.txt` | `trino`, `pydruid` driver 설치 |
| `06_visualization/superset/superset_config.py` | 기본 Superset runtime 설정 |
| `06_visualization/bootstrap/bootstrap_superset_content.py` | datasource / dataset / chart / dashboard bootstrap |

중요한 점은,
Superset 은 `00_infra` main compose 안에 넣지 않고 **standalone compose** 로 분리했다는 점이다.
이렇게 해야 base infra 와 serving/query stack 을 지나치게 무겁게 만들지 않는다.

---

## 3. Trino datasource path

기본 visualization path 는 Trino datasource 다.

- DB URI: `trino://trino@host.docker.internal:8080/hive/market`
- dataset: `market.market_bar_1m`
- time column: `bucket_1m_utc`

즉 기본 dashboard 는
`03_storage -> 04_query -> Trino/Iceberg -> Superset`
경로를 따른다.

---

## 4. Druid datasource path

선택적으로 Druid datasource path 도 bootstrap 할 수 있다.

- DB URI: `druid://host.docker.internal:8082/druid/v2/sql`
- dataset: `druid.market_bar_1m`
- time column: `__time`

즉 serving path 는
`05_serving(Druid) -> Superset`
경로를 따른다.

중요한 점은,
현재 repo 는 **Trino path 와 Druid path 를 모두 허용** 하지만,
둘 중 하나만 필수라고 가정하지 않는다.

---

## 5. 실행 명령

```bash
# local Superset 실행
bash 00_infra/run_visualization_local_up.sh

# Trino datasource 기준 dashboard bootstrap
bash 00_infra/run_visualization_bootstrap_trino.sh

# Druid datasource 기준 dashboard bootstrap
bash 00_infra/run_visualization_bootstrap_druid.sh

# local Superset 종료
bash 00_infra/run_visualization_local_down.sh
```

기본 login 은 아래와 같다.

- URL: `http://localhost:8088`
- ID: `admin`
- PW: `admin`

### 현재 local bootstrap caveat

local Superset runtime 은 실제로 정상 기동한다.

- health endpoint: `http://localhost:8088/health`
- installed drivers: `trino`, `pydruid`

다만 datasource bootstrap 단계는 아래 caveat 가 있다.

1. Trino datasource bootstrap
   - Superset runtime 은 정상 기동하지만,
     bootstrap 전 `hive.market.market_bar_1m` 이 Trino 에서 queryable 해야 한다.
   - 즉 hive-metastore 와 `03_storage -> 04_query` 경로가 먼저 건강해야 한다.
2. Druid datasource bootstrap
   - supervisor 는 RUNNING 이어도,
     `market_bar_1m` datasource 가 실제 queryable row 를 가진 뒤 bootstrap 하는 것이 안정적
   - 즉 `05_serving` supervisor 생성만으로는 충분하지 않고,
     `curated.market.bar.1m.v1` 에서 Druid 로 실제 row 가 들어간 뒤 bootstrap 해야 한다.

즉 현재 `06_visualization` 의 상태는
**Superset local runtime + bootstrap framework 는 완성**, 
**datasource bootstrap 은 prerequisite 를 만족할 때 실행되는 구조** 다.

---

## 6. 현재 레이어 경계

`06_visualization` 은 아래까지만 담당한다.

- datasource 등록
- dataset metadata 동기화
- chart / dashboard bootstrap
- refresh frequency 같은 viewing experience 설정

포함하지 않는 범위는 아래다.

- Kafka/Flink processing
- MinIO/Iceberg storage
- Druid ingestion / retention 운영

즉 `06_visualization` 은 **최종 사용자 화면 레이어** 다.
