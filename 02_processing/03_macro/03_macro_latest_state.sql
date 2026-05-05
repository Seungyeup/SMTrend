-- raw.macro.fred.release.v1 -> state.macro.latest.v1
--
-- 목표:
-- - 각 series_id 에 대해 최신 macro 값을 상태 topic 으로 유지
-- - 이후 market 데이터와 조인할 때 latest state 로 사용

INSERT INTO state_macro_latest
SELECT
  payload.series_id AS series_id,
  payload.`value` AS macro_value,
  payload.release_ts_ms AS release_ts_ms
FROM raw_macro_release;
