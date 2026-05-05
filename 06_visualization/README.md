# 06_visualization

이 레이어는 `05_serving` 이 노출한 datasource 또는 `04_query` 의 query 결과를
**사람이 보는 화면과 대시보드 형태로 구성하는 역할** 을 한다.

현재 기준으로 이 레이어에 속하는 책임은 아래와 같다.

1. dashboard bootstrap
2. dataset / chart / dashboard 구성
3. visualization refresh / viewing experience 설정

## 현재 포함 자산

### 1. local Superset runtime

- `superset/docker-compose.yaml`
- `superset/superset.env`
- `superset/requirements-local.txt`
- `superset/superset_config.py`

### 2. bootstrap asset

- `bootstrap/bootstrap_superset_content.py`

즉 이제 `06_visualization` 은 README placeholder 가 아니라,
**standalone Superset runtime + bootstrap script** 까지 갖춘 실제 레이어다.

즉 `06_visualization` 은 serving datasource 를 직접 운영하는 단계가 아니라,
**그 위에 사람이 보는 시각화 표면을 만드는 단계** 다.

## datasource path

현재 `06_visualization` 은 아래 두 datasource path 를 모두 지원한다.

1. Trino path
   - `trino://trino@host.docker.internal:8080/hive/market`
   - dataset: `market.market_bar_1m`
2. Druid path
   - `druid://host.docker.internal:8082/druid/v2/sql`
   - dataset: `druid.market_bar_1m`

즉 Superset 은 Trino/Iceberg direct path 와 Druid serving path 둘 다 붙을 수 있다.

## 실행 명령

```bash
# local Superset 실행
bash 00_infra/run_visualization_local_up.sh

# Trino datasource bootstrap
bash 00_infra/run_visualization_bootstrap_trino.sh

# Druid datasource bootstrap
bash 00_infra/run_visualization_bootstrap_druid.sh

# local Superset 종료
bash 00_infra/run_visualization_local_down.sh
```

기본 login:

- URL: `http://localhost:8088`
- ID: `admin`
- PW: `admin`

### 현재 local bootstrap 확인 사항

local Superset runtime 자체는 정상 기동한다.

- `http://localhost:8088/health` -> `OK`
- Trino / Druid driver(`trino`, `pydruid`) 설치 후 bootstrap script 실행 가능

다만 datasource bootstrap 은 현재 아래 caveat 가 있다.

1. Trino path
   - bootstrap 전에 `hive.market.market_bar_1m` 이 Trino 에서 queryable 해야 한다.
   - 즉 hive-metastore 와 `03_storage -> 04_query` path 가 먼저 살아 있어야 한다.
2. Druid path
   - Druid datasource supervisor 는 RUNNING 이지만,
     실제 queryable datasource row 가 생긴 뒤 bootstrap 하는 것이 안정적이다.
   - 즉 `curated.market.bar.1m.v1` 가 Druid datasource `market_bar_1m` 로 실제 ingest 된 뒤 실행해야 한다.

즉 `06_visualization` 은 **runtime / bootstrap 구조는 완성** 됐고,
bootstrap 은 datasource별 prerequisite 를 만족할 때 실행하면 된다.

## 아직 이 레이어에 포함하지 않는 것

- Druid ingestion / retention 제어
- datasource-level realtime serving 운영

그 부분은 `05_serving` 이 담당한다.
